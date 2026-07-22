"""Servicio de aplicacion para analisis visual local."""

from __future__ import annotations

import csv
import io
import json
import logging
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.errors import ConflictError, NotFoundError
from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.visual_analysis.entities import (
    VisualAnalysis,
    VisualEvent,
    VisualScene,
    VisualTimelineWindow,
)
from creator_intelligence_studio.domain.visual_analysis.errors import VisualAnalysisStateError, VisualAnalysisValidationError
from creator_intelligence_studio.domain.visual_analysis.repositories import VisualAnalysisRepository
from creator_intelligence_studio.domain.visual_analysis.services import (
    build_visual_configuration_fingerprint,
    build_visual_source_fingerprint,
    is_visual_analysis_stale,
    normalize_visual_analysis_config,
    validate_visual_analysis_options,
)
from creator_intelligence_studio.domain.visual_analysis.value_objects import (
    VisualActivityLabel,
    VisualAnalysisOptions,
    VisualAnalysisStatus,
    VisualEventData,
    VisualEventType,
    VisualSceneData,
    VisualTimelineWindowData,
)
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_inspection_repository import SQLiteVideoInspectionRepository
from creator_intelligence_studio.infrastructure.visual_analysis.frame_metrics import compute_frame_metrics
from creator_intelligence_studio.infrastructure.visual_analysis.frame_sampler import FrameSamplingError, sample_frames
from creator_intelligence_studio.infrastructure.visual_analysis.keyframe_extractor import KeyframeExtractionError, build_keyframe_path, extract_keyframe
from creator_intelligence_studio.infrastructure.visual_analysis.scene_detector import DetectedCut, DetectedScene, build_scenes, detect_cut_candidates
from creator_intelligence_studio.infrastructure.visual_analysis.visual_event_detector import detect_visual_events
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class VisualAnalysisReport:
    """Estado y resultado de un analisis visual."""

    video: VideoAsset
    inspection: VideoInspection | None
    analysis: VisualAnalysis | None
    windows: tuple[VisualTimelineWindow, ...]
    scenes: tuple[VisualScene, ...]
    events: tuple[VisualEvent, ...]
    status: VisualAnalysisStatus
    is_stale: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    progress_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "inspection": self.inspection.to_dict() if self.inspection else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "windows": [window.to_dict() for window in self.windows],
            "scenes": [scene.to_dict() for scene in self.scenes],
            "events": [event.to_dict() for event in self.events],
            "status": self.status.value,
            "is_stale": self.is_stale,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "progress_message": self.progress_message,
        }


@dataclass(frozen=True, slots=True)
class VisualAnalysisExportResult:
    """Resultado de exportacion del analisis visual."""

    video: VideoAsset
    analysis: VisualAnalysis
    format: str
    content: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "analysis": self.analysis.to_dict(),
            "format": self.format,
            "content": self.content,
            "path": self.path,
        }


