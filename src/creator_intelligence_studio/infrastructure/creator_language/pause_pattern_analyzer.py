"""Analisis de pausas y ritmo a partir de marcas temporales locales."""

from __future__ import annotations

from statistics import mean


def analyze_pause_patterns(sentences: list[dict[str, object]]) -> dict[str, object]:
    pauses: list[float] = []
    leading_pauses: list[float] = []
    for previous, current in zip(sentences, sentences[1:]):
        previous_end = previous.get("end_seconds")
        current_start = current.get("start_seconds")
        if previous_end is None or current_start is None:
            continue
        pause = float(current_start) - float(previous_end)
        if pause >= 0:
            pauses.append(pause)
            leading_pauses.append(pause)
    average_pause = mean(pauses) if pauses else 0.0
    long_pause_ratio = sum(1 for pause in pauses if pause >= 1.5) / max(1, len(pauses))
    return {
        "pause_count": len(pauses),
        "average_pause_duration": average_pause,
        "long_pause_ratio": long_pause_ratio,
        "pause_rate": len(pauses) / max(1, len(sentences)),
        "pauses": pauses,
        "leading_pauses": leading_pauses,
    }
