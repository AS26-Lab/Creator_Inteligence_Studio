"""Calculo simple de evoluciones temporales para Analytics Lab."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricSnapshot


@dataclass(frozen=True, slots=True)
class TrendPoint:
    snapshot_date: str
    captured_at: str
    value: float | None


def compute_trend_points(snapshots: list[AnalyticsMetricSnapshot]) -> dict[str, list[TrendPoint]]:
    grouped: dict[str, list[TrendPoint]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.metric_key].append(
            TrendPoint(
                snapshot_date=snapshot.snapshot_date,
                captured_at=snapshot.captured_at.isoformat(),
                value=snapshot.numeric_value,
            )
        )
    return {key: sorted(items, key=lambda item: (item.snapshot_date, item.captured_at)) for key, items in grouped.items()}

