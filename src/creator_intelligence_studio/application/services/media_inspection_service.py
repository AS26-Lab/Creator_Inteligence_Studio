"""Servicio de aplicacion para inspeccion tecnica de videos."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.errors import NotFoundError
from creator_intelligence_studio.domain.media.entities import (
    MediaToolInfo,
    VideoInspection,
    VideoInspectionStatus,
)
from creator_intelligence_studio.domain.media.errors import MediaInspectionError, MediaToolUnavailableError
from creator_intelligence_studio.domain.media.repositories import VideoInspectionRepository
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.media.ffmpeg_client import (
    FFmpegError,
    build_thumbnail_path,
    generate_initial_thumbnail,
)
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator, MediaTools
from creator_intelligence_studio.infrastructure.media.ffprobe_client import (
    FFprobeClient,
    FFprobeError,
    FFprobeTimeoutError,
)
from creator_intelligence_studio.infrastructure.media.parsers import parse_ffprobe_json
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


THUMBNAIL_CACHE_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class MediaToolsReport:
    """Resultado de deteccion de ffmpeg y ffprobe."""

    ffmpeg: MediaToolInfo
    ffprobe: MediaToolInfo
    warnings: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.ffmpeg.available and self.ffprobe.available

    def to_dict(self) -> dict[str, object]:
        return {
            "ffmpeg": self.ffmpeg.to_dict(),
            "ffprobe": self.ffprobe.to_dict(),
            "available": self.available,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """Huella liviana del archivo para detectar staleness."""

    exists: bool
    size_bytes: int | None
    modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class VideoInspectionReport:
    """Resultado de una inspeccion tecnica de video."""

    video: VideoAsset
    status: VideoInspectionStatus
    is_stale: bool
    file_available: bool
    inspection: VideoInspection | None
    thumbnail_path: str | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def summary(self):
        return self.inspection.to_summary() if self.inspection else None

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "status": self.status.value,
            "is_stale": self.is_stale,
            "file_available": self.file_available,
            "inspection": self.inspection.to_dict() if self.inspection else None,
            "summary": self.summary.to_dict() if self.summary else None,
            "thumbnail_path": self.thumbnail_path,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def _snapshot_file(video: VideoAsset) -> FileSnapshot:
    path = Path(video.source_path)
    if not path.exists() or not path.is_file():
        return FileSnapshot(exists=False, size_bytes=None, modified_at=None)
    stat = path.stat()
    return FileSnapshot(
        exists=True,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


def _inspection_is_stale(video: VideoAsset, inspection: VideoInspection | None, snapshot: FileSnapshot) -> bool:
    if inspection is None or not snapshot.exists:
        return False
    return (
        inspection.source_file_size_bytes != snapshot.size_bytes
        or inspection.source_file_modified_at != snapshot.modified_at
    )


def _inspection_status_from_snapshot(
    inspection: VideoInspection | None,
    *,
    snapshot: FileSnapshot,
    stale: bool,
) -> VideoInspectionStatus:
    if not snapshot.exists:
        return VideoInspectionStatus.FILE_MISSING
    if inspection is None:
        return VideoInspectionStatus.NOT_INSPECTED
    if stale:
        return VideoInspectionStatus.STALE
    return inspection.inspection_status


class MediaInspectionService:
    """Coordina inspeccion tecnica, herramientas y caché local."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        video_repository: VideoRepository,
        inspection_repository: VideoInspectionRepository,
        logger: logging.Logger | None = None,
        tool_locator: MediaToolLocator | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.video_repository = video_repository
        self.inspection_repository = inspection_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.media")
        self.tool_locator = tool_locator or MediaToolLocator()

    @property
    def cache_root(self) -> Path:
        return self.paths.project_root / "cache"

    def verify_media_tools(self) -> MediaToolsReport:
        tools = self.tool_locator.discover()
        warnings: list[str] = []
        if not tools.ffprobe.available:
            warnings.append(tools.ffprobe.error_message or "ffprobe no esta disponible.")
        if not tools.ffmpeg.available:
            warnings.append(tools.ffmpeg.error_message or "ffmpeg no esta disponible.")
        self.logger.info(
            "Media inspection using FFmpeg source=%s version=%s health=%s and FFprobe source=%s version=%s health=%s",
            tools.ffmpeg.source or tools.ffmpeg.installation_type or "unknown",
            tools.ffmpeg.version or "unknown",
            tools.ffmpeg.health_status or "unknown",
            tools.ffprobe.source or tools.ffprobe.installation_type or "unknown",
            tools.ffprobe.version or "unknown",
            tools.ffprobe.health_status or "unknown",
        )
        return MediaToolsReport(ffmpeg=tools.ffmpeg, ffprobe=tools.ffprobe, warnings=tuple(warnings))

    def _require_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return video

    def _load_existing(self, video_id: str) -> VideoInspection | None:
        return self.inspection_repository.get_by_video_asset_id(video_id)

    def _build_inspection_entity(
        self,
        *,
        video: VideoAsset,
        status: VideoInspectionStatus,
        snapshot: FileSnapshot,
        summary,
        tools: MediaToolsReport,
        metadata_json: str,
        thumbnail_relative_path: str | None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> VideoInspection:
        now = utc_now()
        frame_rate = summary.frame_rate
        average_frame_rate = summary.average_frame_rate
        return VideoInspection(
            id=str(uuid4()),
            video_asset_id=video.id,
            inspection_status=status,
            inspected_at=now,
            source_file_size_bytes=snapshot.size_bytes,
            source_file_modified_at=snapshot.modified_at,
            duration_seconds=summary.duration_seconds,
            format_name=summary.format_name,
            format_long_name=summary.format_long_name,
            overall_bitrate=summary.overall_bitrate,
            stream_count=summary.stream_count,
            video_stream_count=summary.video_stream_count,
            audio_stream_count=summary.audio_stream_count,
            subtitle_stream_count=summary.subtitle_stream_count,
            width=summary.width,
            height=summary.height,
            display_aspect_ratio=summary.display_aspect_ratio,
            pixel_aspect_ratio=summary.pixel_aspect_ratio,
            frame_rate_numerator=frame_rate.numerator,
            frame_rate_denominator=frame_rate.denominator,
            average_frame_rate_numerator=average_frame_rate.numerator,
            average_frame_rate_denominator=average_frame_rate.denominator,
            video_codec=summary.video_codec,
            video_codec_profile=summary.video_codec_profile,
            pixel_format=summary.pixel_format,
            video_bitrate=summary.video_bitrate,
            audio_codec=summary.audio_codec,
            audio_sample_rate=summary.audio_sample_rate,
            audio_channels=summary.audio_channels,
            audio_channel_layout=summary.audio_channel_layout,
            audio_bitrate=summary.audio_bitrate,
            rotation_degrees=summary.rotation_degrees,
            metadata_json=metadata_json,
            ffprobe_version=tools.ffprobe.version,
            ffprobe_path=tools.ffprobe.path,
            ffmpeg_version=tools.ffmpeg.version,
            ffmpeg_path=tools.ffmpeg.path,
            thumbnail_relative_path=thumbnail_relative_path,
            error_code=error_code,
            error_message=error_message,
            created_at=now,
            updated_at=now,
        )

    def _current_report(
        self,
        *,
        video: VideoAsset,
        inspection: VideoInspection | None,
        snapshot: FileSnapshot,
    ) -> VideoInspectionReport:
        stale = _inspection_is_stale(video, inspection, snapshot)
        status = _inspection_status_from_snapshot(inspection, snapshot=snapshot, stale=stale)
        thumbnail_path = None
        if inspection and inspection.thumbnail_relative_path:
            thumbnail_path = str(self.cache_root / inspection.thumbnail_relative_path)
        return VideoInspectionReport(
            video=video,
            status=status,
            is_stale=stale,
            file_available=snapshot.exists,
            inspection=inspection,
            thumbnail_path=thumbnail_path,
        )

    def get_video_inspection(self, video_id: str) -> VideoInspectionReport | None:
        video = self._require_video(video_id)
        inspection = self._load_existing(video_id)
        snapshot = _snapshot_file(video)
        if inspection is None:
            return None
        return self._current_report(video=video, inspection=inspection, snapshot=snapshot)

    def is_inspection_stale(self, video_id: str) -> bool:
        report = self.get_video_inspection(video_id)
        return bool(report and report.is_stale)

    def generate_initial_thumbnail(self, video_id: str, force: bool = False) -> str:
        video = self._require_video(video_id)
        inspection = self._load_existing(video_id)
        snapshot = _snapshot_file(video)
        if not snapshot.exists:
            raise MediaInspectionError("El archivo no esta disponible para generar miniatura.")
        if inspection and inspection.thumbnail_relative_path and not force and not _inspection_is_stale(video, inspection, snapshot):
            return str(self.cache_root / inspection.thumbnail_relative_path)
        tools = self.verify_media_tools()
        if not tools.available:
            raise MediaToolUnavailableError("No se puede generar la miniatura porque ffmpeg no esta disponible.")
        if inspection is None:
            raise MediaInspectionError("Primero inspecciona el video antes de generar la miniatura.")
        destination = build_thumbnail_path(self.cache_root, video.id, THUMBNAIL_CACHE_VERSION)
        result = generate_initial_thumbnail(
            ffmpeg_path=Path(tools.ffmpeg.path or ""),
            source_path=Path(video.source_path),
            destination_path=destination,
            duration_seconds=inspection.duration_seconds,
        )
        return str(result.path)

    def inspect_video(self, video_id: str, force: bool = False) -> VideoInspectionReport:
        video = self._require_video(video_id)
        snapshot = _snapshot_file(video)
        existing = self._load_existing(video_id)
        if existing and not force and not _inspection_is_stale(video, existing, snapshot):
            return self._current_report(video=video, inspection=existing, snapshot=snapshot)
        if not snapshot.exists:
            inspection = self._build_inspection_entity(
                video=video,
                status=VideoInspectionStatus.FILE_MISSING,
                snapshot=snapshot,
                summary=parse_ffprobe_json({"format": {}, "streams": []}),
                tools=self.verify_media_tools(),
                metadata_json="{}",
                thumbnail_relative_path=None,
                error_code="file_missing",
                error_message="El archivo original no existe o no esta disponible.",
            )
            inspection = self.inspection_repository.upsert(inspection)
            return self._current_report(video=video, inspection=inspection, snapshot=snapshot)

        tools = self.verify_media_tools()
        if not tools.ffprobe.available:
            inspection = self._build_inspection_entity(
                video=video,
                status=VideoInspectionStatus.TOOL_UNAVAILABLE,
                snapshot=snapshot,
                summary=parse_ffprobe_json({"format": {}, "streams": []}),
                tools=tools,
                metadata_json="{}",
                thumbnail_relative_path=None,
                error_code="tool_unavailable",
                error_message="ffmpeg o ffprobe no estan disponibles.",
            )
            inspection = self.inspection_repository.upsert(inspection)
            return self._current_report(video=video, inspection=inspection, snapshot=snapshot)

        try:
            ffprobe_client = FFprobeClient(Path(tools.ffprobe.path or ""), timeout_seconds=30.0)
            with self.tool_locator.acquire_lease("ffprobe"):
                probe_result = ffprobe_client.inspect(Path(video.source_path))
            summary = parse_ffprobe_json(probe_result.payload)
            inspection = self._build_inspection_entity(
                video=video,
                status=VideoInspectionStatus.COMPLETED,
                snapshot=snapshot,
                summary=summary,
                tools=tools,
                metadata_json=probe_result.raw_json,
                thumbnail_relative_path=None,
            )
            inspection = self.inspection_repository.upsert(inspection)
            thumbnail_warning = None
            if tools.ffmpeg.available:
                try:
                    destination = build_thumbnail_path(self.cache_root, video.id, THUMBNAIL_CACHE_VERSION)
                    with self.tool_locator.acquire_lease("ffmpeg"):
                        thumbnail_result = generate_initial_thumbnail(
                            ffmpeg_path=Path(tools.ffmpeg.path or ""),
                            source_path=Path(video.source_path),
                            destination_path=destination,
                            duration_seconds=summary.duration_seconds,
                        )
                    thumbnail_relative_path = str(thumbnail_result.path.relative_to(self.cache_root))
                    inspection = self._build_inspection_entity(
                        video=video,
                        status=VideoInspectionStatus.COMPLETED,
                        snapshot=snapshot,
                        summary=summary,
                        tools=tools,
                        metadata_json=probe_result.raw_json,
                        thumbnail_relative_path=thumbnail_relative_path,
                    )
                    inspection = self.inspection_repository.upsert(inspection)
                except FFmpegError as exc:
                    thumbnail_warning = str(exc)
                    self.logger.warning("No se pudo generar la miniatura tecnica: %s", exc)
            else:
                thumbnail_warning = "ffmpeg no esta disponible; no se genero miniatura."
            report = self._current_report(video=video, inspection=inspection, snapshot=snapshot)
            if thumbnail_warning:
                return VideoInspectionReport(
                    video=report.video,
                    status=report.status,
                    is_stale=report.is_stale,
                    file_available=report.file_available,
                    inspection=report.inspection,
                    thumbnail_path=report.thumbnail_path,
                    warnings=(*report.warnings, thumbnail_warning),
                    errors=report.errors,
                )
            return report
        except FFprobeTimeoutError as exc:
            self.logger.warning("ffprobe excedio el tiempo permitido para %s: %s", video.id, exc)
            inspection = self._build_inspection_entity(
                video=video,
                status=VideoInspectionStatus.FAILED,
                snapshot=snapshot,
                summary=parse_ffprobe_json({"format": {}, "streams": []}),
                tools=tools,
                metadata_json="{}",
                thumbnail_relative_path=None,
                error_code="timeout",
                error_message=str(exc),
            )
            inspection = self.inspection_repository.upsert(inspection)
            return self._current_report(video=video, inspection=inspection, snapshot=snapshot)
        except FFprobeError as exc:
            self.logger.warning("ffprobe devolvio un error para %s: %s", video.id, exc)
            inspection = self._build_inspection_entity(
                video=video,
                status=VideoInspectionStatus.FAILED,
                snapshot=snapshot,
                summary=parse_ffprobe_json({"format": {}, "streams": []}),
                tools=tools,
                metadata_json="{}",
                thumbnail_relative_path=None,
                error_code="ffprobe_error",
                error_message=str(exc),
            )
            inspection = self.inspection_repository.upsert(inspection)
            return self._current_report(video=video, inspection=inspection, snapshot=snapshot)


def build_media_inspection_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    video_repository: VideoRepository,
    inspection_repository: VideoInspectionRepository,
    logger: logging.Logger | None = None,
    tool_locator: MediaToolLocator | None = None,
) -> MediaInspectionService:
    """Construye el servicio de inspeccion tecnica."""

    return MediaInspectionService(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        inspection_repository=inspection_repository,
        logger=logger,
        tool_locator=tool_locator or MediaToolLocator(settings=settings, project_root=paths.project_root),
    )
