"""Contratos de benchmark funcional para transcripcion local."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.domain.components.entities import ComponentCatalogEntry, ComponentInstallationStatus, RuntimeCheckStatus
from creator_intelligence_studio.shared.dates import to_iso_z


class TranscriptionRuntimeBenchmarkStatus(str, Enum):
    """Estados de ejecucion del benchmark."""

    PENDING = "pending"
    CHECKING_RUNTIME = "checking_runtime"
    CHECKING_MODEL = "checking_model"
    LOADING_MODEL = "loading_model"
    PREPARING_FIXTURE = "preparing_fixture"
    RUNNING_INFERENCE = "running_inference"
    VALIDATING_RESULT = "validating_result"
    RELEASING_RESOURCES = "releasing_resources"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class TranscriptionRuntimeBenchmarkReadiness(str, Enum):
    """Estados de disponibilidad funcional derivados del benchmark."""

    READY = "ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    DEGRADED = "degraded"
    INCOMPATIBLE = "incompatible"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class TranscriptionRuntimeBenchmarkErrorCode(str, Enum):
    """Errores normalizados del benchmark."""

    RUNTIME_MISSING = "runtime_missing"
    RUNTIME_IMPORT_FAILED = "runtime_import_failed"
    MODEL_MISSING = "model_missing"
    MODEL_INVALID = "model_invalid"
    MODEL_LOAD_FAILED = "model_load_failed"
    GPU_NOT_DETECTED = "gpu_not_detected"
    GPU_RUNTIME_MISSING = "gpu_runtime_missing"
    GPU_INITIALIZATION_FAILED = "gpu_initialization_failed"
    INSUFFICIENT_VRAM = "insufficient_vram"
    INSUFFICIENT_RAM = "insufficient_ram"
    UNSUPPORTED_COMPUTE_TYPE = "unsupported_compute_type"
    INFERENCE_FAILED = "inference_failed"
    INFERENCE_EMPTY = "inference_empty"
    INFERENCE_TIMEOUT = "inference_timeout"
    CANCELLATION_REQUESTED = "cancellation_requested"
    RESOURCE_RELEASE_FAILED = "resource_release_failed"
    FIXTURE_INVALID = "fixture_invalid"
    UNEXPECTED_ERROR = "unexpected_error"


@dataclass(frozen=True, slots=True)
class TranscriptionRuntimeBenchmarkRequest:
    """Solicitud segura y determinista de benchmark."""

    requested_profile: str = "balanced"
    requested_device: str = "auto"
    model_component_id: str | None = None
    timeout_seconds: float = 30.0
    fixture_id: str = "synthetic_voice_v1"
    persist_result: bool = True
    force_refresh: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_profile": self.requested_profile,
            "requested_device": self.requested_device,
            "model_component_id": self.model_component_id,
            "timeout_seconds": self.timeout_seconds,
            "fixture_id": self.fixture_id,
            "persist_result": self.persist_result,
            "force_refresh": self.force_refresh,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionRuntimeBenchmarkResult:
    """Resultado funcional del benchmark local."""

    benchmark_id: str
    status: TranscriptionRuntimeBenchmarkStatus
    requested_device: str
    actual_device: str | None
    runtime_status: RuntimeCheckStatus
    model_status: ComponentInstallationStatus
    inference_status: str
    selected_model: ComponentCatalogEntry | None
    selected_compute_type: str | None
    started_at: datetime
    completed_at: datetime | None
    load_duration_ms: int | None
    inference_duration_ms: int | None
    total_duration_ms: int | None
    audio_duration_ms: int | None
    real_time_factor: float | None
    approximate_ram_before: int | None
    approximate_ram_peak: int | None
    approximate_ram_after: int | None
    approximate_vram_before: int | None
    approximate_vram_peak: int | None
    approximate_vram_after: int | None
    transcript_present: bool
    segment_count: int
    detected_language: str | None
    warnings: tuple[str, ...] = ()
    safe_error_category: str | None = None
    safe_error_message: str | None = None
    readiness: TranscriptionRuntimeBenchmarkReadiness = TranscriptionRuntimeBenchmarkReadiness.UNKNOWN
    evidence: tuple[str, ...] = ()
    benchmark_version: int = 1
    fixture_id: str | None = None
    requested_profile: str = "balanced"
    model_component_id: str | None = None
    compute_policy: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "status": self.status.value,
            "requested_profile": self.requested_profile,
            "requested_device": self.requested_device,
            "actual_device": self.actual_device,
            "runtime_status": self.runtime_status.value,
            "model_status": self.model_status.value,
            "inference_status": self.inference_status,
            "selected_model": self.selected_model.to_dict() if self.selected_model else None,
            "selected_compute_type": self.selected_compute_type,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "load_duration_ms": self.load_duration_ms,
            "inference_duration_ms": self.inference_duration_ms,
            "total_duration_ms": self.total_duration_ms,
            "audio_duration_ms": self.audio_duration_ms,
            "real_time_factor": self.real_time_factor,
            "approximate_ram_before": self.approximate_ram_before,
            "approximate_ram_peak": self.approximate_ram_peak,
            "approximate_ram_after": self.approximate_ram_after,
            "approximate_vram_before": self.approximate_vram_before,
            "approximate_vram_peak": self.approximate_vram_peak,
            "approximate_vram_after": self.approximate_vram_after,
            "transcript_present": self.transcript_present,
            "segment_count": self.segment_count,
            "detected_language": self.detected_language,
            "warnings": list(self.warnings),
            "safe_error_category": self.safe_error_category,
            "safe_error_message": self.safe_error_message,
            "readiness": self.readiness.value,
            "evidence": list(self.evidence),
            "benchmark_version": self.benchmark_version,
            "fixture_id": self.fixture_id,
            "model_component_id": self.model_component_id,
            "compute_policy": self.compute_policy,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionRuntimeBenchmarkPresentation:
    """Resumen user-friendly del benchmark."""

    title: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "message": self.message,
            "details": dict(self.details),
        }
