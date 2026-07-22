"""Alineacion temporal para analisis multimodal."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True, slots=True)
class WindowSpan:
    """Intervalo temporal base."""

    window_index: int
    start_seconds: float
    end_seconds: float


def build_window_spans(duration_seconds: float, window_size_seconds: float) -> list[WindowSpan]:
    if duration_seconds <= 0:
        return []
    if window_size_seconds <= 0:
        raise ValueError("window_size_seconds debe ser mayor que cero.")
    count = max(1, int(floor(duration_seconds / window_size_seconds + 1e-9)) + (1 if duration_seconds % window_size_seconds > 1e-9 else 0))
    spans: list[WindowSpan] = []
    start = 0.0
    for index in range(count):
        end = min(duration_seconds, start + window_size_seconds)
        spans.append(WindowSpan(window_index=index, start_seconds=start, end_seconds=end))
        start = end
        if start >= duration_seconds:
            break
    if spans and spans[-1].end_seconds < duration_seconds:
        spans.append(WindowSpan(window_index=len(spans), start_seconds=spans[-1].end_seconds, end_seconds=duration_seconds))
    return spans


def overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def overlap_ratio(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    span = max(1e-9, end_a - start_a)
    return overlap_seconds(start_a, end_a, start_b, end_b) / span


def midpoint(start_seconds: float, end_seconds: float) -> float:
    return start_seconds + (max(0.0, end_seconds - start_seconds) / 2.0)

