"""Analisis de conectores y marcadores discursivos."""

from __future__ import annotations

from collections import Counter

from .tokenizer import tokenize_language_text

DISCOURSE_MARKERS = {
    "entonces",
    "ademas",
    "además",
    "porque",
    "por eso",
    "sin embargo",
    "o sea",
    "bueno",
    "mira",
    "fíjate",
    "primero",
    "despues",
    "después",
    "por ejemplo",
    "en cambio",
}


def analyze_discourse_markers(text: str) -> dict[str, object]:
    normalized = " ".join(token.normalized for token in tokenize_language_text(text).tokens)
    counts: Counter[str] = Counter()
    for marker in DISCOURSE_MARKERS:
        counts[marker] += normalized.count(marker)
    total = sum(counts.values())
    return {
        "counts": counts,
        "total": total,
        "rate": total / max(1, len(normalized.split())),
    }
