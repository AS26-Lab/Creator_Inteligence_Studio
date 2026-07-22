"""Entidades de video."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.shared.dates import to_iso_z


class VideoSourceType(str, Enum):
    """Origen del video."""

    LOCAL_FILE = "local_file"
    PLATFORM_IMPORT = "platform_import"
    MANUAL_REFERENCE = "manual_reference"


class VideoProcessingStatus(str, Enum):
    """Estado de procesamiento del video."""

    REGISTERED = "registered"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class VideoAsset:
    """Representa un video registrado en un proyecto."""

    id: str
    project_id: str
    title: str
    source_path: str
    original_filename: str
    extension: str
    file_size_bytes: int
    file_modified_at: datetime | None
    source_type: VideoSourceType
    processing_status: VideoProcessingStatus
    registered_at: datetime
    updated_at: datetime
    notes: str | None
    file_available: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "source_path": self.source_path,
            "original_filename": self.original_filename,
            "extension": self.extension,
            "file_size_bytes": self.file_size_bytes,
            "file_modified_at": to_iso_z(self.file_modified_at),
            "source_type": self.source_type.value,
            "processing_status": self.processing_status.value,
            "registered_at": to_iso_z(self.registered_at),
            "updated_at": to_iso_z(self.updated_at),
            "notes": self.notes,
            "file_available": self.file_available,
        }

