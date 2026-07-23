"""Entidades persistidas de subtitulos locales."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import SubtitleCueValidationStatus, SubtitleExportFormat, SubtitleSourceType, SubtitleTrackStatus


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    id: str
    video_asset_id: str
    transcription_id: str
    ranked_clip_candidate_id: str | None
    render_job_id: str | None
    language: str
    name: str
    status: SubtitleTrackStatus
    source_type: SubtitleSourceType
    track_version: int
    configuration_fingerprint: str
    source_fingerprint: str
    source_start_seconds: float
    source_end_seconds: float
    cue_count: int
    total_text_length: int
    is_default: bool
    is_locked: bool
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "transcription_id": self.transcription_id,
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "render_job_id": self.render_job_id,
            "language": self.language,
            "name": self.name,
            "status": self.status.value,
            "source_type": self.source_type.value,
            "track_version": self.track_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "source_start_seconds": self.source_start_seconds,
            "source_end_seconds": self.source_end_seconds,
            "cue_count": self.cue_count,
            "total_text_length": self.total_text_length,
            "is_default": self.is_default,
            "is_locked": self.is_locked,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
            "completed_at": to_iso_z(self.completed_at),
        }


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    id: str
    subtitle_track_id: str
    cue_index: int
    start_seconds: float
    end_seconds: float
    text: str
    original_text: str
    source_segment_ids_json: str
    speaker_label: str | None
    line_count: int
    character_count: int
    characters_per_second: float
    words_per_minute: float
    validation_status: SubtitleCueValidationStatus
    warning_codes_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subtitle_track_id": self.subtitle_track_id,
            "cue_index": self.cue_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "original_text": self.original_text,
            "source_segment_ids_json": self.source_segment_ids_json,
            "speaker_label": self.speaker_label,
            "line_count": self.line_count,
            "character_count": self.character_count,
            "characters_per_second": self.characters_per_second,
            "words_per_minute": self.words_per_minute,
            "validation_status": self.validation_status.value,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class SubtitleEditEvent:
    id: str
    subtitle_track_id: str
    subtitle_cue_id: str | None
    event_index: int
    action: str
    previous_json: str
    new_json: str
    note: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subtitle_track_id": self.subtitle_track_id,
            "subtitle_cue_id": self.subtitle_cue_id,
            "event_index": self.event_index,
            "action": self.action,
            "previous_json": self.previous_json,
            "new_json": self.new_json,
            "note": self.note,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class SubtitleExport:
    id: str
    subtitle_track_id: str
    format: SubtitleExportFormat
    output_path: str
    fingerprint: str
    size_bytes: int | None
    status: str
    created_at: datetime
    verified_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subtitle_track_id": self.subtitle_track_id,
            "format": self.format.value,
            "output_path": self.output_path,
            "fingerprint": self.fingerprint,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
            "verified_at": to_iso_z(self.verified_at),
        }

