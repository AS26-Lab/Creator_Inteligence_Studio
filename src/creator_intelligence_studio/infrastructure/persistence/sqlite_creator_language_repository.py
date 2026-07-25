"""Repositorio SQLite para Creator Language Analysis."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from creator_intelligence_studio.domain.creator_language.analysis_types import (
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
from creator_intelligence_studio.domain.creator_language.repositories import CreatorLanguageRepository
from creator_intelligence_studio.domain.creator_language.value_objects import (
    CreatorLanguageAnalysisRunStatus,
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
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


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


def _row_to_corpus(row: sqlite3.Row) -> CreatorLanguageCorpus:
    return CreatorLanguageCorpus(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        description=row["description"],
        language=row["language"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        status=CreatorLanguageCorpusStatus(row["status"]),
        source_count=row["source_count"],
        token_count=row["token_count"],
        duration_seconds=row["duration_seconds"],
        source_fingerprint=row["source_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_source(row: sqlite3.Row) -> CreatorLanguageCorpusSource:
    return CreatorLanguageCorpusSource(
        id=row["id"],
        corpus_id=row["corpus_id"],
        source_type=CreatorLanguageSourceType(row["source_type"]),
        source_id=row["source_id"],
        video_asset_id=row["video_asset_id"],
        publication_id=row["publication_id"],
        transcription_id=row["transcription_id"],
        segment_id=row["segment_id"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        text_snapshot=row["text_snapshot"],
        language=row["language"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        include_status=CreatorLanguageCorpusSourceIncludeStatus(row["include_status"]),
        exclusion_reason=row["exclusion_reason"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_run(row: sqlite3.Row) -> CreatorLanguageAnalysisRun:
    return CreatorLanguageAnalysisRun(
        id=row["id"],
        creator_id=row["creator_id"],
        corpus_id=row["corpus_id"],
        analysis_version=row["analysis_version"],
        status=CreatorLanguageAnalysisRunStatus(row["status"]),
        configuration_json=row["configuration_json"],
        source_fingerprint=row["source_fingerprint"],
        source_count=row["source_count"],
        token_count=row["token_count"],
        sentence_count=row["sentence_count"],
        warning_count=row["warning_count"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric(row: sqlite3.Row) -> CreatorLanguageMetric:
    return CreatorLanguageMetric(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        metric_key=row["metric_key"],
        metric_group=row["metric_group"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        scope=CreatorLanguageScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        sample_size=row["sample_size"],
        confidence_level=CreatorLanguageConfidenceLevel(row["confidence_level"]),
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_pattern(row: sqlite3.Row) -> CreatorLanguagePattern:
    return CreatorLanguagePattern(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        creator_id=row["creator_id"],
        pattern_type=CreatorLanguagePatternType(row["pattern_type"]),
        pattern_key=row["pattern_key"],
        title=row["title"],
        description=row["description"],
        scope=CreatorLanguageScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        frequency_count=row["frequency_count"],
        supporting_example_count=row["supporting_example_count"],
        contradicting_example_count=row["contradicting_example_count"],
        confidence_level=CreatorLanguageConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        status=CreatorLanguagePatternStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_evidence(row: sqlite3.Row) -> CreatorLanguagePatternEvidence:
    return CreatorLanguagePatternEvidence(
        id=row["id"],
        pattern_id=row["pattern_id"],
        corpus_source_id=row["corpus_source_id"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        quoted_text=row["quoted_text"],
        normalized_text=row["normalized_text"],
        supports_pattern=bool(row["supports_pattern"]),
        weight=row["weight"],
        notes=row["notes"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_profile(row: sqlite3.Row) -> CreatorNarrativeProfile:
    return CreatorNarrativeProfile(
        id=row["id"],
        creator_id=row["creator_id"],
        analysis_run_id=row["analysis_run_id"],
        profile_version=row["profile_version"],
        status=row["status"],
        summary=row["summary"],
        opening_profile_json=row["opening_profile_json"],
        development_profile_json=row["development_profile_json"],
        explanation_profile_json=row["explanation_profile_json"],
        humor_profile_json=row["humor_profile_json"],
        pacing_profile_json=row["pacing_profile_json"],
        closing_profile_json=row["closing_profile_json"],
        platform_differences_json=row["platform_differences_json"],
        content_type_differences_json=row["content_type_differences_json"],
        limitations_json=row["limitations_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_candidate(row: sqlite3.Row) -> CreatorLanguageCandidate:
    return CreatorLanguageCandidate(
        id=row["id"],
        creator_id=row["creator_id"],
        analysis_run_id=row["analysis_run_id"],
        candidate_type=row["candidate_type"],
        target_memory_type=CreatorLanguageTargetMemoryType(row["target_memory_type"]),
        proposed_key=row["proposed_key"],
        proposed_value_json=row["proposed_value_json"],
        scope=CreatorLanguageScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        evidence_json=row["evidence_json"],
        confidence_level=CreatorLanguageConfidenceLevel(row["confidence_level"]),
        status=CreatorLanguageCandidateStatus(row["status"]),
        review_reason=row["review_reason"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        reviewed_at=from_iso_z(row["reviewed_at"]),
    )


def _row_to_snapshot(row: sqlite3.Row) -> CreatorLanguageProfileSnapshot:
    return CreatorLanguageProfileSnapshot(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_version=row["profile_version"],
        snapshot_json=row["snapshot_json"],
        source_fingerprint=row["source_fingerprint"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteCreatorLanguageRepository(CreatorLanguageRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_corpus(self, corpus: CreatorLanguageCorpus) -> CreatorLanguageCorpus:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_corpora (
                    id, creator_id, name, description, language, platform,
                    content_type, topic, status, source_count, token_count,
                    duration_seconds, source_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :name, :description, :language, :platform,
                    :content_type, :topic, :status, :source_count, :token_count,
                    :duration_seconds, :source_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    language = excluded.language,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    status = excluded.status,
                    source_count = excluded.source_count,
                    token_count = excluded.token_count,
                    duration_seconds = excluded.duration_seconds,
                    source_fingerprint = excluded.source_fingerprint,
                    updated_at = excluded.updated_at
                """,
                {
                    **corpus.to_dict(),
                    "status": corpus.status.value,
                    "created_at": corpus.created_at.isoformat(),
                    "updated_at": corpus.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_corpora WHERE id = ?", (corpus.id,)).fetchone()
        return _row_to_corpus(row)

    def get_corpus(self, corpus_id: str) -> CreatorLanguageCorpus | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_corpora WHERE id = ?", (corpus_id,)).fetchone()
        return _row_to_corpus(row) if row else None

    def list_corpora(self, creator_id: str) -> list[CreatorLanguageCorpus]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_corpora WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_corpus(row) for row in rows]

    def get_corpus_by_fingerprint(self, creator_id: str, source_fingerprint: str) -> CreatorLanguageCorpus | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_language_corpora WHERE creator_id = ? AND source_fingerprint = ? ORDER BY updated_at DESC LIMIT 1",
                (creator_id, source_fingerprint),
            ).fetchone()
        return _row_to_corpus(row) if row else None

    def upsert_corpus_source(self, source: CreatorLanguageCorpusSource) -> CreatorLanguageCorpusSource:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_corpus_sources (
                    id, corpus_id, source_type, source_id, video_asset_id, publication_id,
                    transcription_id, segment_id, start_seconds, end_seconds,
                    text_snapshot, language, platform, content_type, topic,
                    include_status, exclusion_reason, created_at
                ) VALUES (
                    :id, :corpus_id, :source_type, :source_id, :video_asset_id, :publication_id,
                    :transcription_id, :segment_id, :start_seconds, :end_seconds,
                    :text_snapshot, :language, :platform, :content_type, :topic,
                    :include_status, :exclusion_reason, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    video_asset_id = excluded.video_asset_id,
                    publication_id = excluded.publication_id,
                    transcription_id = excluded.transcription_id,
                    segment_id = excluded.segment_id,
                    start_seconds = excluded.start_seconds,
                    end_seconds = excluded.end_seconds,
                    text_snapshot = excluded.text_snapshot,
                    language = excluded.language,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    include_status = excluded.include_status,
                    exclusion_reason = excluded.exclusion_reason
                """,
                {
                    **source.to_dict(),
                    "source_type": source.source_type.value,
                    "include_status": source.include_status.value,
                    "created_at": source.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_corpus_sources WHERE id = ?", (source.id,)).fetchone()
        return _row_to_source(row)

    def list_corpus_sources(self, corpus_id: str) -> list[CreatorLanguageCorpusSource]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_corpus_sources WHERE corpus_id = ? ORDER BY created_at ASC",
                (corpus_id,),
            ).fetchall()
        return [_row_to_source(row) for row in rows]

    def get_corpus_source(self, source_id: str) -> CreatorLanguageCorpusSource | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_corpus_sources WHERE id = ?", (source_id,)).fetchone()
        return _row_to_source(row) if row else None

    def upsert_analysis_run(self, run: CreatorLanguageAnalysisRun) -> CreatorLanguageAnalysisRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_analysis_runs (
                    id, creator_id, corpus_id, analysis_version, status,
                    configuration_json, source_fingerprint, source_count, token_count,
                    sentence_count, warning_count, started_at, completed_at,
                    error_code, error_message, created_at
                ) VALUES (
                    :id, :creator_id, :corpus_id, :analysis_version, :status,
                    :configuration_json, :source_fingerprint, :source_count, :token_count,
                    :sentence_count, :warning_count, :started_at, :completed_at,
                    :error_code, :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    source_fingerprint = excluded.source_fingerprint,
                    source_count = excluded.source_count,
                    token_count = excluded.token_count,
                    sentence_count = excluded.sentence_count,
                    warning_count = excluded.warning_count,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                {
                    **run.to_dict(),
                    "status": run.status.value,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "created_at": run.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_analysis_runs WHERE id = ?", (run.id,)).fetchone()
        return _row_to_run(row)

    def get_analysis_run(self, run_id: str) -> CreatorLanguageAnalysisRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_analysis_runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def get_analysis_run_by_fingerprint(self, creator_id: str, source_fingerprint: str, analysis_version: str) -> CreatorLanguageAnalysisRun | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM creator_language_analysis_runs
                WHERE creator_id = ? AND source_fingerprint = ? AND analysis_version = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (creator_id, source_fingerprint, analysis_version),
            ).fetchone()
        return _row_to_run(row) if row else None

    def list_analysis_runs(self, creator_id: str, corpus_id: str | None = None) -> list[CreatorLanguageAnalysisRun]:
        query = "SELECT * FROM creator_language_analysis_runs WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if corpus_id:
            query += " AND corpus_id = ?"
            params.append(corpus_id)
        query += " ORDER BY created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_run(row) for row in rows]

    def upsert_metric(self, metric: CreatorLanguageMetric) -> CreatorLanguageMetric:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_metrics (
                    id, analysis_run_id, metric_key, metric_group, numeric_value, text_value,
                    unit, scope, platform, content_type, topic, sample_size,
                    confidence_level, warning_codes_json, created_at
                ) VALUES (
                    :id, :analysis_run_id, :metric_key, :metric_group, :numeric_value, :text_value,
                    :unit, :scope, :platform, :content_type, :topic, :sample_size,
                    :confidence_level, :warning_codes_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    metric_group = excluded.metric_group,
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    scope = excluded.scope,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    sample_size = excluded.sample_size,
                    confidence_level = excluded.confidence_level,
                    warning_codes_json = excluded.warning_codes_json
                """,
                {
                    **metric.to_dict(),
                    "scope": metric.scope.value,
                    "confidence_level": metric.confidence_level.value,
                    "created_at": metric.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_metrics WHERE id = ?", (metric.id,)).fetchone()
        return _row_to_metric(row)

    def list_metrics(self, run_id: str) -> list[CreatorLanguageMetric]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_metrics WHERE analysis_run_id = ? ORDER BY metric_key ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_metric(row) for row in rows]

    def upsert_pattern(self, pattern: CreatorLanguagePattern) -> CreatorLanguagePattern:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_patterns (
                    id, analysis_run_id, creator_id, pattern_type, pattern_key, title,
                    description, scope, platform, content_type, topic, frequency_count,
                    supporting_example_count, contradicting_example_count,
                    confidence_level, confidence_score, status, created_at, updated_at
                ) VALUES (
                    :id, :analysis_run_id, :creator_id, :pattern_type, :pattern_key, :title,
                    :description, :scope, :platform, :content_type, :topic, :frequency_count,
                    :supporting_example_count, :contradicting_example_count,
                    :confidence_level, :confidence_score, :status, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    scope = excluded.scope,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    frequency_count = excluded.frequency_count,
                    supporting_example_count = excluded.supporting_example_count,
                    contradicting_example_count = excluded.contradicting_example_count,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                {
                    **pattern.to_dict(),
                    "pattern_type": pattern.pattern_type.value,
                    "scope": pattern.scope.value,
                    "confidence_level": pattern.confidence_level.value,
                    "status": pattern.status.value,
                    "created_at": pattern.created_at.isoformat(),
                    "updated_at": pattern.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_patterns WHERE id = ?", (pattern.id,)).fetchone()
        return _row_to_pattern(row)

    def list_patterns(self, creator_id: str, run_id: str | None = None) -> list[CreatorLanguagePattern]:
        query = "SELECT * FROM creator_language_patterns WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if run_id:
            query += " AND analysis_run_id = ?"
            params.append(run_id)
        query += " ORDER BY frequency_count DESC, created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_pattern(row) for row in rows]

    def get_pattern(self, pattern_id: str) -> CreatorLanguagePattern | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_patterns WHERE id = ?", (pattern_id,)).fetchone()
        return _row_to_pattern(row) if row else None

    def upsert_pattern_evidence(self, evidence: CreatorLanguagePatternEvidence) -> CreatorLanguagePatternEvidence:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_pattern_evidence (
                    id, pattern_id, corpus_source_id, start_seconds, end_seconds,
                    quoted_text, normalized_text, supports_pattern, weight, notes, created_at
                ) VALUES (
                    :id, :pattern_id, :corpus_source_id, :start_seconds, :end_seconds,
                    :quoted_text, :normalized_text, :supports_pattern, :weight, :notes, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    start_seconds = excluded.start_seconds,
                    end_seconds = excluded.end_seconds,
                    quoted_text = excluded.quoted_text,
                    normalized_text = excluded.normalized_text,
                    supports_pattern = excluded.supports_pattern,
                    weight = excluded.weight,
                    notes = excluded.notes
                """,
                {
                    **evidence.to_dict(),
                    "supports_pattern": 1 if evidence.supports_pattern else 0,
                    "created_at": evidence.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_language_pattern_evidence WHERE id = ?", (evidence.id,)).fetchone()
        return _row_to_evidence(row)

    def list_pattern_evidence(self, pattern_id: str) -> list[CreatorLanguagePatternEvidence]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_pattern_evidence WHERE pattern_id = ? ORDER BY created_at ASC",
                (pattern_id,),
            ).fetchall()
        return [_row_to_evidence(row) for row in rows]

    def upsert_narrative_profile(self, profile: CreatorNarrativeProfile) -> CreatorNarrativeProfile:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_narrative_profiles (
                    id, creator_id, analysis_run_id, profile_version, status, summary,
                    opening_profile_json, development_profile_json, explanation_profile_json,
                    humor_profile_json, pacing_profile_json, closing_profile_json,
                    platform_differences_json, content_type_differences_json,
                    limitations_json, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :analysis_run_id, :profile_version, :status, :summary,
                    :opening_profile_json, :development_profile_json, :explanation_profile_json,
                    :humor_profile_json, :pacing_profile_json, :closing_profile_json,
                    :platform_differences_json, :content_type_differences_json,
                    :limitations_json, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    analysis_run_id = excluded.analysis_run_id,
                    profile_version = excluded.profile_version,
                    status = excluded.status,
                    summary = excluded.summary,
                    opening_profile_json = excluded.opening_profile_json,
                    development_profile_json = excluded.development_profile_json,
                    explanation_profile_json = excluded.explanation_profile_json,
                    humor_profile_json = excluded.humor_profile_json,
                    pacing_profile_json = excluded.pacing_profile_json,
                    closing_profile_json = excluded.closing_profile_json,
                    platform_differences_json = excluded.platform_differences_json,
                    content_type_differences_json = excluded.content_type_differences_json,
                    limitations_json = excluded.limitations_json,
                    updated_at = excluded.updated_at
                """,
                {
                    **profile.to_dict(),
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM creator_narrative_profiles WHERE id = ?", (profile.id,)).fetchone()
        return _row_to_profile(row)

    def get_narrative_profile(self, creator_id: str) -> CreatorNarrativeProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_narrative_profiles WHERE creator_id = ? ORDER BY profile_version DESC, created_at DESC LIMIT 1",
                (creator_id,),
            ).fetchone()
        return _row_to_profile(row) if row else None

    def list_narrative_profiles(self, creator_id: str) -> list[CreatorNarrativeProfile]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_narrative_profiles WHERE creator_id = ? ORDER BY profile_version DESC, created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_profile(row) for row in rows]

    def upsert_candidate(self, candidate: CreatorLanguageCandidate) -> CreatorLanguageCandidate:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_candidates (
                    id, creator_id, analysis_run_id, candidate_type, target_memory_type,
                    proposed_key, proposed_value_json, scope, platform, content_type, topic,
                    evidence_json, confidence_level, status, review_reason, created_at, reviewed_at
                ) VALUES (
                    :id, :creator_id, :analysis_run_id, :candidate_type, :target_memory_type,
                    :proposed_key, :proposed_value_json, :scope, :platform, :content_type, :topic,
                    :evidence_json, :confidence_level, :status, :review_reason, :created_at, :reviewed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    review_reason = excluded.review_reason,
                    reviewed_at = excluded.reviewed_at,
                    proposed_value_json = excluded.proposed_value_json,
                    evidence_json = excluded.evidence_json
                """,
                {
                    **candidate.to_dict(),
                    "target_memory_type": candidate.target_memory_type.value,
                    "scope": candidate.scope.value,
                    "confidence_level": candidate.confidence_level.value,
                    "status": candidate.status.value,
                    "created_at": candidate.created_at.isoformat(),
                    "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
                },
            )
            row = connection.execute("SELECT * FROM creator_language_candidates WHERE id = ?", (candidate.id,)).fetchone()
        return _row_to_candidate(row)

    def list_candidates(self, creator_id: str) -> list[CreatorLanguageCandidate]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_candidates WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_candidate(row) for row in rows]

    def get_candidate(self, candidate_id: str) -> CreatorLanguageCandidate | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate(row) if row else None

    def upsert_profile_snapshot(self, snapshot: CreatorLanguageProfileSnapshot) -> CreatorLanguageProfileSnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_language_profile_snapshots (
                    id, creator_id, profile_version, snapshot_json, source_fingerprint, status, created_at
                ) VALUES (
                    :id, :creator_id, :profile_version, :snapshot_json, :source_fingerprint, :status, :created_at
                )
                ON CONFLICT(creator_id, profile_version) DO NOTHING
                """,
                {
                    **snapshot.to_dict(),
                    "status": snapshot.status,
                    "created_at": snapshot.created_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM creator_language_profile_snapshots WHERE creator_id = ? AND profile_version = ?",
                (snapshot.creator_id, snapshot.profile_version),
            ).fetchone()
        return _row_to_snapshot(row)

    def list_profile_snapshots(self, creator_id: str) -> list[CreatorLanguageProfileSnapshot]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_language_profile_snapshots WHERE creator_id = ? ORDER BY profile_version DESC, created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def get_profile_snapshot(self, snapshot_id: str) -> CreatorLanguageProfileSnapshot | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_language_profile_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return _row_to_snapshot(row) if row else None

    def compare_profile_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str) -> CreatorLanguageProfileComparison:
        base = self.get_profile_snapshot(base_snapshot_id)
        compare = self.get_profile_snapshot(compare_snapshot_id)
        if base is None or compare is None or base.creator_id != creator_id or compare.creator_id != creator_id:
            raise sqlite3.IntegrityError("Snapshot no encontrado o creator incompatible.")
        base_payload = _json_loads(base.snapshot_json, {})
        compare_payload = _json_loads(compare.snapshot_json, {})
        changed_sections = tuple(
            key for key in sorted(set(base_payload) | set(compare_payload))
            if base_payload.get(key) != compare_payload.get(key)
        )
        return CreatorLanguageProfileComparison(
            creator_id=creator_id,
            base_profile_version=base.profile_version,
            compare_profile_version=compare.profile_version,
            changed_sections=changed_sections,
            base_summary=base_payload,
            compare_summary=compare_payload,
        )

    def retrieve_context(self, creator_id: str, filters: CreatorLanguageQueryFilters) -> list[CreatorLanguageRetrievalResult]:
        results: list[CreatorLanguageRetrievalResult] = []
        with self._database.connect() as connection:
            pattern_rows = connection.execute(
                "SELECT * FROM creator_language_patterns WHERE creator_id = ? ORDER BY confidence_score DESC, frequency_count DESC, created_at DESC",
                (creator_id,),
            ).fetchall()
            candidate_rows = connection.execute(
                "SELECT * FROM creator_language_candidates WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
            source_rows = connection.execute(
                """
                SELECT source.* FROM creator_language_corpus_sources AS source
                JOIN creator_language_corpora AS corpus ON corpus.id = source.corpus_id
                WHERE corpus.creator_id = ? AND source.include_status = 'included'
                ORDER BY source.created_at DESC
                """,
                (creator_id,),
            ).fetchall()
        query = (filters.query or "").casefold().strip()
        for row in pattern_rows:
            pattern = _row_to_pattern(row)
            if filters.platform and pattern.platform != filters.platform:
                continue
            if filters.content_type and pattern.content_type != filters.content_type:
                continue
            if filters.topic and pattern.topic != filters.topic:
                continue
            if filters.status and pattern.status.value != filters.status:
                continue
            if query and query not in pattern.title.casefold() and query not in pattern.description.casefold():
                continue
            score = float(pattern.confidence_score or 0.0)
            if pattern.platform == filters.platform:
                score += 1.0
            if pattern.content_type == filters.content_type:
                score += 0.75
            results.append(
                CreatorLanguageRetrievalResult(
                    item_type="pattern",
                    item_id=pattern.id,
                    title=pattern.title,
                    summary=pattern.description,
                    scope=pattern.scope.value,
                    platform=pattern.platform,
                    content_type=pattern.content_type,
                    topic=pattern.topic,
                    confidence_level=pattern.confidence_level.value,
                    score=score,
                    evidence_weight=float(pattern.supporting_example_count),
                    warnings=(),
                    payload=pattern.to_dict(),
                )
            )
        for row in candidate_rows:
            candidate = _row_to_candidate(row)
            if filters.platform and candidate.platform != filters.platform:
                continue
            if filters.content_type and candidate.content_type != filters.content_type:
                continue
            if filters.topic and candidate.topic != filters.topic:
                continue
            if filters.status and candidate.status.value != filters.status:
                continue
            if query and query not in candidate.proposed_key.casefold() and query not in candidate.proposed_value_json.casefold():
                continue
            score = 0.5
            if candidate.status == CreatorLanguageCandidateStatus.APPROVED:
                score += 1.0
            elif candidate.status == CreatorLanguageCandidateStatus.APPROVED_WITH_CHANGES:
                score += 0.8
            results.append(
                CreatorLanguageRetrievalResult(
                    item_type="candidate",
                    item_id=candidate.id,
                    title=candidate.proposed_key,
                    summary=candidate.review_reason or candidate.proposed_value_json,
                    scope=candidate.scope.value,
                    platform=candidate.platform,
                    content_type=candidate.content_type,
                    topic=candidate.topic,
                    confidence_level=candidate.confidence_level.value,
                    score=score,
                    evidence_weight=float(len(_json_loads(candidate.evidence_json, []))),
                    warnings=(),
                    payload=candidate.to_dict(),
                )
            )
        for row in source_rows:
            source = _row_to_source(row)
            if filters.platform and source.platform != filters.platform:
                continue
            if filters.content_type and source.content_type != filters.content_type:
                continue
            if filters.topic and source.topic != filters.topic:
                continue
            if query and query not in source.text_snapshot.casefold():
                continue
            results.append(
                CreatorLanguageRetrievalResult(
                    item_type="source",
                    item_id=source.id,
                    title=source.source_type.value,
                    summary=source.text_snapshot[:180],
                    scope="source",
                    platform=source.platform,
                    content_type=source.content_type,
                    topic=source.topic,
                    confidence_level="low",
                    score=0.2,
                    evidence_weight=1.0,
                    warnings=(),
                    payload=source.to_dict(),
                )
            )
        results.sort(key=lambda item: (item.score, item.evidence_weight), reverse=True)
        return results
