"""Entidades de inspeccion tecnica de medios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.domain.media.value_objects import (
    FractionValue,
    MediaStreamInfo,
    MediaToolInfo,
    VideoTechnicalSummary,
)


class VideoInspectionStatus(str, Enum):
    """Estado de una inspeccion tecnica."""

    NOT_INSPECTED = "not_inspected"
    QUEUED = "queued"
    INSPECTING = "inspecting"
    COMPLETED = "completed"
    FAILED = "failed"
    FILE_MISSING = "file_missing"
    TOOL_UNAVAILABLE = "tool_unavailable"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class VideoInspection:
    """Registro persistido de inspeccion tecnica."""

    id: str
    video_asset_id: str
    inspection_status: VideoInspectionStatus
    inspected_at: datetime
    source_file_size_bytes: int | None
    source_file_modified_at: datetime | None
    duration_seconds: float | None
    format_name: str | None
    format_long_name: str | None
    overall_bitrate: int | None
    stream_count: int | None
    video_stream_count: int | None
    audio_stream_count: int | None
    subtitle_stream_count: int | None
    width: int | None
    height: int | None
    display_aspect_ratio: str | None
    pixel_aspect_ratio: str | None
    frame_rate_numerator: int | None
    frame_rate_denominator: int | None
    average_frame_rate_numerator: int | None
    average_frame_rate_denominator: int | None
    video_codec: str | None
    video_codec_profile: str | None
    pixel_format: str | None
    video_bitrate: int | None
    audio_codec: str | None
    audio_sample_rate: int | None
    audio_channels: int | None
    audio_channel_layout: str | None
    audio_bitrate: int | None
    rotation_degrees: int | None
    metadata_json: str
    ffprobe_version: str | None
    ffprobe_path: str | None
    ffmpeg_version: str | None
    ffmpeg_path: str | None
    thumbnail_relative_path: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def frame_rate(self) -> FractionValue:
        return FractionValue(self.frame_rate_numerator, self.frame_rate_denominator)

    @property
    def average_frame_rate(self) -> FractionValue:
        return FractionValue(
            self.average_frame_rate_numerator,
            self.average_frame_rate_denominator,
        )

    def to_summary(self) -> VideoTechnicalSummary:
        return VideoTechnicalSummary(
            format_name=self.format_name,
            format_long_name=self.format_long_name,
            duration_seconds=self.duration_seconds,
            overall_bitrate=self.overall_bitrate,
            stream_count=self.stream_count or 0,
            video_stream_count=self.video_stream_count or 0,
            audio_stream_count=self.audio_stream_count or 0,
            subtitle_stream_count=self.subtitle_stream_count or 0,
            width=self.width,
            height=self.height,
            display_aspect_ratio=self.display_aspect_ratio,
            pixel_aspect_ratio=self.pixel_aspect_ratio,
            frame_rate=self.frame_rate,
            average_frame_rate=self.average_frame_rate,
            video_codec=self.video_codec,
            video_codec_profile=self.video_codec_profile,
            pixel_format=self.pixel_format,
            video_bitrate=self.video_bitrate,
            audio_codec=self.audio_codec,
            audio_sample_rate=self.audio_sample_rate,
            audio_channels=self.audio_channels,
            audio_channel_layout=self.audio_channel_layout,
            audio_bitrate=self.audio_bitrate,
            rotation_degrees=self.rotation_degrees,
            metadata_json=self.metadata_json,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "inspection_status": self.inspection_status.value,
            "inspected_at": self.inspected_at.isoformat(),
            "source_file_size_bytes": self.source_file_size_bytes,
            "source_file_modified_at": self.source_file_modified_at.isoformat()
            if self.source_file_modified_at
            else None,
            "duration_seconds": self.duration_seconds,
            "format_name": self.format_name,
            "format_long_name": self.format_long_name,
            "overall_bitrate": self.overall_bitrate,
            "stream_count": self.stream_count,
            "video_stream_count": self.video_stream_count,
            "audio_stream_count": self.audio_stream_count,
            "subtitle_stream_count": self.subtitle_stream_count,
            "width": self.width,
            "height": self.height,
            "display_aspect_ratio": self.display_aspect_ratio,
            "pixel_aspect_ratio": self.pixel_aspect_ratio,
            "frame_rate_numerator": self.frame_rate_numerator,
            "frame_rate_denominator": self.frame_rate_denominator,
            "average_frame_rate_numerator": self.average_frame_rate_numerator,
            "average_frame_rate_denominator": self.average_frame_rate_denominator,
            "video_codec": self.video_codec,
            "video_codec_profile": self.video_codec_profile,
            "pixel_format": self.pixel_format,
            "video_bitrate": self.video_bitrate,
            "audio_codec": self.audio_codec,
            "audio_sample_rate": self.audio_sample_rate,
            "audio_channels": self.audio_channels,
            "audio_channel_layout": self.audio_channel_layout,
            "audio_bitrate": self.audio_bitrate,
            "rotation_degrees": self.rotation_degrees,
            "metadata_json": self.metadata_json,
            "ffprobe_version": self.ffprobe_version,
            "ffprobe_path": self.ffprobe_path,
            "ffmpeg_version": self.ffmpeg_version,
            "ffmpeg_path": self.ffmpeg_path,
            "thumbnail_relative_path": self.thumbnail_relative_path,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
