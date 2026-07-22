"""Objetos de valor para analisis acustico."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AcousticAnalysisStatus(str, Enum):
    """Estados de una analisis acustico."""

    NOT_ANALYZED = "not_analyzed"
    QUEUED = "queued"
    READING_AUDIO = "reading_audio"
    ANALYZING_FRAMES = "analyzing_frames"
    COMBINING_TRANSCRIPTION = "combining_transcription"
    DETECTING_PAUSES_EVENTS = "detecting_pauses_events"
    SAVING_RESULTS = "saving_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FILE_MISSING = "file_missing"
    AUDIO_NOT_PREPARED = "audio_not_prepared"
    AUDIO_STALE = "audio_stale"
    STALE = "stale"


class AcousticActivityLabel(str, Enum):
    """Etiquetas tecnicas de actividad acustica."""

    SILENCE = "silence"
    LOW_ACTIVITY = "low_activity"
    SPEECH_LOW = "speech_low"
    SPEECH_NORMAL = "speech_normal"
    SPEECH_HIGH = "speech_high"
    NON_SPEECH_ACTIVITY = "non_speech_activity"
    UNKNOWN = "unknown"


class AcousticEventType(str, Enum):
    """Tipos de eventos candidatos."""

    LAUGHTER_CANDIDATE = "laughter_candidate"
    TRANSIENT_PEAK = "transient_peak"
    SUSTAINED_NON_SPEECH = "sustained_non_speech"
    LONG_SILENCE = "long_silence"
    ABRUPT_ENERGY_CHANGE = "abrupt_energy_change"


@dataclass(frozen=True, slots=True)
class AcousticAnalysisOptions:
    """Configuracion reproducible del analisis acustico."""

    frame_duration_ms: int = 25
    frame_hop_ms: int = 10
    window_duration_seconds: float = 1.0
    rhythm_window_seconds: float = 5.0
    speech_energy_multiplier: float = 2.5
    silence_energy_multiplier: float = 1.2
    minimum_speech_seconds: float = 0.2
    pause_micro_max_seconds: float = 0.25
    pause_short_max_seconds: float = 0.75
    pause_medium_max_seconds: float = 2.0
    cache_version: str = "v1"
    analyzer_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_duration_ms": self.frame_duration_ms,
            "frame_hop_ms": self.frame_hop_ms,
            "window_duration_seconds": self.window_duration_seconds,
            "rhythm_window_seconds": self.rhythm_window_seconds,
            "speech_energy_multiplier": self.speech_energy_multiplier,
            "silence_energy_multiplier": self.silence_energy_multiplier,
            "minimum_speech_seconds": self.minimum_speech_seconds,
            "pause_micro_max_seconds": self.pause_micro_max_seconds,
            "pause_short_max_seconds": self.pause_short_max_seconds,
            "pause_medium_max_seconds": self.pause_medium_max_seconds,
            "cache_version": self.cache_version,
            "analyzer_version": self.analyzer_version,
        }


@dataclass(frozen=True, slots=True)
class AcousticTimelineWindowData:
    """Ventana tecnica agregada del analisis acustico."""

    window_index: int
    start_seconds: float
    end_seconds: float
    speech_probability: float
    is_speech: bool
    rms_energy: float
    peak_amplitude: float
    normalized_energy: float
    zero_crossing_rate: float
    speech_rate_estimate: float | None
    word_count: int
    pause_duration_seconds: float
    activity_label: AcousticActivityLabel

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "speech_probability": self.speech_probability,
            "is_speech": self.is_speech,
            "rms_energy": self.rms_energy,
            "peak_amplitude": self.peak_amplitude,
            "normalized_energy": self.normalized_energy,
            "zero_crossing_rate": self.zero_crossing_rate,
            "speech_rate_estimate": self.speech_rate_estimate,
            "word_count": self.word_count,
            "pause_duration_seconds": self.pause_duration_seconds,
            "activity_label": self.activity_label.value,
        }


@dataclass(frozen=True, slots=True)
class AcousticEventData:
    """Evento candidato detectado por heuristicas."""

    event_index: int
    start_seconds: float
    end_seconds: float
    event_type: AcousticEventType
    confidence: float
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_index": self.event_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "event_type": self.event_type.value,
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
        }
