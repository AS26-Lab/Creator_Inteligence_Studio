"""Construccion de oportunidades candidatas."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import current_utc_iso


def build_opportunity_candidate(*, creator_id: str, title: str, summary: str, opportunity_type: str, fit: dict[str, Any], evidence_quality: str, confidence_level: str, market_id: str | None = None, topic_id: str | None = None, trend_signal_id: str | None = None, pattern_id: str | None = None, platform_scope_json: str | None = None, content_type_scope_json: str | None = None, expires_at: str | None = None) -> dict[str, Any]:
    payload = {
        "id": f"candidate-{creator_id}-{trend_signal_id or pattern_id or title[:20]}".replace(" ", "-"),
        "creator_id": creator_id,
        "market_id": market_id,
        "topic_id": topic_id,
        "trend_signal_id": trend_signal_id,
        "pattern_id": pattern_id,
        "title": title,
        "summary": summary,
        "opportunity_type": opportunity_type,
        "platform_scope_json": platform_scope_json,
        "content_type_scope_json": content_type_scope_json,
        "lifecycle_stage": fit.get("lifecycle_stage", "unknown"),
        "urgency": fit.get("urgency", "medium"),
        "freshness_status": fit.get("freshness_status", "unknown"),
        "saturation_level": fit.get("saturation_level", "unknown"),
        "creator_fit": fit.get("overall_fit", 0.0),
        "audience_fit": fit.get("audience_fit", 0.0),
        "historical_fit": fit.get("historical_fit", 0.0),
        "differentiation_potential": fit.get("differentiation_potential", 0.0),
        "copying_risk": fit.get("copying_risk", 0.0),
        "evidence_quality": evidence_quality,
        "confidence_level": confidence_level,
        "status": "requires_review",
        "expires_at": expires_at,
        "created_at": current_utc_iso(),
        "updated_at": current_utc_iso(),
    }
    return payload

