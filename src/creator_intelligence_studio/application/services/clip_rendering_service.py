"""Servicio de aplicacion para render local de clips."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.clip_ranking_service import ClipRankingService
from creator_intelligence_studio.application.services.media_inspection_service import MediaInspectionService, VideoInspectionReport
from creator_intelligence_studio.application.services.subtitle_service import SubtitleService, SubtitleTrackReport
from creator_intelligence_studio.domain.clip_ranking.entities import ClipCollection, ClipCollectionItem, RankedClipCandidate
from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingReviewStatus
from creator_intelligence_studio.domain.clip_rendering.entities import ClipRenderArtifact, ClipRenderBatch, ClipRenderBatchItem, ClipRenderDelivery, ClipRenderDeliveryArtifact, ClipRenderEvent, ClipRenderJob
from creator_intelligence_studio.domain.clip_rendering.errors import ClipRenderCapabilityError, ClipRenderExecutionError, ClipRenderStateError, ClipRenderValidationError
from creator_intelligence_studio.domain.clip_rendering.repositories import ClipRenderRepository
from creator_intelligence_studio.domain.clip_rendering.services import build_source_fingerprint, candidate_is_eligible_for_render, normalize_render_profile, render_profile_config
from creator_intelligence_studio.domain.clip_rendering.value_objects import (
    ClipRenderArtifactType,
    ClipRenderBatchStatus,
    ClipRenderDeliveryStatus,
    ClipRenderJobStatus,
    ClipRenderPlan,
    ClipRenderProfile,
    ClipRenderSubtitleConfig,
    ClipRenderSubtitleStyle,
    SubtitleRenderMode,
    SubtitleRenderStylePreset,
    RenderOutputVerification,
)
from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.projects.entities import Project
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.infrastructure.clip_rendering.encoding_capability_detector import EncodingCapabilityDetector, EncodingCapabilityReport
from creator_intelligence_studio.infrastructure.clip_rendering.ffmpeg_clip_renderer import CancelToken, ClipRenderExecutionResult, FFmpegClipRenderer
from creator_intelligence_studio.infrastructure.clip_rendering.filename_builder import build_render_filename, build_render_output_path, sanitize_filename_component
from creator_intelligence_studio.infrastructure.clip_rendering.subtitle_rendering import build_delivery_manifest, resolve_subtitle_style
from creator_intelligence_studio.infrastructure.clip_rendering.render_output_verifier import RenderOutputVerifier
from creator_intelligence_studio.infrastructure.clip_rendering.render_plan_builder import build_render_plan
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.subtitles.subtitle_exporter import SubtitleExporter
from creator_intelligence_studio.infrastructure.subtitles.subtitle_importer import SubtitleImporter
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleGenerationOptions
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleTrackStatus
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


class RenderProgressCallback(Protocol):
    def __call__(self, phase: str, progress: float, payload: dict[str, object]) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ClipRenderOperationReport:
    job: ClipRenderJob
    plan: ClipRenderPlan
    verification: RenderOutputVerification | None
    artifact: ClipRenderArtifact | None
    reused_output: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "job": self.job.to_dict(),
            "plan": self.plan.to_dict(),
            "verification": self.verification.to_dict() if self.verification else None,
            "artifact": self.artifact.to_dict() if self.artifact else None,
            "reused_output": self.reused_output,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderBatchReport:
    batch: ClipRenderBatch
    jobs: tuple[ClipRenderJob, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "batch": self.batch.to_dict(),
            "jobs": [job.to_dict() for job in self.jobs],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderDeliveryReport:
    delivery: ClipRenderDelivery
    job: ClipRenderJob | None
    artifacts: tuple[ClipRenderDeliveryArtifact, ...]
    verification: RenderOutputVerification | None
    reused_output: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "delivery": self.delivery.to_dict(),
            "job": self.job.to_dict() if self.job else None,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "verification": self.verification.to_dict() if self.verification else None,
            "reused_output": self.reused_output,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _safe_output_path(root: Path, output: str | Path | None) -> Path:
    root_resolved = root.resolve(strict=False)
    if output is None:
        return root_resolved
    candidate = Path(output)
    resolved = candidate if candidate.is_absolute() else root_resolved / candidate
    resolved = resolved.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved):
        raise ClipRenderValidationError("La ruta de salida no puede salir del directorio administrado.")
    return resolved


def _job_status_from_phase(phase: str) -> ClipRenderJobStatus:
    return {
        "preparing": ClipRenderJobStatus.PREPARING,
        "rendering": ClipRenderJobStatus.RENDERING,
        "verifying": ClipRenderJobStatus.VERIFYING,
        "completed": ClipRenderJobStatus.COMPLETED,
        "cancelled": ClipRenderJobStatus.CANCELLED,
        "failed": ClipRenderJobStatus.FAILED,
    }.get(phase, ClipRenderJobStatus.PREPARING)


def _temporary_output_path(output_path: str) -> str:
    path = Path(output_path)
    return str(path.with_name(f"{path.stem}.part{path.suffix}"))


class ClipRenderService:
    """Orquesta la creacion, ejecucion y verificacion de renders de clips."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        media_service: MediaInspectionService,
        clip_service: ClipRankingService,
        repository: ClipRenderRepository,
        subtitle_service: SubtitleService | None = None,
        logger: logging.Logger | None = None,
        tool_locator: MediaToolLocator | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.media_service = media_service
        self.clip_service = clip_service
        self.repository = repository
        self.subtitle_service = subtitle_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.clip_rendering")
        self._output_root = self.paths.project_root / "exports" / "clips"
        self._delivery_root_path = self.paths.project_root / "exports" / "deliveries"
        self.tool_locator = tool_locator or MediaToolLocator(settings=settings, project_root=paths.project_root)
        tools = self.tool_locator.discover()
        ffmpeg_path = Path(tools.ffmpeg.path) if tools.ffmpeg.available and tools.ffmpeg.path else None
        ffprobe_path = Path(tools.ffprobe.path) if tools.ffprobe.available and tools.ffprobe.path else None
        self._renderer = FFmpegClipRenderer(ffmpeg_path)
        self._verifier = RenderOutputVerifier(ffprobe_path)
        self._capabilities = EncodingCapabilityDetector(ffmpeg_path)
        self._subtitle_exporter = SubtitleExporter()
        self._subtitle_importer = SubtitleImporter()
        self._recover_interrupted_jobs()

    def render_capabilities(self) -> EncodingCapabilityReport:
        return self._capabilities.detect()

    def render_profiles(self) -> tuple[dict[str, object], ...]:
        return tuple(render_profile_config(profile).to_dict() for profile in ClipRenderProfile)

    def _recover_interrupted_jobs(self) -> None:
        for job in self.repository.list_jobs():
            if job.status not in {
                ClipRenderJobStatus.QUEUED,
                ClipRenderJobStatus.VALIDATING,
                ClipRenderJobStatus.PREPARING,
                ClipRenderJobStatus.RENDERING,
                ClipRenderJobStatus.VERIFYING,
            }:
                continue
            updated = self._update_job(
                job,
                status=ClipRenderJobStatus.INTERRUPTED,
                warning_code="interrupted_on_restart",
                warning_message="La tarea de render quedo interrumpida al reiniciar la aplicacion.",
            )
            self._append_event(updated.id, "interrupted", updated.progress_percent, "Render interrumpido por reinicio.", {})

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.catalog_service.get_video(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _require_creator_and_project(self, video: VideoAsset) -> tuple[str, str]:
        project = self.catalog_service.get_project(video.project_id)
        if project is None:
            raise NotFoundError("El proyecto del video no existe.")
        creator = self.catalog_service.get_creator(project.creator_id)
        if creator is None:
            raise NotFoundError("El creador del video no existe.")
        return creator.slug, sanitize_filename_component(project.name, fallback="project")

    def _require_candidate(self, candidate_id: str) -> RankedClipCandidate:
        candidate = self.clip_service.get_ranked_candidate(candidate_id)
        if candidate is None:
            raise NotFoundError("El candidato solicitado no existe.")
        return candidate

    def _require_collection(self, collection_id: str) -> ClipCollection:
        collection = self.clip_service.clip_repository.get_collection_by_id(collection_id)
        if collection is None:
            raise NotFoundError("La coleccion solicitada no existe.")
        return collection

    def _collection_item(self, collection_id: str, candidate_id: str) -> ClipCollectionItem | None:
        return next((item for item in self.clip_service.clip_repository.list_collection_items(collection_id) if item.ranked_clip_candidate_id == candidate_id), None)

    def _inspection_report(self, video: VideoAsset) -> VideoInspectionReport | None:
        return self.media_service.get_video_inspection(video.id)

    def _source_duration_seconds(self, report: VideoInspectionReport | None) -> float | None:
        return report.summary.duration_seconds if report and report.summary else None

    def _delivery_root(self, creator_slug: str, project_slug: str) -> Path:
        root = self._delivery_root_path / sanitize_filename_component(creator_slug, fallback="creator") / sanitize_filename_component(project_slug, fallback="project")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _subtitle_track_report(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise ClipRenderCapabilityError("El servicio de subtitulos no esta disponible.")
        report = self.subtitle_service.get_subtitle_track(track_id)
        if report.track is None:
            raise ClipRenderStateError("El track de subtitulos no existe.")
        return report

    def _subtitle_style(self, preset: SubtitleRenderStylePreset) -> ClipRenderSubtitleStyle:
        return resolve_subtitle_style(preset)

    def render_subtitle_capabilities(self) -> dict[str, object]:
        capabilities = self.render_capabilities()
        payload = capabilities.to_dict()
        payload.update(
            {
                "sidecar_available": True,
                "burn_in_available": bool(capabilities.burn_in_available),
            }
        )
        return payload

    def render_subtitle_styles(self) -> tuple[dict[str, object], ...]:
        return tuple(resolve_subtitle_style(preset).to_dict() for preset in SubtitleRenderStylePreset)

    def _render_root(self, creator_slug: str, project_slug: str) -> Path:
        root = self._output_root / sanitize_filename_component(creator_slug, fallback="creator") / sanitize_filename_component(project_slug, fallback="project")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _build_job(self, plan: ClipRenderPlan, *, status: ClipRenderJobStatus, existing: ClipRenderJob | None = None) -> ClipRenderJob:
        now = utc_now()
        return ClipRenderJob(
            id=plan.job_id,
            video_asset_id=plan.video_asset_id,
            ranked_clip_candidate_id=plan.ranked_clip_candidate_id,
            collection_id=plan.collection_id,
            status=status,
            render_profile=plan.profile,
            source_path_snapshot=plan.source_path_snapshot,
            source_fingerprint=plan.source_fingerprint,
            start_seconds=plan.start_seconds,
            end_seconds=plan.end_seconds,
            duration_seconds=plan.duration_seconds,
            output_path=plan.output_path,
            output_container=plan.container,
            video_codec=plan.video_codec,
            audio_codec=plan.audio_codec,
            width=plan.expected_width,
            height=plan.expected_height,
            frame_rate=plan.max_frame_rate,
            audio_sample_rate=None,
            configuration_fingerprint=plan.configuration_fingerprint,
            renderer_version=plan.renderer_version,
            progress_percent=0.0 if existing is None else existing.progress_percent,
            started_at=existing.started_at if existing else None,
            completed_at=existing.completed_at if existing else None,
            cancelled_at=existing.cancelled_at if existing else None,
            retry_count=0 if existing is None else existing.retry_count,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )

    def _persist_job(self, job: ClipRenderJob) -> ClipRenderJob:
        return self.repository.upsert_job(job)

    def _append_event(self, job_id: str, event_type: str, progress_percent: float, message: str, details: dict[str, object] | None = None) -> None:
        events = self.repository.list_events_for_job(job_id)
        self.repository.append_event(
            ClipRenderEvent(
                id=str(uuid4()),
                render_job_id=job_id,
                event_index=len(events),
                event_type=event_type,
                progress_percent=max(0.0, min(100.0, progress_percent)),
                message=message,
                details_json=_json_dumps(details or {}),
                created_at=utc_now(),
            )
        )

    def _update_job(self, job: ClipRenderJob, **changes) -> ClipRenderJob:
        updated = replace(job, updated_at=utc_now(), **changes)
        return self._persist_job(updated)

    def _delivery_subtitle_config(self, delivery: ClipRenderDelivery) -> ClipRenderSubtitleConfig:
        style = None
        if delivery.style_json:
            try:
                payload = json.loads(delivery.style_json)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                try:
                    style = ClipRenderSubtitleStyle(
                        preset=SubtitleRenderStylePreset(payload.get("preset", SubtitleRenderStylePreset.CLEAN.value)),
                        font_family=str(payload.get("font_family") or "Arial"),
                        font_size=int(payload.get("font_size") or 48),
                        primary_color=str(payload.get("primary_color") or "&H00FFFFFF"),
                        outline_color=str(payload.get("outline_color") or "&H00000000"),
                        outline_width=int(payload.get("outline_width") or 2),
                        shadow=int(payload.get("shadow") or 0),
                        bold=bool(payload.get("bold", False)),
                        alignment=int(payload.get("alignment") or 2),
                        margin_left=int(payload.get("margin_left") or 40),
                        margin_right=int(payload.get("margin_right") or 40),
                        margin_vertical=int(payload.get("margin_vertical") or 40),
                        safe_area=int(payload.get("safe_area") or 10),
                        background_box=bool(payload.get("background_box", False)),
                        max_lines=int(payload.get("max_lines") or 2),
                    )
                except Exception:
                    style = None
        return ClipRenderSubtitleConfig(
            mode=delivery.subtitle_mode,
            track_id=delivery.subtitle_track_id,
            track_version=delivery.subtitle_track_version,
            fingerprint=delivery.subtitle_track_fingerprint,
            format=delivery.subtitle_format,
            style_preset=delivery.style_preset,
            style=style,
            expected_cue_count=delivery.expected_cue_count,
            stale_acknowledged=bool(delivery.status in {ClipRenderDeliveryStatus.COMPLETED, ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS}),
            temporary_ass_path=None,
            sidecar_output_path=delivery.output_path,
            source_export_path=delivery.source_export_path,
            source_export_fingerprint=delivery.source_export_fingerprint,
        )

    def _current_plan(self, job: ClipRenderJob) -> ClipRenderPlan:
        delivery = self.repository.list_deliveries_for_job(job.id)
        subtitle_config = self._delivery_subtitle_config(delivery[0]) if delivery else None
        return ClipRenderPlan(
            job_id=job.id,
            video_asset_id=job.video_asset_id,
            creator_slug="",
            project_slug="",
            ranked_clip_candidate_id=job.ranked_clip_candidate_id,
            collection_id=job.collection_id,
            source_path=job.source_path_snapshot,
            source_path_snapshot=job.source_path_snapshot,
            source_fingerprint=job.source_fingerprint,
            start_seconds=job.start_seconds,
            end_seconds=job.end_seconds,
            duration_seconds=job.duration_seconds,
            profile=job.render_profile,
            output_path=job.output_path,
            temporary_output_path=_temporary_output_path(job.output_path),
            container=job.output_container,
            video_codec=job.video_codec,
            audio_codec=job.audio_codec,
            pixel_format="yuv420p",
            preset="medium",
            crf=23,
            audio_bitrate_kbps=128,
            max_width=job.width,
            max_height=job.height,
            max_frame_rate=job.frame_rate,
            faststart=True,
            allow_fast_copy=False,
            hardware_acceleration=False,
            expected_width=job.width,
            expected_height=job.height,
            expected_audio=job.audio_codec is not None,
            subtitle_config=subtitle_config,
            configuration_fingerprint=job.configuration_fingerprint,
            renderer_version=job.renderer_version,
            custom_name=None,
        )

    def _reusable_job(self, *, candidate_id: str | None, collection_id: str | None, configuration_fingerprint: str, output_path: Path) -> ClipRenderJob | None:
        candidates: list[ClipRenderJob] = []
        if candidate_id is not None:
            candidates.extend(self.repository.list_jobs_for_candidate(candidate_id))
        if collection_id is not None:
            candidates.extend(self.repository.list_jobs_for_collection(collection_id))
        seen: set[str] = set()
        for job in candidates:
            if job.id in seen:
                continue
            seen.add(job.id)
            if job.configuration_fingerprint != configuration_fingerprint:
                continue
            if Path(job.output_path) != output_path:
                continue
            artifact = self.repository.get_artifact_for_job(job.id)
            if artifact is None or not artifact.verified:
                continue
            if not Path(artifact.managed_path).exists():
                continue
            if job.status in {ClipRenderJobStatus.COMPLETED, ClipRenderJobStatus.COMPLETED_WITH_WARNINGS}:
                return job
        return None

    def _build_plan(
        self,
        *,
        candidate: RankedClipCandidate,
        collection_item: ClipCollectionItem | None,
        profile: ClipRenderProfile,
        subtitle_config: ClipRenderSubtitleConfig | None,
        output: str | Path | None,
        output_root_override: str | Path | None,
        custom_name: str | None,
        renderer_version: str,
        allow_stale: bool,
        allow_overwrite: bool,
        explicit: bool,
    ) -> tuple[ClipRenderPlan, VideoAsset, VideoInspectionReport, str, str, Path]:
        if candidate.review_status == ClipRankingReviewStatus.NEEDS_REVIEW and not explicit:
            raise ClipRenderStateError("El candidato requiere confirmacion explicita para renderizarse.")
        if not candidate_is_eligible_for_render(candidate, explicit=explicit):
            raise ClipRenderStateError("El candidato no es elegible para render.")
        run = self.clip_service.get_ranking_run(candidate.ranking_run_id)
        video = self._require_video(run.video_asset_id)
        inspection = self._inspection_report(video)
        if inspection is None or inspection.summary is None:
            raise ClipRenderStateError("El video no tiene una inspeccion tecnica valida.")
        if not inspection.file_available:
            raise ClipRenderStateError("El archivo fuente no esta disponible.")
        if (inspection.is_stale or self.clip_service.is_clip_ranking_stale(video.id)) and not allow_stale:
            raise ClipRenderStateError("El candidato esta desactualizado y requiere confirmacion para renderizarse.")
        creator_slug, project_slug = self._require_creator_and_project(video)
        output_root = Path(output_root_override) if output_root_override is not None else self._render_root(creator_slug, project_slug)
        output_root.mkdir(parents=True, exist_ok=True)
        profile_config = render_profile_config(profile)
        clip_title = candidate.explanation.get("title") if isinstance(candidate.explanation, dict) else None
        filename = build_render_filename(
            video_title=video.title,
            clip_title=clip_title,
            start_seconds=candidate.adjusted_start_seconds,
            end_seconds=candidate.adjusted_end_seconds,
            profile=profile,
            extension=profile_config.container,
            suffix=custom_name,
        )
        output_path = _safe_output_path(output_root, Path(output) if output is not None else build_render_output_path(output_root, creator_slug=creator_slug, project_slug=project_slug, video_title=video.title, filename=filename))
        source_duration_seconds = self._source_duration_seconds(inspection)
        if source_duration_seconds is None:
            raise ClipRenderStateError("La inspeccion tecnica no reporta duracion suficiente.")
        plan = build_render_plan(
            job_id=str(uuid4()),
            video=video,
            creator_slug=creator_slug,
            project_slug=project_slug,
            candidate=candidate,
            collection_item=collection_item,
            profile=profile,
            subtitle_config=subtitle_config,
            source_duration_seconds=source_duration_seconds,
            output_root=output_root,
            output_path=output_path,
            custom_name=custom_name,
            renderer_version=renderer_version,
        )
        return plan, video, inspection, creator_slug, project_slug, output_path

    def create_render_job(
        self,
        candidate_id: str,
        *,
        profile: str | ClipRenderProfile = "balanced",
        subtitle_config: ClipRenderSubtitleConfig | None = None,
        output: str | Path | None = None,
        output_root_override: str | Path | None = None,
        explicit: bool = False,
        allow_stale: bool = False,
        allow_overwrite: bool = False,
        custom_name: str | None = None,
        renderer_version: str = "v1",
        collection_id: str | None = None,
    ) -> ClipRenderJob:
        candidate = self._require_candidate(candidate_id)
        collection_item = self._collection_item(collection_id, candidate.id) if collection_id else None
        normalized_profile = normalize_render_profile(profile.value if isinstance(profile, ClipRenderProfile) else str(profile))
        plan, _, _, _, _, output_path = self._build_plan(
            candidate=candidate,
            collection_item=collection_item,
            profile=normalized_profile,
            subtitle_config=subtitle_config,
            output=output,
            output_root_override=output_root_override,
            custom_name=custom_name,
            renderer_version=renderer_version,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            explicit=explicit,
        )
        reusable = self._reusable_job(candidate_id=candidate.id, collection_id=collection_id, configuration_fingerprint=plan.configuration_fingerprint, output_path=output_path)
        if reusable is not None:
            return reusable
        if output_path.exists() and not allow_overwrite:
            raise ClipRenderStateError("La salida final ya existe.")
        job = self._build_job(plan, status=ClipRenderJobStatus.QUEUED)
        job = self._persist_job(job)
        self._append_event(job.id, "queued", 0.0, "Render en cola.", {"profile": normalized_profile.value})
        return job

    def render_candidate(
        self,
        candidate_id: str,
        *,
        profile: str | ClipRenderProfile = "balanced",
        subtitle_config: ClipRenderSubtitleConfig | None = None,
        output: str | Path | None = None,
        output_root_override: str | Path | None = None,
        explicit: bool = False,
        allow_stale: bool = False,
        allow_overwrite: bool = False,
        custom_name: str | None = None,
        renderer_version: str = "v1",
        progress_callback: RenderProgressCallback | None = None,
        cancellation_token: CancelToken | None = None,
        collection_id: str | None = None,
    ) -> ClipRenderOperationReport:
        candidate = self._require_candidate(candidate_id)
        collection_item = self._collection_item(collection_id, candidate.id) if collection_id else None
        normalized_profile = normalize_render_profile(profile.value if isinstance(profile, ClipRenderProfile) else str(profile))
        plan, video, inspection, _, _, output_path = self._build_plan(
            candidate=candidate,
            collection_item=collection_item,
            profile=normalized_profile,
            subtitle_config=subtitle_config,
            output=output,
            output_root_override=output_root_override,
            custom_name=custom_name,
            renderer_version=renderer_version,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            explicit=explicit,
        )
        reusable = self._reusable_job(candidate_id=candidate.id, collection_id=collection_id, configuration_fingerprint=plan.configuration_fingerprint, output_path=output_path)
        if reusable is not None:
            artifact = self.repository.get_artifact_for_job(reusable.id)
            verification = None
            if artifact is not None:
                verification = RenderOutputVerification(
                    verified=artifact.verified,
                    output_path=artifact.managed_path,
                    size_bytes=artifact.size_bytes,
                    duration_seconds=artifact.duration_seconds,
                    video_codec=artifact.video_codec,
                    audio_codec=artifact.audio_codec,
                    width=artifact.width,
                    height=artifact.height,
                    frame_rate=artifact.frame_rate,
                    audio_sample_rate=artifact.audio_sample_rate,
                    fingerprint=artifact.fingerprint,
                    warnings=(),
                    errors=(),
                    details={"reused": True},
                )
            return ClipRenderOperationReport(job=reusable, plan=plan, verification=verification, artifact=artifact, reused_output=True)
        if output_path.exists() and not allow_overwrite:
            raise ClipRenderStateError("La salida final ya existe.")

        job = self.create_render_job(
            candidate_id,
            profile=normalized_profile,
            subtitle_config=subtitle_config,
            output=output,
            output_root_override=output_root_override,
            explicit=explicit,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            custom_name=custom_name,
            renderer_version=renderer_version,
            collection_id=collection_id,
        )
        job = self._update_job(job, status=ClipRenderJobStatus.VALIDATING, started_at=job.started_at or utc_now(), progress_percent=0.0)
        self._append_event(job.id, "validating", 0.0, "Validando candidato y bordes.", {"candidate_id": candidate.id})
        job = self._update_job(job, status=ClipRenderJobStatus.PREPARING, progress_percent=5.0)
        self._append_event(job.id, "preparing", 5.0, "Preparando render.", {"plan": plan.to_dict()})
        if self._renderer.ffmpeg_path is None:
            job = self._update_job(job, status=ClipRenderJobStatus.FAILED, error_code="ffmpeg_unavailable", error_message="ffmpeg no esta disponible.", completed_at=utc_now())
            raise ClipRenderCapabilityError("ffmpeg no esta disponible.")

        output_path = Path(plan.output_path)
        temp_path = Path(plan.temporary_output_path)
        if allow_overwrite:
            output_path.unlink(missing_ok=True)
        temp_path.unlink(missing_ok=True)

        def _progress(phase: str, percent: float, payload: dict[str, object]) -> None:
            current_percent = max(0.0, min(99.0, percent * 100.0))
            mapped_status = _job_status_from_phase(phase)
            self._update_job(job, status=mapped_status, progress_percent=current_percent)
            self._append_event(job.id, phase, current_percent, str(payload.get("message") or phase), payload)
            if progress_callback is not None:
                progress_callback(phase, percent, payload)

        try:
            execution: ClipRenderExecutionResult = self._renderer.render(plan, cancellation_token=cancellation_token, progress_callback=_progress)
        except ClipRenderExecutionError as exc:
            job = self._update_job(job, status=ClipRenderJobStatus.FAILED, error_code="render_failed", error_message=str(exc), completed_at=utc_now())
            self._append_event(job.id, "failed", job.progress_percent, str(exc), {"error": str(exc)})
            raise

        if any(event.phase == "cancelled" for event in execution.progress_events):
            job = self._update_job(job, status=ClipRenderJobStatus.CANCELLED, cancelled_at=utc_now(), error_code="cancelled", error_message="Render cancelado por el usuario.")
            self._append_event(job.id, "cancelled", job.progress_percent, "Render cancelado.", {})
            return ClipRenderOperationReport(job=job, plan=plan, verification=None, artifact=None, reused_output=False, warnings=(), errors=("Render cancelado.",))

        if execution.returncode != 0:
            job = self._update_job(job, status=ClipRenderJobStatus.FAILED, error_code="render_failed", error_message="FFmpeg devolvio un codigo de salida distinto de cero.", completed_at=utc_now())
            self._append_event(job.id, "failed", job.progress_percent, "FFmpeg devolvio un codigo de salida distinto de cero.", {"returncode": execution.returncode})
            raise ClipRenderExecutionError("FFmpeg devolvio un codigo de salida distinto de cero.")

        job = self._update_job(job, status=ClipRenderJobStatus.VERIFYING, progress_percent=99.0)
        self._append_event(job.id, "verifying", 99.0, "Verificando salida.")
        verification = self._verifier.verify(plan, output_path)
        artifact = self.repository.upsert_artifact(
            ClipRenderArtifact(
                id=str(uuid4()),
                render_job_id=job.id,
                artifact_type=ClipRenderArtifactType.OUTPUT,
                managed_path=verification.output_path,
                fingerprint=verification.fingerprint or "",
                size_bytes=verification.size_bytes,
                duration_seconds=verification.duration_seconds,
                video_codec=verification.video_codec,
                audio_codec=verification.audio_codec,
                width=verification.width,
                height=verification.height,
                frame_rate=verification.frame_rate,
                audio_sample_rate=verification.audio_sample_rate,
                verified=verification.verified,
                verification_json=_json_dumps(verification.to_dict()),
                created_at=utc_now(),
            )
        )
        if verification.verified:
            status = ClipRenderJobStatus.COMPLETED_WITH_WARNINGS if verification.warnings else ClipRenderJobStatus.COMPLETED
            job = self._update_job(
                job,
                status=status,
                progress_percent=100.0,
                completed_at=utc_now(),
                warning_code="verification_warnings" if verification.warnings else None,
                warning_message="; ".join(verification.warnings) if verification.warnings else None,
            )
            self._append_event(job.id, status.value, 100.0, "Render completado.", {"warnings": list(verification.warnings)})
        else:
            job = self._update_job(job, status=ClipRenderJobStatus.FAILED, progress_percent=job.progress_percent, error_code="verification_failed", error_message="; ".join(verification.errors) or "La verificacion fallo.", completed_at=utc_now())
            self._append_event(job.id, "failed", job.progress_percent, "La verificacion fallo.", {"errors": list(verification.errors)})
        return ClipRenderOperationReport(job=job, plan=plan, verification=verification, artifact=artifact, reused_output=False, warnings=verification.warnings, errors=verification.errors)

    def _delivery_context(self, job: ClipRenderJob) -> tuple[VideoAsset, str, str, Path]:
        video = self._require_video(job.video_asset_id)
        creator_slug, project_slug = self._require_creator_and_project(video)
        root = self._delivery_root(creator_slug, project_slug) / sanitize_filename_component(video.title, fallback="video")
        root.mkdir(parents=True, exist_ok=True)
        return video, creator_slug, project_slug, root

    def _delivery_configuration_fingerprint(
        self,
        *,
        job: ClipRenderJob,
        subtitle_track: ClipRenderSubtitleConfig,
        output_path: Path,
        manifest_path: Path | None,
    ) -> str:
        payload = {
            "job_configuration_fingerprint": job.configuration_fingerprint,
            "job_id": job.id,
            "subtitle_track": subtitle_track.to_dict(),
            "output_path": str(output_path),
            "manifest_path": str(manifest_path) if manifest_path else None,
            "delivery_version": "v1",
        }
        return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()

    def _persist_delivery(self, delivery: ClipRenderDelivery) -> ClipRenderDelivery:
        return self.repository.upsert_delivery(delivery)

    def _persist_delivery_artifact(self, artifact: ClipRenderDeliveryArtifact) -> ClipRenderDeliveryArtifact:
        return self.repository.upsert_delivery_artifact(artifact)

    def _delivery_artifact(self, delivery_id: str, artifact_type: ClipRenderArtifactType, path: Path, *, verified: bool, verification: dict[str, object] | None = None) -> ClipRenderDeliveryArtifact:
        return ClipRenderDeliveryArtifact(
            id=str(uuid4()),
            delivery_id=delivery_id,
            artifact_type=artifact_type,
            managed_path=str(path),
            fingerprint=self._fingerprint_file(path) if path.exists() else "",
            size_bytes=path.stat().st_size if path.exists() else None,
            verified=verified,
            verification_json=_json_dumps(verification or {}),
            created_at=utc_now(),
        )

    def _fingerprint_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _write_manifest(self, delivery: ClipRenderDelivery, *, output_path: Path, subtitle_track: SubtitleTrackReport, job: ClipRenderJob, style: ClipRenderSubtitleStyle | None) -> Path:
        manifest_path = Path(delivery.manifest_path or output_path.with_name(f"{output_path.stem}.delivery.json"))
        payload = {
            "manifest_version": 1,
            "delivery": delivery.to_dict(),
            "job": job.to_dict(),
            "subtitle_track": subtitle_track.track.to_dict() if subtitle_track.track else None,
            "warnings": list(subtitle_track.warnings),
            "errors": list(subtitle_track.errors),
            "style": style.to_dict() if style else None,
            "outputs": {
                "video": str(output_path) if output_path.suffix.lower() == ".mp4" else None,
                "subtitle": delivery.output_path,
                "manifest": str(manifest_path),
            },
            "created_at": utc_now().isoformat(),
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp = manifest_path.with_name(f"{manifest_path.stem}.part{manifest_path.suffix}")
        temp.write_text(build_delivery_manifest(payload), encoding="utf-8")
        temp.replace(manifest_path)
        return manifest_path

    def _build_delivery_record(
        self,
        *,
        job: ClipRenderJob,
        subtitle_track: SubtitleTrackReport,
        subtitle_config: ClipRenderSubtitleConfig,
        output_path: Path,
        manifest_path: Path | None,
        status: ClipRenderDeliveryStatus,
        warning_code: str | None = None,
        warning_message: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
        rendered_cue_count: int | None = None,
    ) -> ClipRenderDelivery:
        return ClipRenderDelivery(
            id=str(uuid4()),
            render_job_id=job.id,
            subtitle_track_id=subtitle_track.track.id if subtitle_track.track else None,
            subtitle_track_version=subtitle_track.track.track_version if subtitle_track.track else None,
            subtitle_track_fingerprint=subtitle_track.track.configuration_fingerprint if subtitle_track.track else None,
            subtitle_mode=subtitle_config.mode,
            subtitle_format=subtitle_config.format,
            style_preset=subtitle_config.style_preset,
            style_json=_json_dumps(subtitle_config.style.to_dict()) if subtitle_config.style else "{}",
            source_export_path=subtitle_config.source_export_path,
            source_export_fingerprint=subtitle_config.source_export_fingerprint,
            expected_cue_count=subtitle_config.expected_cue_count or 0,
            rendered_cue_count=rendered_cue_count or 0,
            output_path=str(output_path),
            manifest_path=str(manifest_path) if manifest_path else None,
            configuration_fingerprint=self._delivery_configuration_fingerprint(
                job=job,
                subtitle_track=subtitle_config,
                output_path=output_path,
                manifest_path=manifest_path,
            ),
            status=status,
            progress_percent=100.0 if status in {ClipRenderDeliveryStatus.COMPLETED, ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS} else 0.0,
            warning_code=warning_code,
            warning_message=warning_message,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
            created_at=utc_now(),
            updated_at=utc_now(),
            completed_at=utc_now() if status in {ClipRenderDeliveryStatus.COMPLETED, ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS} else None,
            cancelled_at=None,
        )

    def create_sidecar_delivery(
        self,
        job_id: str,
        track_id: str,
        *,
        format_name: str = "srt",
        output: str | Path | None = None,
        allow_stale: bool = False,
        allow_overwrite: bool = False,
        explicit: bool = False,
        custom_name: str | None = None,
    ) -> ClipRenderDeliveryReport:
        if self.subtitle_service is None:
            raise ClipRenderCapabilityError("El servicio de subtitulos no esta disponible.")
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            raise NotFoundError("El render solicitado no existe.")
        track_report = self._subtitle_track_report(track_id)
        if track_report.validation and track_report.validation.blocking_errors:
            raise ClipRenderStateError("El track de subtitulos contiene errores bloqueantes.")
        if track_report.is_stale and not allow_stale:
            raise ClipRenderStateError("El track de subtitulos esta desactualizado y requiere confirmacion.")
        if job.ranked_clip_candidate_id and track_report.track.ranked_clip_candidate_id not in {None, job.ranked_clip_candidate_id}:
            raise ClipRenderStateError("El track de subtitulos pertenece a otro candidato.")
        if track_report.track.status == SubtitleTrackStatus.ARCHIVED:
            raise ClipRenderStateError("El track de subtitulos esta archivado.")
        format_enum = SubtitleExportFormat(format_name)
        video, _, _, delivery_root = self._delivery_context(job)
        base_name = sanitize_filename_component(custom_name or Path(job.output_path).stem, fallback="delivery")
        delivery_dir = delivery_root / base_name
        delivery_dir.mkdir(parents=True, exist_ok=True)
        output_path = Path(output) if output is not None else delivery_dir / f"{base_name}.{format_enum.value}"
        manifest_path = delivery_dir / "delivery.json"
        if output_path.exists() and not allow_overwrite:
            raise ClipRenderStateError("La salida de subtitulos ya existe.")
        if allow_overwrite:
            output_path.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
        export_result = self.subtitle_service.export_subtitles(track_id, format_enum, output=output_path, custom_name=custom_name)
        verification = RenderOutputVerification(
            verified=export_result.verified,
            output_path=export_result.path,
            size_bytes=Path(export_result.path).stat().st_size if Path(export_result.path).exists() else None,
            duration_seconds=None,
            video_codec=None,
            audio_codec=None,
            width=None,
            height=None,
            frame_rate=None,
            audio_sample_rate=None,
            fingerprint=export_result.fingerprint,
            warnings=tuple(track_report.validation.warnings if track_report.validation else ()),
            errors=tuple(track_report.validation.blocking_errors if track_report.validation else ()),
            details={"round_trip": True, "format": format_enum.value},
        )
        subtitle_config = ClipRenderSubtitleConfig(
            mode=SubtitleRenderMode.SIDECAR_SRT if format_enum == SubtitleExportFormat.SRT else SubtitleRenderMode.SIDECAR_VTT,
            track_id=track_report.track.id,
            track_version=track_report.track.track_version,
            fingerprint=track_report.track.configuration_fingerprint,
            format=format_enum.value,
            style_preset=None,
            style=None,
            expected_cue_count=len(track_report.cues),
            stale_acknowledged=track_report.is_stale,
            temporary_ass_path=None,
            sidecar_output_path=str(output_path),
            source_export_path=export_result.path,
            source_export_fingerprint=export_result.fingerprint,
        )
        delivery = self._build_delivery_record(
            job=job,
            subtitle_track=track_report,
            subtitle_config=subtitle_config,
            output_path=output_path,
            manifest_path=manifest_path,
            status=ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS if verification.warnings else ClipRenderDeliveryStatus.COMPLETED,
            warning_code="warnings" if verification.warnings else None,
            warning_message="; ".join(verification.warnings) if verification.warnings else None,
            rendered_cue_count=len(track_report.cues),
        )
        manifest_path = self._write_manifest(delivery, output_path=Path(job.output_path), subtitle_track=track_report, job=job, style=None)
        delivery = replace(delivery, manifest_path=str(manifest_path), updated_at=utc_now())
        delivery = self._persist_delivery(delivery)
        artifacts = (
            self._persist_delivery_artifact(
                self._delivery_artifact(delivery.id, ClipRenderArtifactType.SUBTITLE_SRT if format_enum == SubtitleExportFormat.SRT else ClipRenderArtifactType.SUBTITLE_VTT, Path(export_result.path), verified=verification.verified, verification=verification.to_dict())
            ),
            self._persist_delivery_artifact(
                self._delivery_artifact(delivery.id, ClipRenderArtifactType.DELIVERY_MANIFEST, manifest_path, verified=True, verification={"manifest": True})
            ),
        )
        return ClipRenderDeliveryReport(delivery=delivery, job=job, artifacts=artifacts, verification=verification, reused_output=False, warnings=verification.warnings, errors=verification.errors)

    def create_burn_in_render(
        self,
        candidate_id: str,
        track_id: str,
        *,
        profile: str | ClipRenderProfile = "balanced",
        style_preset: str | SubtitleRenderStylePreset = SubtitleRenderStylePreset.CLEAN,
        output: str | Path | None = None,
        output_root_override: str | Path | None = None,
        explicit: bool = True,
        allow_stale: bool = False,
        allow_overwrite: bool = False,
        custom_name: str | None = None,
        renderer_version: str = "v1",
        progress_callback: RenderProgressCallback | None = None,
        cancellation_token: CancelToken | None = None,
    ) -> ClipRenderDeliveryReport:
        if self.subtitle_service is None:
            raise ClipRenderCapabilityError("El servicio de subtitulos no esta disponible.")
        candidate = self._require_candidate(candidate_id)
        track_report = self._subtitle_track_report(track_id)
        if track_report.validation and track_report.validation.blocking_errors:
            raise ClipRenderStateError("El track de subtitulos contiene errores bloqueantes.")
        if track_report.track is None:
            raise NotFoundError("El track de subtitulos no existe.")
        if track_report.track.ranked_clip_candidate_id not in {None, candidate.id}:
            raise ClipRenderStateError("El track de subtitulos pertenece a otro candidato.")
        if track_report.is_stale and not allow_stale:
            raise ClipRenderStateError("El track de subtitulos esta desactualizado y requiere confirmacion.")
        normalized_profile = normalize_render_profile(profile.value if isinstance(profile, ClipRenderProfile) else str(profile))
        preset = SubtitleRenderStylePreset(style_preset.value if isinstance(style_preset, SubtitleRenderStylePreset) else str(style_preset))
        style = self._subtitle_style(preset)
        video = self._require_video(self.clip_service.get_ranking_run(candidate.ranking_run_id).video_asset_id)
        creator_slug, project_slug = self._require_creator_and_project(video)
        delivery_root = self._delivery_root(creator_slug, project_slug) / sanitize_filename_component(video.title, fallback="video")
        delivery_root.mkdir(parents=True, exist_ok=True)
        base_name = sanitize_filename_component(custom_name or video.title or "subtitled", fallback="delivery")
        delivery_dir = delivery_root / base_name
        delivery_dir.mkdir(parents=True, exist_ok=True)
        ass_path = delivery_dir / f"{base_name}.ass"
        delivery_output = Path(output) if output is not None else delivery_dir / f"{base_name}_subtitled.mp4"
        if delivery_output.exists() and not allow_overwrite:
            raise ClipRenderStateError("La salida final ya existe.")
        ass_content = self._subtitle_exporter.export(track_report.track, list(track_report.cues), SubtitleExportFormat.ASS, style=style)
        ass_path.write_text(ass_content, encoding="utf-8")
        subtitle_config = ClipRenderSubtitleConfig(
            mode=SubtitleRenderMode.BURN_IN,
            track_id=track_report.track.id,
            track_version=track_report.track.track_version,
            fingerprint=track_report.track.configuration_fingerprint,
            format=SubtitleExportFormat.ASS.value,
            style_preset=preset,
            style=style,
            expected_cue_count=len(track_report.cues),
            stale_acknowledged=track_report.is_stale,
            temporary_ass_path=str(ass_path),
            sidecar_output_path=None,
            source_export_path=str(ass_path),
            source_export_fingerprint=hashlib.sha256(ass_content.encode("utf-8")).hexdigest(),
        )
        report = self.render_candidate(
            candidate.id,
            profile=normalized_profile,
            subtitle_config=subtitle_config,
            output=delivery_output,
            output_root_override=output_root_override or delivery_root,
            explicit=explicit,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            custom_name=custom_name or "subtitled",
            renderer_version=renderer_version,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )
        if report.job.status == ClipRenderJobStatus.CANCELLED:
            ass_path.unlink(missing_ok=True)
            if delivery_output.exists():
                delivery_output.unlink(missing_ok=True)
            cancelled_delivery = self._build_delivery_record(
                job=report.job,
                subtitle_track=track_report,
                subtitle_config=subtitle_config,
                output_path=delivery_output,
                manifest_path=None,
                status=ClipRenderDeliveryStatus.CANCELLED,
                warning_code="cancelled",
                warning_message="Render cancelado por el usuario.",
                error_code="cancelled",
                error_message="Render cancelado por el usuario.",
                rendered_cue_count=0,
            )
            cancelled_delivery = replace(cancelled_delivery, updated_at=utc_now())
            cancelled_delivery = self._persist_delivery(cancelled_delivery)
            return ClipRenderDeliveryReport(
                delivery=cancelled_delivery,
                job=report.job,
                artifacts=(),
                verification=None,
                reused_output=False,
                warnings=(),
                errors=("Render cancelado.",),
            )
        manifest_path = delivery_dir / "delivery.json"
        delivery = self._build_delivery_record(
            job=report.job,
            subtitle_track=track_report,
            subtitle_config=subtitle_config,
            output_path=delivery_output,
            manifest_path=manifest_path,
            status=ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS if report.warnings else ClipRenderDeliveryStatus.COMPLETED,
            warning_code="warnings" if report.warnings else None,
            warning_message="; ".join(report.warnings) if report.warnings else None,
            error_code="failed" if report.errors else None,
            error_message="; ".join(report.errors) if report.errors else None,
            rendered_cue_count=len(track_report.cues),
        )
        manifest_path = self._write_manifest(delivery, output_path=delivery_output, subtitle_track=track_report, job=report.job, style=style)
        delivery = replace(delivery, manifest_path=str(manifest_path), updated_at=utc_now())
        delivery = self._persist_delivery(delivery)
        artifacts = (
            self._persist_delivery_artifact(self._delivery_artifact(delivery.id, ClipRenderArtifactType.OUTPUT, delivery_output, verified=bool(report.verification and report.verification.verified), verification=report.verification.to_dict() if report.verification else {})),
            self._persist_delivery_artifact(self._delivery_artifact(delivery.id, ClipRenderArtifactType.BURN_IN_SOURCE_ASS, ass_path, verified=True, verification={"ass": True})),
            self._persist_delivery_artifact(self._delivery_artifact(delivery.id, ClipRenderArtifactType.DELIVERY_MANIFEST, manifest_path, verified=True, verification={"manifest": True})),
        )
        return ClipRenderDeliveryReport(delivery=delivery, job=report.job, artifacts=artifacts, verification=report.verification, reused_output=report.reused_output, warnings=report.warnings, errors=report.errors)

    def get_delivery(self, delivery_id: str) -> ClipRenderDelivery | None:
        return self.repository.get_delivery_by_id(delivery_id)

    def list_render_deliveries(self, job_id: str) -> list[ClipRenderDelivery]:
        return self.repository.list_deliveries_for_job(job_id)

    def list_candidate_deliveries(self, candidate_id: str) -> list[ClipRenderDelivery]:
        return self.repository.list_deliveries_for_candidate(candidate_id)

    def list_video_deliveries(self, video_asset_id: str) -> list[ClipRenderDelivery]:
        return self.repository.list_deliveries_for_video(video_asset_id)

    def verify_delivery(self, delivery_id: str) -> ClipRenderDeliveryReport:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None:
            raise NotFoundError("La entrega solicitada no existe.")
        job = self.repository.get_job_by_id(delivery.render_job_id)
        if job is None:
            raise NotFoundError("El job asociado a la entrega no existe.")
        artifacts = tuple(self.repository.list_delivery_artifacts_for_delivery(delivery.id))
        subtitle_track = self._subtitle_track_report(delivery.subtitle_track_id) if delivery.subtitle_track_id else None
        if delivery.subtitle_mode == SubtitleRenderMode.BURN_IN:
            verification = self._verifier.verify(self._current_plan(job), Path(delivery.output_path or job.output_path))
        else:
            output = Path(delivery.output_path or "")
            if not output.exists() or output.stat().st_size <= 0:
                verification = RenderOutputVerification(
                    verified=False,
                    output_path=str(output),
                    size_bytes=output.stat().st_size if output.exists() else None,
                    duration_seconds=None,
                    video_codec=None,
                    audio_codec=None,
                    width=None,
                    height=None,
                    frame_rate=None,
                    audio_sample_rate=None,
                    fingerprint=None,
                    warnings=(),
                    errors=("La salida de subtitulos no existe o esta vacia.",),
                    details={"delivery_id": delivery.id},
                )
            else:
                try:
                    parsed = self._subtitle_importer.import_file(output, format=SubtitleExportFormat(delivery.subtitle_format or "srt"), options=SubtitleGenerationOptions())
                except Exception as exc:
                    verification = RenderOutputVerification(
                        verified=False,
                        output_path=str(output),
                        size_bytes=output.stat().st_size,
                        duration_seconds=None,
                        video_codec=None,
                        audio_codec=None,
                        width=None,
                        height=None,
                        frame_rate=None,
                        audio_sample_rate=None,
                        fingerprint=self._fingerprint_file(output),
                        warnings=(),
                        errors=(str(exc),),
                        details={"delivery_id": delivery.id},
                    )
                else:
                    cue_count = len(parsed.cues)
                    verification = RenderOutputVerification(
                        verified=cue_count > 0,
                        output_path=str(output),
                        size_bytes=output.stat().st_size,
                        duration_seconds=None,
                        video_codec=None,
                        audio_codec=None,
                        width=None,
                        height=None,
                        frame_rate=None,
                        audio_sample_rate=None,
                        fingerprint=self._fingerprint_file(output),
                        warnings=parsed.warnings,
                        errors=() if cue_count > 0 else ("La salida de subtitulos no contiene cues.",),
                        details={"delivery_id": delivery.id, "cue_count": cue_count, "round_trip": True},
                    )
        updated = replace(
            delivery,
            status=ClipRenderDeliveryStatus.COMPLETED_WITH_WARNINGS if verification.warnings else ClipRenderDeliveryStatus.COMPLETED if verification.verified else ClipRenderDeliveryStatus.FAILED,
            progress_percent=100.0 if verification.verified else delivery.progress_percent,
            warning_code="verification_warnings" if verification.warnings else delivery.warning_code,
            warning_message="; ".join(verification.warnings) if verification.warnings else delivery.warning_message,
            error_code=None if verification.verified else "verification_failed",
            error_message=None if verification.verified else ("; ".join(verification.errors) or "La verificacion fallo."),
            updated_at=utc_now(),
            completed_at=utc_now() if verification.verified else delivery.completed_at,
        )
        self._persist_delivery(updated)
        return ClipRenderDeliveryReport(delivery=updated, job=job, artifacts=artifacts, verification=verification, reused_output=False, warnings=verification.warnings, errors=verification.errors)

    def retry_delivery(self, delivery_id: str, *, progress_callback: RenderProgressCallback | None = None, cancellation_token: CancelToken | None = None) -> ClipRenderDeliveryReport:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None:
            raise NotFoundError("La entrega solicitada no existe.")
        if delivery.subtitle_mode == SubtitleRenderMode.BURN_IN:
            if delivery.subtitle_track_id is None:
                raise ClipRenderStateError("La entrega no tiene track asociado.")
            job = self.repository.get_job_by_id(delivery.render_job_id)
            if job is None or job.ranked_clip_candidate_id is None:
                raise ClipRenderStateError("La entrega no tiene job asociado para reintento.")
            return self.create_burn_in_render(
                job.ranked_clip_candidate_id,
                delivery.subtitle_track_id,
                profile=job.render_profile,
                style_preset=delivery.style_preset or SubtitleRenderStylePreset.CLEAN,
                output=delivery.output_path,
                allow_stale=True,
                allow_overwrite=True,
                renderer_version=job.renderer_version,
                progress_callback=progress_callback,
                cancellation_token=cancellation_token,
            )
        if delivery.subtitle_mode in {SubtitleRenderMode.SIDECAR_SRT, SubtitleRenderMode.SIDECAR_VTT}:
            if delivery.subtitle_track_id is None:
                raise ClipRenderStateError("La entrega no tiene track asociado.")
            format_name = delivery.subtitle_format or "srt"
            return self.create_sidecar_delivery(
                delivery.render_job_id,
                delivery.subtitle_track_id,
                format_name=format_name,
                output=delivery.output_path,
                allow_stale=True,
                allow_overwrite=True,
                custom_name=Path(delivery.output_path or "").stem if delivery.output_path else None,
            )
        raise ClipRenderStateError("La modalidad de entrega no se puede reintentar.")

    def cancel_delivery(self, delivery_id: str) -> ClipRenderDelivery | None:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None:
            return None
        if delivery.output_path:
            Path(delivery.output_path).unlink(missing_ok=True)
        if delivery.manifest_path:
            Path(delivery.manifest_path).unlink(missing_ok=True)
        if delivery.source_export_path:
            Path(delivery.source_export_path).unlink(missing_ok=True)
        updated = replace(
            delivery,
            status=ClipRenderDeliveryStatus.CANCELLED,
            cancelled_at=utc_now(),
            updated_at=utc_now(),
            warning_code="cancelled",
            warning_message="Entrega cancelada por el usuario.",
        )
        self._persist_delivery(updated)
        return updated

    def delete_delivery(self, delivery_id: str) -> bool:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None:
            return False
        if delivery.output_path:
            Path(delivery.output_path).unlink(missing_ok=True)
        if delivery.manifest_path:
            Path(delivery.manifest_path).unlink(missing_ok=True)
        if delivery.source_export_path:
            Path(delivery.source_export_path).unlink(missing_ok=True)
        self.repository.delete_delivery_artifacts_for_delivery(delivery_id)
        return self.repository.delete_delivery(delivery_id)

    def reveal_delivery(self, delivery_id: str) -> Path | None:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None or not delivery.output_path:
            return None
        path = Path(delivery.output_path)
        return path if path.exists() else None

    def export_delivery_manifest(self, delivery_id: str, *, destination: str | Path | None = None) -> Path:
        delivery = self.repository.get_delivery_by_id(delivery_id)
        if delivery is None:
            raise NotFoundError("La entrega solicitada no existe.")
        manifest_path = Path(delivery.manifest_path) if delivery.manifest_path else None
        if manifest_path is None or not manifest_path.exists():
            raise ClipRenderStateError("La entrega no tiene manifest disponible.")
        destination_path = Path(destination) if destination is not None else manifest_path
        if destination_path != manifest_path:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(manifest_path.read_bytes())
        return destination_path

    def retry_render(self, job_id: str, *, progress_callback: RenderProgressCallback | None = None, cancellation_token: CancelToken | None = None) -> ClipRenderOperationReport:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            raise NotFoundError("El render solicitado no existe.")
        if job.ranked_clip_candidate_id is None:
            raise ClipRenderStateError("El render no tiene un candidato asociado para reintentar.")
        return self.render_candidate(
            job.ranked_clip_candidate_id,
            profile=job.render_profile,
            output=job.output_path,
            explicit=True,
            allow_stale=True,
            allow_overwrite=True,
            custom_name=None,
            renderer_version=job.renderer_version,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
            collection_id=job.collection_id,
        )

    def get_render_job(self, job_id: str) -> ClipRenderJob | None:
        return self.repository.get_job_by_id(job_id)

    def list_candidate_renders(self, candidate_id: str) -> list[ClipRenderJob]:
        return self.repository.list_jobs_for_candidate(candidate_id)

    def list_collection_renders(self, collection_id: str) -> list[ClipRenderJob]:
        return self.repository.list_jobs_for_collection(collection_id)

    def list_video_renders(self, video_asset_id: str) -> list[ClipRenderJob]:
        return self.repository.list_jobs_for_video(video_asset_id)

    def list_render_jobs(self) -> list[ClipRenderJob]:
        return self.repository.list_jobs()

    def list_render_batches_for_collection(self, collection_id: str) -> list[ClipRenderBatch]:
        return self.repository.list_batches_for_collection(collection_id)

    def list_render_batches_for_video(self, video_asset_id: str) -> list[ClipRenderBatch]:
        return self.repository.list_batches_for_video(video_asset_id)

    def get_render_batch(self, batch_id: str) -> ClipRenderBatch | None:
        return self.repository.get_batch_by_id(batch_id)

    def list_batch_items(self, batch_id: str) -> list[ClipRenderBatchItem]:
        return self.repository.list_batch_items(batch_id)

    def cancel_render_batch(self, batch_id: str) -> ClipRenderBatch | None:
        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            return None
        updated = replace(
            batch,
            status=ClipRenderBatchStatus.CANCELLED,
            updated_at=utc_now(),
            completed_at=utc_now(),
        )
        self.repository.upsert_batch(updated)
        for item in self.repository.list_batch_items(batch_id):
            self.cancel_render(item.render_job_id)
        return updated

    def retry_render_batch(self, batch_id: str, *, progress_callback: RenderProgressCallback | None = None, cancellation_token: CancelToken | None = None) -> ClipRenderBatchReport:
        batch = self.repository.get_batch_by_id(batch_id)
        if batch is None:
            raise NotFoundError("El lote solicitado no existe.")
        items = self.repository.list_batch_items(batch_id)
        jobs: list[ClipRenderJob] = []
        completed = failed = cancelled = 0
        for item in items:
            job = self.repository.get_job_by_id(item.render_job_id)
            if job is None or job.ranked_clip_candidate_id is None:
                failed += 1
                continue
            try:
                report = self.retry_render(job.id, progress_callback=progress_callback, cancellation_token=cancellation_token)
                jobs.append(report.job)
                if report.job.status in {ClipRenderJobStatus.COMPLETED, ClipRenderJobStatus.COMPLETED_WITH_WARNINGS}:
                    completed += 1
                elif report.job.status == ClipRenderJobStatus.CANCELLED:
                    cancelled += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        status = ClipRenderBatchStatus.COMPLETED if failed == 0 and cancelled == 0 else ClipRenderBatchStatus.COMPLETED_WITH_WARNINGS if completed > 0 and failed == 0 else ClipRenderBatchStatus.FAILED
        updated_batch = replace(
            batch,
            status=status,
            completed_count=completed,
            failed_count=failed,
            cancelled_count=cancelled,
            completed_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.upsert_batch(updated_batch)
        return ClipRenderBatchReport(batch=updated_batch, jobs=tuple(jobs))

    def verify_render(self, job_id: str) -> ClipRenderOperationReport:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            raise NotFoundError("El render solicitado no existe.")
        plan = self._current_plan(job)
        verification = self._verifier.verify(plan, Path(job.output_path))
        artifact = self.repository.upsert_artifact(
            ClipRenderArtifact(
                id=str(uuid4()),
                render_job_id=job.id,
                artifact_type=ClipRenderArtifactType.OUTPUT,
                managed_path=verification.output_path,
                fingerprint=verification.fingerprint or "",
                size_bytes=verification.size_bytes,
                duration_seconds=verification.duration_seconds,
                video_codec=verification.video_codec,
                audio_codec=verification.audio_codec,
                width=verification.width,
                height=verification.height,
                frame_rate=verification.frame_rate,
                audio_sample_rate=verification.audio_sample_rate,
                verified=verification.verified,
                verification_json=_json_dumps(verification.to_dict()),
                created_at=utc_now(),
            )
        )
        if verification.verified:
            job = self._update_job(
                job,
                status=ClipRenderJobStatus.COMPLETED_WITH_WARNINGS if verification.warnings else ClipRenderJobStatus.COMPLETED,
                progress_percent=100.0,
                completed_at=utc_now(),
                warning_code="verification_warnings" if verification.warnings else None,
                warning_message="; ".join(verification.warnings) if verification.warnings else None,
                error_code=None,
                error_message=None,
            )
        else:
            status = ClipRenderJobStatus.STALE if not Path(job.output_path).exists() else ClipRenderJobStatus.FAILED
            job = self._update_job(job, status=status, error_code="verification_failed", error_message="; ".join(verification.errors) or "La verificacion fallo.")
        self._append_event(job.id, "verified", 100.0 if verification.verified else job.progress_percent, "Verificacion de salida ejecutada.", {"verified": verification.verified, "warnings": list(verification.warnings), "errors": list(verification.errors)})
        return ClipRenderOperationReport(job=job, plan=plan, verification=verification, artifact=artifact, reused_output=False, warnings=verification.warnings, errors=verification.errors)

    def delete_render_artifact(self, job_id: str) -> bool:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            return False
        artifact = self.repository.get_artifact_for_job(job_id)
        if artifact is None:
            return False
        managed = Path(artifact.managed_path)
        if managed.exists():
            managed.unlink()
        temp_path = Path(_temporary_output_path(job.output_path))
        temp_path.unlink(missing_ok=True)
        self.repository.delete_artifact_for_job(job_id)
        self._update_job(job, status=ClipRenderJobStatus.STALE, warning_code="artifact_deleted", warning_message="El artefacto fue eliminado.")
        self._append_event(job.id, "artifact_deleted", job.progress_percent, "Artefacto eliminado.", {"path": artifact.managed_path})
        return True

    def reveal_render_output(self, job_id: str) -> Path | None:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            return None
        path = Path(job.output_path)
        return path if path.exists() else None

    def cancel_render(self, job_id: str) -> ClipRenderJob | None:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            return None
        temp_path = Path(_temporary_output_path(job.output_path))
        temp_path.unlink(missing_ok=True)
        updated = self._update_job(job, status=ClipRenderJobStatus.CANCELLED, cancelled_at=utc_now(), error_code="cancelled", error_message="Render cancelado por el usuario.")
        self._append_event(updated.id, "cancelled", updated.progress_percent, "Render cancelado.", {})
        return updated

    def render_collection(
        self,
        collection_id: str,
        *,
        profile: str | ClipRenderProfile = "balanced",
        output_root: str | Path | None = None,
        explicit: bool = False,
        allow_stale: bool = False,
        continue_on_failure: bool = False,
    ) -> ClipRenderBatchReport:
        collection = self._require_collection(collection_id)
        items = self.clip_service.clip_repository.list_collection_items(collection_id)
        if not items:
            raise ClipRenderStateError("La coleccion no tiene candidatos para renderizar.")
        batch = ClipRenderBatch(
            id=str(uuid4()),
            collection_id=collection.id,
            video_asset_id=collection.video_asset_id,
            name=collection.name,
            status=ClipRenderBatchStatus.QUEUED,
            job_count=len(items),
            completed_count=0,
            failed_count=0,
            cancelled_count=0,
            started_at=utc_now(),
            completed_at=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.upsert_batch(batch)
        jobs: list[ClipRenderJob] = []
        completed = failed = cancelled = 0
        batch_status = ClipRenderBatchStatus.RUNNING
        for item in items:
            candidate = self._require_candidate(item.ranked_clip_candidate_id)
            try:
                report = self.render_candidate(
                    candidate.id,
                    profile=profile,
                    output=None,
                    output_root_override=output_root,
                    explicit=explicit,
                    allow_stale=allow_stale,
                    allow_overwrite=False,
                    custom_name=item.custom_title or (candidate.explanation.get("title") if isinstance(candidate.explanation, dict) else None),
                    collection_id=collection.id,
                )
                jobs.append(report.job)
                if report.job.status in {ClipRenderJobStatus.COMPLETED, ClipRenderJobStatus.COMPLETED_WITH_WARNINGS}:
                    completed += 1
                else:
                    failed += 1
                    if not continue_on_failure:
                        batch_status = ClipRenderBatchStatus.FAILED
                        break
            except ClipRenderExecutionError:
                failed += 1
                if not continue_on_failure:
                    batch_status = ClipRenderBatchStatus.FAILED
                    break
            except Exception:
                failed += 1
                if not continue_on_failure:
                    batch_status = ClipRenderBatchStatus.FAILED
                    break
        if batch_status != ClipRenderBatchStatus.FAILED:
            if failed:
                batch_status = ClipRenderBatchStatus.COMPLETED_WITH_WARNINGS
            else:
                batch_status = ClipRenderBatchStatus.COMPLETED
        updated_batch = replace(
            batch,
            status=batch_status,
            job_count=len(items),
            completed_count=completed,
            failed_count=failed,
            cancelled_count=cancelled,
            completed_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.upsert_batch(updated_batch)
        return ClipRenderBatchReport(batch=updated_batch, jobs=tuple(jobs))

    def export_render_plan(self, job_id: str, *, destination: str | Path | None = None) -> Path:
        job = self.repository.get_job_by_id(job_id)
        if job is None:
            raise NotFoundError("El render solicitado no existe.")
        payload = {
            "job": job.to_dict(),
            "exported_at": utc_now().isoformat(),
        }
        output = Path(destination) if destination is not None else Path(job.output_path).with_suffix(".plan.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output


def build_clip_render_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    media_service: MediaInspectionService,
    clip_service: ClipRankingService,
    repository: ClipRenderRepository,
    subtitle_service: SubtitleService | None = None,
    logger: logging.Logger | None = None,
    tool_locator: MediaToolLocator | None = None,
) -> ClipRenderService:
    return ClipRenderService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        media_service=media_service,
        clip_service=clip_service,
        repository=repository,
        subtitle_service=subtitle_service,
        logger=logger,
        tool_locator=tool_locator,
    )
