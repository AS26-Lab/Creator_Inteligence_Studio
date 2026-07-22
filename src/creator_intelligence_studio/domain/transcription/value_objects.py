"""Objetos de valor para transcripcion local."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TranscriptionExportFormat(str, Enum):
    """Formatos soportados para exportacion."""

    TXT = "txt"
    SRT = "srt"
    JSON = "json"


class TranscriptionModelStatus(str, Enum):
    """Estados posibles de la caché de un modelo."""

    NOT_INSTALLED = "not_installed"
    DOWNLOADING = "downloading"
    INSTALLED = "installed"
    INCOMPLETE = "incomplete"
    CORRUPT = "corrupt"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class TranscriptionOptions:
    """Opciones normalizadas para una transcripcion."""

    profile: str = "balanced"
    model_name: str = "small"
    device: str = "auto"
    compute_type: str | None = None
    language: str | None = None
    beam_size: int = 5
    vad_filter: bool = False
    word_timestamps: bool = False
    cache_version: str = "v1"
    model_cache_root: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter,
            "word_timestamps": self.word_timestamps,
            "cache_version": self.cache_version,
            "model_cache_root": self.model_cache_root,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionWordData:
    """Palabra con timestamps opcionales."""

    start_seconds: float
    end_seconds: float
    word: str
    probability: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "word": self.word,
            "probability": self.probability,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionSegmentData:
    """Segmento estructurado de la salida del motor."""

    segment_index: int
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None = None
    no_speech_probability: float | None = None
    temperature: float | None = None
    words: tuple[TranscriptionWordData, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_index": self.segment_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "confidence": self.confidence,
            "no_speech_probability": self.no_speech_probability,
            "temperature": self.temperature,
            "words": [word.to_dict() for word in self.words],
        }


@dataclass(frozen=True, slots=True)
class TranscriptionModelInfo:
    """Descripcion resumida de un modelo disponible."""

    model_name: str
    profile: str
    path: str | None
    installed: bool
    size_bytes: int | None = None
    notes: str | None = None
    status: TranscriptionModelStatus = TranscriptionModelStatus.NOT_INSTALLED
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "profile": self.profile,
            "path": self.path,
            "installed": self.installed,
            "size_bytes": self.size_bytes,
            "notes": self.notes,
            "status": self.status.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionBackendInfo:
    """Resultado de verificacion del backend."""

    available: bool
    device_count: int
    supported_compute_types: tuple[str, ...]
    cuda_runtime_available: bool
    cudnn_available: bool
    dll_directories: tuple[str, ...]
    backend: str
    fallback_reason: str | None = None
    errors: tuple[str, ...] = ()
    version: str | None = None
    ctranslate2_version: str | None = None
    faster_whisper_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "device_count": self.device_count,
            "supported_compute_types": list(self.supported_compute_types),
            "cuda_runtime_available": self.cuda_runtime_available,
            "cudnn_available": self.cudnn_available,
            "dll_directories": list(self.dll_directories),
            "backend": self.backend,
            "fallback_reason": self.fallback_reason,
            "errors": list(self.errors),
            "version": self.version,
            "ctranslate2_version": self.ctranslate2_version,
            "faster_whisper_version": self.faster_whisper_version,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionCancellationToken:
    """Token cooperativo de cancelacion."""

    is_cancelled: Callable[[], bool]

    def cancelled(self) -> bool:
        return bool(self.is_cancelled())


@dataclass(frozen=True, slots=True)
class TranscriptionProgress:
    """Estado de progreso aproximado."""

    phase: str
    progress_ratio: float | None = None
    current_segment_end_seconds: float | None = None
    total_duration_seconds: float | None = None
    approximate: bool = True
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "progress_ratio": self.progress_ratio,
            "current_segment_end_seconds": self.current_segment_end_seconds,
            "total_duration_seconds": self.total_duration_seconds,
            "approximate": self.approximate,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Resultado final normalizado de una transcripcion."""

    transcription_id: str | None
    video_asset_id: str
    prepared_audio_asset_id: str
    status: str
    engine: str
    model_name: str
    device: str
    compute_type: str
    requested_language: str | None
    detected_language: str | None
    language_probability: float | None
    full_text: str
    duration_seconds: float
    processing_time_seconds: float
    real_time_factor: float
    segment_count: int
    word_timestamps_enabled: bool
    vad_enabled: bool
    source_audio_size_bytes: int | None
    source_audio_modified_at: str | None
    source_audio_fingerprint: str
    configuration_fingerprint: str
    engine_version: str | None
    model_version: str | None
    warning_code: str | None = None
    warning_message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    segments: tuple[TranscriptionSegmentData, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcription_id": self.transcription_id,
            "video_asset_id": self.video_asset_id,
            "prepared_audio_asset_id": self.prepared_audio_asset_id,
            "status": self.status,
            "engine": self.engine,
            "model_name": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "requested_language": self.requested_language,
            "detected_language": self.detected_language,
            "language_probability": self.language_probability,
            "full_text": self.full_text,
            "duration_seconds": self.duration_seconds,
            "processing_time_seconds": self.processing_time_seconds,
            "real_time_factor": self.real_time_factor,
            "segment_count": self.segment_count,
            "word_timestamps_enabled": self.word_timestamps_enabled,
            "vad_enabled": self.vad_enabled,
            "source_audio_size_bytes": self.source_audio_size_bytes,
            "source_audio_modified_at": self.source_audio_modified_at,
            "source_audio_fingerprint": self.source_audio_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "engine_version": self.engine_version,
            "model_version": self.model_version,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "segments": [segment.to_dict() for segment in self.segments],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class TranscriptionVerificationResult:
    """Resultado resumido de verificacion del backend."""

    backend: TranscriptionBackendInfo
    model_statuses: tuple[TranscriptionModelInfo, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend.to_dict(),
            "model_statuses": [item.to_dict() for item in self.model_statuses],
            "notes": list(self.notes),
        }

