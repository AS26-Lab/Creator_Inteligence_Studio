"""Calculo simple de velocidad de crecimiento."""

from __future__ import annotations


def calculate_velocity(previous_value: float | None, current_value: float | None, *, period_days: float | None = None) -> float | None:
    if previous_value is None or current_value is None:
        return None
    delta = current_value - previous_value
    if period_days is None or period_days <= 0:
        return delta
    return delta / period_days

