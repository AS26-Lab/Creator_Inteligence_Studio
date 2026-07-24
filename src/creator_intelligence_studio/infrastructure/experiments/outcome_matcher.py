"""Emparejamiento de outcomes y ventanas comparables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricSnapshot, AnalyticsPublication


@dataclass(frozen=True, slots=True)
class ComparableOutcome:
    publication_id: str
    metric_key: str
    observed_value: float | None
    comparable_window: str
    quality_status: str
    warnings: tuple[str, ...]


def _window_label(age_days: int | None) -> str:
    if age_days is None:
        return "latest"
    if age_days <= 2:
        return "day_1"
    if age_days <= 10:
        return "day_7"
    if age_days <= 45:
        return "day_30"
    return "custom_window"


def publication_age_days(publication: AnalyticsPublication, snapshot: AnalyticsMetricSnapshot | None) -> int | None:
    if snapshot is None:
        return None
    published_at = publication.published_at.astimezone(timezone.utc)
    captured_at = snapshot.captured_at.astimezone(timezone.utc)
    return max(0, (captured_at.date() - published_at.date()).days)


def select_comparable_snapshot(
    publication: AnalyticsPublication,
    snapshots: list[AnalyticsMetricSnapshot],
    metric_key: str,
) -> ComparableOutcome:
    metric_snapshots = [item for item in snapshots if item.metric_key == metric_key]
    if not metric_snapshots:
        return ComparableOutcome(publication.id, metric_key, None, "missing_snapshot", "missing", ("missing_primary_metric",))
    snapshot = sorted(metric_snapshots, key=lambda item: (item.captured_at, item.snapshot_date))[-1]
    age_days = publication_age_days(publication, snapshot)
    return ComparableOutcome(
        publication_id=publication.id,
        metric_key=metric_key,
        observed_value=snapshot.numeric_value,
        comparable_window=_window_label(age_days),
        quality_status=snapshot.quality_status.value,
        warnings=tuple(sorted(set(_json_warnings(snapshot.warning_codes_json)))),
    )


def _json_warnings(payload: str | None) -> list[str]:
    if not payload:
        return []
    try:
        import json

        value = json.loads(payload)
        if isinstance(value, list):
            return [str(item) for item in value]
    except Exception:
        return []
    return []

