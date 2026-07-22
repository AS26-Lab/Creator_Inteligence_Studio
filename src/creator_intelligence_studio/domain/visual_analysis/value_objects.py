"""Objetos de valor para analisis visual tecnico."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .errors import VisualAnalysisValidationError


class VisualAnalysisStatus(str, Enum):
    """Estados persistidos para analisis visual."""

    NOT_ANALYZED = "not_analyzed"
    QUEUED = "queued"
    PREPARING_VIDEO = "preparing_video"
    SAMPLING_FRAMES = "sampling_frames"
    DETECTING_CUTS = "detecting_cuts"
    GROUPING_SCENES = "grouping_scenes"
    GENERATING_KEYFRAMES = "generating_keyframes"
    CALCULATING_METRICS = "calculating_metrics"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FILE_MISSING = "file_missing"
    INSPECTION_MISSING = "inspection_missing"
    STALE = "stale"
    TOOL_UNAVAILABLE = "tool_unavailable"


class VisualActivityLabel(str, Enum):
    """Etiquetas tecnicas de actividad visual."""

    STATIC = "static"
    LOW_MOTION = "low_motion"
    MODERATE_MOTION = "moderate_motion"
    HIGH_MOTION = "high_motion"
    DARK = "dark"
    NORMAL_EXPOSURE = "normal_exposure"
    BRIGHT = "bright"
    POSSIBLE_BLACK_FRAME = "possible_black_frame"
    POSSIBLE_FREEZE = "possible_freeze"
    TRANSITION_CANDIDATE = "transition_candidate"
    UNKNOWN = "unknown"


class VisualEventType(str, Enum):
    """Tipos de eventos visuales candidatos."""

    HARD_CUT = "hard_cut"
    GRADUAL_TRANSITION = "gradual_transition"
    FLASH_CANDIDATE = "flash_candidate"
    BLACK_FRAME_CANDIDATE = "black_frame_candidate"
    FREEZE_CANDIDATE = "freeze_candidate"
    ABRUPT_MOTION_CHANGE = "abrupt_motion_change"
    ABRUPT_BRIGHTNESS_CHANGE = "abrupt_brightness_change"


@dataclass(frozen=True, slots=True)
class VisualAnalysisOptions:
    """Configuracion reproducible para analisis visual."""

    sample_fps: float = 2.0
    refine_sample_fps: float = 4.0
    refine_window_seconds: float = 1.0
    max_sample_frames: int = 1800
    target_sample_width: int = 256
    target_sample_height: int = 144
    cut_threshold: float = 0.38
    hard_cut_threshold: float = 0.58
    scene_min_duration_seconds: float = 0.5
    freeze_motion_threshold: float = 0.02
    black_brightness_threshold: float = 0.06
    dark_brightness_threshold: float = 0.18
    bright_brightness_threshold: float = 0.82
    cache_version: str = "v1"
    analyzer_version: str = "v1"
    keyframe_width: int = 640

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_fps": self.sample_fps,
            "refine_sample_fps": self.refine_sample_fps,
            "refine_window_seconds": self.refine_window_seconds,
            "max_sample_frames": self.max_sample_frames,
            "target_sample_width": self.target_sample_width,
            "target_sample_height": self.target_sample_height,
            "cut_threshold": self.cut_threshold,
            "hard_cut_threshold": self.hard_cut_threshold,
            "scene_min_duration_seconds": self.scene_min_duration_seconds,
            "freeze_motion_threshold": self.freeze_motion_threshold,
            "black_brightness_threshold": self.black_brightness_threshold,
            "dark_brightness_threshold": self.dark_brightness_threshold,
            "bright_brightness_threshold": self.bright_brightness_threshold,
            "cache_version": self.cache_version,
            "analyzer_version": self.analyzer_version,
            "keyframe_width": self.keyframe_width,
        }


def normalize_visual_analysis_config(options: VisualAnalysisOptions) -> VisualAnalysisOptions:
    if options.sample_fps < 1.0 or options.sample_fps > 4.0:
        raise VisualAnalysisValidationError("sample_fps debe estar entre 1 y 4.")
    if options.refine_sample_fps < options.sample_fps:
        raise VisualAnalysisValidationError("refine_sample_fps debe ser mayor o igual que sample_fps.")
    if options.refine_window_seconds <= 0:
        raise VisualAnalysisValidationError("refine_window_seconds debe ser mayor que cero.")
    if options.max_sample_frames <= 0:
        raise VisualAnalysisValidationError("max_sample_frames debe ser mayor que cero.")
    if options.target_sample_width <= 0 or options.target_sample_height <= 0:
        raise VisualAnalysisValidationError("target_sample_width y target_sample_height deben ser mayores que cero.")
    if not 0.0 < options.cut_threshold < 1.0:
        raise VisualAnalysisValidationError("cut_threshold debe estar entre 0 y 1.")
    if not 0.0 < options.hard_cut_threshold < 1.0:
        raise VisualAnalysisValidationError("hard_cut_threshold debe estar entre 0 y 1.")
    if options.hard_cut_threshold <= options.cut_threshold:
        raise VisualAnalysisValidationError("hard_cut_threshold debe ser mayor que cut_threshold.")
    if options.scene_min_duration_seconds <= 0:
        raise VisualAnalysisValidationError("scene_min_duration_seconds debe ser mayor que cero.")
    if options.freeze_motion_threshold < 0:
        raise VisualAnalysisValidationError("freeze_motion_threshold no puede ser negativo.")
    if not 0.0 < options.black_brightness_threshold < 1.0:
        raise VisualAnalysisValidationError("black_brightness_threshold debe estar entre 0 y 1.")
    if not 0.0 < options.dark_brightness_threshold < 1.0:
        raise VisualAnalysisValidationError("dark_brightness_threshold debe estar entre 0 y 1.")
    if not 0.0 < options.bright_brightness_threshold < 1.0:
        raise VisualAnalysisValidationError("bright_brightness_threshold debe estar entre 0 y 1.")
    if options.keyframe_width <= 0:
        raise VisualAnalysisValidationError("keyframe_width debe ser mayor que cero.")
    if not options.cache_version.strip():
        raise VisualAnalysisValidationError("cache_version no puede estar vacio.")
    if not options.analyzer_version.strip():
        raise VisualAnalysisValidationError("analyzer_version no puede estar vacio.")
    return replace(
        options,
        cache_version=options.cache_version.strip(),
        analyzer_version=options.analyzer_version.strip(),
    )


def validate_visual_analysis_options(options: VisualAnalysisOptions) -> None:
    normalize_visual_analysis_config(options)


@dataclass(frozen=True, slots=True)
class VisualTimelineWindowData:
    """Ventana temporal derivada de muestreo visual."""

    window_index: int
    start_seconds: float
    end_seconds: float
    sampled_frame_count: int
    brightness: float
    contrast: float
    saturation: float
    motion_score: float
    color_change_score: float
    is_static: bool
    is_black: bool
    is_possible_freeze: bool
    activity_label: VisualActivityLabel


@dataclass(frozen=True, slots=True)
class VisualSceneData:
    """Escena tecnica derivada de cortes."""

    scene_index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    representative_keyframe_path: str | None
    cut_in_score: float
    average_motion: float
    average_brightness: float
    average_contrast: float


@dataclass(frozen=True, slots=True)
class VisualEventData:
    """Evento visual candidato."""

    event_index: int
    start_seconds: float
    end_seconds: float
    event_type: VisualEventType
    confidence: float
    evidence: dict[str, object]
