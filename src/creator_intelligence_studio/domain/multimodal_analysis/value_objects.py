"""Objetos de valor para analisis multimodal local."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .errors import MultimodalAnalysisValidationError


class MultimodalAnalysisStatus(str, Enum):
    """Estados persistidos para analisis multimodal."""

    NOT_ANALYZED = "not_analyzed"
    QUEUED = "queued"
    LOADING_SOURCES = "loading_sources"
    ALIGNING_TIMELINES = "aligning_timelines"
    NORMALIZING_SIGNALS = "normalizing_signals"
    DETECTING_CHANGES = "detecting_changes"
    GENERATING_CANDIDATES = "generating_candidates"
    FUSING_CANDIDATES = "fusing_candidates"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class MultimodalCandidateType(str, Enum):
    """Tipos tecnicos de candidatos multimodales."""

    HIGH_COMBINED_ACTIVITY = "high_combined_activity"
    ABRUPT_MULTIMODAL_CHANGE = "abrupt_multimodal_change"
    SPEECH_ENERGY_PEAK = "speech_energy_peak"
    VISUAL_TRANSITION_WITH_SPEECH = "visual_transition_with_speech"
    LONG_SILENCE_OR_PAUSE = "long_silence_or_pause"
    LOW_ACTIVITY_SEGMENT = "low_activity_segment"
    ACOUSTIC_EVENT_WITH_VISUAL_CHANGE = "acoustic_event_with_visual_change"
    SCENE_OPENING = "scene_opening"
    SCENE_CLOSING = "scene_closing"
    POSSIBLE_HOOK_CANDIDATE = "possible_hook_candidate"
    POSSIBLE_REACTION_CANDIDATE = "possible_reaction_candidate"
    UNKNOWN_CANDIDATE = "unknown_candidate"


@dataclass(frozen=True, slots=True)
class MultimodalAnalysisOptions:
    """Configuracion reproducible del analisis multimodal."""

    window_size_seconds: float = 1.0
    context_window_seconds: float = 5.0
    candidate_min_duration_seconds: float = 3.0
    candidate_max_duration_seconds: float = 30.0
    candidate_merge_gap_seconds: float = 1.0
    high_activity_threshold: float = 0.72
    transition_threshold: float = 0.65
    low_activity_threshold: float = 0.25
    candidate_confidence_threshold: float = 0.35
    hook_window_seconds: float = 30.0
    reaction_window_seconds: float = 8.0
    acoustic_energy_weight: float = 0.35
    speech_rate_weight: float = 0.20
    visual_motion_weight: float = 0.20
    cut_weight: float = 0.15
    event_weight: float = 0.10
    cache_version: str = "v1"
    analyzer_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_size_seconds": self.window_size_seconds,
            "context_window_seconds": self.context_window_seconds,
            "candidate_min_duration_seconds": self.candidate_min_duration_seconds,
            "candidate_max_duration_seconds": self.candidate_max_duration_seconds,
            "candidate_merge_gap_seconds": self.candidate_merge_gap_seconds,
            "high_activity_threshold": self.high_activity_threshold,
            "transition_threshold": self.transition_threshold,
            "low_activity_threshold": self.low_activity_threshold,
            "candidate_confidence_threshold": self.candidate_confidence_threshold,
            "hook_window_seconds": self.hook_window_seconds,
            "reaction_window_seconds": self.reaction_window_seconds,
            "acoustic_energy_weight": self.acoustic_energy_weight,
            "speech_rate_weight": self.speech_rate_weight,
            "visual_motion_weight": self.visual_motion_weight,
            "cut_weight": self.cut_weight,
            "event_weight": self.event_weight,
            "cache_version": self.cache_version,
            "analyzer_version": self.analyzer_version,
        }


def normalize_multimodal_analysis_config(options: MultimodalAnalysisOptions) -> MultimodalAnalysisOptions:
    if options.window_size_seconds <= 0:
        raise MultimodalAnalysisValidationError("window_size_seconds debe ser mayor que cero.")
    if options.context_window_seconds <= 0:
        raise MultimodalAnalysisValidationError("context_window_seconds debe ser mayor que cero.")
    if options.candidate_min_duration_seconds <= 0:
        raise MultimodalAnalysisValidationError("candidate_min_duration_seconds debe ser mayor que cero.")
    if options.candidate_max_duration_seconds < options.candidate_min_duration_seconds:
        raise MultimodalAnalysisValidationError("candidate_max_duration_seconds debe ser mayor o igual que candidate_min_duration_seconds.")
    if options.candidate_merge_gap_seconds < 0:
        raise MultimodalAnalysisValidationError("candidate_merge_gap_seconds no puede ser negativo.")
    for name, value in (
        ("high_activity_threshold", options.high_activity_threshold),
        ("transition_threshold", options.transition_threshold),
        ("low_activity_threshold", options.low_activity_threshold),
        ("candidate_confidence_threshold", options.candidate_confidence_threshold),
    ):
        if not 0.0 <= value <= 1.0:
            raise MultimodalAnalysisValidationError(f"{name} debe estar entre 0 y 1.")
    if options.acoustic_energy_weight < 0 or options.speech_rate_weight < 0 or options.visual_motion_weight < 0 or options.cut_weight < 0 or options.event_weight < 0:
        raise MultimodalAnalysisValidationError("Los pesos no pueden ser negativos.")
    total = (
        options.acoustic_energy_weight
        + options.speech_rate_weight
        + options.visual_motion_weight
        + options.cut_weight
        + options.event_weight
    )
    if total <= 0:
        raise MultimodalAnalysisValidationError("La suma de los pesos debe ser mayor que cero.")
    if not options.cache_version.strip():
        raise MultimodalAnalysisValidationError("cache_version no puede estar vacio.")
    if not options.analyzer_version.strip():
        raise MultimodalAnalysisValidationError("analyzer_version no puede estar vacio.")
    return options


def validate_multimodal_analysis_options(options: MultimodalAnalysisOptions) -> None:
    normalize_multimodal_analysis_config(options)


@dataclass(frozen=True, slots=True)
class MultimodalTimelineWindowData:
    """Ventana temporal multimodal sincronizada."""

    window_index: int
    start_seconds: float
    end_seconds: float
    transcript_text: str
    word_count: int
    speech_ratio: float
    silence_ratio: float
    speech_rate: float | None
    acoustic_energy: float
    acoustic_change: float
    visual_motion: float
    visual_change: float
    brightness: float
    cut_count: int
    scene_index: int | None
    acoustic_event_count: int
    visual_event_count: int
    combined_activity_score: float
    transition_score: float
    novelty_score: float
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "transcript_text": self.transcript_text,
            "word_count": self.word_count,
            "speech_ratio": self.speech_ratio,
            "silence_ratio": self.silence_ratio,
            "speech_rate": self.speech_rate,
            "acoustic_energy": self.acoustic_energy,
            "acoustic_change": self.acoustic_change,
            "visual_motion": self.visual_motion,
            "visual_change": self.visual_change,
            "brightness": self.brightness,
            "cut_count": self.cut_count,
            "scene_index": self.scene_index,
            "acoustic_event_count": self.acoustic_event_count,
            "visual_event_count": self.visual_event_count,
            "combined_activity_score": self.combined_activity_score,
            "transition_score": self.transition_score,
            "novelty_score": self.novelty_score,
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class MultimodalMomentCandidateData:
    """Candidato tecnico de momento multimodal."""

    candidate_index: int
    start_seconds: float
    end_seconds: float
    candidate_type: MultimodalCandidateType
    score: float
    confidence: float
    title: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    source_window_start: float | None = None
    source_window_end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_index": self.candidate_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "candidate_type": self.candidate_type.value,
            "score": self.score,
            "confidence": self.confidence,
            "title": self.title,
            "summary": self.summary,
            "evidence": dict(self.evidence),
            "source_window_start": self.source_window_start,
            "source_window_end": self.source_window_end,
        }

