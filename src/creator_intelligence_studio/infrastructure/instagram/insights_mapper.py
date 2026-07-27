"""Mapeador de insights Instagram."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.instagram_integration.entities import InstagramInsightImport, InstagramInsightValue
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod, InstagramInsightScope
from creator_intelligence_studio.infrastructure.instagram.value_objects import build_instagram_fingerprint


def _safe_str(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: Any | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def map_insight_import(
    *,
    creator_id: str,
    account_id: str,
    sync_run_id: str,
    source_payload: dict[str, Any],
    insight_scope: InstagramInsightScope,
    metric_period: InstagramInsightPeriod | None,
    remote_media_id: str | None = None,
) -> InstagramInsightImport:
    now = datetime.now(timezone.utc)
    fingerprint = build_instagram_fingerprint(
        {
            "creator_id": creator_id,
            "account_id": account_id,
            "sync_run_id": sync_run_id,
            "source_payload": source_payload,
            "insight_scope": insight_scope.value,
            "metric_period": None if metric_period is None else metric_period.value,
            "remote_media_id": remote_media_id,
        }
    )
    return InstagramInsightImport(
        id=str(uuid4()),
        creator_id=creator_id,
        account_id=account_id,
        remote_media_id=remote_media_id,
        sync_run_id=sync_run_id,
        insight_scope=insight_scope,
        metric_period=metric_period,
        date_start=_safe_str(source_payload.get("date_start")),
        date_end=_safe_str(source_payload.get("date_end")),
        comparable_window=_safe_str(source_payload.get("comparable_window")),
        source_fingerprint=fingerprint,
        status=_safe_str(source_payload.get("status")) or "imported",
        created_at=now,
    )


def map_insight_value(
    *,
    insight_import_id: str,
    metric_key: str,
    raw_metric_name: str,
    raw_value: dict[str, Any],
) -> InstagramInsightValue:
    now = datetime.now(timezone.utc)
    return InstagramInsightValue(
        id=str(uuid4()),
        insight_import_id=insight_import_id,
        metric_key=metric_key,
        raw_metric_name=raw_metric_name,
        numeric_value=_safe_float(raw_value.get("numeric_value") or raw_value.get("value")),
        text_value=_safe_str(raw_value.get("text_value") or raw_value.get("text")),
        unit=_safe_str(raw_value.get("unit")),
        period=_safe_str(raw_value.get("period")),
        dimensions_json=_safe_str(raw_value.get("dimensions_json")) or "{}",
        breakdowns_json=_safe_str(raw_value.get("breakdowns_json")) or "{}",
        quality_status=_safe_str(raw_value.get("quality_status")) or "available",
        warning_codes_json=_safe_str(raw_value.get("warning_codes_json")) or "[]",
        created_at=now,
    )

