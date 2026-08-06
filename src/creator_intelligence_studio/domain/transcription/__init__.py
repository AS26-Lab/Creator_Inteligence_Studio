"""Dominio de transcripcion local."""

from .entities import (
    Transcription,
    TranscriptionSegment,
    TranscriptionStatus,
)
from .errors import (
    TranscriptionBackendError,
    TranscriptionError,
    TranscriptionStateError,
    TranscriptionValidationError,
)
from .repositories import TranscriptionRepository
from .services import (
    DEFAULT_TRANSCRIPTION_MODELS,
    PROFILE_TO_MODEL,
    build_configuration_fingerprint,
    build_source_audio_fingerprint,
    is_transcription_stale,
    normalize_device,
    normalize_language,
    normalize_model_name,
    normalize_profile,
    normalize_requested_compute_type,
    validate_transcription_options,
)
from .value_objects import (
    TranscriptionBackendInfo,
    TranscriptionCancellationToken,
    TranscriptionExportFormat,
    TranscriptionModelInfo,
    TranscriptionModelStatus,
    TranscriptionOptions,
    TranscriptionProgress,
    TranscriptionResult,
    TranscriptionSegmentData,
    TranscriptionWordData,
    TranscriptionVerificationResult,
)
from .benchmark import (
    TranscriptionRuntimeBenchmarkErrorCode,
    TranscriptionRuntimeBenchmarkPresentation,
    TranscriptionRuntimeBenchmarkReadiness,
    TranscriptionRuntimeBenchmarkRequest,
    TranscriptionRuntimeBenchmarkResult,
    TranscriptionRuntimeBenchmarkStatus,
)
