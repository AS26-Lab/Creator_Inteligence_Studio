"""Perfiles versionados de transcripcion local."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z


DEFAULT_TRANSCRIPTION_PROFILE_VERSION = 1


class TranscriptionProfileStatus(str, Enum):
    """Estado de curacion de un perfil."""

    VERIFIED = "verified"
    PROVISIONAL = "provisional"
    LEGACY = "legacy"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TranscriptionProfileDefinition:
    """Contrato versionado para seleccionar modelo y dispositivo."""

    profile_id: str
    display_name: str
    description: str
    model_component_id: str | None
    model_revision: str | None
    device_policy: str
    cpu_compute_type: str | None
    gpu_compute_type: str | None
    beam_size: int | None
    vad_policy: str
    language_detection: str
    word_timestamps: bool | None
    segment_timestamps: bool | None
    batching_policy: str
    minimum_ram_gb: float | None
    minimum_vram_gb: float | None
    recommended_vram_gb: float | None
    estimated_disk_bytes: int | None
    status: TranscriptionProfileStatus
    version: int
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "description": self.description,
            "model_component_id": self.model_component_id,
            "model_revision": self.model_revision,
            "device_policy": self.device_policy,
            "cpu_compute_type": self.cpu_compute_type,
            "gpu_compute_type": self.gpu_compute_type,
            "beam_size": self.beam_size,
            "vad_policy": self.vad_policy,
            "language_detection": self.language_detection,
            "word_timestamps": self.word_timestamps,
            "segment_timestamps": self.segment_timestamps,
            "batching_policy": self.batching_policy,
            "minimum_ram_gb": self.minimum_ram_gb,
            "minimum_vram_gb": self.minimum_vram_gb,
            "recommended_vram_gb": self.recommended_vram_gb,
            "estimated_disk_bytes": self.estimated_disk_bytes,
            "status": self.status.value,
            "version": self.version,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }
