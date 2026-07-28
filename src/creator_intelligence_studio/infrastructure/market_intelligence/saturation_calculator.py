"""Estimacion simple de saturacion."""

from __future__ import annotations


def calculate_saturation(*, supporting_count: int, contradicting_count: int, sample_size: int) -> float | None:
    if sample_size <= 0:
        return None
    pressure = max(0, supporting_count - contradicting_count)
    ratio = 1.0 - min(1.0, pressure / sample_size)
    return round(ratio, 3)

