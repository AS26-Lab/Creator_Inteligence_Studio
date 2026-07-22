"""Normalizacion robusta de señales multimodales."""

from __future__ import annotations

from statistics import median
from typing import Iterable, Sequence

import numpy as np


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def robust_bounds(values: Sequence[float], *, lower_percentile: float = 10.0, upper_percentile: float = 90.0) -> tuple[float, float]:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return 0.0, 1.0
    low = float(np.percentile(filtered, lower_percentile))
    high = float(np.percentile(filtered, upper_percentile))
    if abs(high - low) < 1e-9:
        high = low + 1.0
    return low, high


def normalize_series(values: Sequence[float], *, lower_percentile: float = 10.0, upper_percentile: float = 90.0) -> list[float]:
    low, high = robust_bounds(values, lower_percentile=lower_percentile, upper_percentile=upper_percentile)
    return [normalize_value(value, low, high) for value in values]


def normalize_value(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return clamp01((float(value) - low) / (high - low))


def robust_center(values: Sequence[float]) -> float:
    filtered = [float(value) for value in values if value is not None]
    return float(median(filtered)) if filtered else 0.0


def robust_deviation(values: Sequence[float], center: float | None = None) -> float:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return 1.0
    center_value = robust_center(filtered) if center is None else float(center)
    deviations = [abs(value - center_value) for value in filtered]
    dev = float(median(deviations)) if deviations else 1.0
    return dev or 1.0


def relative_change(current: float, previous: float | None, *, baseline: float = 1.0) -> float:
    if previous is None:
        return 0.0
    return clamp01(abs(float(current) - float(previous)) / max(abs(float(previous)), baseline))

