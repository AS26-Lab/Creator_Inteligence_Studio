"""Dominio de analisis acustico local."""

from __future__ import annotations

from .entities import AcousticAnalysis, AcousticAnalysisStatus, AcousticEvent, AcousticTimelineWindow
from .errors import AcousticAnalysisError, AcousticAnalysisStateError, AcousticAnalysisValidationError
from .repositories import AcousticAnalysisRepository
from .services import (
    build_acoustic_configuration_fingerprint,
    build_acoustic_source_fingerprint,
    is_acoustic_analysis_stale,
    normalize_acoustic_analysis_config,
    validate_acoustic_analysis_options,
)
from .value_objects import (
    AcousticAnalysisOptions,
    AcousticActivityLabel,
    AcousticEventData,
    AcousticEventType,
    AcousticTimelineWindowData,
)

__all__ = [
    "AcousticAnalysis",
    "AcousticAnalysisStatus",
    "AcousticEvent",
    "AcousticTimelineWindow",
    "AcousticAnalysisError",
    "AcousticAnalysisStateError",
    "AcousticAnalysisValidationError",
    "AcousticAnalysisRepository",
    "build_acoustic_configuration_fingerprint",
    "build_acoustic_source_fingerprint",
    "is_acoustic_analysis_stale",
    "normalize_acoustic_analysis_config",
    "validate_acoustic_analysis_options",
    "AcousticAnalysisOptions",
    "AcousticActivityLabel",
    "AcousticEventData",
    "AcousticEventType",
    "AcousticTimelineWindowData",
]
