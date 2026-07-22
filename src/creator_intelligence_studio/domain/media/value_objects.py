"""Objetos de valor para inspeccion tecnica de medios."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from typing import Any


@dataclass(frozen=True, slots=True)
class FractionValue:
    """Representa un valor fraccional con preservacion exacta."""

    numerator: int | None
    denominator: int | None

    @classmethod
    def from_fraction(cls, value: Fraction | None) -> "FractionValue":
        if value is None:
            return cls(None, None)
        return cls(value.numerator, value.denominator)

    @classmethod
    def from_text(cls, value: str | None) -> "FractionValue":
        if value is None:
            return cls(None, None)
        text = value.strip()
        if not text or text in {"0/0", "N/A"}:
            return cls(None, None)
        if "/" in text:
            numerator_text, denominator_text = text.split("/", 1)
            try:
                return cls(int(numerator_text), int(denominator_text))
            except ValueError:
                return cls(None, None)
        try:
            fraction = Fraction(text)
        except (ValueError, ZeroDivisionError):
            return cls(None, None)
        return cls.from_fraction(fraction)

    def to_fraction(self) -> Fraction | None:
        if self.numerator is None or self.denominator in {None, 0}:
            return None
        return Fraction(self.numerator, self.denominator)

    def to_float(self) -> float | None:
        fraction = self.to_fraction()
        if fraction is None:
            return None
        return float(fraction)

    def to_text(self) -> str | None:
        if self.numerator is None or self.denominator in {None, 0}:
            return None
        return f"{self.numerator}/{self.denominator}"


@dataclass(frozen=True, slots=True)
class MediaStreamInfo:
    """Resumen tipado de un stream de ffprobe."""

    index: int
    codec_type: str | None
    codec_name: str | None
    codec_long_name: str | None
    profile: str | None = None
    width: int | None = None
    height: int | None = None
    display_aspect_ratio: str | None = None
    pixel_aspect_ratio: str | None = None
    pixel_format: str | None = None
    bit_rate: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None
    frame_rate: FractionValue = field(default_factory=FractionValue)
    average_frame_rate: FractionValue = field(default_factory=FractionValue)
    rotation_degrees: int | None = None
    tags: dict[str, str] = field(default_factory=dict)
    disposition: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "codec_type": self.codec_type,
            "codec_name": self.codec_name,
            "codec_long_name": self.codec_long_name,
            "profile": self.profile,
            "width": self.width,
            "height": self.height,
            "display_aspect_ratio": self.display_aspect_ratio,
            "pixel_aspect_ratio": self.pixel_aspect_ratio,
            "pixel_format": self.pixel_format,
            "bit_rate": self.bit_rate,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "channel_layout": self.channel_layout,
            "frame_rate": self.frame_rate.to_text(),
            "average_frame_rate": self.average_frame_rate.to_text(),
            "rotation_degrees": self.rotation_degrees,
            "tags": dict(self.tags),
            "disposition": dict(self.disposition),
        }


@dataclass(frozen=True, slots=True)
class VideoTechnicalSummary:
    """Resumen tecnico extraido de ffprobe."""

    format_name: str | None
    format_long_name: str | None
    duration_seconds: float | None
    overall_bitrate: int | None
    stream_count: int
    video_stream_count: int
    audio_stream_count: int
    subtitle_stream_count: int
    width: int | None
    height: int | None
    display_aspect_ratio: str | None
    pixel_aspect_ratio: str | None
    frame_rate: FractionValue
    average_frame_rate: FractionValue
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_name": self.format_name,
            "format_long_name": self.format_long_name,
            "duration_seconds": self.duration_seconds,
            "overall_bitrate": self.overall_bitrate,
            "stream_count": self.stream_count,
            "video_stream_count": self.video_stream_count,
            "audio_stream_count": self.audio_stream_count,
            "subtitle_stream_count": self.subtitle_stream_count,
            "width": self.width,
            "height": self.height,
            "display_aspect_ratio": self.display_aspect_ratio,
            "pixel_aspect_ratio": self.pixel_aspect_ratio,
            "frame_rate": self.frame_rate.to_text(),
            "average_frame_rate": self.average_frame_rate.to_text(),
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
        }


@dataclass(frozen=True, slots=True)
class MediaToolInfo:
    """Informacion detectada para una herramienta externa."""

    name: str
    path: str | None
    version: str | None
    available: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "available": self.available,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class VideoInspection:
    """Inspeccion tecnica persistida de un video."""

    id: str
    video_asset_id: str
    inspection_status: str
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "inspection_status": self.inspection_status,
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
            "frame_rate": self.frame_rate.to_text(),
            "average_frame_rate": self.average_frame_rate.to_text(),
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

