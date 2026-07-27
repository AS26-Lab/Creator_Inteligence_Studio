"""Deteccion local de contradicciones."""

from __future__ import annotations


def detect_contradictions(signals: list[dict[str, object]]) -> list[dict[str, object]]:
    contradictions: list[dict[str, object]] = []
    by_platform: dict[str, dict[str, float]] = {}
    for signal in signals:
        platform = str(signal.get("platform") or "unknown")
        key = str(signal.get("signal_key") or "")
        value = signal.get("numeric_value")
        if not isinstance(value, (int, float)):
            continue
        by_platform.setdefault(platform, {})[key] = float(value)
    for platform, values in by_platform.items():
        views = values.get("views")
        completion = values.get("completion_rate")
        returning = values.get("returning_viewers")
        new_viewers = values.get("new_viewers")
        if views is not None and completion is not None and views > 0 and completion < 0.25:
            contradictions.append({"platform": platform, "type": "high_views_low_completion"})
        if returning is not None and new_viewers is not None and returning > new_viewers * 1.5:
            contradictions.append({"platform": platform, "type": "returning_dominates_new"})
    return contradictions

