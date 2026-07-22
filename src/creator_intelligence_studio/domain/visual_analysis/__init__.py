"""Dominio de analisis visual tecnico."""

from .entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow
from .errors import VisualAnalysisStateError, VisualAnalysisValidationError
from .repositories import VisualAnalysisRepository
from .services import (
    build_visual_configuration_fingerprint,
    build_visual_source_fingerprint,
    is_visual_analysis_stale,
    normalize_visual_analysis_config,
    validate_visual_analysis_options,
)
from .value_objects import (
    VisualActivityLabel,
    VisualAnalysisOptions,
    VisualAnalysisStatus,
    VisualEventData,
    VisualEventType,
    VisualSceneData,
    VisualTimelineWindowData,
)

__all__ = [
    "VisualActivityLabel",
    "VisualAnalysis",
    "VisualAnalysisOptions",
    "VisualAnalysisRepository",
    "VisualAnalysisStateError",
    "VisualAnalysisStatus",
    "VisualAnalysisValidationError",
    "VisualEvent",
    "VisualEventData",
    "VisualEventType",
    "VisualScene",
    "VisualSceneData",
    "VisualTimelineWindow",
    "VisualTimelineWindowData",
    "build_visual_configuration_fingerprint",
    "build_visual_source_fingerprint",
    "is_visual_analysis_stale",
    "normalize_visual_analysis_config",
    "validate_visual_analysis_options",
]
