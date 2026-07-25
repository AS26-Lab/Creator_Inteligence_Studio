"""Reglas de dominio para la integracion YouTube."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .connection_types import YouTubeRemoteContentType
from .metric_types import YOUTUBE_METRIC_MAP


READ_ONLY_SCOPES = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)


def build_youtube_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_write_scope(scope: str) -> bool:
    return any(
        forbidden in scope
        for forbidden in (
            "youtube.upload",
            "youtube.force-ssl",
            "youtube",
            "youtubepartner",
            "youtubepartner-channel-audit",
            "yt-analytics-monetary.readonly",
        )
    ) and scope not in READ_ONLY_SCOPES


def classify_remote_content_type(*, content_type_hint: str | None, duration_seconds: float | None, has_shorts_dimension: bool | None = None) -> tuple[YouTubeRemoteContentType, float, tuple[str, ...]]:
    warnings: list[str] = []
    if content_type_hint:
        normalized = content_type_hint.lower()
        mapping = {
            "shorts": YouTubeRemoteContentType.YOUTUBE_SHORT,
            "short": YouTubeRemoteContentType.YOUTUBE_SHORT,
            "video_on_demand": YouTubeRemoteContentType.YOUTUBE_LONGFORM,
            "live_stream": YouTubeRemoteContentType.LIVE,
            "live": YouTubeRemoteContentType.LIVE,
            "upcoming": YouTubeRemoteContentType.UPCOMING,
        }
        result = mapping.get(normalized, YouTubeRemoteContentType.UNKNOWN)
        confidence = 0.95 if result != YouTubeRemoteContentType.UNKNOWN else 0.35
        return result, confidence, tuple(warnings)
    if has_shorts_dimension is True:
        return YouTubeRemoteContentType.YOUTUBE_SHORT, 0.95, tuple(warnings)
    if duration_seconds is not None and duration_seconds <= 60:
        warnings.append("probable_short")
        return YouTubeRemoteContentType.PROBABLE_SHORT, 0.7, tuple(warnings)
    if duration_seconds is not None:
        return YouTubeRemoteContentType.YOUTUBE_LONGFORM, 0.7, tuple(warnings)
    warnings.append("unknown_content_type")
    return YouTubeRemoteContentType.UNKNOWN, 0.2, tuple(warnings)


def map_official_metric(metric_name: str) -> str | None:
    for spec in YOUTUBE_METRIC_MAP:
        if spec.raw_metric_name == metric_name or spec.internal_key == metric_name:
            return spec.internal_key
    return None

