"""Entidades de preparacion tecnica de audio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.shared.dates import to_iso_z


class PreparedAudioStatus(str, Enum):
    """Estado de un audio preparado."""

    NOT_PREPARED = "not_prepared"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"
    FILE_MISSING = "file_missing"
    NO_AUDIO_STREAM = "no_audio_stream"
    TOOL_UNAVAILABLE = "tool_unavailable"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class PreparedAudioAsset:
    """Registro persistido de un audio preparado."""

    id: str
    video_asset_id: str
    source_inspection_id: str | None
    status: PreparedAudioStatus
    relative_cache_path: str | None
    metadata_relative_path: str | None
    format_name: str | None
    codec_name: str | None
    sample_rate_hz: int | None
    channels: int | None
    channel_layout: str | None
    bit_depth: int | None
    duration_seconds: float | None
    file_size_bytes: int | None
    source_file_size_bytes: int | None
    source_file_modified_at: datetime | None
    selected_stream_index: int | None
    selected_stream_codec_name: str | None
    selected_stream_channels: int | None
    selected_stream_channel_layout: str | None
    selected_stream_sample_rate_hz: int | None
    selected_stream_language: str | None
    selected_stream_is_default: bool | None
    extraction_started_at: datetime | None
    extraction_completed_at: datetime | None
    ffmpeg_version: str | None
    cache_version: str
    normalization_sample_rate_hz: int
    normalization_channels: int
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
            "source_inspection_id": self.source_inspection_id,
            "status": self.status.value,
            "relative_cache_path": self.relative_cache_path,
            "metadata_relative_path": self.metadata_relative_path,
            "format_name": self.format_name,
            "codec_name": self.codec_name,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "channel_layout": self.channel_layout,
            "bit_depth": self.bit_depth,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "source_file_size_bytes": self.source_file_size_bytes,
            "source_file_modified_at": to_iso_z(self.source_file_modified_at),
            "selected_stream_index": self.selected_stream_index,
            "selected_stream_codec_name": self.selected_stream_codec_name,
            "selected_stream_channels": self.selected_stream_channels,
            "selected_stream_channel_layout": self.selected_stream_channel_layout,
            "selected_stream_sample_rate_hz": self.selected_stream_sample_rate_hz,
            "selected_stream_language": self.selected_stream_language,
            "selected_stream_is_default": self.selected_stream_is_default,
            "extraction_started_at": to_iso_z(self.extraction_started_at),
            "extraction_completed_at": to_iso_z(self.extraction_completed_at),
            "ffmpeg_version": self.ffmpeg_version,
            "cache_version": self.cache_version,
            "normalization_sample_rate_hz": self.normalization_sample_rate_hz,
            "normalization_channels": self.normalization_channels,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }
