"""Servicio de aplicacion para ranking de clips."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.multimodal_analysis_service import MultimodalAnalysisReport, MultimodalAnalysisService
from creator_intelligence_studio.domain.clip_ranking.entities import (
    ClipCollection,
    ClipCollectionItem,
    ClipRankingRun,
    ClipReviewEvent,
    RankedClipCandidate,
)
from creator_intelligence_studio.domain.clip_ranking.errors import ClipRankingStateError, ClipRankingValidationError
from creator_intelligence_studio.domain.clip_ranking.repositories import ClipRankingRepository
from creator_intelligence_studio.domain.clip_ranking.services import (
    apply_profile_weights,
    build_clip_ranking_configuration_fingerprint,
    build_clip_ranking_source_fingerprint,
    is_clip_ranking_stale,
)
from creator_intelligence_studio.domain.clip_ranking.value_objects import (
    ClipRankingOptions,
    ClipRankingProfile,
    ClipRankingReviewStatus,
    ClipRankingRunStatus,
)
from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.repositories import TranscriptionRepository
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.infrastructure.clip_ranking.diversity_filter import diversify_candidates
from creator_intelligence_studio.infrastructure.clip_ranking.explanation_builder import build_candidate_explanation
from creator_intelligence_studio.infrastructure.clip_ranking.export_planner import build_clip_export, clip_export_suffix
from creator_intelligence_studio.infrastructure.clip_ranking.overlap_resolver import compute_temporal_iou, resolve_overlaps
from creator_intelligence_studio.infrastructure.clip_ranking.rule_based_ranker import RankedCandidateDraft, score_clip_candidate
from creator_intelligence_studio.infrastructure.multimodal_analysis.timeline_aligner import overlap_ratio
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_default(value):
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _profile_from_string(profile: str) -> ClipRankingProfile:
    normalized = profile.strip().lower().replace("-", "_")
    aliases = {
        "balanced": ClipRankingProfile.BALANCED,
        "speech_focused": ClipRankingProfile.SPEECH_FOCUSED,
        "speech": ClipRankingProfile.SPEECH_FOCUSED,
        "visual_focused": ClipRankingProfile.VISUAL_FOCUSED,
        "visual": ClipRankingProfile.VISUAL_FOCUSED,
        "high_energy": ClipRankingProfile.HIGH_ENERGY,
        "energy": ClipRankingProfile.HIGH_ENERGY,
        "story_beats": ClipRankingProfile.STORY_BEATS,
        "story": ClipRankingProfile.STORY_BEATS,
    }
    if normalized not in aliases:
        raise ClipRankingValidationError("Perfil de ranking no reconocido.")
    return aliases[normalized]


def _snapshot_file(video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
    path = Path(video.source_path)
    if not path.exists() or not path.is_file():
        return False, None, None
    stat = path.stat()
    return True, stat.st_size, datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ClipRankingReport:
    """Estado y resultado del ranking de clips."""

    video: VideoAsset
    multimodal_report: MultimodalAnalysisReport | None
    run: ClipRankingRun | None
    candidates: tuple[RankedClipCandidate, ...]
    status: ClipRankingRunStatus
    is_stale: bool
    available_sources: tuple[str, ...] = ()
    missing_sources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "multimodal_report": self.multimodal_report.to_dict() if self.multimodal_report else None,
            "run": self.run.to_dict() if self.run else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "available_sources": list(self.available_sources),
            "missing_sources": list(self.missing_sources),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class ClipRankingExportResult:
    """Resultado de exportacion de ranking de clips."""

    video: VideoAsset
    run: ClipRankingRun
    format: str
    content: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "run": self.run.to_dict(),
            "format": self.format,
            "content": self.content,
            "path": self.path,
        }


class ClipRankingService:
    """Orquesta ranking de clips, revision humana y exportacion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        multimodal_service: MultimodalAnalysisService,
        transcription_repository: TranscriptionRepository,
        clip_repository: ClipRankingRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.multimodal_service = multimodal_service
        self.transcription_repository = transcription_repository
        self.clip_repository = clip_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.clips")
        self.options = apply_profile_weights(ClipRankingOptions())

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.catalog_service.get_video(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _current_multimodal_report(self, video_id: str) -> MultimodalAnalysisReport | None:
        try:
            return self.multimodal_service.get_multimodal_analysis(video_id)
        except NotFoundError:
            return None

    def _current_transcription(self, video_id: str) -> Transcription | None:
        transcription = self.transcription_repository.get_by_video_asset_id(video_id)
        return transcription if transcription is not None and transcription.status == TranscriptionStatus.COMPLETED else None

    def _analysis_sources(
        self,
        report: MultimodalAnalysisReport | None,
    ) -> tuple[str, ...]:
        if report is None:
            return ()
        sources: list[str] = []
        if report.transcription is not None:
            sources.append("transcription")
        if report.acoustic_analysis is not None:
            sources.append("acoustic")
        if report.visual_analysis is not None:
            sources.append("visual")
        return tuple(sources)

    def _missing_sources(self, report: MultimodalAnalysisReport | None) -> tuple[str, ...]:
        if report is None:
            return ("multimodal",)
        sources = []
        if report.transcription is None:
            sources.append("transcription")
        if report.acoustic_analysis is None:
            sources.append("acoustic")
        if report.visual_analysis is None:
            sources.append("visual")
        return tuple(sources)

    def _ranking_root(self, video_id: str) -> Path:
        return self.paths.project_root / "cache" / "clips" / video_id / "exports"

    def _load_previous_candidates(self, video_id: str) -> tuple[ClipRankingRun | None, list[RankedClipCandidate]]:
        run = self.clip_repository.get_by_video_asset_id(video_id)
        if run is None:
            return None, []
        return run, self.clip_repository.list_candidates(run.id)

    def _transcription_segments(self, report: MultimodalAnalysisReport | None) -> list[TranscriptionSegment]:
        if report is None or report.transcription is None:
            return []
        transcription = self.transcription_repository.get_by_id(report.transcription.id)
        if transcription is None or transcription.status != TranscriptionStatus.COMPLETED:
            return []
        return self.transcription_repository.list_segments(transcription.id)

    def _segments_for_candidate(self, segments: list[TranscriptionSegment], start_seconds: float, end_seconds: float) -> list[TranscriptionSegment]:
        return [
            segment
            for segment in segments
            if overlap_ratio(start_seconds, end_seconds, segment.start_seconds, segment.end_seconds) > 0.0
        ]

    def _adjust_bounds(
        self,
        candidate: RankedCandidateDraft,
        segments: list[TranscriptionSegment],
        report: MultimodalAnalysisReport | None,
    ) -> tuple[float, float, list[str]]:
        adjusted_start = candidate.original_start_seconds
        adjusted_end = candidate.original_end_seconds
        notes: list[str] = []
        segment_matches = self._segments_for_candidate(segments, candidate.original_start_seconds, candidate.original_end_seconds)
        if segment_matches:
            new_start = min(segment.start_seconds for segment in segment_matches)
            new_end = max(segment.end_seconds for segment in segment_matches)
            if new_start < adjusted_start:
                adjusted_start = new_start
                notes.append("inicio ajustado a limite de transcripcion")
            if new_end > adjusted_end:
                adjusted_end = new_end
                notes.append("fin ajustado a limite de transcripcion")
        if report is not None and report.analysis is not None and report.candidates:
            if candidate.duration_seconds < self.options.minimum_duration_seconds:
                candidate_windows = [
                    window
                    for window in report.windows
                    if overlap_ratio(candidate.original_start_seconds, candidate.original_end_seconds, window.start_seconds, window.end_seconds) > 0.0
                ]
                if candidate_windows:
                    adjusted_start = min(adjusted_start, candidate_windows[0].start_seconds)
                    adjusted_end = max(adjusted_end, candidate_windows[-1].end_seconds)
                    notes.append("bordes ampliados por continuidad multimodal")
        if adjusted_end <= adjusted_start:
            adjusted_end = adjusted_start + max(1.0, candidate.duration_seconds or self.options.minimum_duration_seconds)
            notes.append("bordes corregidos por duracion minima")
        return adjusted_start, adjusted_end, notes

    def _match_previous_candidate(
        self,
        draft: RankedCandidateDraft,
        previous_candidates: list[RankedClipCandidate],
    ) -> tuple[RankedClipCandidate | None, str | None]:
        by_source = [candidate for candidate in previous_candidates if candidate.multimodal_candidate_id == draft.multimodal_candidate_id]
        if by_source:
            return by_source[0], "source"
        best: tuple[float, RankedClipCandidate] | None = None
        for candidate in previous_candidates:
            iou = compute_temporal_iou(
                draft.adjusted_start_seconds,
                draft.adjusted_end_seconds,
                candidate.adjusted_start_seconds,
                candidate.adjusted_end_seconds,
            )
            if iou < 0.35:
                continue
            if best is None or iou > best[0]:
                best = (iou, candidate)
        if best is not None:
            return best[1], "overlap"
        return None, None

    def _migrate_feedback(
        self,
        drafts: list[RankedCandidateDraft],
        previous_candidates: list[RankedClipCandidate],
    ) -> list[RankedCandidateDraft]:
        migrated: list[RankedCandidateDraft] = []
        for draft in drafts:
            previous, match_reason = self._match_previous_candidate(draft, previous_candidates)
            if previous is None:
                migrated.append(draft)
                continue
            explanation = dict(draft.explanation)
            explanation["feedback_migrated_from"] = previous.id
            explanation["feedback_migration_reason"] = match_reason
            preserve_adjusted_bounds = previous.review_status != ClipRankingReviewStatus.UNREVIEWED or previous.user_rating is not None or previous.user_note or previous.tags
            migrated.append(
                RankedCandidateDraft(
                    multimodal_candidate_id=draft.multimodal_candidate_id,
                    original_start_seconds=draft.original_start_seconds,
                    original_end_seconds=draft.original_end_seconds,
                    adjusted_start_seconds=previous.adjusted_start_seconds if preserve_adjusted_bounds else draft.adjusted_start_seconds,
                    adjusted_end_seconds=previous.adjusted_end_seconds if preserve_adjusted_bounds else draft.adjusted_end_seconds,
                    duration_seconds=(previous.adjusted_end_seconds - previous.adjusted_start_seconds) if preserve_adjusted_bounds else draft.duration_seconds,
                    candidate_type=draft.candidate_type,
                    source_score=draft.source_score,
                    source_confidence=draft.source_confidence,
                    rank_score=draft.rank_score,
                    quality_score=draft.quality_score,
                    diversity_score=draft.diversity_score,
                    overlap_penalty=draft.overlap_penalty,
                    duration_score=draft.duration_score,
                    opening_score=draft.opening_score,
                    closing_score=draft.closing_score,
                    speech_score=draft.speech_score,
                    visual_score=draft.visual_score,
                    acoustic_score=draft.acoustic_score,
                    transition_score=draft.transition_score,
                    novelty_score=draft.novelty_score,
                    evidence_strength_score=draft.evidence_strength_score,
                    review_status=previous.review_status.value,
                    user_rating=previous.user_rating,
                    user_note=previous.user_note,
                    explanation=explanation,
                    tags=previous.tags,
                    transcript_text=draft.transcript_text,
                    scene_index=draft.scene_index,
                    source_window_start=draft.source_window_start,
                    source_window_end=draft.source_window_end,
                )
            )
        return migrated

    def _to_entity_candidates(
        self,
        *,
        run_id: str,
        drafts: list[RankedCandidateDraft],
        previous_candidates: list[RankedClipCandidate],
    ) -> list[RankedClipCandidate]:
        entities: list[RankedClipCandidate] = []
        for index, draft in enumerate(sorted(drafts, key=lambda item: (-item.rank_score, item.adjusted_start_seconds, item.adjusted_end_seconds, item.multimodal_candidate_id))):
            previous, _ = self._match_previous_candidate(draft, previous_candidates)
            candidate_id = previous.id if previous is not None else str(uuid4())
            entity = RankedClipCandidate(
                id=candidate_id,
                ranking_run_id=run_id,
                multimodal_candidate_id=draft.multimodal_candidate_id,
                rank_position=index + 1,
                original_start_seconds=draft.original_start_seconds,
                original_end_seconds=draft.original_end_seconds,
                adjusted_start_seconds=draft.adjusted_start_seconds,
                adjusted_end_seconds=draft.adjusted_end_seconds,
                duration_seconds=max(0.0, draft.adjusted_end_seconds - draft.adjusted_start_seconds),
                candidate_type=draft.candidate_type,
                source_score=draft.source_score,
                source_confidence=draft.source_confidence,
                rank_score=draft.rank_score,
                quality_score=draft.quality_score,
                diversity_score=draft.diversity_score,
                overlap_penalty=draft.overlap_penalty,
                duration_score=draft.duration_score,
                opening_score=draft.opening_score,
                closing_score=draft.closing_score,
                speech_score=draft.speech_score,
                visual_score=draft.visual_score,
                acoustic_score=draft.acoustic_score,
                transition_score=draft.transition_score,
                novelty_score=draft.novelty_score,
                evidence_strength_score=draft.evidence_strength_score,
                review_status=ClipRankingReviewStatus(draft.review_status),
                user_rating=draft.user_rating,
                user_note=draft.user_note,
                explanation=draft.explanation,
                tags=draft.tags,
                created_at=previous.created_at if previous is not None else utc_now(),
                updated_at=utc_now(),
            )
            entities.append(entity)
        return entities

    def _build_run(
        self,
        *,
        video: VideoAsset,
        creator_id: str,
        report: MultimodalAnalysisReport,
        candidates: list[RankedClipCandidate],
        options: ClipRankingOptions,
        existing: ClipRankingRun | None,
    ) -> ClipRankingRun:
        now = utc_now()
        created_at = existing.created_at if existing is not None else now
        started_at = existing.started_at if existing is not None else now
        review_count = sum(1 for candidate in candidates if candidate.review_status != ClipRankingReviewStatus.UNREVIEWED)
        selected_count = sum(1 for candidate in candidates if candidate.review_status in {ClipRankingReviewStatus.APPROVED, ClipRankingReviewStatus.SHORTLISTED})
        rejected_count = sum(1 for candidate in candidates if candidate.review_status in {ClipRankingReviewStatus.REJECTED, ClipRankingReviewStatus.DUPLICATE, ClipRankingReviewStatus.INVALID})
        run_id = existing.id if existing is not None else str(uuid4())
        return ClipRankingRun(
            id=run_id,
            video_asset_id=video.id,
            multimodal_analysis_id=report.analysis.id if report.analysis else "",
            creator_id=creator_id,
            project_id=video.project_id,
            status=ClipRankingRunStatus.COMPLETED,
            ranker_version=options.ranker_version,
            configuration_fingerprint=build_clip_ranking_configuration_fingerprint(options),
            source_fingerprint=build_clip_ranking_source_fingerprint(
                multimodal_analysis=report.analysis,
                multimodal_candidates=list(report.candidates),
                options=options,
            ),
            candidate_count=len(report.candidates),
            ranked_candidate_count=len(candidates),
            selected_count=selected_count,
            rejected_count=rejected_count,
            review_count=review_count,
            started_at=started_at,
            completed_at=now,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=created_at,
            updated_at=now,
        )

    def _current_report(
        self,
        video_id: str,
        *,
        force: bool = False,
        profile: str | None = None,
    ) -> ClipRankingReport:
        video = self._require_video(video_id)
        report = self._current_multimodal_report(video_id)
        run, candidates = self._load_previous_candidates(video_id)
        if run is not None and report is not None and not force and not is_clip_ranking_stale(run, multimodal_analysis=report.analysis, multimodal_candidates=list(report.candidates), options=self.options):
            return ClipRankingReport(
                video=video,
                multimodal_report=report,
                run=run,
                candidates=tuple(candidates),
                status=run.status,
                is_stale=False,
                available_sources=self._analysis_sources(report),
                missing_sources=self._missing_sources(report),
            )
        stale = run is not None and report is not None and is_clip_ranking_stale(run, multimodal_analysis=report.analysis, multimodal_candidates=list(report.candidates), options=self.options)
        return ClipRankingReport(
            video=video,
            multimodal_report=report,
            run=run,
            candidates=tuple(candidates),
            status=run.status if run else ClipRankingRunStatus.NOT_RANKED,
            is_stale=stale,
            available_sources=self._analysis_sources(report),
            missing_sources=self._missing_sources(report),
        )

    def rank_clip_candidates(self, video_id: str, profile: str = "balanced", force: bool = False, *, progress_callback=None) -> ClipRankingReport:
        video = self._require_video(video_id)
        if progress_callback is not None:
            progress_callback("Cargando candidatos", 0.1)
        report = self._current_multimodal_report(video_id)
        if report is None or report.analysis is None or not report.candidates:
            raise ClipRankingStateError("No existen candidatos multimodales disponibles para el ranking de clips.")
        profile_enum = _profile_from_string(profile)
        options = apply_profile_weights(
            ClipRankingOptions(
                profile=profile_enum,
                ranker_version=self.options.ranker_version,
                source_fingerprint_version=self.options.source_fingerprint_version,
                minimum_duration_seconds=self.options.minimum_duration_seconds,
                recommended_duration_seconds=self.options.recommended_duration_seconds,
                target_short_duration_seconds=self.options.target_short_duration_seconds,
                target_medium_duration_seconds=self.options.target_medium_duration_seconds,
                maximum_duration_seconds=self.options.maximum_duration_seconds,
                iou_duplicate_threshold=self.options.iou_duplicate_threshold,
                iou_overlap_threshold=self.options.iou_overlap_threshold,
                diversity_min_gap_seconds=self.options.diversity_min_gap_seconds,
                diversity_window_seconds=self.options.diversity_window_seconds,
            )
        )
        existing_run = self.clip_repository.get_by_video_asset_id(video.id)
        if existing_run is not None and not force and not is_clip_ranking_stale(existing_run, multimodal_analysis=report.analysis, multimodal_candidates=list(report.candidates), options=options):
            return self.get_ranking_run(video.id)

        transcription = self._current_transcription(video.id)
        segments = self._transcription_segments(report)
        if progress_callback is not None:
            progress_callback("Calculando scores", 0.3)
        drafts: list[RankedCandidateDraft] = []
        for candidate in report.candidates:
            windows = [
                window
                for window in report.windows
                if overlap_ratio(candidate.start_seconds, candidate.end_seconds, window.start_seconds, window.end_seconds) > 0.0
            ]
            draft = score_clip_candidate(candidate, windows=windows, transcription_segments=segments, options=options)
            adjusted_start, adjusted_end, notes = self._adjust_bounds(draft, segments, report)
            explanation = dict(draft.explanation)
            if notes:
                explanation["boundary_adjustments"] = notes
            draft = RankedCandidateDraft(
                multimodal_candidate_id=draft.multimodal_candidate_id,
                original_start_seconds=draft.original_start_seconds,
                original_end_seconds=draft.original_end_seconds,
                adjusted_start_seconds=adjusted_start,
                adjusted_end_seconds=adjusted_end,
                duration_seconds=max(0.0, adjusted_end - adjusted_start),
                candidate_type=draft.candidate_type,
                source_score=draft.source_score,
                source_confidence=draft.source_confidence,
                rank_score=draft.rank_score,
                quality_score=draft.quality_score,
                diversity_score=draft.diversity_score,
                overlap_penalty=draft.overlap_penalty,
                duration_score=draft.duration_score,
                opening_score=draft.opening_score,
                closing_score=draft.closing_score,
                speech_score=draft.speech_score,
                visual_score=draft.visual_score,
                acoustic_score=draft.acoustic_score,
                transition_score=draft.transition_score,
                novelty_score=draft.novelty_score,
                evidence_strength_score=draft.evidence_strength_score,
                review_status=draft.review_status,
                user_rating=draft.user_rating,
                user_note=draft.user_note,
                explanation=explanation,
                tags=draft.tags,
                transcript_text=draft.transcript_text,
                scene_index=draft.scene_index,
                source_window_start=draft.source_window_start,
                source_window_end=draft.source_window_end,
            )
            drafts.append(draft)
        if progress_callback is not None:
            progress_callback("Resolviendo solapamientos", 0.55)
        drafts = resolve_overlaps(drafts, options)
        if progress_callback is not None:
            progress_callback("Aplicando diversidad", 0.75)
        drafts = diversify_candidates(drafts, options)
        if progress_callback is not None:
            progress_callback("Migrando feedback previo", 0.85)
        previous_candidates = list(self.clip_repository.list_candidates(existing_run.id)) if existing_run is not None else []
        drafts = self._migrate_feedback(drafts, previous_candidates)
        if progress_callback is not None:
            progress_callback("Guardando ranking", 0.95)
        project = self.catalog_service.get_project(video.project_id)
        resolved_run = self._build_run(video=video, creator_id=project.creator_id, report=report, candidates=[], options=options, existing=existing_run)
        candidate_entities = self._to_entity_candidates(run_id=resolved_run.id, drafts=drafts, previous_candidates=previous_candidates)
        resolved_run = ClipRankingRun(
            id=resolved_run.id,
            video_asset_id=resolved_run.video_asset_id,
            multimodal_analysis_id=resolved_run.multimodal_analysis_id,
            creator_id=project.creator_id,
            project_id=video.project_id,
            status=ClipRankingRunStatus.COMPLETED,
            ranker_version=resolved_run.ranker_version,
            configuration_fingerprint=resolved_run.configuration_fingerprint,
            source_fingerprint=resolved_run.source_fingerprint,
            candidate_count=resolved_run.candidate_count,
            ranked_candidate_count=len(candidate_entities),
            selected_count=sum(1 for candidate in candidate_entities if candidate.review_status in {ClipRankingReviewStatus.APPROVED, ClipRankingReviewStatus.SHORTLISTED}),
            rejected_count=sum(1 for candidate in candidate_entities if candidate.review_status in {ClipRankingReviewStatus.REJECTED, ClipRankingReviewStatus.DUPLICATE, ClipRankingReviewStatus.INVALID}),
            review_count=sum(1 for candidate in candidate_entities if candidate.review_status != ClipRankingReviewStatus.UNREVIEWED),
            started_at=resolved_run.started_at,
            completed_at=utc_now(),
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=resolved_run.created_at,
            updated_at=utc_now(),
        )
        persisted_run = self.clip_repository.upsert(resolved_run, candidate_entities)
        if progress_callback is not None:
            progress_callback("Completado", 1.0)
        persisted_candidates = tuple(self.clip_repository.list_candidates(persisted_run.id))
        return ClipRankingReport(
            video=video,
            multimodal_report=report,
            run=persisted_run,
            candidates=persisted_candidates,
            status=persisted_run.status,
            is_stale=False,
            available_sources=self._analysis_sources(report),
            missing_sources=self._missing_sources(report),
            progress_message="Ranking completado",
        )

    def get_ranking_run(self, video_id: str) -> ClipRankingReport:
        video = self._require_video(video_id)
        report = self._current_multimodal_report(video_id)
        run = self.clip_repository.get_by_video_asset_id(video_id)
        if run is None:
            return ClipRankingReport(
                video=video,
                multimodal_report=report,
                run=None,
                candidates=(),
                status=ClipRankingRunStatus.NOT_RANKED,
                is_stale=False,
                available_sources=self._analysis_sources(report),
                missing_sources=self._missing_sources(report),
            )
        candidates = tuple(self.clip_repository.list_candidates(run.id))
        stale = is_clip_ranking_stale(run, multimodal_analysis=report.analysis if report else None, multimodal_candidates=list(report.candidates) if report else None, options=self.options)
        status = ClipRankingRunStatus.STALE if stale else run.status
        return ClipRankingReport(
            video=video,
            multimodal_report=report,
            run=run,
            candidates=candidates,
            status=status,
            is_stale=stale,
            available_sources=self._analysis_sources(report),
            missing_sources=self._missing_sources(report),
        )

    def list_ranked_candidates(self, video_id: str, filters=None, sort=None) -> list[RankedClipCandidate]:
        report = self.get_ranking_run(video_id)
        candidates = list(report.candidates)
        if filters:
            review_status = getattr(filters, "review_status", None) if not isinstance(filters, dict) else filters.get("review_status")
            candidate_type = getattr(filters, "candidate_type", None) if not isinstance(filters, dict) else filters.get("candidate_type")
            min_score = getattr(filters, "min_score", None) if not isinstance(filters, dict) else filters.get("min_score")
            max_score = getattr(filters, "max_score", None) if not isinstance(filters, dict) else filters.get("max_score")
            rating = getattr(filters, "rating", None) if not isinstance(filters, dict) else filters.get("rating")
            tags = getattr(filters, "tags", None) if not isinstance(filters, dict) else filters.get("tags")
            min_duration = getattr(filters, "min_duration", None) if not isinstance(filters, dict) else filters.get("min_duration")
            max_duration = getattr(filters, "max_duration", None) if not isinstance(filters, dict) else filters.get("max_duration")
            has_transcription = getattr(filters, "has_transcription", None) if not isinstance(filters, dict) else filters.get("has_transcription")
            if review_status:
                candidates = [candidate for candidate in candidates if candidate.review_status.value == str(review_status)]
            if candidate_type:
                candidates = [candidate for candidate in candidates if candidate.candidate_type == str(candidate_type)]
            if min_score is not None:
                candidates = [candidate for candidate in candidates if candidate.rank_score >= float(min_score)]
            if max_score is not None:
                candidates = [candidate for candidate in candidates if candidate.rank_score <= float(max_score)]
            if rating is not None:
                candidates = [candidate for candidate in candidates if candidate.user_rating == int(rating)]
            if tags:
                required = {str(tag).strip().lower() for tag in (tags if isinstance(tags, (list, tuple, set)) else str(tags).split(",")) if str(tag).strip()}
                candidates = [candidate for candidate in candidates if required.issubset({tag.lower() for tag in candidate.tags})]
            if min_duration is not None:
                candidates = [candidate for candidate in candidates if candidate.duration_seconds >= float(min_duration)]
            if max_duration is not None:
                candidates = [candidate for candidate in candidates if candidate.duration_seconds <= float(max_duration)]
            if has_transcription is True:
                candidates = [candidate for candidate in candidates if candidate.explanation.get("transcript_text")]
            if has_transcription is False:
                candidates = [candidate for candidate in candidates if not candidate.explanation.get("transcript_text")]
        sort_key = str(sort or "rank").strip().lower()
        if sort_key in {"time", "timestamp"}:
            candidates.sort(key=lambda candidate: (candidate.adjusted_start_seconds, candidate.adjusted_end_seconds, candidate.rank_position))
        elif sort_key == "score":
            candidates.sort(key=lambda candidate: (-candidate.rank_score, candidate.adjusted_start_seconds, candidate.rank_position))
        elif sort_key == "duration":
            candidates.sort(key=lambda candidate: (-candidate.duration_seconds, candidate.adjusted_start_seconds, candidate.rank_position))
        elif sort_key == "rating":
            candidates.sort(key=lambda candidate: (-(candidate.user_rating or 0), -candidate.rank_score, candidate.rank_position))
        elif sort_key == "review":
            candidates.sort(key=lambda candidate: (candidate.review_status.value, -candidate.rank_score, candidate.rank_position))
        else:
            candidates.sort(key=lambda candidate: (candidate.rank_position, candidate.adjusted_start_seconds))
        return candidates

    def get_ranked_candidate(self, candidate_id: str) -> RankedClipCandidate:
        candidate = self.clip_repository.get_candidate_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("El candidato solicitado no existe.")
        return candidate

    def _update_candidate(
        self,
        candidate_id: str,
        *,
        action: str,
        status: ClipRankingReviewStatus | None = None,
        rating: int | None = None,
        note: str | None = None,
        tags: tuple[str, ...] | None = None,
        start_seconds: float | None = None,
        end_seconds: float | None = None,
        reset: bool = False,
    ) -> RankedClipCandidate:
        candidate = self.get_ranked_candidate(candidate_id)
        previous = candidate
        if rating is not None and not 1 <= rating <= 5:
            raise ClipRankingValidationError("rating debe estar entre 1 y 5.")
        new_status = status or candidate.review_status
        new_rating = None if reset else (rating if rating is not None else candidate.user_rating)
        new_note = None if reset else (note if note is not None else candidate.user_note)
        new_tags = tuple(tags) if tags is not None else (() if reset else candidate.tags)
        new_start = candidate.adjusted_start_seconds if start_seconds is None else float(start_seconds)
        new_end = candidate.adjusted_end_seconds if end_seconds is None else float(end_seconds)
        if new_end <= new_start:
            raise ClipRankingValidationError("adjusted_end_seconds debe ser mayor que adjusted_start_seconds.")
        updated = RankedClipCandidate(
            id=candidate.id,
            ranking_run_id=candidate.ranking_run_id,
            multimodal_candidate_id=candidate.multimodal_candidate_id,
            rank_position=candidate.rank_position,
            original_start_seconds=candidate.original_start_seconds,
            original_end_seconds=candidate.original_end_seconds,
            adjusted_start_seconds=new_start,
            adjusted_end_seconds=new_end,
            duration_seconds=new_end - new_start,
            candidate_type=candidate.candidate_type,
            source_score=candidate.source_score,
            source_confidence=candidate.source_confidence,
            rank_score=candidate.rank_score,
            quality_score=candidate.quality_score,
            diversity_score=candidate.diversity_score,
            overlap_penalty=candidate.overlap_penalty,
            duration_score=candidate.duration_score,
            opening_score=candidate.opening_score,
            closing_score=candidate.closing_score,
            speech_score=candidate.speech_score,
            visual_score=candidate.visual_score,
            acoustic_score=candidate.acoustic_score,
            transition_score=candidate.transition_score,
            novelty_score=candidate.novelty_score,
            evidence_strength_score=candidate.evidence_strength_score,
            review_status=new_status,
            user_rating=new_rating,
            user_note=new_note,
            explanation=dict(candidate.explanation),
            tags=new_tags,
            created_at=candidate.created_at,
            updated_at=utc_now(),
        )
        persisted = self.clip_repository.upsert_candidate(updated)
        events = self.clip_repository.list_review_events(candidate.id)
        event = ClipReviewEvent(
            id=str(uuid4()),
            ranked_clip_candidate_id=candidate.id,
            event_index=len(events),
            action=action,
            previous_status=previous.review_status,
            new_status=persisted.review_status,
            previous_start_seconds=previous.adjusted_start_seconds,
            previous_end_seconds=previous.adjusted_end_seconds,
            new_start_seconds=persisted.adjusted_start_seconds,
            new_end_seconds=persisted.adjusted_end_seconds,
            rating=rating if rating is not None else persisted.user_rating,
            note=note if note is not None else persisted.user_note,
            tags=new_tags,
            created_at=utc_now(),
        )
        self.clip_repository.append_review_event(event)
        return persisted

    def approve_candidate(self, candidate_id: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="approve_candidate", status=ClipRankingReviewStatus.APPROVED)

    def reject_candidate(self, candidate_id: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="reject_candidate", status=ClipRankingReviewStatus.REJECTED)

    def shortlist_candidate(self, candidate_id: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="shortlist_candidate", status=ClipRankingReviewStatus.SHORTLISTED)

    def mark_candidate_needs_review(self, candidate_id: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="mark_needs_review", status=ClipRankingReviewStatus.NEEDS_REVIEW)

    def rate_candidate(self, candidate_id: str, rating: int) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="rate_candidate", rating=rating)

    def add_candidate_note(self, candidate_id: str, note: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="add_candidate_note", note=note)

    def set_candidate_tags(self, candidate_id: str, tags: list[str]) -> RankedClipCandidate:
        normalized = tuple(sorted({tag.strip() for tag in tags if tag and tag.strip()}))
        return self._update_candidate(candidate_id, action="set_candidate_tags", tags=normalized)

    def adjust_candidate_bounds(self, candidate_id: str, start_seconds: float, end_seconds: float) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="adjust_candidate_bounds", start_seconds=start_seconds, end_seconds=end_seconds)

    def reset_candidate_review(self, candidate_id: str) -> RankedClipCandidate:
        return self._update_candidate(candidate_id, action="reset_candidate_review", status=ClipRankingReviewStatus.UNREVIEWED, reset=True)

    def get_candidate_review_history(self, candidate_id: str) -> list[ClipReviewEvent]:
        return self.clip_repository.list_review_events(candidate_id)

    def is_clip_ranking_stale(self, video_id: str) -> bool:
        run = self.clip_repository.get_by_video_asset_id(video_id)
        report = self._current_multimodal_report(video_id)
        if run is None:
            return False
        if report is None or report.analysis is None:
            return True
        return is_clip_ranking_stale(run, multimodal_analysis=report.analysis, multimodal_candidates=list(report.candidates), options=self.options)

    def delete_clip_ranking(self, video_id: str) -> bool:
        return self.clip_repository.delete_by_video_asset_id(video_id)

    def create_clip_collection(self, video_id: str, name: str, description: str | None = None) -> ClipCollection:
        video = self._require_video(video_id)
        now = utc_now()
        collection = ClipCollection(
            id=str(uuid4()),
            video_asset_id=video.id,
            name=name.strip(),
            description=description,
            status="active",
            created_at=now,
            updated_at=now,
        )
        return self.clip_repository.upsert_collection(collection)

    def add_candidate_to_collection(self, collection_id: str, candidate_id: str) -> ClipCollectionItem:
        collection = self.clip_repository.get_collection_by_id(collection_id)
        candidate = self.get_ranked_candidate(candidate_id)
        if collection is None:
            raise NotFoundError("La coleccion solicitada no existe.")
        run = self.clip_repository.get_by_id(candidate.ranking_run_id)
        if run is None or run.video_asset_id != collection.video_asset_id:
            raise ClipRankingStateError("El candidato no pertenece al video de la coleccion.")
        existing_items = self.clip_repository.list_collection_items(collection_id)
        index = len(existing_items)
        item = ClipCollectionItem(
            id=str(uuid4()),
            collection_id=collection_id,
            ranked_clip_candidate_id=candidate_id,
            item_index=index,
            custom_title=None,
            custom_note=None,
            created_at=utc_now(),
        )
        return self.clip_repository.add_collection_item(item)

    def remove_candidate_from_collection(self, collection_id: str, candidate_id: str) -> bool:
        return self.clip_repository.remove_collection_item(collection_id, candidate_id)

    def export_clip_plan(self, video_id: str, format: str, *, destination: Path | None = None) -> ClipRankingExportResult:
        report = self.get_ranking_run(video_id)
        if report.run is None:
            raise ClipRankingStateError("No hay ranking de clips disponible para exportar.")
        candidates = list(report.candidates)
        content, suffix = build_clip_export(report.run, candidates, format)
        export_root = self._ranking_root(video_id)
        export_root.mkdir(parents=True, exist_ok=True)
        destination = destination or export_root / f"clip_plan.{clip_export_suffix(suffix)}"
        destination.write_text(content, encoding="utf-8")
        for candidate in candidates:
            persisted = self.clip_repository.upsert_candidate(
                RankedClipCandidate(
                    id=candidate.id,
                    ranking_run_id=candidate.ranking_run_id,
                    multimodal_candidate_id=candidate.multimodal_candidate_id,
                    rank_position=candidate.rank_position,
                    original_start_seconds=candidate.original_start_seconds,
                    original_end_seconds=candidate.original_end_seconds,
                    adjusted_start_seconds=candidate.adjusted_start_seconds,
                    adjusted_end_seconds=candidate.adjusted_end_seconds,
                    duration_seconds=candidate.duration_seconds,
                    candidate_type=candidate.candidate_type,
                    source_score=candidate.source_score,
                    source_confidence=candidate.source_confidence,
                    rank_score=candidate.rank_score,
                    quality_score=candidate.quality_score,
                    diversity_score=candidate.diversity_score,
                    overlap_penalty=candidate.overlap_penalty,
                    duration_score=candidate.duration_score,
                    opening_score=candidate.opening_score,
                    closing_score=candidate.closing_score,
                    speech_score=candidate.speech_score,
                    visual_score=candidate.visual_score,
                    acoustic_score=candidate.acoustic_score,
                    transition_score=candidate.transition_score,
                    novelty_score=candidate.novelty_score,
                    evidence_strength_score=candidate.evidence_strength_score,
                    review_status=ClipRankingReviewStatus.EXPORTED,
                    user_rating=candidate.user_rating,
                    user_note=candidate.user_note,
                    explanation=dict(candidate.explanation),
                    tags=candidate.tags,
                    created_at=candidate.created_at,
                    updated_at=utc_now(),
                )
            )
            event_index = len(self.clip_repository.list_review_events(candidate.id))
            self.clip_repository.append_review_event(
                ClipReviewEvent(
                    id=str(uuid4()),
                    ranked_clip_candidate_id=candidate.id,
                    event_index=event_index,
                    action="export_clip_plan",
                    previous_status=candidate.review_status,
                    new_status=ClipRankingReviewStatus.EXPORTED,
                    previous_start_seconds=candidate.adjusted_start_seconds,
                    previous_end_seconds=candidate.adjusted_end_seconds,
                    new_start_seconds=persisted.adjusted_start_seconds,
                    new_end_seconds=persisted.adjusted_end_seconds,
                    rating=persisted.user_rating,
                    note=persisted.user_note,
                    tags=persisted.tags,
                    created_at=utc_now(),
                )
            )
        return ClipRankingExportResult(
            video=report.video,
            run=report.run,
            format=suffix,
            content=content,
            path=str(destination),
        )


def build_clip_ranking_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    multimodal_service: MultimodalAnalysisService,
    transcription_repository: TranscriptionRepository,
    clip_repository: ClipRankingRepository,
    logger: logging.Logger | None = None,
) -> ClipRankingService:
    return ClipRankingService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        multimodal_service=multimodal_service,
        transcription_repository=transcription_repository,
        clip_repository=clip_repository,
        logger=logger,
    )
