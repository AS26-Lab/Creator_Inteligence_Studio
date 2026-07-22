"""Servicios de dominio para videos."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.domain.errors import ConflictError, ValidationError
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus
from creator_intelligence_studio.domain.videos.entities import (
    VideoAsset,
    VideoProcessingStatus,
    VideoSourceType,
)
from creator_intelligence_studio.shared.dates import utc_now

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def validate_title(title: str) -> str:
    """Valida el titulo del video."""

    value = title.strip()
    if not value:
        raise ValidationError("El titulo del video no puede quedar vacío.")
    return value


def validate_source_type(source_type: str | VideoSourceType) -> VideoSourceType:
    """Valida el tipo de origen del video."""

    if isinstance(source_type, VideoSourceType):
        return source_type
    try:
        return VideoSourceType(source_type)
    except ValueError as exc:
        raise ValidationError(
            "El tipo de origen no es válido. Use local_file, platform_import o manual_reference."
        ) from exc


def validate_processing_status(status: str | VideoProcessingStatus) -> VideoProcessingStatus:
    """Valida el estado de procesamiento."""

    if isinstance(status, VideoProcessingStatus):
        return status
    try:
        return VideoProcessingStatus(status)
    except ValueError as exc:
        raise ValidationError(
            "El estado de procesamiento no es válido."
        ) from exc


def normalize_source_path(path: str | Path) -> Path:
    """Normaliza una ruta absoluta para almacenar el video."""

    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = candidate.resolve(strict=False)
    return candidate.resolve(strict=False)


def validate_video_file_path(path: Path) -> Path:
    """Valida que la ruta apunte a un archivo de video existente."""

    if not path.exists():
        raise ValidationError(f"El archivo no existe: {path}")
    if path.is_dir():
        raise ValidationError(f"La ruta apunta a una carpeta, no a un archivo: {path}")
    if path.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(
            f"La extensión '{path.suffix}' no está permitida para videos."
        )
    return path


def build_video_asset(
    *,
    project_id: str,
    title: str,
    source_path: str | Path,
    source_type: str | VideoSourceType = VideoSourceType.LOCAL_FILE,
    notes: str | None = None,
    video_id: str | None = None,
    registered_at: datetime | None = None,
    updated_at: datetime | None = None,
    processing_status: str | VideoProcessingStatus = VideoProcessingStatus.REGISTERED,
    file_size_bytes: int | None = None,
    file_modified_at: datetime | None = None,
    file_available: bool | None = None,
) -> VideoAsset:
    """Construye un video validado para persistencia."""

    source_type_value = validate_source_type(source_type)
    processing_status_value = validate_processing_status(processing_status)
    normalized_path = normalize_source_path(source_path)
    stat = None
    if source_type_value == VideoSourceType.LOCAL_FILE:
        validate_video_file_path(normalized_path)
        stat = normalized_path.stat()
    elif normalized_path.exists() and not normalized_path.is_dir():
        stat = normalized_path.stat()
    return VideoAsset(
        id=video_id or str(uuid.uuid4()),
        project_id=project_id,
        title=validate_title(title),
        source_path=str(normalized_path),
        original_filename=normalized_path.name,
        extension=normalized_path.suffix.lower(),
        file_size_bytes=file_size_bytes if file_size_bytes is not None else (stat.st_size if stat else 0),
        file_modified_at=file_modified_at
        if file_modified_at is not None
        else (datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc) if stat else None),
        source_type=source_type_value,
        processing_status=processing_status_value,
        registered_at=registered_at or utc_now(),
        updated_at=updated_at or utc_now(),
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
        file_available=normalized_path.exists() and normalized_path.is_file(),
    )


def ensure_project_allows_videos(project: Project | None) -> Project:
    """Garantiza que el proyecto exista y acepte videos."""

    if project is None:
        raise ConflictError("El proyecto solicitado no existe.")
    if project.status == ProjectStatus.ARCHIVED:
        raise ConflictError("El proyecto está archivado y no acepta nuevos videos.")
    return project


def build_current_availability(video: VideoAsset) -> tuple[bool, int | None, datetime | None]:
    """Evalúa disponibilidad y metadatos actuales sin modificar la ruta."""

    path = Path(video.source_path)
    if not path.exists() or path.is_dir():
        return False, None, None
    stat = path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return True, stat.st_size, modified_at


def has_metadata_changed(video: VideoAsset) -> bool:
    """Indica si tamaño o fecha de modificación cambiaron respecto al registro."""

    available, size, modified_at = build_current_availability(video)
    if not available:
        return False
    return size != video.file_size_bytes or modified_at != video.file_modified_at
