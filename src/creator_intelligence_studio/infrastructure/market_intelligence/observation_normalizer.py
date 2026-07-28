"""Normalizacion de observaciones de mercado."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import normalize_text, normalize_url


def normalize_observation(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["observed_value_json"] = normalized.get("observed_value_json") or "{}"
    normalized["source_url"] = normalize_url(normalized.get("source_url"))
    normalized["notes"] = normalize_text(normalized.get("notes")) or None
    return normalized

