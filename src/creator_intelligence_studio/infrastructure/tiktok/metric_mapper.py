"""Mapeo de metricas TikTok."""

from __future__ import annotations

from uuid import uuid4

from creator_intelligence_studio.domain.tiktok_integration.entities import TikTokMetricImport, TikTokMetricValue
from creator_intelligence_studio.domain.tiktok_integration.metric_types import TikTokMetricScope, TikTokMetricSourceType, TikTokMetricStatus
from creator_intelligence_studio.domain.tiktok_integration.value_objects import build_tiktok_fingerprint
from creator_intelligence_studio.shared.dates import utc_now


def map_metric_import(
    *,
    creator_id: str,
    profile_id: str,
    sync_run_id: str,
    remote_video_id: str | None,
    metric_scope: TikTokMetricScope,
    source_type: TikTokMetricSourceType,
    observed_at=None,
    period_start: str | None = None,
    period_end: str | None = None,
    comparable_window: str | None = None,
    source_payload: dict[str, object],
    status: TikTokMetricStatus = TikTokMetricStatus.AVAILABLE,
) -> TikTokMetricImport:
    observed_at = observed_at or utc_now()
    return TikTokMetricImport(
        id=str(uuid4()),
        creator_id=creator_id,
        profile_id=profile_id,
        remote_video_id=remote_video_id,
        sync_run_id=sync_run_id,
        metric_scope=metric_scope,
        source_type=source_type,
        observed_at=observed_at,
        period_start=period_start,
        period_end=period_end,
        comparable_window=comparable_window,
        source_fingerprint=build_tiktok_fingerprint(source_payload),
        status=status,
        created_at=utc_now(),
    )


def map_metric_value(metric_import_id: str, metric_key: str, raw_metric_name: str, raw_value: dict[str, object]) -> TikTokMetricValue:
    numeric_value = raw_value.get("value")
    if isinstance(numeric_value, bool):
        numeric_value = None
    if isinstance(numeric_value, (int, float)):
        numeric = float(numeric_value)
    else:
        try:
            numeric = float(str(numeric_value)) if numeric_value is not None else None
        except (TypeError, ValueError):
            numeric = None
    return TikTokMetricValue(
        id=str(uuid4()),
        metric_import_id=metric_import_id,
        metric_key=metric_key,
        raw_metric_name=raw_metric_name,
        numeric_value=numeric,
        text_value=None if raw_value.get("text") is None else str(raw_value.get("text")),
        unit=None if raw_value.get("unit") is None else str(raw_value.get("unit")),
        dimensions_json="{}",
        quality_status=str(raw_value.get("quality_status") or "accepted"),
        warning_codes_json="[]",
        created_at=utc_now(),
    )

