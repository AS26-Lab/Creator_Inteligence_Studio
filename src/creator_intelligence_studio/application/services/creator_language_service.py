"""Servicio principal para Creator Language Analysis."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, median
from uuid import uuid4

from creator_intelligence_studio.domain.analytics.repositories import AnalyticsRepository
from creator_intelligence_studio.domain.creator_language.analysis_types import (
    CreatorLanguageCorpusSelection,
    CreatorLanguageProfileComparison,
    CreatorLanguageQueryFilters,
    CreatorLanguageRetrievalResult,
)
from creator_intelligence_studio.domain.creator_language.entities import (
    CreatorLanguageAnalysisRun,
    CreatorLanguageCandidate,
    CreatorLanguageCorpus,
    CreatorLanguageCorpusSource,
    CreatorLanguageMetric,
    CreatorLanguagePattern,
    CreatorLanguagePatternEvidence,
    CreatorLanguageProfileSnapshot,
    CreatorNarrativeProfile,
)
from creator_intelligence_studio.domain.creator_language.errors import (
    CreatorLanguageNotFoundError,
    CreatorLanguageStateError,
    CreatorLanguageValidationError,
)
from creator_intelligence_studio.domain.creator_language.repositories import CreatorLanguageRepository
from creator_intelligence_studio.domain.creator_language.services import (
    build_creator_language_fingerprint,
    build_narrative_profile_fingerprint,
    build_source_snapshot_payload,
)
from creator_intelligence_studio.domain.creator_language.value_objects import (
    CreatorLanguageAnalysisRunStatus,
    CreatorLanguageCandidateReviewDecision,
    CreatorLanguageCandidateStatus,
    CreatorLanguageConfidenceLevel,
    CreatorLanguageCorpusSourceIncludeStatus,
    CreatorLanguageCorpusStatus,
    CreatorLanguagePatternStatus,
    CreatorLanguagePatternType,
    CreatorLanguageScope,
    CreatorLanguageSourceType,
    CreatorLanguageTargetMemoryType,
)
from creator_intelligence_studio.infrastructure.creator_language import (
    analyze_discourse_markers,
    analyze_filler_words,
    analyze_narrative_structure,
    analyze_pause_patterns,
    analyze_phrase_frequency,
    analyze_sentence_style,
    analyze_vocabulary,
    build_language_profile_summary,
    generate_language_candidates,
    normalize_language_text,
    segment_sentences,
    tokenize_language_text,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import SQLiteCreatorMemoryRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_subtitle_repository import SQLiteSubtitleRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback):
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return value if value is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _sanitize_csv(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] in "=+-@" and not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
        return "'" + value
    return value


@dataclass(frozen=True, slots=True)
class CreatorLanguageAnalysisDetail:
    run: CreatorLanguageAnalysisRun
    corpus: CreatorLanguageCorpus
    sources: tuple[CreatorLanguageCorpusSource, ...]
    metrics: tuple[CreatorLanguageMetric, ...]
    patterns: tuple[CreatorLanguagePattern, ...]
    profile: CreatorNarrativeProfile
    candidates: tuple[CreatorLanguageCandidate, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "corpus": self.corpus.to_dict(),
            "sources": [item.to_dict() for item in self.sources],
            "metrics": [item.to_dict() for item in self.metrics],
            "patterns": [item.to_dict() for item in self.patterns],
            "profile": self.profile.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageProfileDetail:
    profile: CreatorNarrativeProfile | None
    corpora: tuple[CreatorLanguageCorpus, ...]
    sources: tuple[CreatorLanguageCorpusSource, ...]
    metrics: tuple[CreatorLanguageMetric, ...]
    patterns: tuple[CreatorLanguagePattern, ...]
    candidates: tuple[CreatorLanguageCandidate, ...]
    snapshots: tuple[CreatorLanguageProfileSnapshot, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.to_dict() if self.profile else None,
            "corpora": [item.to_dict() for item in self.corpora],
            "sources": [item.to_dict() for item in self.sources],
            "metrics": [item.to_dict() for item in self.metrics],
            "patterns": [item.to_dict() for item in self.patterns],
            "candidates": [item.to_dict() for item in self.candidates],
            "snapshots": [item.to_dict() for item in self.snapshots],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageExportResult:
    creator_id: str
    format: str
    path: str
    rows_written: int
    created_at: str
    summary: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "format": self.format,
            "path": self.path,
            "rows_written": self.rows_written,
            "created_at": self.created_at,
            "summary": self.summary,
        }


class CreatorLanguageService:
    ANALYSIS_VERSION = "v1"

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: CreatorLanguageRepository,
        database: SQLiteDatabase,
        transcription_repository: SQLiteTranscriptionRepository | None = None,
        subtitle_repository: SQLiteSubtitleRepository | None = None,
        analytics_repository: SQLiteAnalyticsRepository | None = None,
        creator_memory_service: object | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.transcription_repository = transcription_repository
        self.subtitle_repository = subtitle_repository
        self.analytics_repository = analytics_repository
        self.creator_memory_service = creator_memory_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_language")
        self._exports_root = self.paths.data_directory / "creator_language" / "exports"
        self._ensure_exports_root()

    def _ensure_exports_root(self) -> None:
        self._exports_root.mkdir(parents=True, exist_ok=True)

    def _normalize_text(self, value: str | None) -> str:
        return normalize_language_text(value or "")

    def _compute_source_payloads(self, sources: list[CreatorLanguageCorpusSource]) -> list[dict[str, object]]:
        return [build_source_snapshot_payload(
            source_type=source.source_type.value,
            source_id=source.source_id,
            text_snapshot=source.text_snapshot,
            language=source.language,
            platform=source.platform,
            content_type=source.content_type,
            topic=source.topic,
            start_seconds=source.start_seconds,
            end_seconds=source.end_seconds,
        ) for source in sources]

    def _load_transcription_source(self, source_id: str, *, segment_id: str | None = None) -> tuple[str | None, str | None, str | None, str | None, float | None, float | None]:
        if self.transcription_repository is None:
            return None, None, None, None, None, None
        transcription = self.transcription_repository.get_by_id(source_id) or self.transcription_repository.get_by_video_asset_id(source_id)
        if transcription is None:
            return None, None, None, None, None, None
        if segment_id:
            segment = next((item for item in self.transcription_repository.list_segments(transcription.id) if item.id == segment_id), None)
            if segment:
                return segment.text, transcription.video_asset_id, transcription.id, segment.id, segment.start_seconds, segment.end_seconds
        return transcription.full_text, transcription.video_asset_id, transcription.id, None, 0.0, transcription.duration_seconds

    def _load_subtitle_source(self, source_id: str, *, cue_id: str | None = None) -> tuple[str | None, str | None, str | None, str | None, float | None, float | None]:
        if self.subtitle_repository is None:
            return None, None, None, None, None, None
        track = self.subtitle_repository.get_track_by_id(source_id) or self.subtitle_repository.get_track_by_video_asset_id(source_id)
        if track is None:
            return None, None, None, None, None, None
        if cue_id:
            cue = self.subtitle_repository.get_cue_by_id(cue_id)
            if cue and cue.subtitle_track_id == track.id:
                return cue.text, track.video_asset_id, track.id, cue.id, cue.start_seconds, cue.end_seconds
        cues = self.subtitle_repository.list_cues(track.id)
        text = " ".join(cue.text for cue in cues)
        start_seconds = cues[0].start_seconds if cues else 0.0
        end_seconds = cues[-1].end_seconds if cues else None
        return text, track.video_asset_id, track.id, None, start_seconds, end_seconds

    def _load_publication_source(self, source_id: str, *, field: str = "title") -> tuple[str | None, str | None, str | None]:
        if self.analytics_repository is None:
            return None, None, None
        publication = self.analytics_repository.get_publication_by_id(source_id)
        if publication is None:
            return None, None, None
        if field == "caption":
            text = publication.description or publication.title
        elif field == "copy":
            text = f"{publication.title}\n{publication.description or ''}".strip()
        else:
            text = publication.title
        return text, publication.platform, publication.content_type.value

    def _load_memory_example_source(self, source_id: str) -> tuple[str | None, str | None, str | None]:
        service = self.creator_memory_service
        if service is None:
            return None, None, None
        example = getattr(service, "get_example", lambda _id: None)(source_id)
        if example is None:
            return None, None, None
        return example.text_content or example.title, example.platform, example.content_type

    def _resolve_source_snapshot(
        self,
        *,
        source_type: str,
        source_id: str,
        text_snapshot: str | None,
        platform: str | None,
        content_type: str | None,
        topic: str | None,
        language: str | None,
        segment_id: str | None = None,
        cue_id: str | None = None,
    ) -> tuple[str, str | None, str | None, str | None, str | None, float | None, float | None, str | None]:
        start_seconds = None
        end_seconds = None
        video_asset_id = None
        transcription_id = None
        text = text_snapshot
        resolved_platform = platform
        resolved_content_type = content_type
        resolved_topic = topic
        if not text:
            if source_type in {CreatorLanguageSourceType.TRANSCRIPTION.value, CreatorLanguageSourceType.TRANSCRIPT_SEGMENT.value}:
                text, video_asset_id, transcription_id, segment_id, start_seconds, end_seconds = self._load_transcription_source(source_id, segment_id=segment_id)
            elif source_type in {CreatorLanguageSourceType.SUBTITLE_TRACK.value, CreatorLanguageSourceType.SUBTITLE_CUE.value}:
                text, video_asset_id, transcription_id, segment_id, start_seconds, end_seconds = self._load_subtitle_source(source_id, cue_id=cue_id)
            elif source_type == CreatorLanguageSourceType.PUBLICATION_TITLE.value:
                text, resolved_platform, resolved_content_type = self._load_publication_source(source_id, field="title")
            elif source_type == CreatorLanguageSourceType.PUBLICATION_CAPTION.value:
                text, resolved_platform, resolved_content_type = self._load_publication_source(source_id, field="caption")
            elif source_type == CreatorLanguageSourceType.PUBLICATION_COPY.value:
                text, resolved_platform, resolved_content_type = self._load_publication_source(source_id, field="copy")
            elif source_type == CreatorLanguageSourceType.MEMORY_EXAMPLE.value:
                text, resolved_platform, resolved_content_type = self._load_memory_example_source(source_id)
        if not text:
            raise CreatorLanguageValidationError("La fuente no contiene texto utilizable.")
        return text, resolved_platform, resolved_content_type, resolved_topic, language, start_seconds, end_seconds, video_asset_id or transcription_id

    def list_corpora(self, creator_id: str) -> list[CreatorLanguageCorpus]:
        return self.repository.list_corpora(creator_id)

    def get_corpus(self, corpus_id: str) -> CreatorLanguageCorpus | None:
        return self.repository.get_corpus(corpus_id)

    def create_corpus(
        self,
        *,
        creator_id: str,
        name: str,
        description: str | None = None,
        language: str = "es",
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        status: str = CreatorLanguageCorpusStatus.ACTIVE.value,
    ) -> CreatorLanguageCorpus:
        corpus_id = str(uuid4())
        source_fingerprint = build_creator_language_fingerprint({
            "corpus_id": corpus_id,
            "creator_id": creator_id,
            "name": name.strip(),
            "description": description,
            "language": language.strip() or "es",
            "platform": platform,
            "content_type": content_type,
            "topic": topic,
            "status": status,
        })
        corpus = CreatorLanguageCorpus(
            id=corpus_id,
            creator_id=creator_id,
            name=name.strip(),
            description=description,
            language=language.strip() or "es",
            platform=platform,
            content_type=content_type,
            topic=topic,
            status=CreatorLanguageCorpusStatus(status),
            source_count=0,
            token_count=0,
            duration_seconds=None,
            source_fingerprint=source_fingerprint,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_corpus(corpus)

    def update_corpus(self, corpus_id: str, **changes) -> CreatorLanguageCorpus:
        current = self.repository.get_corpus(corpus_id)
        if current is None:
            raise CreatorLanguageNotFoundError("El corpus no existe.")
        payload = replace(current, **{key: value for key, value in changes.items() if value is not None}, updated_at=utc_now())
        return self.repository.upsert_corpus(payload)

    def archive_corpus(self, corpus_id: str) -> CreatorLanguageCorpus:
        return self.update_corpus(corpus_id, status=CreatorLanguageCorpusStatus.ARCHIVED.value)

    def add_corpus_source(
        self,
        *,
        corpus_id: str,
        source_type: str,
        source_id: str,
        text_snapshot: str | None = None,
        language: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        include_status: str = CreatorLanguageCorpusSourceIncludeStatus.INCLUDED.value,
        exclusion_reason: str | None = None,
        video_asset_id: str | None = None,
        publication_id: str | None = None,
        transcription_id: str | None = None,
        segment_id: str | None = None,
        start_seconds: float | None = None,
        end_seconds: float | None = None,
        cue_id: str | None = None,
    ) -> CreatorLanguageCorpusSource:
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise CreatorLanguageNotFoundError("El corpus no existe.")
        resolved_text, resolved_platform, resolved_content_type, resolved_topic, resolved_language, resolved_start, resolved_end, resolved_link = self._resolve_source_snapshot(
            source_type=source_type,
            source_id=source_id,
            text_snapshot=text_snapshot,
            platform=platform or corpus.platform,
            content_type=content_type or corpus.content_type,
            topic=topic or corpus.topic,
            language=language or corpus.language,
            segment_id=segment_id,
            cue_id=cue_id,
        )
        existing_sources = self.repository.list_corpus_sources(corpus_id)
        existing_source = next(
            (
                item
                for item in existing_sources
                if item.source_type.value == source_type and item.source_id == source_id and item.text_snapshot == resolved_text
            ),
            None,
        )
        if existing_source:
            return existing_source
        source = CreatorLanguageCorpusSource(
            id=str(uuid4()),
            corpus_id=corpus_id,
            source_type=CreatorLanguageSourceType(source_type),
            source_id=source_id,
            video_asset_id=video_asset_id or (resolved_link if resolved_link and source_type in {CreatorLanguageSourceType.TRANSCRIPTION.value, CreatorLanguageSourceType.TRANSCRIPT_SEGMENT.value, CreatorLanguageSourceType.SUBTITLE_TRACK.value, CreatorLanguageSourceType.SUBTITLE_CUE.value} else None),
            publication_id=publication_id,
            transcription_id=transcription_id,
            segment_id=segment_id,
            start_seconds=start_seconds if start_seconds is not None else resolved_start,
            end_seconds=end_seconds if end_seconds is not None else resolved_end,
            text_snapshot=resolved_text,
            language=resolved_language or corpus.language,
            platform=resolved_platform or corpus.platform,
            content_type=resolved_content_type or corpus.content_type,
            topic=resolved_topic or corpus.topic,
            include_status=CreatorLanguageCorpusSourceIncludeStatus(include_status),
            exclusion_reason=exclusion_reason,
            created_at=utc_now(),
        )
        stored = self.repository.upsert_corpus_source(source)
        self._refresh_corpus_stats(corpus_id)
        return stored

    def remove_corpus_source(self, source_id: str, *, reason: str | None = None) -> CreatorLanguageCorpusSource:
        source = self.repository.get_corpus_source(source_id)
        if source is None:
            raise CreatorLanguageNotFoundError("La fuente del corpus no existe.")
        updated = replace(
            source,
            include_status=CreatorLanguageCorpusSourceIncludeStatus.EXCLUDED,
            exclusion_reason=reason,
        )
        stored = self.repository.upsert_corpus_source(updated)
        self._refresh_corpus_stats(source.corpus_id)
        return stored

    def list_corpus_sources(self, corpus_id: str) -> list[CreatorLanguageCorpusSource]:
        return self.repository.list_corpus_sources(corpus_id)

    def _refresh_corpus_stats(self, corpus_id: str) -> None:
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            return
        sources = [item for item in self.repository.list_corpus_sources(corpus_id) if item.include_status == CreatorLanguageCorpusSourceIncludeStatus.INCLUDED]
        source_fingerprint = build_creator_language_fingerprint({
            "corpus_id": corpus_id,
            "sources": [item.to_dict() for item in sources],
        })
        token_count = sum(len(tokenize_language_text(source.text_snapshot).tokens) for source in sources)
        duration_seconds = None
        durations = [float(source.end_seconds - source.start_seconds) for source in sources if source.start_seconds is not None and source.end_seconds is not None and source.end_seconds >= source.start_seconds]
        if durations:
            duration_seconds = float(sum(durations))
        updated = replace(
            corpus,
            source_count=len(sources),
            token_count=token_count,
            duration_seconds=duration_seconds,
            source_fingerprint=source_fingerprint,
            updated_at=utc_now(),
        )
        self.repository.upsert_corpus(updated)

    def _build_metrics(self, run_id: str, analysis_payload: dict[str, object], sources: list[CreatorLanguageCorpusSource]) -> list[CreatorLanguageMetric]:
        metrics: list[CreatorLanguageMetric] = []
        counters = analysis_payload["sentence_style"]
        metrics.append(
            CreatorLanguageMetric(
                id=str(uuid4()),
                analysis_run_id=run_id,
                metric_key="total_tokens",
                metric_group="language",
                numeric_value=float(counters["total_tokens"]),
                text_value=None,
                unit="count",
                scope=CreatorLanguageScope.CREATOR_GENERAL,
                platform=None,
                content_type=None,
                topic=None,
                sample_size=int(counters["total_tokens"]),
                confidence_level=CreatorLanguageConfidenceLevel.MEDIUM,
                warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                created_at=utc_now(),
            )
        )
        for key in [
            "unique_tokens",
            "vocabulary_diversity",
            "average_sentence_length",
            "median_sentence_length",
            "short_sentence_ratio",
            "long_sentence_ratio",
            "question_ratio",
            "exclamation_ratio",
            "first_person_ratio",
            "second_person_ratio",
            "imperative_ratio",
            "repetition_rate",
            "lexical_repetition",
            "average_clause_estimate",
        ]:
            value = counters.get(key)
            metrics.append(
                CreatorLanguageMetric(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    metric_key=key,
                    metric_group="sentence_style",
                    numeric_value=float(value) if isinstance(value, (int, float)) else None,
                    text_value=None,
                    unit="ratio" if "ratio" in key or "diversity" in key else ("count" if "tokens" in key or "repetition" in key else "words"),
                    scope=CreatorLanguageScope.CREATOR_GENERAL,
                    platform=None,
                    content_type=None,
                    topic=None,
                    sample_size=len(counters.get("sentence_length_distribution", [])) or len(sources),
                    confidence_level=CreatorLanguageConfidenceLevel.MEDIUM if len(sources) >= 2 else CreatorLanguageConfidenceLevel.LOW,
                    warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                    created_at=utc_now(),
                )
            )
        filler = analysis_payload["filler_words"]
        metrics.append(
            CreatorLanguageMetric(
                id=str(uuid4()),
                analysis_run_id=run_id,
                metric_key="filler_word_rate",
                metric_group="vocabulary",
                numeric_value=float(filler["rate"]),
                text_value=None,
                unit="ratio",
                scope=CreatorLanguageScope.CREATOR_GENERAL,
                platform=None,
                content_type=None,
                topic=None,
                sample_size=max(1, int(filler["total"]) or len(sources)),
                confidence_level=CreatorLanguageConfidenceLevel.LOW if filler["total"] < 3 else CreatorLanguageConfidenceLevel.MEDIUM,
                warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                created_at=utc_now(),
            )
        )
        discourse = analysis_payload["discourse_markers"]
        metrics.append(
            CreatorLanguageMetric(
                id=str(uuid4()),
                analysis_run_id=run_id,
                metric_key="discourse_marker_rate",
                metric_group="vocabulary",
                numeric_value=float(discourse["rate"]),
                text_value=None,
                unit="ratio",
                scope=CreatorLanguageScope.CREATOR_GENERAL,
                platform=None,
                content_type=None,
                topic=None,
                sample_size=max(1, int(discourse["total"]) or len(sources)),
                confidence_level=CreatorLanguageConfidenceLevel.LOW if discourse["total"] < 2 else CreatorLanguageConfidenceLevel.MEDIUM,
                warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                created_at=utc_now(),
            )
        )
        pause = analysis_payload["pause_data"]
        metrics.append(
            CreatorLanguageMetric(
                id=str(uuid4()),
                analysis_run_id=run_id,
                metric_key="average_pause_duration",
                metric_group="rhythm",
                numeric_value=float(pause["average_pause_duration"]),
                text_value=None,
                unit="seconds",
                scope=CreatorLanguageScope.CREATOR_GENERAL,
                platform=None,
                content_type=None,
                topic=None,
                sample_size=max(1, int(pause["pause_count"]) or len(sources)),
                confidence_level=CreatorLanguageConfidenceLevel.LOW if pause["pause_count"] < 2 else CreatorLanguageConfidenceLevel.MEDIUM,
                warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                created_at=utc_now(),
            )
        )
        metrics.append(
            CreatorLanguageMetric(
                id=str(uuid4()),
                analysis_run_id=run_id,
                metric_key="pause_rate",
                metric_group="rhythm",
                numeric_value=float(pause["pause_rate"]),
                text_value=None,
                unit="ratio",
                scope=CreatorLanguageScope.CREATOR_GENERAL,
                platform=None,
                content_type=None,
                topic=None,
                sample_size=max(1, int(pause["pause_count"]) or len(sources)),
                confidence_level=CreatorLanguageConfidenceLevel.LOW if pause["pause_count"] < 2 else CreatorLanguageConfidenceLevel.MEDIUM,
                warning_codes_json=_json_dumps(analysis_payload["warnings"]),
                created_at=utc_now(),
            )
        )
        return metrics

    def _build_patterns(self, run: CreatorLanguageAnalysisRun, sources: list[CreatorLanguageCorpusSource], analysis_payload: dict[str, object]) -> list[CreatorLanguagePattern]:
        patterns: list[CreatorLanguagePattern] = []
        phrase_frequency = analysis_payload["phrase_frequency"]
        filler_words = analysis_payload["filler_words"]
        sentence_style = analysis_payload["sentence_style"]
        narrative = analysis_payload["narrative"]

        if phrase_frequency["top_unigrams"]:
            term, count = phrase_frequency["top_unigrams"][0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.VOCABULARY_PATTERN,
                    pattern_key=f"vocab_{term}",
                    title=f"Termino frecuente: {term}",
                    description=f"El termino '{term}' aparece {count} veces en el corpus.",
                    scope=CreatorLanguageScope.CREATOR_GENERAL,
                    platform=run.corpus_id if False else None,
                    content_type=None,
                    topic=None,
                    frequency_count=int(count),
                    supporting_example_count=int(count),
                    contradicting_example_count=0,
                    confidence_level=CreatorLanguageConfidenceLevel.MEDIUM,
                    confidence_score=min(1.0, 0.25 + count / max(1, len(sources))),
                    status=CreatorLanguagePatternStatus.OBSERVED,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if phrase_frequency["top_bigrams"]:
            term, count = phrase_frequency["top_bigrams"][0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.PHRASE_PATTERN,
                    pattern_key=f"phrase_{term.replace(' ', '_')}",
                    title=f"Frase recurrente: {term}",
                    description=f"La frase '{term}' aparece de forma recurrente.",
                    scope=CreatorLanguageScope.CREATOR_GENERAL,
                    platform=None,
                    content_type=None,
                    topic=None,
                    frequency_count=int(count),
                    supporting_example_count=int(count),
                    contradicting_example_count=0,
                    confidence_level=CreatorLanguageConfidenceLevel.LOW if count < 3 else CreatorLanguageConfidenceLevel.MEDIUM,
                    confidence_score=min(1.0, 0.2 + count / max(1, len(sources))),
                    status=CreatorLanguagePatternStatus.PROVISIONAL if count < 3 else CreatorLanguagePatternStatus.OBSERVED,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if filler_words["total"]:
            top_filler = max(filler_words["counts"].items(), key=lambda item: item[1])[0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.FILLER_PATTERN,
                    pattern_key=f"filler_{top_filler.replace(' ', '_')}",
                    title=f"Muletilla: {top_filler}",
                    description=f"Se observa uso recurrente de '{top_filler}'.",
                    scope=CreatorLanguageScope.CREATOR_GENERAL,
                    platform=None,
                    content_type=None,
                    topic=None,
                    frequency_count=int(filler_words["counts"][top_filler]),
                    supporting_example_count=int(filler_words["counts"][top_filler]),
                    contradicting_example_count=0,
                    confidence_level=CreatorLanguageConfidenceLevel.LOW,
                    confidence_score=min(1.0, 0.2 + float(filler_words["counts"][top_filler]) / max(1, len(sources))),
                    status=CreatorLanguagePatternStatus.OBSERVED,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        opening = narrative["opening"]
        if opening:
            opening_payload = opening[0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.OPENING_PATTERN,
                    pattern_key=str(opening_payload["pattern_key"]),
                    title="Patron de apertura",
                    description=str(opening_payload["description"]),
                    scope=CreatorLanguageScope.PLATFORM_SPECIFIC if any(source.platform for source in sources) else CreatorLanguageScope.CREATOR_GENERAL,
                    platform=sources[0].platform if sources and sources[0].platform else None,
                    content_type=sources[0].content_type if sources and sources[0].content_type else None,
                    topic=sources[0].topic if sources and sources[0].topic else None,
                    frequency_count=int(opening_payload["frequency_count"]),
                    supporting_example_count=int(opening_payload["supporting_example_count"]),
                    contradicting_example_count=int(opening_payload["contradicting_example_count"]),
                    confidence_level=CreatorLanguageConfidenceLevel(str(opening_payload["confidence_level"])),
                    confidence_score=0.45,
                    status=CreatorLanguagePatternStatus(str(opening_payload.get("status", "observed")) if opening_payload.get("status") else CreatorLanguagePatternStatus.OBSERVED.value),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        for section_name, pattern_type in [("explanation", CreatorLanguagePatternType.EXPLANATION_PATTERN), ("humor", CreatorLanguagePatternType.HUMOR_PATTERN), ("pacing", CreatorLanguagePatternType.PACING_PATTERN), ("closing", CreatorLanguagePatternType.CLOSING_PATTERN)]:
            section = narrative.get(section_name) or []
            if not section:
                continue
            payload = section[0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=pattern_type,
                    pattern_key=str(payload["pattern_key"]),
                    title=str(payload["label"]),
                    description=str(payload["description"]),
                    scope=CreatorLanguageScope.CREATOR_GENERAL,
                    platform=None,
                    content_type=None,
                    topic=None,
                    frequency_count=int(payload["frequency_count"]),
                    supporting_example_count=int(payload["supporting_example_count"]),
                    contradicting_example_count=int(payload["contradicting_example_count"]),
                    confidence_level=CreatorLanguageConfidenceLevel(str(payload["confidence_level"])),
                    confidence_score=0.4,
                    status=CreatorLanguagePatternStatus(str(payload.get("status", "observed")) if payload.get("status") else CreatorLanguagePatternStatus.OBSERVED.value),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if narrative.get("platform_differences"):
            payload = narrative["platform_differences"][0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.PLATFORM_DIFFERENCE,
                    pattern_key=str(payload["pattern_key"]),
                    title="Diferencia por plataforma",
                    description=str(payload["description"]),
                    scope=CreatorLanguageScope.PLATFORM_SPECIFIC,
                    platform=sources[0].platform if sources and sources[0].platform else None,
                    content_type=sources[0].content_type if sources and sources[0].content_type else None,
                    topic=None,
                    frequency_count=int(payload["frequency_count"]),
                    supporting_example_count=int(payload["supporting_example_count"]),
                    contradicting_example_count=int(payload["contradicting_example_count"]),
                    confidence_level=CreatorLanguageConfidenceLevel(str(payload["confidence_level"])),
                    confidence_score=0.3,
                    status=CreatorLanguagePatternStatus(str(payload.get("status", "observed")) if payload.get("status") else CreatorLanguagePatternStatus.OBSERVED.value),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if narrative.get("content_type_differences"):
            payload = narrative["content_type_differences"][0]
            patterns.append(
                CreatorLanguagePattern(
                    id=str(uuid4()),
                    analysis_run_id=run.id,
                    creator_id=run.creator_id,
                    pattern_type=CreatorLanguagePatternType.CONTENT_TYPE_DIFFERENCE,
                    pattern_key=str(payload["pattern_key"]),
                    title="Diferencia por tipo de contenido",
                    description=str(payload["description"]),
                    scope=CreatorLanguageScope.CONTENT_TYPE_SPECIFIC,
                    platform=None,
                    content_type=sources[0].content_type if sources and sources[0].content_type else None,
                    topic=None,
                    frequency_count=int(payload["frequency_count"]),
                    supporting_example_count=int(payload["supporting_example_count"]),
                    contradicting_example_count=int(payload["contradicting_example_count"]),
                    confidence_level=CreatorLanguageConfidenceLevel(str(payload["confidence_level"])),
                    confidence_score=0.3,
                    status=CreatorLanguagePatternStatus(str(payload.get("status", "observed")) if payload.get("status") else CreatorLanguagePatternStatus.OBSERVED.value),
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        return patterns

    def _build_evidence(self, pattern: CreatorLanguagePattern, sources: list[CreatorLanguageCorpusSource]) -> list[CreatorLanguagePatternEvidence]:
        evidence: list[CreatorLanguagePatternEvidence] = []
        for source in sources[:3]:
            normalized = normalize_language_text(source.text_snapshot).casefold()
            if not normalized:
                continue
            quoted_text = source.text_snapshot[:200]
            evidence.append(
                CreatorLanguagePatternEvidence(
                    id=str(uuid4()),
                    pattern_id=pattern.id,
                    corpus_source_id=source.id,
                    start_seconds=source.start_seconds,
                    end_seconds=source.end_seconds,
                    quoted_text=quoted_text,
                    normalized_text=normalized[:200],
                    supports_pattern=True,
                    weight=1.0,
                    notes=None,
                    created_at=utc_now(),
                )
            )
        return evidence

    def _group_platform_stats(self, sources: list[CreatorLanguageCorpusSource]) -> list[dict[str, object]]:
        by_platform: dict[str | None, list[CreatorLanguageCorpusSource]] = {}
        for source in sources:
            by_platform.setdefault(source.platform, []).append(source)
        groups: list[dict[str, object]] = []
        for platform, items in by_platform.items():
            texts = [item.text_snapshot for item in items]
            lengths = [len(normalize_language_text(text).split()) for text in texts if text.strip()]
            if not lengths:
                continue
            groups.append({
                "platform": platform,
                "source_count": len(items),
                "average_sentence_length": mean(lengths),
                "median_sentence_length": median(lengths),
                "token_count": sum(len(tokenize_language_text(text).tokens) for text in texts),
                "text": " ".join(texts[:2]),
            })
        return groups

    def analyze_corpus(
        self,
        corpus_id: str,
        *,
        force_recompute: bool = False,
        configuration: dict[str, object] | None = None,
    ) -> CreatorLanguageAnalysisDetail:
        corpus = self.repository.get_corpus(corpus_id)
        if corpus is None:
            raise CreatorLanguageNotFoundError("El corpus no existe.")
        sources = [item for item in self.repository.list_corpus_sources(corpus_id) if item.include_status == CreatorLanguageCorpusSourceIncludeStatus.INCLUDED]
        configuration = configuration or {}
        source_payloads = self._compute_source_payloads(sources)
        force_nonce = str(uuid4()) if force_recompute else None
        source_fingerprint = build_creator_language_fingerprint({
            "creator_id": corpus.creator_id,
            "corpus_id": corpus_id,
            "analysis_version": self.ANALYSIS_VERSION,
            "configuration": configuration,
            "sources": source_payloads,
            "force_recompute_nonce": force_nonce,
        })
        existing = self.repository.get_analysis_run_by_fingerprint(corpus.creator_id, source_fingerprint, self.ANALYSIS_VERSION)
        if existing and not force_recompute and existing.status in {CreatorLanguageAnalysisRunStatus.COMPLETED, CreatorLanguageAnalysisRunStatus.COMPLETED_WITH_WARNINGS}:
            return self.get_analysis_detail(existing.id)
        combined_text = "\n\n".join(source.text_snapshot for source in sources if source.text_snapshot)
        tokenization = tokenize_language_text(combined_text)
        pause_data = analyze_pause_patterns([
            {
                "start_seconds": source.start_seconds,
                "end_seconds": source.end_seconds,
            }
            for source in sources
        ])
        sentence_style = analyze_sentence_style(combined_text)
        phrase_frequency = analyze_phrase_frequency(combined_text)
        vocabulary = analyze_vocabulary(combined_text)
        filler_words = analyze_filler_words(combined_text)
        discourse_markers = analyze_discourse_markers(combined_text)
        narrative = analyze_narrative_structure(combined_text, platform=corpus.platform, content_type=corpus.content_type)
        platform_groups = self._group_platform_stats(sources)
        warnings = set(tokenization.warnings) | set(narrative.get("limitations", []))
        if len(sources) < 2:
            warnings.add("insufficient_sample")
        if any(source.language != corpus.language for source in sources if source.language):
            warnings.add("mixed_language")
        if len({source.platform for source in sources if source.platform}) > 1:
            warnings.add("mixed_platform")
        if len({source.content_type for source in sources if source.content_type}) > 1:
            warnings.add("mixed_content_type")
        if not any(source.start_seconds is not None and source.end_seconds is not None for source in sources):
            warnings.add("duration_missing")
        profile_summary = build_language_profile_summary({
            "opening": narrative.get("opening", []),
            "development": narrative.get("development", []),
            "explanation": narrative.get("explanation", []),
            "humor": narrative.get("humor", []),
            "pacing": narrative.get("pacing", []),
            "closing": narrative.get("closing", []),
            "platform_differences": narrative.get("platform_differences", []),
            "content_type_differences": narrative.get("content_type_differences", []),
            "limitations": sorted(warnings),
            "summary": narrative.get("summary", "Perfil narrativo heuristico construido localmente."),
        })
        analysis_run = CreatorLanguageAnalysisRun(
            id=str(uuid4()) if force_recompute or existing is None else existing.id,
            creator_id=corpus.creator_id,
            corpus_id=corpus.id,
            analysis_version=self.ANALYSIS_VERSION,
            status=CreatorLanguageAnalysisRunStatus.RUNNING,
            configuration_json=_json_dumps(configuration),
            source_fingerprint=source_fingerprint,
            source_count=len(sources),
            token_count=len(tokenization.tokens),
            sentence_count=len(tokenization.sentences),
            warning_count=len(warnings),
            started_at=utc_now(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=existing.created_at if existing and not force_recompute else utc_now(),
        )
        self.repository.upsert_analysis_run(analysis_run)
        analysis_payload = {
            "warnings": sorted(warnings),
            "sentence_style": sentence_style,
            "phrase_frequency": phrase_frequency,
            "vocabulary": vocabulary,
            "filler_words": filler_words,
            "discourse_markers": discourse_markers,
            "narrative": narrative,
            "pause_data": pause_data,
            "platform_groups": platform_groups,
        }
        metrics = self._build_metrics(analysis_run.id, analysis_payload, sources)
        for metric in metrics:
            self.repository.upsert_metric(metric)
        run_snapshot = self.repository.get_analysis_run(analysis_run.id)
        if run_snapshot is None:
            raise CreatorLanguageStateError("No se pudo registrar la corrida de analisis.")
        patterns = self._build_patterns(run_snapshot, sources, analysis_payload)
        for pattern in patterns:
            stored = self.repository.upsert_pattern(pattern)
            for evidence in self._build_evidence(stored, sources):
                self.repository.upsert_pattern_evidence(evidence)
        profile_payload = {
            "opening": narrative.get("opening", []),
            "development": narrative.get("development", []),
            "explanation": narrative.get("explanation", []),
            "humor": narrative.get("humor", []),
            "pacing": narrative.get("pacing", []),
            "closing": narrative.get("closing", []),
            "platform_differences": narrative.get("platform_differences", []),
            "content_type_differences": narrative.get("content_type_differences", []),
            "limitations": sorted(warnings),
            "summary": profile_summary.summary,
        }
        narrative_profile = CreatorNarrativeProfile(
            id=str(uuid4()) if force_recompute or existing is None else existing.id,
            creator_id=corpus.creator_id,
            analysis_run_id=run_snapshot.id,
            profile_version=(self.get_latest_profile_version(corpus.creator_id) + 1),
            status="completed_with_warnings" if warnings else "completed",
            summary=str(profile_payload["summary"]),
            opening_profile_json=_json_dumps(profile_payload["opening"]),
            development_profile_json=_json_dumps(profile_payload["development"]),
            explanation_profile_json=_json_dumps(profile_payload["explanation"]),
            humor_profile_json=_json_dumps(profile_payload["humor"]),
            pacing_profile_json=_json_dumps(profile_payload["pacing"]),
            closing_profile_json=_json_dumps(profile_payload["closing"]),
            platform_differences_json=_json_dumps(profile_payload["platform_differences"]),
            content_type_differences_json=_json_dumps(profile_payload["content_type_differences"]),
            limitations_json=_json_dumps(profile_payload["limitations"]),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        stored_profile = self.repository.upsert_narrative_profile(narrative_profile)
        profile_snapshot = CreatorLanguageProfileSnapshot(
            id=str(uuid4()),
            creator_id=corpus.creator_id,
            profile_version=stored_profile.profile_version,
            snapshot_json=_json_dumps({
                "profile": stored_profile.to_dict(),
                "metrics": [metric.to_dict() for metric in metrics],
                "patterns": [pattern.to_dict() for pattern in patterns],
                "corpus": corpus.to_dict(),
            }),
            source_fingerprint=build_narrative_profile_fingerprint({
                "profile": stored_profile.to_dict(),
                "metrics": [metric.to_dict() for metric in metrics],
                "patterns": [pattern.to_dict() for pattern in patterns],
                "source_fingerprint": source_fingerprint,
            }),
            status="active",
            created_at=utc_now(),
        )
        self.repository.upsert_profile_snapshot(profile_snapshot)
        candidates_payload = generate_language_candidates(
            creator_id=corpus.creator_id,
            analysis_run_id=run_snapshot.id,
            profile_payload=profile_payload,
            evidence_payloads=[evidence.to_dict() for pattern in patterns for evidence in self.repository.list_pattern_evidence(pattern.id)],
        )
        candidates: list[CreatorLanguageCandidate] = []
        for payload in candidates_payload:
            candidate = CreatorLanguageCandidate(
                id=str(uuid4()),
                creator_id=payload["creator_id"],
                analysis_run_id=payload["analysis_run_id"],
                candidate_type=payload["candidate_type"],
                target_memory_type=CreatorLanguageTargetMemoryType(payload["target_memory_type"]),
                proposed_key=payload["proposed_key"],
                proposed_value_json=payload["proposed_value_json"],
                scope=CreatorLanguageScope(payload["scope"]),
                platform=payload["platform"],
                content_type=payload["content_type"],
                topic=payload["topic"],
                evidence_json=_json_dumps(payload["evidence_json"]),
                confidence_level=CreatorLanguageConfidenceLevel(payload["confidence_level"]),
                status=CreatorLanguageCandidateStatus(payload["status"]),
                review_reason=payload["review_reason"],
                created_at=utc_now(),
                reviewed_at=None,
            )
            candidates.append(self.repository.upsert_candidate(candidate))
        completed_status = CreatorLanguageAnalysisRunStatus.COMPLETED_WITH_WARNINGS if warnings else CreatorLanguageAnalysisRunStatus.COMPLETED
        completed_run = replace(run_snapshot, status=completed_status, completed_at=utc_now(), warning_count=len(warnings))
        self.repository.upsert_analysis_run(completed_run)
        return CreatorLanguageAnalysisDetail(
            run=completed_run,
            corpus=corpus,
            sources=tuple(sources),
            metrics=tuple(self.repository.list_metrics(completed_run.id)),
            patterns=tuple(self.repository.list_patterns(corpus.creator_id, completed_run.id)),
            profile=stored_profile,
            candidates=tuple(candidates),
            warnings=tuple(sorted(warnings)),
        )

    def get_analysis_run(self, run_id: str) -> CreatorLanguageAnalysisRun | None:
        return self.repository.get_analysis_run(run_id)

    def get_analysis_detail(self, run_id: str) -> CreatorLanguageAnalysisDetail:
        run = self.repository.get_analysis_run(run_id)
        if run is None:
            raise CreatorLanguageNotFoundError("La corrida de analisis no existe.")
        corpus = self.repository.get_corpus(run.corpus_id)
        if corpus is None:
            raise CreatorLanguageNotFoundError("El corpus no existe.")
        sources = self.repository.list_corpus_sources(corpus.id)
        profile = self.repository.get_narrative_profile(corpus.creator_id)
        return CreatorLanguageAnalysisDetail(
            run=run,
            corpus=corpus,
            sources=tuple(sources),
            metrics=tuple(self.repository.list_metrics(run.id)),
            patterns=tuple(self.repository.list_patterns(corpus.creator_id, run.id)),
            profile=profile or CreatorNarrativeProfile(
                id=str(uuid4()),
                creator_id=corpus.creator_id,
                analysis_run_id=run.id,
                profile_version=0,
                status="missing",
                summary="Sin perfil.",
                opening_profile_json="[]",
                development_profile_json="[]",
                explanation_profile_json="[]",
                humor_profile_json="[]",
                pacing_profile_json="[]",
                closing_profile_json="[]",
                platform_differences_json="[]",
                content_type_differences_json="[]",
                limitations_json="[]",
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            candidates=tuple(item for item in self.repository.list_candidates(corpus.creator_id) if item.analysis_run_id == run.id),
            warnings=tuple(sorted(_json_loads(run.configuration_json, {}).get("warnings", []))) if run.configuration_json else (),
        )

    def list_analysis_runs(self, creator_id: str, corpus_id: str | None = None) -> list[CreatorLanguageAnalysisRun]:
        return self.repository.list_analysis_runs(creator_id, corpus_id)

    def list_metrics(self, run_id: str) -> list[CreatorLanguageMetric]:
        return self.repository.list_metrics(run_id)

    def list_patterns(self, creator_id: str, run_id: str | None = None) -> list[CreatorLanguagePattern]:
        return self.repository.list_patterns(creator_id, run_id)

    def get_pattern(self, pattern_id: str) -> CreatorLanguagePattern | None:
        return self.repository.get_pattern(pattern_id)

    def get_profile(self, creator_id: str) -> CreatorNarrativeProfile | None:
        return self.repository.get_narrative_profile(creator_id)

    def get_profile_detail(self, creator_id: str) -> CreatorLanguageProfileDetail:
        profile = self.repository.get_narrative_profile(creator_id)
        corpora = tuple(self.repository.list_corpora(creator_id))
        sources = tuple(source for corpus in corpora for source in self.repository.list_corpus_sources(corpus.id))
        runs = tuple(self.repository.list_analysis_runs(creator_id))
        metrics = tuple(metric for run in runs for metric in self.repository.list_metrics(run.id))
        patterns = tuple(self.repository.list_patterns(creator_id))
        candidates = tuple(self.repository.list_candidates(creator_id))
        snapshots = tuple(self.repository.list_profile_snapshots(creator_id))
        warnings = tuple(sorted({warning for run in runs for warning in _json_loads(run.configuration_json, {}).get("warnings", [])}))
        return CreatorLanguageProfileDetail(
            profile=profile,
            corpora=corpora,
            sources=sources,
            metrics=metrics,
            patterns=patterns,
            candidates=candidates,
            snapshots=snapshots,
            warnings=warnings,
        )

    def get_latest_profile_version(self, creator_id: str) -> int:
        profiles = self.repository.list_narrative_profiles(creator_id)
        return profiles[0].profile_version if profiles else 0

    def list_profile_history(self, creator_id: str) -> list[CreatorNarrativeProfile]:
        return self.repository.list_narrative_profiles(creator_id)

    def compare_profile_versions(self, creator_id: str, base_profile_version: int, compare_profile_version: int) -> CreatorLanguageProfileComparison:
        profiles = {profile.profile_version: profile for profile in self.repository.list_narrative_profiles(creator_id)}
        base = profiles.get(base_profile_version)
        compare = profiles.get(compare_profile_version)
        if base is None or compare is None:
            raise CreatorLanguageNotFoundError("No se encontraron las versiones solicitadas.")
        section_pairs = (
            ("opening", base.opening_profile_json, compare.opening_profile_json),
            ("development", base.development_profile_json, compare.development_profile_json),
            ("explanation", base.explanation_profile_json, compare.explanation_profile_json),
            ("humor", base.humor_profile_json, compare.humor_profile_json),
            ("pacing", base.pacing_profile_json, compare.pacing_profile_json),
            ("closing", base.closing_profile_json, compare.closing_profile_json),
            ("platform_differences", base.platform_differences_json, compare.platform_differences_json),
            ("content_type_differences", base.content_type_differences_json, compare.content_type_differences_json),
            ("limitations", base.limitations_json, compare.limitations_json),
            ("summary", base.summary, compare.summary),
        )
        changed = tuple(section for section, base_value, compare_value in section_pairs if base_value != compare_value)
        return CreatorLanguageProfileComparison(
            creator_id=creator_id,
            base_profile_version=base_profile_version,
            compare_profile_version=compare_profile_version,
            changed_sections=changed,
            base_summary=base.to_dict(),
            compare_summary=compare.to_dict(),
        )

    def list_profile_snapshots(self, creator_id: str) -> list[CreatorLanguageProfileSnapshot]:
        return self.repository.list_profile_snapshots(creator_id)

    def create_profile_snapshot(self, creator_id: str) -> CreatorLanguageProfileSnapshot:
        profile = self.repository.get_narrative_profile(creator_id)
        if profile is None:
            raise CreatorLanguageNotFoundError("No hay perfil narrativo para crear snapshot.")
        snapshot = CreatorLanguageProfileSnapshot(
            id=str(uuid4()),
            creator_id=creator_id,
            profile_version=profile.profile_version,
            snapshot_json=_json_dumps(profile.to_dict()),
            source_fingerprint=build_narrative_profile_fingerprint(profile.to_dict()),
            status="active",
            created_at=utc_now(),
        )
        return self.repository.upsert_profile_snapshot(snapshot)

    def compare_profile_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str) -> CreatorLanguageProfileComparison:
        return self.repository.compare_profile_snapshots(creator_id, base_snapshot_id, compare_snapshot_id)

    def list_candidates(self, creator_id: str) -> list[CreatorLanguageCandidate]:
        return self.repository.list_candidates(creator_id)

    def review_candidate(self, candidate_id: str, *, decision: str, reason: str | None = None, modified_value_json: str | None = None) -> CreatorLanguageCandidate:
        candidate = self.repository.get_candidate(candidate_id)
        if candidate is None:
            raise CreatorLanguageNotFoundError("El candidato no existe.")
        status_map = {
            CreatorLanguageCandidateReviewDecision.APPROVE.value: CreatorLanguageCandidateStatus.APPROVED,
            CreatorLanguageCandidateReviewDecision.APPROVE_WITH_CHANGES.value: CreatorLanguageCandidateStatus.APPROVED_WITH_CHANGES,
            CreatorLanguageCandidateReviewDecision.REJECT.value: CreatorLanguageCandidateStatus.REJECTED,
            CreatorLanguageCandidateReviewDecision.NEEDS_MORE_DATA.value: CreatorLanguageCandidateStatus.NEEDS_MORE_DATA,
        }
        status = status_map.get(decision)
        if status is None:
            raise CreatorLanguageValidationError("Decision de candidato no valida.")
        updated = replace(candidate, status=status, review_reason=reason, proposed_value_json=modified_value_json or candidate.proposed_value_json, reviewed_at=utc_now())
        return self.repository.upsert_candidate(updated)

    def retrieve_creator_context(self, creator_id: str, query_filters: CreatorLanguageQueryFilters | dict[str, object]) -> list[CreatorLanguageRetrievalResult]:
        if not isinstance(query_filters, CreatorLanguageQueryFilters):
            query_filters = CreatorLanguageQueryFilters(creator_id=creator_id, **{key: value for key, value in query_filters.items() if key in CreatorLanguageQueryFilters.__annotations__})
        return self.repository.retrieve_context(creator_id, query_filters)

    def record_corpus_analysis_interrupt(self, run_id: str) -> CreatorLanguageAnalysisRun:
        run = self.repository.get_analysis_run(run_id)
        if run is None:
            raise CreatorLanguageNotFoundError("La corrida no existe.")
        interrupted = replace(run, status=CreatorLanguageAnalysisRunStatus.INTERRUPTED, error_code="interrupted", error_message="Interrumpida por el usuario.", completed_at=utc_now())
        return self.repository.upsert_analysis_run(interrupted)

    def retry_corpus_analysis(self, run_id: str) -> CreatorLanguageAnalysisDetail:
        run = self.repository.get_analysis_run(run_id)
        if run is None:
            raise CreatorLanguageNotFoundError("La corrida no existe.")
        return self.analyze_corpus(run.corpus_id, force_recompute=True, configuration=_json_loads(run.configuration_json, {}))

    def export(self, *, creator_id: str, format_name: str, summary: bool = False, destination: Path | None = None) -> CreatorLanguageExportResult:
        profile = self.repository.get_narrative_profile(creator_id)
        corpora = self.repository.list_corpora(creator_id)
        runs = self.repository.list_analysis_runs(creator_id)
        metrics = [metric.to_dict() for run in runs for metric in self.repository.list_metrics(run.id)]
        patterns = [pattern.to_dict() for pattern in self.repository.list_patterns(creator_id)]
        candidates = [candidate.to_dict() for candidate in self.repository.list_candidates(creator_id)]
        payload = {
            "creator_id": creator_id,
            "profile": profile.to_dict() if profile else None,
            "corpora": [item.to_dict() for item in corpora],
            "analysis_runs": [item.to_dict() for item in runs],
            "metrics": metrics,
            "patterns": patterns,
            "candidates": candidates,
            "summary": summary,
        }
        export_root = destination or self._exports_root
        export_root.mkdir(parents=True, exist_ok=True)
        created_at = utc_now().isoformat()
        if format_name == "json":
            path = export_root / f"{creator_id}_language_{'summary' if summary else 'full'}.json"
            path.write_text(_json_dumps(payload if not summary else {
                "creator_id": creator_id,
                "corpus_count": len(corpora),
                "analysis_run_count": len(runs),
                "pattern_count": len(patterns),
                "candidate_count": len(candidates),
                "profile_version": profile.profile_version if profile else None,
            }), encoding="utf-8")
            return CreatorLanguageExportResult(creator_id, format_name, str(path), 1, created_at, summary)
        if format_name == "txt":
            path = export_root / f"{creator_id}_language_{'summary' if summary else 'full'}.txt"
            lines = [
                f"Creator: {creator_id}",
                f"Profile version: {profile.profile_version if profile else 'none'}",
                f"Corpora: {len(corpora)}",
                f"Runs: {len(runs)}",
                f"Patterns: {len(patterns)}",
                f"Candidates: {len(candidates)}",
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            return CreatorLanguageExportResult(creator_id, format_name, str(path), len(lines), created_at, summary)
        if format_name == "csv":
            path = export_root / f"{creator_id}_language_{'summary' if summary else 'full'}.csv"
            rows = [
                ["section", "item_id", "title", "summary", "platform", "content_type", "confidence", "warning"],
            ]
            for corpus in corpora:
                rows.append([
                    _sanitize_csv("corpus"),
                    _sanitize_csv(corpus.id),
                    _sanitize_csv(corpus.name),
                    _sanitize_csv(corpus.description or ""),
                    _sanitize_csv(corpus.platform or ""),
                    _sanitize_csv(corpus.content_type or ""),
                    _sanitize_csv(corpus.status.value),
                    _sanitize_csv(""),
                ])
            for metric in metrics:
                rows.append([
                    _sanitize_csv("metric"),
                    _sanitize_csv(metric["id"]),
                    _sanitize_csv(metric["metric_key"]),
                    _sanitize_csv(metric.get("text_value") or metric.get("numeric_value")),
                    _sanitize_csv(metric.get("platform") or ""),
                    _sanitize_csv(metric.get("content_type") or ""),
                    _sanitize_csv(metric.get("confidence_level") or ""),
                    _sanitize_csv(metric.get("warning_codes_json") or ""),
                ])
            for pattern in patterns:
                rows.append([
                    _sanitize_csv("pattern"),
                    _sanitize_csv(pattern["id"]),
                    _sanitize_csv(pattern["title"]),
                    _sanitize_csv(pattern["description"]),
                    _sanitize_csv(pattern.get("platform") or ""),
                    _sanitize_csv(pattern.get("content_type") or ""),
                    _sanitize_csv(pattern.get("confidence_level") or ""),
                    _sanitize_csv(""),
                ])
            for candidate in candidates:
                rows.append([
                    _sanitize_csv("candidate"),
                    _sanitize_csv(candidate["id"]),
                    _sanitize_csv(candidate["proposed_key"]),
                    _sanitize_csv(candidate["proposed_value_json"][:200]),
                    _sanitize_csv(candidate.get("platform") or ""),
                    _sanitize_csv(candidate.get("content_type") or ""),
                    _sanitize_csv(candidate.get("confidence_level") or ""),
                    _sanitize_csv(candidate.get("status") or ""),
                ])
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            return CreatorLanguageExportResult(creator_id, format_name, str(path), len(rows), created_at, summary)
        raise CreatorLanguageValidationError("Formato de exportacion no soportado.")


def build_creator_language_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: CreatorLanguageRepository,
    database: SQLiteDatabase,
    transcription_repository: SQLiteTranscriptionRepository | None = None,
    subtitle_repository: SQLiteSubtitleRepository | None = None,
    analytics_repository: SQLiteAnalyticsRepository | None = None,
    creator_memory_service: object | None = None,
    logger: logging.Logger | None = None,
) -> CreatorLanguageService:
    return CreatorLanguageService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        transcription_repository=transcription_repository,
        subtitle_repository=subtitle_repository,
        analytics_repository=analytics_repository,
        creator_memory_service=creator_memory_service,
        logger=logger,
    )
