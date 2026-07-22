"""Entidades persistidas de analisis acustico."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import AcousticActivityLabel, AcousticAnalysisStatus, AcousticEventType


@dataclass(frozen=True, slots=True)
class AcousticAnalysis:
    """Registro persistido de un analisis acustico."""

    id: str
    video_asset_id: str
    prepared_audio_asset_id: str | None
    transcription_id: str | None
    status: AcousticAnalysisStatus
    analyzer_version: str
    configuration_fingerprint: str
    source_audio_fingerprint: str
    duration_seconds: float
    speech_duration_seconds: float
    silence_duration_seconds: float
    speech_ratio: float
    silence_ratio: float
    words_per_minute: float | None
    voiced_words_per_minute: float | None
    average_energy: float
    peak_energy: float
    dynamic_range: float
    pause_count: int
    average_pause_seconds: float | None
    longest_pause_seconds: float | None
    short_pause_count: int
    medium_pause_count: int
    long_pause_count: int
    low_activity_segment_count: int
    abrupt_change_count: int
    event_candidate_count: int
    started_at: datetime | None
    completed_at: datetime | None
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "prepared_audio_asset_id": self.prepared_audio_asset_id,
            "transcription_id": self.transcription_id,
            "status": self.status.value,
            "analyzer_version": self.analyzer_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_audio_fingerprint": self.source_audio_fingerprint,
            "duration_seconds": self.duration_seconds,
            "speech_duration_seconds": self.speech_duration_seconds,
            "silence_duration_seconds": self.silence_duration_seconds,
            "speech_ratio": self.speech_ratio,
            "silence_ratio": self.silence_ratio,
            "words_per_minute": self.words_per_minute,
            "voiced_words_per_minute": self.voiced_words_per_minute,
            "average_energy": self.average_energy,
            "peak_energy": self.peak_energy,
            "dynamic_range": self.dynamic_range,
            "pause_count": self.pause_count,
            "average_pause_seconds": self.average_pause_seconds,
            "longest_pause_seconds": self.longest_pause_seconds,
            "short_pause_count": self.short_pause_count,
            "medium_pause_count": self.medium_pause_count,
            "long_pause_count": self.long_pause_count,
            "low_activity_segment_count": self.low_activity_segment_count,
            "abrupt_change_count": self.abrupt_change_count,
            "event_candidate_count": self.event_candidate_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AcousticTimelineWindow:
    """Ventana agregada persistida."""

    id: str
    acoustic_analysis_id: str
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
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "acoustic_analysis_id": self.acoustic_analysis_id,
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
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AcousticEvent:
    """Evento candidato persistido."""

    id: str
    acoustic_analysis_id: str
    event_index: int
    start_seconds: float
    end_seconds: float
    event_type: AcousticEventType
    confidence: float
    evidence_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "acoustic_analysis_id": self.acoustic_analysis_id,
            "event_index": self.event_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "event_type": self.event_type.value,
            "confidence": self.confidence,
            "evidence_json": self.evidence_json,
            "created_at": to_iso_z(self.created_at),
        }
