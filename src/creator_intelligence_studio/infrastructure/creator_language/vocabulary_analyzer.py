"""Analisis de vocabulario y expresiones recurrentes."""

from __future__ import annotations

from collections import Counter

from .phrase_frequency_analyzer import FUNCTION_WORDS
from .tokenizer import tokenize_language_text


def analyze_vocabulary(text: str, *, max_terms: int = 30) -> dict[str, object]:
    tokens = [token.normalized for token in tokenize_language_text(text).tokens]
    content_tokens = [token for token in tokens if token.isalnum() and token not in FUNCTION_WORDS]
    counts = Counter(content_tokens)
    return {
        "frequent_terms": counts.most_common(max_terms),
        "unique_terms": len(counts),
        "vocabulary_diversity": (len(counts) / max(1, len(content_tokens))) if content_tokens else 0.0,
        "content_token_count": len(content_tokens),
    }
