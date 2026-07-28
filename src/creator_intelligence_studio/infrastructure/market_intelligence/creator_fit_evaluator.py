"""Heuristicas de compatibilidad entre creador y mercado."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import normalize_text


def evaluate_creator_fit(*, creator_profile: dict[str, Any] | None, market_topics: Iterable[str], platform_scope: Iterable[str], evidence_strength: float, copying_risk: float) -> dict[str, float]:
    profile_text = " ".join(str(value) for value in (creator_profile or {}).values())
    topic_overlap = sum(1 for topic in market_topics if normalize_text(topic).lower() in profile_text.lower())
    platform_overlap = sum(1 for platform in platform_scope if normalize_text(platform).lower() in profile_text.lower())
    brand_fit = min(1.0, 0.2 * topic_overlap + 0.1 * platform_overlap + evidence_strength * 0.2)
    audience_fit = min(1.0, 0.15 * topic_overlap + evidence_strength * 0.25)
    historical_fit = min(1.0, 0.1 * topic_overlap)
    platform_fit = min(1.0, 0.2 * platform_overlap + 0.2)
    strategic_fit = min(1.0, (brand_fit + audience_fit + platform_fit) / 3)
    authenticity_fit = max(0.0, 1.0 - copying_risk * 0.8)
    capability_fit = min(1.0, evidence_strength)
    timing_fit = min(1.0, 0.5 + evidence_strength * 0.5)
    differentiation_potential = max(0.0, 1.0 - copying_risk)
    overall_fit = round((brand_fit + audience_fit + historical_fit + platform_fit + strategic_fit + authenticity_fit + capability_fit + timing_fit + differentiation_potential) / 9, 3)
    return {
        "brand_fit": round(brand_fit, 3),
        "audience_fit": round(audience_fit, 3),
        "historical_fit": round(historical_fit, 3),
        "platform_fit": round(platform_fit, 3),
        "strategic_fit": round(strategic_fit, 3),
        "authenticity_fit": round(authenticity_fit, 3),
        "capability_fit": round(capability_fit, 3),
        "timing_fit": round(timing_fit, 3),
        "differentiation_potential": round(differentiation_potential, 3),
        "overall_fit": overall_fit,
    }

