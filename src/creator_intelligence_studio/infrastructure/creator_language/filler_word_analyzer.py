"""Analisis de muletillas y palabras de relleno."""

from __future__ import annotations

from collections import Counter

from .tokenizer import tokenize_language_text

FILLER_WORDS = {
    "eh",
    "em",
    "este",
    "o sea",
    "pues",
    "bueno",
    "literal",
    "basicamente",
    "básicamente",
    "digamos",
    "como que",
    "la verdad",
    "en plan",
    "entonces",
}


def analyze_filler_words(text: str) -> dict[str, object]:
    normalized = " ".join(token.normalized for token in tokenize_language_text(text).tokens)
    counts: Counter[str] = Counter()
    for filler in FILLER_WORDS:
        if " " in filler:
            counts[filler] += normalized.count(filler)
        else:
            counts[filler] += normalized.split().count(filler)
    total = sum(counts.values())
    return {
        "counts": counts,
        "total": total,
        "rate": (total / max(1, len(normalized.split()))) if normalized else 0.0,
        "examples": [term for term, count in counts.items() if count > 0],
    }
