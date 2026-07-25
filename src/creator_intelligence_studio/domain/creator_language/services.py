"""Reglas puras de Creator Language Analysis."""

from __future__ import annotations

import hashlib
import json


def _normalize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    return value


def build_creator_language_fingerprint(payload: dict[str, object]) -> str:
    normalized = json.dumps(_normalize(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_narrative_profile_fingerprint(payload: dict[str, object]) -> str:
    return build_creator_language_fingerprint(payload)


def build_source_snapshot_payload(*, source_type: str, source_id: str, text_snapshot: str, language: str | None, platform: str | None, content_type: str | None, topic: str | None, start_seconds: float | None = None, end_seconds: float | None = None) -> dict[str, object]:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "text_snapshot": text_snapshot,
        "language": language,
        "platform": platform,
        "content_type": content_type,
        "topic": topic,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
    }