def _snapshot_file(video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
    path = Path(video.source_path)
    if not path.exists() or not path.is_file():
        return False, None, None
    stat = path.stat()
    return True, stat.st_size, datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _safe_delete(path: Path, *, root: Path) -> bool:
    try:
        if not path.resolve().is_relative_to(root.resolve()):
            return False
    except FileNotFoundError:
        pass
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def _json_default(value):
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class VisualAnalysisService:
    """Coordina analisis visual, persistencia y exportacion."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        inspection_repository: SQLiteVideoInspectionRepository,
        visual_repository: VisualAnalysisRepository,
        logger: logging.Logger | None = None,
        tool_locator: MediaToolLocator | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.inspection_repository = inspection_repository
        self.visual_repository = visual_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.visual")
        self.tool_locator = tool_locator or MediaToolLocator(settings=settings, project_root=paths.project_root)
        self.options = normalize_visual_analysis_config(VisualAnalysisOptions())
        self._active_jobs: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _load_inspection(self, video_id: str) -> VideoInspection | None:
        return self.inspection_repository.get_by_video_asset_id(video_id)

    def _load_analysis(self, video_id: str) -> VisualAnalysis | None:
        return self.visual_repository.get_by_video_asset_id(video_id)

    def _visual_cache_root(self, video_id: str) -> Path:
        return self.paths.project_root / "cache" / "videos" / video_id / "visual"

    def _visual_keyframe_root(self, video_id: str, fingerprint: str) -> Path:
        return self._visual_cache_root(video_id) / "keyframes" / fingerprint

    def _visual_analysis_root(self, video_id: str) -> Path:
        return self._visual_cache_root(video_id) / "analysis"

    def _report(
        self,
        *,
        video: VideoAsset,
        inspection: VideoInspection | None,
        analysis: VisualAnalysis | None,
        windows: list[VisualTimelineWindow] | None = None,
        scenes: list[VisualScene] | None = None,
        events: list[VisualEvent] | None = None,
        status: VisualAnalysisStatus | None = None,
        is_stale: bool = False,
        warnings: tuple[str, ...] = (),
        errors: tuple[str, ...] = (),
        progress_message: str | None = None,
    ) -> VisualAnalysisReport:
        if analysis is not None:
            if windows is None:
                windows = self.visual_repository.list_windows(analysis.id)
            if scenes is None:
                scenes = self.visual_repository.list_scenes(analysis.id)
            if events is None:
                events = self.visual_repository.list_events(analysis.id)
        resolved_status = status or (analysis.status if analysis else VisualAnalysisStatus.NOT_ANALYZED)
        return VisualAnalysisReport(
            video=video,
            inspection=inspection,
            analysis=analysis,
            windows=tuple(windows or ()),
            scenes=tuple(scenes or ()),
            events=tuple(events or ()),
            status=resolved_status,
            is_stale=is_stale,
            warnings=warnings,
            errors=errors,
            progress_message=progress_message,
        )

    def _build_analysis_entity(
        self,
        *,
        analysis_id: str,
        video: VideoAsset,
        inspection: VideoInspection,
        source_snapshot: tuple[bool, int | None, datetime | None],
        windows: list[VisualTimelineWindowData],
        scenes: list[VisualSceneData],
        events: list[VisualEventData],
        started_at: datetime,
        completed_at: datetime,
    ) -> tuple[VisualAnalysis, list[VisualTimelineWindow], list[VisualScene], list[VisualEvent]]:
        exists, size_bytes, modified_at = source_snapshot
        source_fingerprint = build_visual_source_fingerprint(
            video=video,
            inspection=inspection,
            source_file_size_bytes=size_bytes if exists else None,
            source_file_modified_at=modified_at.isoformat() if modified_at else None,
        )
        configuration_fingerprint = build_visual_configuration_fingerprint(self.options)
        analysis = VisualAnalysis(
            id=analysis_id,
            video_asset_id=video.id,
            source_inspection_id=inspection.id,
            status=VisualAnalysisStatus.COMPLETED,
            analyzer_version=self.options.analyzer_version,
            configuration_fingerprint=configuration_fingerprint,
            source_fingerprint=source_fingerprint,
            source_file_size_bytes=size_bytes if exists else None,
            source_file_modified_at=modified_at,
            duration_seconds=inspection.duration_seconds,
            sampled_frame_count=len(windows),
            detected_cut_count=sum(1 for event in events if event.event_type in {VisualEventType.HARD_CUT, VisualEventType.GRADUAL_TRANSITION}),
            detected_scene_count=len(scenes),
            keyframe_count=len(scenes),
            static_segment_count=sum(1 for window in windows if window.activity_label == VisualActivityLabel.STATIC),
            black_frame_event_count=sum(1 for event in events if event.event_type == VisualEventType.BLACK_FRAME_CANDIDATE),
            freeze_event_count=sum(1 for event in events if event.event_type == VisualEventType.FREEZE_CANDIDATE),
            average_brightness=float(sum(window.brightness for window in windows) / len(windows)) if windows else 0.0,
            brightness_variation=float((max(window.brightness for window in windows) - min(window.brightness for window in windows)) if windows else 0.0),
            average_contrast=float(sum(window.contrast for window in windows) / len(windows)) if windows else 0.0,
            average_motion=float(sum(window.motion_score for window in windows) / len(windows)) if windows else 0.0,
            peak_motion=float(max((window.motion_score for window in windows), default=0.0)),
            started_at=started_at,
            completed_at=completed_at,
            warning_code=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            created_at=started_at,
            updated_at=completed_at,
        )
        persisted_windows: list[VisualTimelineWindow] = []
        for window in windows:
            persisted_windows.append(
                VisualTimelineWindow(
                    id=str(uuid4()),
                    visual_analysis_id=analysis.id,
                    window_index=window.window_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    sampled_frame_count=window.sampled_frame_count,
                    brightness=window.brightness,
                    contrast=window.contrast,
                    saturation=window.saturation,
                    motion_score=window.motion_score,
                    color_change_score=window.color_change_score,
                    is_static=window.is_static,
                    is_black=window.is_black,
                    is_possible_freeze=window.is_possible_freeze,
                    activity_label=window.activity_label,
                    created_at=completed_at,
                )
            )
        persisted_scenes: list[VisualScene] = []
        for scene in scenes:
            persisted_scenes.append(
                VisualScene(
                    id=str(uuid4()),
                    visual_analysis_id=analysis.id,
                    scene_index=scene.scene_index,
                    start_seconds=scene.start_seconds,
                    end_seconds=scene.end_seconds,
                    duration_seconds=scene.duration_seconds,
                    representative_keyframe_path=scene.representative_keyframe_path,
                    cut_in_score=scene.cut_in_score,
                    average_motion=scene.average_motion,
                    average_brightness=scene.average_brightness,
                    average_contrast=scene.average_contrast,
                    created_at=completed_at,
                )
            )
        persisted_events: list[VisualEvent] = []
        for event in events:
            persisted_events.append(
                VisualEvent(
                    id=str(uuid4()),
                    visual_analysis_id=analysis.id,
                    event_index=event.event_index,
                    start_seconds=event.start_seconds,
                    end_seconds=event.end_seconds,
                    event_type=event.event_type,
                    confidence=event.confidence,
                    evidence_json=json.dumps(event.evidence, ensure_ascii=False, separators=(",", ":")),
                    created_at=completed_at,
                )
            )
        return analysis, persisted_windows, persisted_scenes, persisted_events

    def _analysis_is_stale(
        self,
        analysis: VisualAnalysis | None,
        *,
        video: VideoAsset,
        inspection: VideoInspection | None,
        source_snapshot: tuple[bool, int | None, datetime | None],
    ) -> bool:
        if analysis is None:
            return False
        if inspection is None or inspection.inspection_status != VideoInspectionStatus.COMPLETED:
            return True
        exists, size_bytes, modified_at = source_snapshot
        if not exists:
            return True
        if not is_visual_analysis_stale(
            analysis,
            video=video,
            inspection=inspection,
            options=self.options,
            source_file_size_bytes=size_bytes,
            source_file_modified_at=modified_at.isoformat() if modified_at else None,
        ):
            # comprobar keyframes esperados
            scenes = self.visual_repository.list_scenes(analysis.id)
            for scene in scenes:
                if scene.representative_keyframe_path is None:
                    return True
                if not (self.paths.project_root / scene.representative_keyframe_path).exists():
                    return True
            return False
        return True

    def _merge_samples(self, samples: list, refined_samples: list) -> list:
        merged: dict[float, object] = {}
        for sample in samples + refined_samples:
            merged[round(float(sample.timestamp_seconds), 3)] = sample
        return [merged[key] for key in sorted(merged)]

    def _refine_samples(
        self,
        *,
        ffmpeg_path: Path,
        video: VideoAsset,
        inspection: VideoInspection,
        candidate_timestamps: list[float],
    ) -> list:
        refined = []
        for timestamp in candidate_timestamps:
            start = max(0.0, timestamp - self.options.refine_window_seconds / 2.0)
            refined.extend(
                sample_frames(
                    ffmpeg_path=ffmpeg_path,
                    source_path=Path(video.source_path),
                    duration_seconds=inspection.duration_seconds,
                    source_width=inspection.width,
                    source_height=inspection.height,
                    sample_fps=self.options.refine_sample_fps,
                    max_sample_frames=max(4, int(self.options.refine_sample_fps * self.options.refine_window_seconds * 4)),
                    target_width=self.options.target_sample_width,
                    target_height=self.options.target_sample_height,
                    start_seconds=start,
                    window_duration_seconds=self.options.refine_window_seconds,
                    timeout_seconds=max(30.0, self.settings.audio_extraction_timeout_seconds),
                )
            )
        return refined

    def _persist_failure(
        self,
        *,
        video: VideoAsset,
        inspection: VideoInspection | None,
        status: VisualAnalysisStatus,
        error_code: str,
        error_message: str,
        warnings: tuple[str, ...] = (),
    ) -> VisualAnalysisReport:
        existing = self._load_analysis(video.id)
        now = utc_now()
        if existing is None or existing.status != VisualAnalysisStatus.COMPLETED:
            analysis = VisualAnalysis(
                id=existing.id if existing else str(uuid4()),
                video_asset_id=video.id,
                source_inspection_id=inspection.id if inspection else None,
                status=status,
                analyzer_version=self.options.analyzer_version,
                configuration_fingerprint=build_visual_configuration_fingerprint(self.options),
                source_fingerprint=build_visual_source_fingerprint(
                    video=video,
                    inspection=inspection,
                    source_file_size_bytes=video.file_size_bytes,
                    source_file_modified_at=video.file_modified_at.isoformat() if video.file_modified_at else None,
                ),
                source_file_size_bytes=video.file_size_bytes,
                source_file_modified_at=video.file_modified_at,
                duration_seconds=inspection.duration_seconds if inspection else None,
                sampled_frame_count=0,
                detected_cut_count=0,
                detected_scene_count=0,
                keyframe_count=0,
                static_segment_count=0,
                black_frame_event_count=0,
                freeze_event_count=0,
                average_brightness=0.0,
                brightness_variation=0.0,
                average_contrast=0.0,
                average_motion=0.0,
                peak_motion=0.0,
                started_at=now,
                completed_at=now,
                warning_code=None,
                warning_message=None,
                error_code=error_code,
                error_message=error_message,
                created_at=now,
                updated_at=now,
            )
            persisted = self.visual_repository.upsert(analysis, [], [], [])
        else:
            persisted = existing
        return self._report(
            video=video,
            inspection=inspection,
            analysis=persisted,
            status=status,
            is_stale=False,
            warnings=warnings,
            errors=(error_message,),
        )

    def analyze_visuals(self, video_id: str, force: bool = False, *, progress_callback=None) -> VisualAnalysisReport:
        video = self._require_video(video_id)
        inspection = self._load_inspection(video.id)
        existing = self._load_analysis(video.id)
        source_snapshot = _snapshot_file(video)
        if existing and not force and not self._analysis_is_stale(existing, video=video, inspection=inspection, source_snapshot=source_snapshot):
            return self.get_visual_analysis(video.id)
        if inspection is None:
            return self._persist_failure(
                video=video,
                inspection=None,
                status=VisualAnalysisStatus.INSPECTION_MISSING,
                error_code="inspection_missing",
                error_message="No existe una inspeccion tecnica completada para este video.",
            )
        if inspection.inspection_status != VideoInspectionStatus.COMPLETED:
            return self._persist_failure(
                video=video,
                inspection=inspection,
                status=VisualAnalysisStatus.INSPECTION_MISSING,
                error_code="inspection_missing",
                error_message="La inspeccion tecnica no esta completada.",
            )
        if not source_snapshot[0]:
            return self._persist_failure(
                video=video,
                inspection=inspection,
                status=VisualAnalysisStatus.FILE_MISSING,
                error_code="file_missing",
                error_message="El video fuente no esta disponible.",
            )
        if existing and not force and self._analysis_is_stale(existing, video=video, inspection=inspection, source_snapshot=source_snapshot):
            return self.get_visual_analysis(video.id)
        tools = self.tool_locator.discover()
        if not tools.ffmpeg.available:
            return self._persist_failure(
                video=video,
                inspection=inspection,
                status=VisualAnalysisStatus.TOOL_UNAVAILABLE,
                error_code="tool_unavailable",
                error_message=tools.ffmpeg.error_message or "ffmpeg no esta disponible.",
                warnings=(tools.ffmpeg.error_message or "ffmpeg no esta disponible.",),
            )
        if progress_callback is not None:
            progress_callback("Preparando video", 0.05)
        try:
            base_samples = sample_frames(
                ffmpeg_path=Path(tools.ffmpeg.path) if tools.ffmpeg.path else Path("ffmpeg"),
                source_path=Path(video.source_path),
                duration_seconds=inspection.duration_seconds,
                source_width=inspection.width,
                source_height=inspection.height,
                sample_fps=self.options.sample_fps,
                max_sample_frames=self.options.max_sample_frames,
                target_width=self.options.target_sample_width,
                target_height=self.options.target_sample_height,
                timeout_seconds=max(30.0, self.settings.audio_extraction_timeout_seconds),
            )
        except FrameSamplingError as exc:
            return self._persist_failure(
                video=video,
                inspection=inspection,
                status=VisualAnalysisStatus.FAILED,
                error_code="sampling_failed",
                error_message=str(exc),
                warnings=(str(exc),),
            )
        if progress_callback is not None:
            progress_callback("Muestreando frames", 0.25)
        base_metrics = compute_frame_metrics(base_samples)
        provisional_cuts = detect_cut_candidates(base_metrics, self.options)
        refine_timestamps = [cut.start_seconds for cut in provisional_cuts[: min(8, len(provisional_cuts))]]
        if refine_timestamps:
            try:
                refined_samples = self._refine_samples(
                    ffmpeg_path=Path(tools.ffmpeg.path) if tools.ffmpeg.path else Path("ffmpeg"),
                    video=video,
                    inspection=inspection,
                    candidate_timestamps=refine_timestamps,
                )
            except FrameSamplingError as exc:
                return self._persist_failure(
                    video=video,
                    inspection=inspection,
                    status=VisualAnalysisStatus.FAILED,
                    error_code="sampling_failed",
                    error_message=str(exc),
                    warnings=(str(exc),),
                )
        else:
            refined_samples = []
        merged_samples = self._merge_samples(base_samples, refined_samples)
        if progress_callback is not None:
            progress_callback("Detectando cortes", 0.45)
        metrics = compute_frame_metrics(merged_samples)
        cuts = detect_cut_candidates(metrics, self.options)
        if progress_callback is not None:
            progress_callback("Agrupando escenas", 0.62)
        scenes_raw = build_scenes(
            metrics,
            cuts,
            duration_seconds=inspection.duration_seconds or (merged_samples[-1].timestamp_seconds if merged_samples else 0.0),
            min_scene_duration_seconds=self.options.scene_min_duration_seconds,
        )
        events_raw = detect_visual_events(metrics, cuts, self.options)
        if progress_callback is not None:
            progress_callback("Generando keyframes", 0.78)
        analysis_id = existing.id if existing else str(uuid4())
        keyframe_fingerprint = build_visual_configuration_fingerprint(self.options)
        keyframe_root = self._visual_keyframe_root(video.id, keyframe_fingerprint)
        temp_keyframe_root = keyframe_root.parent / f".tmp-{analysis_id}-{uuid4().hex}"
        temp_keyframe_root.mkdir(parents=True, exist_ok=True)
        scenes: list[VisualSceneData] = []
        keyframe_paths: list[Path] = []
        try:
            for scene in scenes_raw:
                scene_metrics = [metric for metric in metrics if scene.start_seconds <= metric.timestamp_seconds < scene.end_seconds]
                representative = max(scene_metrics or metrics, key=lambda metric: (metric.contrast + metric.motion_score * 0.5, -metric.timestamp_seconds))
                temp_path = temp_keyframe_root / f"scene-{scene.scene_index:04d}.jpg"
                extract_keyframe(
                    ffmpeg_path=Path(tools.ffmpeg.path) if tools.ffmpeg.path else Path("ffmpeg"),
                    source_path=Path(video.source_path),
                    destination_path=temp_path,
                    timestamp_seconds=representative.timestamp_seconds,
                    width=self.options.keyframe_width,
                    timeout_seconds=max(30.0, self.settings.audio_extraction_timeout_seconds),
                )
                final_path = build_keyframe_path(self.paths.project_root / "cache", video.id, keyframe_fingerprint, scene.scene_index)
                final_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.replace(final_path)
                keyframe_paths.append(final_path)
                scenes.append(
                    VisualSceneData(
                        scene_index=scene.scene_index,
                        start_seconds=scene.start_seconds,
                        end_seconds=scene.end_seconds,
                        duration_seconds=scene.duration_seconds,
                        representative_keyframe_path=str(final_path.relative_to(self.paths.project_root)),
                        cut_in_score=scene.cut_in_score,
                        average_motion=scene.average_motion,
                        average_brightness=scene.average_brightness,
                        average_contrast=scene.average_contrast,
                    )
                )
        except KeyframeExtractionError as exc:
            shutil.rmtree(temp_keyframe_root, ignore_errors=True)
            return self._persist_failure(
                video=video,
                inspection=inspection,
                status=VisualAnalysisStatus.FAILED,
                error_code="keyframe_failed",
                error_message=str(exc),
                warnings=(str(exc),),
            )
        shutil.rmtree(temp_keyframe_root, ignore_errors=True)
        if progress_callback is not None:
            progress_callback("Calculando metricas", 0.88)
        analysis, persisted_windows, persisted_scenes, persisted_events = self._build_analysis_entity(
            analysis_id=analysis_id,
            video=video,
            inspection=inspection,
            source_snapshot=source_snapshot,
            windows=[
                VisualTimelineWindowData(
                    window_index=index,
                    start_seconds=metric.timestamp_seconds,
                    end_seconds=metric.timestamp_seconds + (1.0 / max(self.options.sample_fps, 1.0)),
                    sampled_frame_count=1,
                    brightness=metric.brightness,
                    contrast=metric.contrast,
                    saturation=metric.saturation,
                    motion_score=metric.motion_score,
                    color_change_score=metric.color_change_score,
                    is_static=metric.is_static,
                    is_black=metric.is_black,
                    is_possible_freeze=metric.is_possible_freeze,
                    activity_label=metric.activity_label,
                )
                for index, metric in enumerate(metrics)
            ],
            scenes=scenes,
            events=events_raw,
            started_at=utc_now(),
            completed_at=utc_now(),
        )
        if progress_callback is not None:
            progress_callback("Guardando resultados", 0.95)
        persisted = self.visual_repository.upsert(analysis, persisted_windows, persisted_scenes, persisted_events)
        if progress_callback is not None:
            progress_callback("Completado", 1.0)
        return self._report(
            video=video,
            inspection=inspection,
            analysis=persisted,
            windows=self.visual_repository.list_windows(persisted.id),
            scenes=self.visual_repository.list_scenes(persisted.id),
            events=self.visual_repository.list_events(persisted.id),
            status=VisualAnalysisStatus.COMPLETED,
            is_stale=False,
            progress_message="Completado",
        )

    def get_visual_analysis(self, video_id: str) -> VisualAnalysisReport:
        video = self._require_video(video_id)
        inspection = self._load_inspection(video.id)
        analysis = self._load_analysis(video.id)
        source_snapshot = _snapshot_file(video)
        is_stale = self._analysis_is_stale(analysis, video=video, inspection=inspection, source_snapshot=source_snapshot)
        if analysis is None:
            return self._report(
                video=video,
                inspection=inspection,
                analysis=None,
                status=VisualAnalysisStatus.NOT_ANALYZED,
                is_stale=False,
            )
        status = analysis.status
        if inspection is None:
            status = VisualAnalysisStatus.INSPECTION_MISSING
        elif inspection.inspection_status != VideoInspectionStatus.COMPLETED:
            status = VisualAnalysisStatus.INSPECTION_MISSING
        elif not source_snapshot[0]:
            status = VisualAnalysisStatus.FILE_MISSING
        elif is_stale:
            status = VisualAnalysisStatus.STALE
        windows = self.visual_repository.list_windows(analysis.id)
        scenes = self.visual_repository.list_scenes(analysis.id)
        events = self.visual_repository.list_events(analysis.id)
        return self._report(
            video=video,
            inspection=inspection,
            analysis=analysis,
            windows=windows,
            scenes=scenes,
            events=events,
            status=status,
            is_stale=is_stale,
        )

    def get_visual_timeline(self, video_id: str) -> list[VisualTimelineWindow]:
        return list(self.get_visual_analysis(video_id).windows)

    def list_visual_scenes(self, video_id: str) -> list[VisualScene]:
        return list(self.get_visual_analysis(video_id).scenes)

    def list_visual_events(self, video_id: str) -> list[VisualEvent]:
        return list(self.get_visual_analysis(video_id).events)

    def is_visual_analysis_stale(self, video_id: str) -> bool:
        return self.get_visual_analysis(video_id).is_stale

    def delete_visual_analysis(self, video_id: str) -> bool:
        deleted = self.visual_repository.delete_by_video_asset_id(video_id)
        if deleted:
            shutil.rmtree(self._visual_cache_root(video_id), ignore_errors=True)
        return deleted

    def export_visual_analysis(
        self,
        video_id: str,
        format: str,
        *,
        destination: Path | None = None,
    ) -> VisualAnalysisExportResult:
        report = self.get_visual_analysis(video_id)
        if report.analysis is None:
            raise NotFoundError("No existe un analisis visual para exportar.")
        analysis = report.analysis
        windows = list(report.windows)
        scenes = list(report.scenes)
        events = list(report.events)
        format_name = format.lower().strip()
        if format_name == "json":
            content = json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default)
            suffix = ".json"
        elif format_name == "timeline-csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "window_index",
                "start_seconds",
                "end_seconds",
                "sampled_frame_count",
                "brightness",
                "contrast",
                "saturation",
                "motion_score",
                "color_change_score",
                "is_static",
                "is_black",
                "is_possible_freeze",
                "activity_label",
            ])
            for window in windows:
                writer.writerow([
                    window.window_index,
                    window.start_seconds,
                    window.end_seconds,
                    window.sampled_frame_count,
                    window.brightness,
                    window.contrast,
                    window.saturation,
                    window.motion_score,
                    window.color_change_score,
                    int(window.is_static),
                    int(window.is_black),
                    int(window.is_possible_freeze),
                    window.activity_label.value,
                ])
            content = output.getvalue()
            suffix = ".timeline.csv"
        elif format_name == "scenes-csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "scene_index",
                "start_seconds",
                "end_seconds",
                "duration_seconds",
                "representative_keyframe_path",
                "cut_in_score",
                "average_motion",
                "average_brightness",
                "average_contrast",
            ])
            for scene in scenes:
                writer.writerow([
                    scene.scene_index,
                    scene.start_seconds,
                    scene.end_seconds,
                    scene.duration_seconds,
                    scene.representative_keyframe_path,
                    scene.cut_in_score,
                    scene.average_motion,
                    scene.average_brightness,
                    scene.average_contrast,
                ])
            content = output.getvalue()
            suffix = ".scenes.csv"
        elif format_name == "txt":
            lines = [
                f"Video: {video_id}",
                f"Estado: {analysis.status.value}",
                f"Duracion: {analysis.duration_seconds:.3f} s" if analysis.duration_seconds is not None else "Duracion: N/D",
                f"Frames muestreados: {analysis.sampled_frame_count}",
                f"Cortes: {analysis.detected_cut_count}",
                f"Escenas: {analysis.detected_scene_count}",
                f"Keyframes: {analysis.keyframe_count}",
                f"Segmentos estaticos: {analysis.static_segment_count}",
                f"Posibles frames negros: {analysis.black_frame_event_count}",
                f"Posibles congelamientos: {analysis.freeze_event_count}",
                f"Brillo medio: {analysis.average_brightness:.4f}" if analysis.average_brightness is not None else "Brillo medio: N/D",
                f"Variacion de brillo: {analysis.brightness_variation:.4f}" if analysis.brightness_variation is not None else "Variacion de brillo: N/D",
                f"Contraste medio: {analysis.average_contrast:.4f}" if analysis.average_contrast is not None else "Contraste medio: N/D",
                f"Movimiento medio: {analysis.average_motion:.4f}" if analysis.average_motion is not None else "Movimiento medio: N/D",
                f"Movimiento pico: {analysis.peak_motion:.4f}" if analysis.peak_motion is not None else "Movimiento pico: N/D",
                "",
                "Escenas:",
            ]
            for scene in scenes:
                lines.append(
                    f"[{scene.scene_index}] {scene.start_seconds:.3f}-{scene.end_seconds:.3f} keyframe={scene.representative_keyframe_path} motion={scene.average_motion:.4f}"
                )
            lines.append("")
            lines.append("Eventos:")
            for event in events:
                lines.append(
                    f"[{event.event_index}] {event.event_type.value} {event.start_seconds:.3f}-{event.end_seconds:.3f} conf={event.confidence:.3f}"
                )
            content = "\n".join(lines) + "\n"
            suffix = ".txt"
        else:
            raise VisualAnalysisValidationError(f"Formato de exportacion no soportado: {format}")
        target = destination or (self._visual_analysis_root(video_id) / f"visual_analysis{suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return VisualAnalysisExportResult(
            video=report.video,
            analysis=analysis,
            format=format_name,
            content=content,
            path=str(target),
        )


def build_visual_analysis_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    inspection_repository: SQLiteVideoInspectionRepository,
    visual_repository: VisualAnalysisRepository,
    logger: logging.Logger | None = None,
) -> VisualAnalysisService:
    return VisualAnalysisService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        inspection_repository=inspection_repository,
        visual_repository=visual_repository,
        logger=logger,
    )
