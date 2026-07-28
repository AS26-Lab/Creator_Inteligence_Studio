"""Construccion de reportes de mercado."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import current_utc_iso, build_market_fingerprint


def build_report(*, creator_id: str, report_type: str, market_id: str | None, period_start: str | None, period_end: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    fingerprint = build_market_fingerprint(creator_id, report_type, market_id, period_start, period_end, payload)
    return {
        "id": f"report-{fingerprint[:16]}",
        "creator_id": creator_id,
        "market_id": market_id,
        "report_type": report_type,
        "period_start": period_start,
        "period_end": period_end,
        "source_fingerprint": fingerprint,
        "report_json": payload,
        "created_at": current_utc_iso(),
    }

