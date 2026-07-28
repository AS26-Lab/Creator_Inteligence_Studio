"""Normalizacion de evidencia para inteligencia de mercado."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import normalize_text, normalize_url


def normalize_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["notes"] = normalize_text(normalized.get("notes")) or None
    normalized["source_url"] = normalize_url(normalized.get("source_url"))
    return normalized


def normalize_evidence_list(payloads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_evidence(payload) for payload in payloads]

