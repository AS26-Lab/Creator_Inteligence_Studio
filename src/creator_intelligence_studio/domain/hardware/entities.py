"""Entidades del inventario de hardware local."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z


class HardwareCapabilityState(str, Enum):
    """Estados de inventario y lectura de hardware."""

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    UNKNOWN = "unknown"
    REPORTED_NOT_TESTED = "reported_not_tested"
    DEGRADED = "degraded"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True)
class GpuSummary:
    """Resumen no identitario de GPU local."""

    vendor: str | None
    name: str | None
    driver_version: str | None
    vram_total_bytes: int | None
    cuda_visible: bool
    cuda_runtime_reported: str | None = None
    ctranslate2_cuda_available: bool | None = None
    status: HardwareCapabilityState = HardwareCapabilityState.UNKNOWN
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "name": self.name,
            "driver_version": self.driver_version,
            "vram_total_bytes": self.vram_total_bytes,
            "cuda_visible": self.cuda_visible,
            "cuda_runtime_reported": self.cuda_runtime_reported,
            "ctranslate2_cuda_available": self.ctranslate2_cuda_available,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class DiskVolumeSummary:
    """Resumen de un volumen relevante."""

    path: str
    free_bytes: int | None
    total_bytes: int | None
    status: HardwareCapabilityState = HardwareCapabilityState.UNKNOWN
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "free_bytes": self.free_bytes,
            "total_bytes": self.total_bytes,
            "status": self.status.value,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class HardwareProfile:
    """Inventario tecnico persistido del sistema local."""

    generated_at: datetime
    platform: str
    architecture: str
    cpu_logical_count: int | None
    cpu_summary: str | None
    ram_total_bytes: int | None
    ram_available_bytes: int | None
    gpu: GpuSummary
    driver_summary: str | None
    cuda_reported: str | None
    ctranslate2_cuda_status: HardwareCapabilityState
    disk_volumes: tuple[DiskVolumeSummary, ...] = ()
    detection_source: str = "local"
    status: HardwareCapabilityState = HardwareCapabilityState.UNKNOWN
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": to_iso_z(self.generated_at),
            "platform": self.platform,
            "architecture": self.architecture,
            "cpu_logical_count": self.cpu_logical_count,
            "cpu_summary": self.cpu_summary,
            "ram_total_bytes": self.ram_total_bytes,
            "ram_available_bytes": self.ram_available_bytes,
            "gpu": self.gpu.to_dict(),
            "driver_summary": self.driver_summary,
            "cuda_reported": self.cuda_reported,
            "ctranslate2_cuda_status": self.ctranslate2_cuda_status.value,
            "disk_volumes": [volume.to_dict() for volume in self.disk_volumes],
            "detection_source": self.detection_source,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }
