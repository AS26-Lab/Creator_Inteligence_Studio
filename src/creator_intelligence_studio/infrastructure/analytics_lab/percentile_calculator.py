"""Calculo determinista de percentiles para Analytics Lab."""

from __future__ import annotations

from math import floor, sqrt
from statistics import mean, median


def calculate_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(float(value) for value in values)
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = floor(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def median_absolute_deviation(values: list[float]) -> float | None:
    if not values:
        return None
    med = median(values)
    deviations = [abs(value - med) for value in values]
    return float(median(deviations))


def robust_z_score(value: float, values: list[float]) -> float | None:
    if not values:
        return None
    med = median(values)
    mad = median_absolute_deviation(values)
    if mad in (None, 0):
        return 0.0
    return 0.6745 * (value - med) / mad

