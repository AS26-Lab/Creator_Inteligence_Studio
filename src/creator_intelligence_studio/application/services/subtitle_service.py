"""Servicio de aplicacion para subtitulos locales."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingService
from creator_intelligence_studio.application.services.transcription_service import TranscriptionReport, TranscriptionService
from creator_intelligence_studio.domain.clip_ranking.entities import RankedClipCandidate
from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError, StateError
from creator_intelligence_studio.domain.subtitles.entities import SubtitleCue, SubtitleEditEvent, SubtitleExport, SubtitleTrack
from creator_intelligence_studio.domain.subtitles.errors import SubtitleExportError, SubtitleImportError, SubtitleStateError, SubtitleValidationError
from creator_intelligence_studio.domain.subtitles.repositories import SubtitleRepository
from creator_intelligence_studio.domain.subtitles.services import (
    build_subtitle_configuration_fingerprint,
    build_subtitle_source_fingerprint,
    is_subtitle_track_stale,
    normalize_generation_options,
    normalize_subtitle_text,
    validate_subtitle_bounds,
    validate_subtitle_track,
)
from creator_intelligence_studio.domain.subtitles.value_objects import (
    SubtitleCueDraft,
    SubtitleCueValidationStatus,
    SubtitleExportFormat,
    SubtitleGenerationOptions,
    SubtitleSourceType,
    SubtitleTimingSource,
    SubtitleTrackStatus,
)
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.infrastructure.clip_rendering.filename_builder import sanitize_filename_component
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.subtitles.subtitle_exporter import SubtitleExporter
from creator_intelligence_studio.infrastructure.subtitles.subtitle_generator import SubtitleGenerator
from creator_intelligence_studio.infrastructure.subtitles.subtitle_importer import SubtitleImporter
from creator_intelligence_studio.infrastructure.subtitles.timing_validator import SubtitleTimingValidationResult, SubtitleTimingValidator
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fingerprint_text(text: str) -> str:
    return _fingerprint_bytes(text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SubtitleTrackReport:
    video: VideoAsset
    transcription: Transcription | None
    track: SubtitleTrack | None
    cues: tuple[SubtitleCue, ...]
    status: SubtitleTrackStatus
    is_stale: bool
    validation: SubtitleTimingValidationResult | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "transcription": self.transcription.to_dict() if self.transcription else None,
            "track": self.track.to_dict() if self.track else None,
            "cues": [cue.to_dict() for cue in self.cues],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "validation": {
                "cue_statuses": [status.value for status in self.validation.cue_statuses] if self.validation else [],
                "cue_warnings": [list(item) for item in self.validation.cue_warnings] if self.validation else [],
                "blocking_errors": list(self.validation.blocking_errors) if self.validation else [],
                "warnings": list(self.validation.warnings) if self.validation else [],
            }
            if self.validation
            else None,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class SubtitleExportResult:
    track: SubtitleTrack
    format: SubtitleExportFormat
    content: str
    path: str
    fingerprint: str
    verified: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "track": self.track.to_dict(),
            "format": self.format.value,
            "content": self.content,
            "path": self.path,
            "fingerprint": self.fingerprint,
            "verified": self.verified,
        }


class SubtitleService:
    """Coordina generacion, edicion, importacion y exportacion de subtitulos."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        transcription_service: TranscriptionService,
        clip_service: ClipRankingService,
        repository: SubtitleRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.transcription_service = transcription_service
        self.clip_service = clip_service
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.subtitles")
        self._generator = SubtitleGenerator()
        self._importer = SubtitleImporter()
        self._exporter = SubtitleExporter()
        self._validator = SubtitleTimingValidator()
        self._output_root = self.paths.project_root / "exports" / "subtitles"

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.catalog_service.get_video(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _all_videos(self) -> list[VideoAsset]:
        videos: list[VideoAsset] = []
        for creator in self.catalog_service.list_creators():
            for project in self.catalog_service.list_projects(creator.id):
                videos.extend(self.catalog_service.list_videos(project.id))
        return videos

    def _require_track(self, track_id: str) -> SubtitleTrack:
        track = self.repository.get_track_by_id(track_id)
        if track is None:
            raise NotFoundError("El track de subtitulos no existe.")
        return track

    def _require_cue(self, cue_id: str) -> SubtitleCue:
        cue = self.repository.get_cue_by_id(cue_id)
        if cue is None:
            raise NotFoundError("El cue de subtitulos no existe.")
        return cue

    def _current_transcription_report(self, video_id: str) -> TranscriptionReport:
        report = self.transcription_service.get_transcription(video_id)
        if report.transcription is None or report.status != TranscriptionStatus.COMPLETED:
            raise SubtitleStateError("No existe una transcripcion completada para generar subtitulos.")
        return report

    def _current_options(self, options: SubtitleGenerationOptions | None) -> SubtitleGenerationOptions:
        return normalize_generation_options(options or SubtitleGenerationOptions())

    def _candidate_for_track(self, candidate_id: str) -> RankedClipCandidate | None:
        candidate = self.clip_service.get_ranked_candidate(candidate_id)
        if candidate is None:
            raise NotFoundError("El candidato solicitado no existe.")
        return candidate

    def _ranking_run_video(self, candidate: RankedClipCandidate) -> VideoAsset:
        run = self.clip_service.get_ranking_run(candidate.ranking_run_id)
        if run is None:
            raise NotFoundError("No se pudo resolver el ranking del candidato.")
        return self._require_video(run.video_asset_id)

    def _source_bounds(self, candidate: RankedClipCandidate | None, transcription: Transcription) -> tuple[float, float]:
        if candidate is None:
            return 0.0, transcription.duration_seconds
        return candidate.adjusted_start_seconds, candidate.adjusted_end_seconds

    def _track_name(self, video: VideoAsset, *, candidate: RankedClipCandidate | None = None, custom_name: str | None = None) -> str:
        if custom_name:
            return sanitize_filename_component(custom_name, fallback="subtitles")
        if candidate is not None:
            title = candidate.explanation.get("title") if isinstance(candidate.explanation, dict) else None
            if title:
                return sanitize_filename_component(str(title), fallback="clip_subtitles")
        return sanitize_filename_component(video.title, fallback="subtitles")

    def _context_paths(self, video: VideoAsset) -> Path:
        project = self.catalog_service.get_project(video.project_id)
        if project is None:
            raise NotFoundError("El proyecto del video no existe.")
        creator = self.catalog_service.get_creator(project.creator_id)
        if creator is None:
            raise NotFoundError("El creador del video no existe.")
        root = (
            self._output_root
            / sanitize_filename_component(creator.slug, fallback="creator")
            / sanitize_filename_component(project.name, fallback="project")
            / sanitize_filename_component(video.title, fallback="video")
        )
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _safe_export_path(self, destination: Path) -> Path:
        root = self._output_root.resolve(strict=False)
        resolved = destination if destination.is_absolute() else root / destination
        resolved = resolved.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise SubtitleValidationError("La ruta de exportacion debe permanecer dentro del directorio administrado.")
        return resolved

    def _build_cue(self, track: SubtitleTrack, draft: SubtitleCueDraft, index: int, status: SubtitleCueValidationStatus, warnings: tuple[str, ...]) -> SubtitleCue:
        text = normalize_subtitle_text(draft.text)
        duration = max(0.001, draft.end_seconds - draft.start_seconds)
        character_count = len(text.replace("\n", " "))
        words = len(normalize_subtitle_text(draft.original_text).split())
        cps = character_count / duration
        wpm = (words / duration) * 60.0 if duration > 0 else 0.0
        return SubtitleCue(
            id=str(uuid4()),
            subtitle_track_id=track.id,
            cue_index=index,
            start_seconds=round(draft.start_seconds, 3),
            end_seconds=round(draft.end_seconds, 3),
            text=text,
            original_text=normalize_subtitle_text(draft.original_text),
            source_segment_ids_json=_json_dumps(list(draft.source_segment_ids)),
            speaker_label=draft.speaker_label,
            line_count=max(1, len(text.split("\n"))),
            character_count=character_count,
            characters_per_second=round(cps, 3),
            words_per_minute=round(wpm, 3),
            validation_status=status,
            warning_codes_json=_json_dumps(list(warnings)),
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    def _drafts_to_cues(self, track: SubtitleTrack, drafts: list[SubtitleCueDraft], validation: SubtitleTimingValidationResult) -> list[SubtitleCue]:
        cues: list[SubtitleCue] = []
        for index, draft in enumerate(drafts):
            status = validation.cue_statuses[index] if index < len(validation.cue_statuses) else SubtitleCueValidationStatus.WARNING
            warnings = validation.cue_warnings[index] if index < len(validation.cue_warnings) else ()
            cues.append(self._build_cue(track, draft, index, status, warnings))
        return cues

    def _validation_from_cues(self, track: SubtitleTrack, cues: list[SubtitleCue], options: SubtitleGenerationOptions) -> SubtitleTimingValidationResult:
        drafts = [
            SubtitleCueDraft(
                start_seconds=cue.start_seconds,
                end_seconds=cue.end_seconds,
                text=cue.text,
                original_text=cue.original_text,
                source_segment_ids=tuple(json.loads(cue.source_segment_ids_json) or ()),
                timing_source=SubtitleTimingSource.MANUAL,
                absolute_start_seconds=cue.start_seconds,
                absolute_end_seconds=cue.end_seconds,
                speaker_label=cue.speaker_label,
                warning_codes=tuple(json.loads(cue.warning_codes_json) or ()),
            )
            for cue in cues
        ]
        return self._validator.validate(drafts, options=options, source_duration_seconds=track.source_end_seconds - track.source_start_seconds)

    def _load_transcription_segments(self, transcription: Transcription) -> list[TranscriptionSegment]:
        stored = self.transcription_service.list_transcription_segments(transcription.id)
        return list(stored)

    def _generated_track(
        self,
        *,
        video: VideoAsset,
        transcription: Transcription,
        segments: list[TranscriptionSegment],
        options: SubtitleGenerationOptions,
        source_type: SubtitleSourceType,
        candidate: RankedClipCandidate | None = None,
        render_job_id: str | None = None,
        custom_name: str | None = None,
        existing: SubtitleTrack | None = None,
    ) -> tuple[SubtitleTrack, list[SubtitleCueDraft], tuple[str, ...], SubtitleTimingValidationResult]:
        clip_start, clip_end = self._source_bounds(candidate, transcription)
        generation = self._generator.generate(
            transcription=transcription,
            segments=segments,
            options=options,
            source_type=source_type,
            clip_start_seconds=clip_start,
            clip_end_seconds=clip_end,
        )
        source_fingerprint = build_subtitle_source_fingerprint(
            transcription,
            candidate=candidate,
            render_job_id=render_job_id,
            source_type=source_type,
            source_start_seconds=clip_start,
            source_end_seconds=clip_end,
        )
        track = SubtitleTrack(
            id=existing.id if existing else str(uuid4()),
            video_asset_id=video.id,
            transcription_id=transcription.id,
            ranked_clip_candidate_id=candidate.id if candidate else None,
            render_job_id=render_job_id,
            language=options.language,
            name=self._track_name(video, candidate=candidate, custom_name=custom_name),
            status=SubtitleTrackStatus.GENERATING,
            source_type=source_type,
            track_version=(existing.track_version + 1) if existing else 1,
            configuration_fingerprint=build_subtitle_configuration_fingerprint(options),
            source_fingerprint=source_fingerprint,
            source_start_seconds=clip_start,
            source_end_seconds=clip_end,
            cue_count=0,
            total_text_length=0,
            is_default=existing.is_default if existing else False,
            is_locked=False,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=existing.created_at if existing else utc_now(),
            updated_at=utc_now(),
            completed_at=None,
        )
        validation = self._validator.validate(list(generation.cues), options=options, source_duration_seconds=clip_end - clip_start)
        warnings = tuple(dict.fromkeys((*generation.warnings, *validation.warnings)))
        return track, list(generation.cues), warnings, validation

    def _persist_generation(
        self,
        *,
        track: SubtitleTrack,
        drafts: list[SubtitleCueDraft],
        warnings: tuple[str, ...],
        validation: SubtitleTimingValidationResult,
    ) -> SubtitleTrack:
        if validation.blocking_errors:
            failed = replace(
                track,
                status=SubtitleTrackStatus.FAILED,
                warning_code="blocking_validation_error",
                warning_message="; ".join(validation.blocking_errors),
                error_code="subtitle_validation_error",
                error_message="La segmentacion de subtitulos no pudo validarse.",
                cue_count=0,
                total_text_length=0,
                updated_at=utc_now(),
            )
            self.repository.upsert_track(failed)
            return failed
        cues = self._drafts_to_cues(track, drafts, validation)
        final_status = SubtitleTrackStatus.COMPLETED_WITH_WARNINGS if warnings or validation.warnings else SubtitleTrackStatus.COMPLETED
        persisted = replace(
            track,
            status=final_status,
            cue_count=len(cues),
            total_text_length=sum(len(cue.text.replace("\n", " ")) for cue in cues),
            warning_code="subtitle_warnings" if (warnings or validation.warnings) else None,
            warning_message=(warnings or validation.warnings)[0] if (warnings or validation.warnings) else None,
            error_code=None,
            error_message=None,
            completed_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.upsert_track(persisted)
        self.repository.delete_cues_for_track(persisted.id)
        persisted_cues = self.repository.upsert_cues(persisted.id, cues)
        event = SubtitleEditEvent(
            id=str(uuid4()),
            subtitle_track_id=persisted.id,
            subtitle_cue_id=None,
            event_index=len(self.repository.list_events_for_track(persisted.id)),
            action="generate_track",
            previous_json="{}",
            new_json=_json_dumps(persisted.to_dict()),
            note="Generacion inicial de subtitulos.",
            created_at=utc_now(),
        )
        self.repository.append_event(event)
        return replace(persisted, cue_count=len(persisted_cues), total_text_length=sum(len(cue.text.replace("\n", " ")) for cue in persisted_cues))

    def _stale_warning(self, report: TranscriptionReport) -> tuple[str, ...]:
        return ("source_stale",) if report.is_stale else ()

    def _report(
        self,
        *,
        video: VideoAsset,
        transcription: Transcription | None,
        track: SubtitleTrack | None,
        cues: list[SubtitleCue],
        validation: SubtitleTimingValidationResult | None,
        is_stale: bool,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
        progress_message: str | None = None,
    ) -> SubtitleTrackReport:
        status = track.status if track else SubtitleTrackStatus.ARCHIVED
        if is_stale and track is not None and track.status not in {SubtitleTrackStatus.ARCHIVED, SubtitleTrackStatus.FAILED}:
            status = SubtitleTrackStatus.STALE
        return SubtitleTrackReport(
            video=video,
            transcription=transcription,
            track=replace(track, status=status) if track else None,
            cues=tuple(cues),
            status=status,
            is_stale=is_stale,
            validation=validation,
            warnings=warnings,
            errors=errors,
            progress_message=progress_message,
        )

    def _current_track_report(self, track: SubtitleTrack) -> SubtitleTrackReport:
        video = self._require_video(track.video_asset_id)
        transcription_report = self.transcription_service.get_transcription(video.id)
        transcription = transcription_report.transcription
        cues = self.repository.list_cues(track.id)
        options = SubtitleGenerationOptions(language=track.language)
        current_source = build_subtitle_source_fingerprint(
            transcription,
            candidate=self.clip_service.get_ranked_candidate(track.ranked_clip_candidate_id) if track.ranked_clip_candidate_id else None,
            render_job_id=track.render_job_id,
            source_type=track.source_type,
            source_start_seconds=track.source_start_seconds,
            source_end_seconds=track.source_end_seconds,
        ) if transcription else track.source_fingerprint
        stale = transcription is None or is_subtitle_track_stale(
            track,
            current_source_fingerprint=current_source,
            current_configuration_fingerprint=track.configuration_fingerprint,
            current_source_start_seconds=track.source_start_seconds,
            current_source_end_seconds=track.source_end_seconds,
        ) or transcription_report.is_stale
        validation = self._validation_from_cues(track, cues, options)
        warnings = tuple(dict.fromkeys((*validation.warnings, *self._stale_warning(transcription_report))))
        return self._report(
            video=video,
            transcription=transcription,
            track=track,
            cues=cues,
            validation=validation,
            is_stale=stale,
            warnings=warnings,
        )

    def get_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        return self._current_track_report(self._require_track(track_id))

    def list_video_subtitle_tracks(self, video_id: str) -> list[SubtitleTrack]:
        return self.repository.list_tracks_for_video(video_id)

    def list_clip_subtitle_tracks(self, candidate_id: str) -> list[SubtitleTrack]:
        return self.repository.list_tracks_for_candidate(candidate_id)

    def list_render_job_subtitle_tracks(self, render_job_id: str) -> list[SubtitleTrack]:
        return self.repository.list_tracks_for_render_job(render_job_id)

    def validate_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        return self.get_subtitle_track(track_id)

    def _track_exists_and_valid(self, track: SubtitleTrackReport) -> bool:
        return track.track is not None and not track.is_stale and track.status in {
            SubtitleTrackStatus.COMPLETED,
            SubtitleTrackStatus.COMPLETED_WITH_WARNINGS,
            SubtitleTrackStatus.IMPORTED,
            SubtitleTrackStatus.LOCKED,
        }

    def generate_video_subtitles(self, video_id: str, options: SubtitleGenerationOptions | None = None, *, custom_name: str | None = None, force: bool = False) -> SubtitleTrackReport:
        video = self._require_video(video_id)
        transcription_report = self._current_transcription_report(video_id)
        options = self._current_options(options)
        existing = self.repository.get_track_by_video_asset_id(video.id)
        if existing is not None and not force:
            current = self._current_track_report(existing)
            if self._track_exists_and_valid(current):
                return current
        track, drafts, warnings, validation = self._generated_track(
            video=video,
            transcription=transcription_report.transcription,
            segments=self._load_transcription_segments(transcription_report.transcription),
            options=options,
            source_type=SubtitleSourceType.TRANSCRIPTION_GENERATED,
            custom_name=custom_name,
            existing=existing if force or existing is not None else None,
        )
        persisted = self._persist_generation(
            track=track,
            drafts=drafts,
            warnings=tuple(dict.fromkeys((*warnings, *self._stale_warning(transcription_report)))),
            validation=validation,
        )
        return self.get_subtitle_track(persisted.id)

    def generate_clip_subtitles(
        self,
        candidate_id: str,
        options: SubtitleGenerationOptions | None = None,
        *,
        custom_name: str | None = None,
        render_job_id: str | None = None,
        force: bool = False,
    ) -> SubtitleTrackReport:
        candidate = self._candidate_for_track(candidate_id)
        video = self._ranking_run_video(candidate)
        transcription_report = self._current_transcription_report(video.id)
        options = self._current_options(options)
        existing = self.repository.get_track_by_candidate_id(candidate.id)
        if existing is not None and not force:
            current = self._current_track_report(existing)
            if self._track_exists_and_valid(current):
                return current
        track, drafts, warnings, validation = self._generated_track(
            video=video,
            transcription=transcription_report.transcription,
            segments=self._load_transcription_segments(transcription_report.transcription),
            options=options,
            source_type=SubtitleSourceType.CLIP_GENERATED,
            candidate=candidate,
            render_job_id=render_job_id,
            custom_name=custom_name,
            existing=existing if force or existing is not None else None,
        )
        persisted = self._persist_generation(
            track=track,
            drafts=drafts,
            warnings=tuple(dict.fromkeys((*warnings, *self._stale_warning(transcription_report)))),
            validation=validation,
        )
        return self.get_subtitle_track(persisted.id)

    def regenerate_subtitle_track(self, track_id: str, options: SubtitleGenerationOptions | None = None, *, force: bool = False) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        if track.status == SubtitleTrackStatus.LOCKED and not force:
            raise SubtitleStateError("El track esta bloqueado.")
        if track.source_type == SubtitleSourceType.TRANSCRIPTION_GENERATED:
            return self.generate_video_subtitles(track.video_asset_id, options, custom_name=track.name, force=True)
        if track.source_type == SubtitleSourceType.CLIP_GENERATED and track.ranked_clip_candidate_id:
            return self.generate_clip_subtitles(track.ranked_clip_candidate_id, options, custom_name=track.name, render_job_id=track.render_job_id, force=True)
        return self.duplicate_track(track_id)

    def _load_import_options(self, options: SubtitleGenerationOptions | None) -> SubtitleGenerationOptions:
        return self._current_options(options)

    def import_subtitles(
        self,
        video_id: str,
        file: Path,
        *,
        format: SubtitleExportFormat | None = None,
        options: SubtitleGenerationOptions | None = None,
        custom_name: str | None = None,
    ) -> SubtitleTrackReport:
        video = self._require_video(video_id)
        transcription_report = self._current_transcription_report(video.id)
        options = self._load_import_options(options)
        imported = self._importer.import_file(file, format=format, options=options)
        source_duration = max((cue.end_seconds for cue in imported.cues), default=0.0)
        source_type = {
            SubtitleExportFormat.SRT: SubtitleSourceType.IMPORTED_SRT,
            SubtitleExportFormat.VTT: SubtitleSourceType.IMPORTED_VTT,
            SubtitleExportFormat.ASS: SubtitleSourceType.IMPORTED_ASS,
            SubtitleExportFormat.JSON: SubtitleSourceType.MANUAL,
            SubtitleExportFormat.TXT: SubtitleSourceType.MANUAL,
        }[imported.format]
        existing = self.repository.get_track_by_video_asset_id(video.id)
        track = SubtitleTrack(
            id=existing.id if existing else str(uuid4()),
            video_asset_id=video.id,
            transcription_id=transcription_report.transcription.id,
            ranked_clip_candidate_id=None,
            render_job_id=None,
            language=options.language,
            name=self._track_name(video, custom_name=custom_name or file.stem),
            status=SubtitleTrackStatus.GENERATING,
            source_type=source_type,
            track_version=(existing.track_version + 1) if existing else 1,
            configuration_fingerprint=build_subtitle_configuration_fingerprint(options),
            source_fingerprint=_fingerprint_bytes(file.read_bytes()),
            source_start_seconds=0.0,
            source_end_seconds=source_duration,
            cue_count=0,
            total_text_length=0,
            is_default=False,
            is_locked=False,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=existing.created_at if existing else utc_now(),
            updated_at=utc_now(),
            completed_at=None,
        )
        drafts = list(imported.cues)
        validation = self._validator.validate(drafts, options=options, source_duration_seconds=source_duration)
        warnings = tuple(dict.fromkeys((*imported.warnings, *validation.warnings)))
        persisted = self._persist_generation(track=track, drafts=drafts, warnings=warnings, validation=validation)
        return self.get_subtitle_track(persisted.id)

    def export_subtitles(
        self,
        track_id: str,
        format: SubtitleExportFormat,
        *,
        output: Path | None = None,
        custom_name: str | None = None,
    ) -> SubtitleExportResult:
        report = self.get_subtitle_track(track_id)
        if report.track is None:
            raise NotFoundError("El track solicitado no existe.")
        if report.validation and report.validation.blocking_errors:
            raise SubtitleExportError("El track contiene errores bloqueantes y no puede exportarse.")
        video = report.video
        track = report.track
        cues = list(report.cues)
        content = self._exporter.export(track, cues, format)
        destination = output or (self._context_paths(video) / f"{sanitize_filename_component(custom_name or track.name, fallback='subtitles')}.{format.value}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(f"{destination.stem}.part{destination.suffix}")
        temp.write_text(content, encoding="utf-8")
        temp.replace(destination)
        data = destination.read_bytes()
        export = SubtitleExport(
            id=str(uuid4()),
            subtitle_track_id=track.id,
            format=format,
            output_path=str(destination),
            fingerprint=_fingerprint_bytes(data),
            size_bytes=destination.stat().st_size,
            status="verified" if destination.exists() and destination.stat().st_size > 0 else "failed",
            created_at=utc_now(),
            verified_at=utc_now() if destination.exists() and destination.stat().st_size > 0 else None,
        )
        self.repository.upsert_export(export)
        return SubtitleExportResult(track=track, format=format, content=content, path=str(destination), fingerprint=export.fingerprint, verified=bool(export.verified_at))

    def get_subtitle_edit_history(self, track_id: str) -> list[SubtitleEditEvent]:
        return self.repository.list_events_for_track(track_id)

    def get_cue_edit_history(self, cue_id: str) -> list[SubtitleEditEvent]:
        events = self.repository.list_events_for_cue(cue_id)
        if events:
            return events
        for video in self._all_videos():
            for track in self.repository.list_tracks_for_video(video.id):
                for event in self.repository.list_events_for_track(track.id):
                    if event.action != "delete_cue":
                        continue
                    try:
                        payload = json.loads(event.previous_json or "{}")
                    except json.JSONDecodeError:
                        payload = {}
                    payload = payload.get("cue") if isinstance(payload.get("cue"), dict) else payload
                    if isinstance(payload, dict) and str(payload.get("id", "")) == cue_id:
                        return self.repository.list_events_for_track(track.id)
        return []

    def _record_event(self, track_id: str, action: str, previous: object, new: object, note: str | None = None, cue_id: str | None = None) -> SubtitleEditEvent:
        event = SubtitleEditEvent(
            id=str(uuid4()),
            subtitle_track_id=track_id,
            subtitle_cue_id=cue_id,
            event_index=len(self.repository.list_events_for_track(track_id)),
            action=action,
            previous_json=_json_dumps(previous),
            new_json=_json_dumps(new),
            note=note,
            created_at=utc_now(),
        )
        return self.repository.append_event(event)

    def _replace_track_cues(self, track: SubtitleTrack, cues: list[SubtitleCue], *, status: SubtitleTrackStatus | None = None, note: str | None = None, action: str = "edit_track") -> SubtitleTrackReport:
        updated = replace(
            track,
            status=status or SubtitleTrackStatus.EDITING,
            cue_count=len(cues),
            total_text_length=sum(len(cue.text.replace("\n", " ")) for cue in cues),
            updated_at=utc_now(),
        )
        self.repository.upsert_track(updated)
        self.repository.delete_cues_for_track(track.id)
        persisted_cues = self.repository.upsert_cues(track.id, cues)
        self._record_event(track.id, action, track.to_dict(), updated.to_dict(), note=note)
        return self.get_subtitle_track(updated.id)

    def update_cue_text(self, cue_id: str, text: str) -> SubtitleTrackReport:
        cue = self._require_cue(cue_id)
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = self.repository.list_cues(track.id)
        new_text = normalize_subtitle_text(text)
        updated_cue = replace(cue, text=new_text, original_text=cue.original_text, updated_at=utc_now())
        new_cues = [replace(item, cue_index=index) if item.id != cue.id else replace(updated_cue, cue_index=index) for index, item in enumerate(cues)]
        return self._replace_track_cues(track, new_cues, note="Edicion de texto de cue.", action="update_cue_text")

    def update_cue_timing(self, cue_id: str, start_seconds: float, end_seconds: float) -> SubtitleTrackReport:
        cue = self._require_cue(cue_id)
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        validate_subtitle_bounds(start_seconds, end_seconds, track.source_end_seconds - track.source_start_seconds)
        cues = self.repository.list_cues(track.id)
        updated_cue = replace(cue, start_seconds=start_seconds, end_seconds=end_seconds, validation_status=SubtitleCueValidationStatus.WARNING, updated_at=utc_now())
        new_cues = [replace(item, cue_index=index) if item.id != cue.id else replace(updated_cue, cue_index=index) for index, item in enumerate(cues)]
        return self._replace_track_cues(track, new_cues, note="Edicion de tiempos de cue.", action="update_cue_timing")

    def split_cue(self, cue_id: str, split_position: int) -> SubtitleTrackReport:
        cue = self._require_cue(cue_id)
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        text = cue.text.replace("\n", " ")
        if split_position <= 0 or split_position >= len(text):
            raise SubtitleValidationError("La posicion de division no es valida.")
        left = normalize_subtitle_text(text[:split_position])
        right = normalize_subtitle_text(text[split_position:])
        cues = self.repository.list_cues(track.id)
        duration = max(0.001, cue.end_seconds - cue.start_seconds)
        half = duration / 2.0
        first = replace(cue, text=left, original_text=cue.original_text, end_seconds=cue.start_seconds + half, updated_at=utc_now())
        second = SubtitleCue(
            id=str(uuid4()),
            subtitle_track_id=track.id,
            cue_index=cue.cue_index + 1,
            start_seconds=cue.start_seconds + half,
            end_seconds=cue.end_seconds,
            text=right,
            original_text=cue.original_text,
            source_segment_ids_json=cue.source_segment_ids_json,
            speaker_label=cue.speaker_label,
            line_count=1,
            character_count=len(right),
            characters_per_second=len(right) / max(0.001, duration - half),
            words_per_minute=0.0,
            validation_status=SubtitleCueValidationStatus.WARNING,
            warning_codes_json=_json_dumps(["split_cue"]),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        new_cues: list[SubtitleCue] = []
        inserted = False
        for index, item in enumerate(cues):
            if item.id == cue.id:
                new_cues.append(replace(first, cue_index=len(new_cues)))
                new_cues.append(replace(second, cue_index=len(new_cues)))
                inserted = True
            else:
                new_cues.append(replace(item, cue_index=len(new_cues)))
        if not inserted:
            raise NotFoundError("No se pudo dividir el cue.")
        return self._replace_track_cues(track, new_cues, note="Dividir cue.", action="split_cue")

    def merge_cues(self, first_cue_id: str, second_cue_id: str) -> SubtitleTrackReport:
        first = self._require_cue(first_cue_id)
        second = self._require_cue(second_cue_id)
        if first.subtitle_track_id != second.subtitle_track_id:
            raise ConflictError("Los cues pertenecen a tracks distintos.")
        track = self._require_track(first.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = self.repository.list_cues(track.id)
        merged = replace(
            first,
            text=normalize_subtitle_text(f"{first.text} {second.text}"),
            end_seconds=second.end_seconds,
            updated_at=utc_now(),
        )
        new_cues: list[SubtitleCue] = []
        skip = {first.id, second.id}
        for item in cues:
            if item.id == first.id:
                new_cues.append(replace(merged, cue_index=len(new_cues)))
            elif item.id in skip:
                continue
            else:
                new_cues.append(replace(item, cue_index=len(new_cues)))
        return self._replace_track_cues(track, new_cues, note="Fusion de cues.", action="merge_cues")

    def insert_cue(self, track_id: str, index: int, start_seconds: float, end_seconds: float, text: str) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        validate_subtitle_bounds(start_seconds, end_seconds, track.source_end_seconds - track.source_start_seconds)
        cues = self.repository.list_cues(track.id)
        new_cue = SubtitleCue(
            id=str(uuid4()),
            subtitle_track_id=track.id,
            cue_index=index,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            text=normalize_subtitle_text(text),
            original_text=normalize_subtitle_text(text),
            source_segment_ids_json=_json_dumps([]),
            speaker_label=None,
            line_count=1,
            character_count=len(normalize_subtitle_text(text)),
            characters_per_second=len(normalize_subtitle_text(text)) / max(0.001, end_seconds - start_seconds),
            words_per_minute=0.0,
            validation_status=SubtitleCueValidationStatus.WARNING,
            warning_codes_json=_json_dumps(["inserted"]),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        new_cues = cues[:index] + [new_cue] + cues[index:]
        new_cues = [replace(item, cue_index=i) for i, item in enumerate(new_cues)]
        return self._replace_track_cues(track, new_cues, note="Insercion de cue.", action="insert_cue")

    def delete_cue(self, cue_id: str) -> SubtitleTrackReport:
        cue = self._require_cue(cue_id)
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = [item for item in self.repository.list_cues(track.id) if item.id != cue.id]
        cues = [replace(item, cue_index=index) for index, item in enumerate(cues)]
        updated = replace(
            track,
            status=SubtitleTrackStatus.EDITING,
            cue_count=len(cues),
            total_text_length=sum(len(item.text.replace("\n", " ")) for item in cues),
            updated_at=utc_now(),
        )
        self.repository.upsert_track(updated)
        self._record_event(
            track.id,
            "delete_cue",
            {"track": track.to_dict(), "cue": cue.to_dict()},
            {"track": updated.to_dict(), "deleted_cue_id": cue.id},
            note="Eliminacion de cue.",
            cue_id=cue.id,
        )
        self.repository.delete_cues_for_track(track.id)
        self.repository.upsert_cues(track.id, cues)
        return self.get_subtitle_track(updated.id)

    def move_cue(self, cue_id: str, new_index: int) -> SubtitleTrackReport:
        cue = self._require_cue(cue_id)
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = [item for item in self.repository.list_cues(track.id) if item.id != cue.id]
        cues.insert(max(0, min(new_index, len(cues))), cue)
        cues = [replace(item, cue_index=index) for index, item in enumerate(cues)]
        return self._replace_track_cues(track, cues, note="Reordenacion de cue.", action="move_cue")

    def shift_track(self, track_id: str, offset_seconds: float) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = []
        for cue in self.repository.list_cues(track.id):
            start = max(0.0, cue.start_seconds + offset_seconds)
            end = max(start + 0.001, cue.end_seconds + offset_seconds)
            cues.append(replace(cue, start_seconds=start, end_seconds=end, cue_index=len(cues), updated_at=utc_now()))
        return self._replace_track_cues(track, cues, note="Desplazamiento de track.", action="shift_track")

    def restore_cue(self, cue_id: str) -> SubtitleTrackReport:
        cue = self.repository.get_cue_by_id(cue_id)
        if cue is None:
            recovered: SubtitleCue | None = None
            for video in self._all_videos():
                for track in self.repository.list_tracks_for_video(video.id):
                    for event in reversed(self.repository.list_events_for_track(track.id)):
                        if event.action != "delete_cue":
                            continue
                        try:
                            payload = json.loads(event.previous_json or "{}")
                        except json.JSONDecodeError:
                            payload = {}
                        payload = payload.get("cue") if isinstance(payload.get("cue"), dict) else payload
                        if not isinstance(payload, dict) or str(payload.get("id", "")) != cue_id:
                            continue
                        recovered = SubtitleCue(
                            id=str(payload.get("id", cue_id)),
                            subtitle_track_id=track.id,
                            cue_index=int(payload.get("cue_index", len(self.repository.list_cues(track.id)))),
                            start_seconds=float(payload.get("start_seconds", 0.0)),
                            end_seconds=float(payload.get("end_seconds", 0.001)),
                            text=str(payload.get("text", "")),
                            original_text=str(payload.get("original_text", payload.get("text", ""))),
                            source_segment_ids_json=str(payload.get("source_segment_ids_json", "[]")),
                            speaker_label=payload.get("speaker_label"),
                            line_count=int(payload.get("line_count", 1)),
                            character_count=int(payload.get("character_count", len(str(payload.get("text", ""))))),
                            characters_per_second=float(payload.get("characters_per_second", 0.0)),
                            words_per_minute=float(payload.get("words_per_minute", 0.0)),
                            validation_status=SubtitleCueValidationStatus(str(payload.get("validation_status", SubtitleCueValidationStatus.WARNING.value))),
                            warning_codes_json=str(payload.get("warning_codes_json", "[]")),
                            created_at=utc_now(),
                            updated_at=utc_now(),
                        )
                        cue = recovered
                        break
                    if cue is not None:
                        break
                if cue is not None:
                    break
        if cue is None:
            raise NotFoundError("El cue de subtitulos no existe.")
        track = self._require_track(cue.subtitle_track_id)
        if track.is_locked:
            raise SubtitleStateError("El track esta bloqueado.")
        cues = self.repository.list_cues(track.id)
        if any(item.id == cue.id for item in cues):
            return self._replace_track_cues(track, cues, note="Restauracion sin cambio.", action="restore_cue")
        restored_cues = list(cues)
        restored_cues.insert(max(0, min(cue.cue_index, len(restored_cues))), cue)
        restored_cues = [replace(item, cue_index=index) for index, item in enumerate(restored_cues)]
        return self._replace_track_cues(track, restored_cues, note="Restauracion de cue.", action="restore_cue")

    def restore_track(self, track_id: str) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        restored = replace(track, status=SubtitleTrackStatus.EDITING if track.status == SubtitleTrackStatus.ARCHIVED else SubtitleTrackStatus.COMPLETED, updated_at=utc_now())
        self.repository.upsert_track(restored)
        self._record_event(track.id, "restore_track", track.to_dict(), restored.to_dict(), note="Restauracion de track.")
        return self.get_subtitle_track(track.id)

    def lock_track(self, track_id: str) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        locked = replace(track, is_locked=True, status=SubtitleTrackStatus.LOCKED, updated_at=utc_now())
        self.repository.upsert_track(locked)
        self._record_event(track.id, "lock_track", track.to_dict(), locked.to_dict(), note="Bloqueo de track.")
        return self.get_subtitle_track(track.id)

    def unlock_track(self, track_id: str) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        unlocked = replace(track, is_locked=False, status=SubtitleTrackStatus.EDITING, updated_at=utc_now())
        self.repository.upsert_track(unlocked)
        self._record_event(track.id, "unlock_track", track.to_dict(), unlocked.to_dict(), note="Desbloqueo de track.")
        return self.get_subtitle_track(track.id)

    def duplicate_track(self, track_id: str) -> SubtitleTrackReport:
        track = self._require_track(track_id)
        cues = self.repository.list_cues(track.id)
        clone = replace(
            track,
            id=str(uuid4()),
            track_version=track.track_version + 1,
            status=SubtitleTrackStatus.EDITING,
            is_locked=False,
            is_default=False,
            created_at=utc_now(),
            updated_at=utc_now(),
            completed_at=None,
        )
        self.repository.upsert_track(clone)
        new_cues = [
            replace(cue, id=str(uuid4()), subtitle_track_id=clone.id, cue_index=index, updated_at=utc_now())
            for index, cue in enumerate(cues)
        ]
        self.repository.upsert_cues(clone.id, new_cues)
        self._record_event(track.id, "duplicate_track", track.to_dict(), clone.to_dict(), note="Duplicado de track.")
        return self.get_subtitle_track(clone.id)

    def delete_subtitle_track(self, track_id: str) -> bool:
        return self.repository.delete_track(track_id)

    def archive_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        track = self.repository.archive_track(track_id)
        if track is None:
            raise NotFoundError("El track de subtitulos no existe.")
        return self.get_subtitle_track(track.id)

    def revert_edit_event(self, event_id: str) -> SubtitleTrackReport:
        for video in self._all_videos():
            for track in self.repository.list_tracks_for_video(video.id):
                for event in self.repository.list_events_for_track(track.id):
                    if event.id != event_id:
                        continue
                    payload = json.loads(event.previous_json or "{}")
                    cue_id = event.subtitle_cue_id
                    if cue_id:
                        cues = self.repository.list_cues(track.id)
                        restored_cues: list[SubtitleCue] = []
                        restored = False
                        for index, item in enumerate(cues):
                            if item.id == cue_id:
                                restored_cues.append(
                                    replace(
                                        item,
                                        start_seconds=float(payload.get("start_seconds", item.start_seconds)),
                                        end_seconds=float(payload.get("end_seconds", item.end_seconds)),
                                        text=str(payload.get("text", item.text)),
                                        original_text=str(payload.get("original_text", item.original_text)),
                                        updated_at=utc_now(),
                                        cue_index=index,
                                    )
                                )
                                restored = True
                            else:
                                restored_cues.append(replace(item, cue_index=len(restored_cues)))
                        if restored:
                            return self._replace_track_cues(track, restored_cues, note="Reversion de evento.", action="revert_edit_event")
                    return self._replace_track_cues(track, self.repository.list_cues(track.id), note="Reversion de evento sin cambios.", action="revert_edit_event")
        raise NotFoundError("El evento de edicion no existe.")

    def get_subtitle_edit_history(self, track_id: str) -> list[SubtitleEditEvent]:
        return self.repository.list_events_for_track(track_id)

    def get_cue_edit_history(self, cue_id: str) -> list[SubtitleEditEvent]:
        return self.repository.list_events_for_cue(cue_id)

    def export_subtitles(
        self,
        track_id: str,
        format: SubtitleExportFormat,
        *,
        output: Path | None = None,
        custom_name: str | None = None,
    ) -> SubtitleExportResult:
        report = self.get_subtitle_track(track_id)
        if report.track is None:
            raise NotFoundError("El track solicitado no existe.")
        if report.validation and report.validation.blocking_errors:
            raise SubtitleExportError("El track contiene errores bloqueantes.")
        content = self._exporter.export(report.track, list(report.cues), format)
        destination = output or (self._context_paths(report.video) / f"{sanitize_filename_component(custom_name or report.track.name, fallback='subtitles')}.{format.value}")
        destination = self._safe_export_path(destination)
        if destination.exists():
            raise SubtitleExportError("El archivo de exportacion ya existe.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(f"{destination.stem}.part{destination.suffix}")
        temp.write_text(content, encoding="utf-8")
        temp.replace(destination)
        fingerprint = _fingerprint_bytes(destination.read_bytes())
        export = SubtitleExport(
            id=str(uuid4()),
            subtitle_track_id=report.track.id,
            format=format,
            output_path=str(destination),
            fingerprint=fingerprint,
            size_bytes=destination.stat().st_size,
            status="verified",
            created_at=utc_now(),
            verified_at=utc_now(),
        )
        self.repository.upsert_export(export)
        return SubtitleExportResult(track=report.track, format=format, content=content, path=str(destination), fingerprint=fingerprint, verified=True)

    def _track_is_current(self, report: SubtitleTrackReport) -> bool:
        return report.track is not None and not report.is_stale and report.status in {
            SubtitleTrackStatus.COMPLETED,
            SubtitleTrackStatus.COMPLETED_WITH_WARNINGS,
            SubtitleTrackStatus.IMPORTED,
            SubtitleTrackStatus.LOCKED,
        }


def build_subtitle_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    transcription_service: TranscriptionService,
    clip_service: ClipRankingService,
    repository: SubtitleRepository,
    logger: logging.Logger | None = None,
) -> SubtitleService:
    return SubtitleService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        transcription_service=transcription_service,
        clip_service=clip_service,
        repository=repository,
        logger=logger,
    )
