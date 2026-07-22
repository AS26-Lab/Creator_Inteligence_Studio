"""Parsers tipados para la salida de ffprobe."""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

from creator_intelligence_studio.domain.media.entities import MediaStreamInfo, VideoTechnicalSummary
from creator_intelligence_studio.domain.media.value_objects import FractionValue


def _as_int(value: Any) -> int | None:
    if value in {None, "", "N/A"}:
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value in {None, "", "N/A"}:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _as_fraction(value: Any) -> FractionValue:
    if value in {None, "", "N/A"}:
        return FractionValue(None, None)
    text = str(value)
    try:
        fraction = Fraction(text)
    except (ValueError, ZeroDivisionError):
        return FractionValue(None, None)
    return FractionValue.from_fraction(fraction)


def _tags(payload: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        result[str(key)] = str(value)
    return result


def _disposition(payload: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in payload.items():
        parsed = _as_int(value)
        if parsed is not None:
            result[str(key)] = parsed
    return result


def _rotation_from_stream(stream: dict[str, Any]) -> int | None:
    tags = stream.get("tags")
    if isinstance(tags, dict):
        rotate = tags.get("rotate")
        parsed = _as_int(rotate)
        if parsed is not None:
            return parsed
    side_data_list = stream.get("side_data_list")
    if isinstance(side_data_list, list):
        for item in side_data_list:
            if not isinstance(item, dict):
                continue
            rotation = _as_int(item.get("rotation"))
            if rotation is not None:
                return rotation
    return None


def _select_streams(streams: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    subtitle_stream = next((stream for stream in streams if stream.get("codec_type") == "subtitle"), None)
    return video_stream, audio_stream, subtitle_stream


def parse_ffprobe_json(payload: dict[str, Any] | str) -> VideoTechnicalSummary:
    """Convierte el JSON de ffprobe a un resumen tipado."""

    if isinstance(payload, str):
        payload = json.loads(payload)
    format_payload = payload.get("format") if isinstance(payload, dict) else None
    streams_payload = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(streams_payload, list):
        streams_payload = []
    streams: list[dict[str, Any]] = [stream for stream in streams_payload if isinstance(stream, dict)]
    video_stream, audio_stream, subtitle_stream = _select_streams(streams)

    width = _as_int(video_stream.get("width")) if video_stream else None
    height = _as_int(video_stream.get("height")) if video_stream else None
    frame_rate = _as_fraction(video_stream.get("r_frame_rate")) if video_stream else FractionValue(None, None)
    average_frame_rate = _as_fraction(video_stream.get("avg_frame_rate")) if video_stream else FractionValue(None, None)

    format_name = format_payload.get("format_name") if isinstance(format_payload, dict) else None
    format_long_name = format_payload.get("format_long_name") if isinstance(format_payload, dict) else None

    return VideoTechnicalSummary(
        format_name=str(format_name) if format_name is not None else None,
        format_long_name=str(format_long_name) if format_long_name is not None else None,
        duration_seconds=_as_float(format_payload.get("duration")) if isinstance(format_payload, dict) else None,
        overall_bitrate=_as_int(format_payload.get("bit_rate")) if isinstance(format_payload, dict) else None,
        stream_count=len(streams),
        video_stream_count=sum(1 for stream in streams if stream.get("codec_type") == "video"),
        audio_stream_count=sum(1 for stream in streams if stream.get("codec_type") == "audio"),
        subtitle_stream_count=sum(1 for stream in streams if stream.get("codec_type") == "subtitle"),
        width=width,
        height=height,
        display_aspect_ratio=video_stream.get("display_aspect_ratio") if video_stream else None,
        pixel_aspect_ratio=video_stream.get("sample_aspect_ratio") if video_stream else None,
        frame_rate=frame_rate,
        average_frame_rate=average_frame_rate,
        video_codec=video_stream.get("codec_name") if video_stream else None,
        video_codec_profile=video_stream.get("profile") if video_stream else None,
        pixel_format=video_stream.get("pix_fmt") if video_stream else None,
        video_bitrate=_as_int(video_stream.get("bit_rate")) if video_stream else None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        audio_sample_rate=_as_int(audio_stream.get("sample_rate")) if audio_stream else None,
        audio_channels=_as_int(audio_stream.get("channels")) if audio_stream else None,
        audio_channel_layout=audio_stream.get("channel_layout") if audio_stream else None,
        audio_bitrate=_as_int(audio_stream.get("bit_rate")) if audio_stream else None,
        rotation_degrees=_rotation_from_stream(video_stream) if video_stream else None,
        metadata_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )


def parse_ffprobe_streams(payload: dict[str, Any] | str) -> list[MediaStreamInfo]:
    """Convierte los streams de ffprobe a DTOs tipados."""

    if isinstance(payload, str):
        payload = json.loads(payload)
    raw_streams = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(raw_streams, list):
        return []
    result: list[MediaStreamInfo] = []
    for index, stream in enumerate(raw_streams):
        if not isinstance(stream, dict):
            continue
        result.append(
            MediaStreamInfo(
                index=_as_int(stream.get("index")) if stream.get("index") is not None else index,
                codec_type=stream.get("codec_type"),
                codec_name=stream.get("codec_name"),
                codec_long_name=stream.get("codec_long_name"),
                profile=stream.get("profile"),
                width=_as_int(stream.get("width")),
                height=_as_int(stream.get("height")),
                display_aspect_ratio=stream.get("display_aspect_ratio"),
                pixel_aspect_ratio=stream.get("sample_aspect_ratio"),
                pixel_format=stream.get("pix_fmt"),
                bit_rate=_as_int(stream.get("bit_rate")),
                sample_rate=_as_int(stream.get("sample_rate")),
                channels=_as_int(stream.get("channels")),
                channel_layout=stream.get("channel_layout"),
                frame_rate=_as_fraction(stream.get("r_frame_rate")),
                average_frame_rate=_as_fraction(stream.get("avg_frame_rate")),
                rotation_degrees=_rotation_from_stream(stream),
                tags=_tags(stream.get("tags") if isinstance(stream.get("tags"), dict) else None),
                disposition=_disposition(
                    stream.get("disposition") if isinstance(stream.get("disposition"), dict) else None
                ),
            )
        )
    return result

