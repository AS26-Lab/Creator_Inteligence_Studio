"""Mapeos de metricas oficiales de YouTube."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from creator_intelligence_studio.domain.youtube_integration.entities import YouTubeMetricImport, YouTubeMetricValue
from creator_intelligence_studio.domain.youtube_integration.metric_types import YOUTUBE_METRIC_MAP, YouTubeMetricAvailability
from creator_intelligence_studio.domain.youtube_integration.services import build_youtube_fingerprint


def map_metric_values(
    *,
    metric_import_id: str,
    raw_metric_name: str,
    rows: list[dict[str, object]],
    dimensions: dict[str, object] | None = None,
) -> tuple[YouTubeMetricValue, ...]:
    spec = next((item for item in YOUTUBE_METRIC_MAP if item.raw_metric_name == raw_metric_name or item.internal_key == raw_metric_name), None)
    if spec is None:
        spec = next((item for item in YOUTUBE_METRIC_MAP if item.internal_key == raw_metric_name), None)
    metric_key = spec.internal_key if spec else raw_metric_name
    unit = spec.unit if spec else "count"
    values: list[YouTubeMetricValue] = []
    for index, row in enumerate(rows, start=1):
        numeric_value = row.get("numeric_value")
        text_value = row.get("text_value")
        if isinstance(numeric_value, bool):
            numeric_value = None
        if numeric_value is not None and not isinstance(numeric_value, (int, float)):
            try:
                numeric_value = float(numeric_value)
            except (TypeError, ValueError):
                numeric_value = None
        if text_value is not None and not isinstance(text_value, str):
            text_value = str(text_value)
        values.append(
            YouTubeMetricValue(
                id=build_youtube_fingerprint({
                    "metric_import_id": metric_import_id,
                    "metric_key": metric_key,
                    "index": index,
                    "dimensions": dimensions or {},
                    "row": row,
                }),
                metric_import_id=metric_import_id,
                metric_key=metric_key,
                raw_metric_name=raw_metric_name,
                numeric_value=float(numeric_value) if numeric_value is not None else None,
                text_value=text_value,
                unit=unit,
                dimensions_json=json.dumps(dimensions or {}, ensure_ascii=False, sort_keys=True),
                quality_status=(spec.availability.value if spec else YouTubeMetricAvailability.UNKNOWN.value),
                warning_codes_json=json.dumps(row.get("warning_codes") or [], ensure_ascii=False),
                created_at=datetime.now(timezone.utc),
            )
        )
    return tuple(values)

