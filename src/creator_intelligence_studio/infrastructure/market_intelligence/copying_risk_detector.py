"""Detector simple de riesgo de copia."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import normalize_text


def detect_copying_risk(*, external_content: dict[str, Any], creator_profile: dict[str, Any] | None) -> dict[str, float | str]:
    title = normalize_text(external_content.get("title")).lower()
    description = normalize_text(external_content.get("description")).lower()
    profile_text = " ".join(str(value) for value in (creator_profile or {}).values()).lower()
    overlap = sum(1 for token in set((title + " " + description).split()) if token and token in profile_text)
    risk = min(1.0, overlap / 10)
    return {"copying_risk": round(risk, 3), "reason": "token_overlap" if overlap else "insufficient_overlap"}

