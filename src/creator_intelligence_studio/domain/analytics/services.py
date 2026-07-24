"""Reglas y utilidades de analytics manual y aprendizaje."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from creator_intelligence_studio.domain.analytics.metric_definitions import AnalyticsMetricDefinitionSpec
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsContentType, PLATFORM_PRESETS


def normalize_key(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parsed = urlsplit(text)
    if not parsed.scheme:
        parsed = urlsplit(f"https://{text}")
    normalized_path = parsed.path.rstrip("/") or parsed.path
    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.query,
            "",
        )
    )
    return normalized


def normalize_platform_key(platform: str) -> str:
    return normalize_key(platform)


def normalize_content_type(value: str | None) -> AnalyticsContentType:
    key = normalize_key(value or "other")
    mapping = {
        "longform_video": AnalyticsContentType.LONGFORM_VIDEO,
        "long_form_video": AnalyticsContentType.LONGFORM_VIDEO,
        "longform": AnalyticsContentType.LONGFORM_VIDEO,
        "short_video": AnalyticsContentType.SHORT_VIDEO,
        "short": AnalyticsContentType.SHORT_VIDEO,
        "reel": AnalyticsContentType.REEL,
        "tiktok": AnalyticsContentType.TIKTOK,
        "live_replay": AnalyticsContentType.LIVE_REPLAY,
        "community_post": AnalyticsContentType.COMMUNITY_POST,
    }
    return mapping.get(key, AnalyticsContentType.OTHER)


def platform_defaults() -> tuple[dict[str, object], ...]:
    return tuple(preset.to_dict() for preset in PLATFORM_PRESETS)


def build_publication_dedupe_key(
    *,
    platform: str,
    external_publication_id: str | None,
    url: str | None,
    title: str,
    published_at: datetime | None,
    channel_id: str | None,
) -> str:
    payload = {
        "platform": normalize_platform_key(platform),
        "external_publication_id": normalize_text(external_publication_id),
        "url": normalize_url(url),
        "title": normalize_text(title),
        "published_at": published_at.isoformat() if published_at else None,
        "channel_id": channel_id,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_import_fingerprint(content: bytes, *, mapping_json: str, platform: str) -> str:
    digest = hashlib.sha256()
    digest.update(platform.encode("utf-8"))
    digest.update(b"\0")
    digest.update(mapping_json.encode("utf-8"))
    digest.update(b"\0")
    digest.update(content)
    return digest.hexdigest()


def build_row_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_metric_snapshot_dedupe_key(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def spec_aliases_map(specs: tuple[AnalyticsMetricDefinitionSpec, ...]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in specs:
        mapping[normalize_key(spec.metric_key)] = spec.metric_key
        mapping[normalize_key(spec.display_name)] = spec.metric_key
        for alias in spec.aliases:
            mapping[normalize_key(alias)] = spec.metric_key
    return mapping
