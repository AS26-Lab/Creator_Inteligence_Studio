"""Entidades de transcripcion local."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import TranscriptionSegmentData


class TranscriptionStatus(str, Enum):
    """Estado de una transcripcion."""

    NOT_TRANSCRIBED = "not_transcribed"
    QUEUED = "queued"
    LOADING_MODEL = "loading_model"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FILE_MISSING = "file_missing"
    AUDIO_NOT_PREPARED = "audio_not_prepared"
    AUDIO_STALE = "audio_stale"
    MODEL_UNAVAILABLE = "model_unavailable"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class Transcription:
    """Registro persistido de una transcripcion."""

    id: str
    video_asset_id: str
    prepared_audio_asset_id: str
    status: TranscriptionStatus
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
    source_audio_modified_at: datetime | None
    source_audio_fingerprint: str
    configuration_fingerprint: str
    engine_version: str | None
    model_version: str | None
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "prepared_audio_asset_id": self.prepared_audio_asset_id,
            "status": self.status.value,
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
            "source_audio_modified_at": to_iso_z(self.source_audio_modified_at),
            "source_audio_fingerprint": self.source_audio_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "engine_version": self.engine_version,
            "model_version": self.model_version,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    """Segmento persistido de una transcripcion."""

    id: str
    transcription_id: str
    segment_index: int
    start_seconds: float
    end_seconds: float
    text: str
    confidence: float | None
    no_speech_probability: float | None
    temperature: float | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "transcription_id": self.transcription_id,
            "segment_index": self.segment_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "confidence": self.confidence,
            "no_speech_probability": self.no_speech_probability,
            "temperature": self.temperature,
            "created_at": to_iso_z(self.created_at),
        }

    def to_value_object(self) -> TranscriptionSegmentData:
        return TranscriptionSegmentData(
            segment_index=self.segment_index,
            start_seconds=self.start_seconds,
            end_seconds=self.end_seconds,
            text=self.text,
            confidence=self.confidence,
            no_speech_probability=self.no_speech_probability,
            temperature=self.temperature,
        )


