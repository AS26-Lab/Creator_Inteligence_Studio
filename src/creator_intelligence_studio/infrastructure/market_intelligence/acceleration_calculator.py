"""Calculo simple de aceleracion."""

from __future__ import annotations

from .velocity_calculator import calculate_velocity


def calculate_acceleration(previous_value: float | None, mid_value: float | None, current_value: float | None, *, period_days: float | None = None) -> float | None:
    previous_velocity = calculate_velocity(previous_value, mid_value, period_days=period_days)
    current_velocity = calculate_velocity(mid_value, current_value, period_days=period_days)
    if previous_velocity is None or current_velocity is None:
        return None
    return current_velocity - previous_velocity

