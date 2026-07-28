"""Calculadora de señales de tendencia basada en observaciones historicas."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import json_loads
from .acceleration_calculator import calculate_acceleration
from .persistence_calculator import calculate_persistence
from .velocity_calculator import calculate_velocity


def _extract_numeric(payload: dict[str, Any]) -> float | None:
    value = payload.get("value")
    if value is None and "observed_value_json" in payload:
        observed = json_loads(payload.get("observed_value_json"), {})
        if isinstance(observed, dict):
            value = observed.get("value")
    if value is None and "numeric_value" in payload:
        value = payload.get("numeric_value")
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def compute_trend_points(observations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        key = str(observation.get("topic_id") or observation.get("market_id") or observation.get("platform") or "unknown")
        grouped[key].append(observation)
    result: dict[str, dict[str, Any]] = {}
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda item: str(item.get("observed_at") or ""))
        values = [_extract_numeric(item) for item in ordered]
        velocity = calculate_velocity(values[-2] if len(values) >= 2 else None, values[-1] if values else None)
        acceleration = calculate_acceleration(values[-3] if len(values) >= 3 else None, values[-2] if len(values) >= 2 else None, values[-1] if values else None)
        persistence = calculate_persistence(values)
        result[key] = {
            "sample_size": len(values),
            "values": values,
            "velocity": velocity,
            "acceleration": acceleration,
            "persistence": persistence,
            "latest": ordered[-1] if ordered else None,
        }
    return result
