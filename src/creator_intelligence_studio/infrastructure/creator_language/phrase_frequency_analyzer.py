"""Analizador de frecuencias de frases."""

from __future__ import annotations

from collections import Counter

from .tokenizer import normalize_language_text, tokenize_language_text

FUNCTION_WORDS = {
    "de", "la", "que", "el", "y", "a", "en", "un", "ser", "se", "no", "haber", "por", "con", "su", "para",
    "como", "estar", "tener", "le", "lo", "del", "al", "si", "pero", "o", "porque", "cuando", "muy", "sin",
    "sobre", "tambien", "me", "ya", "este", "esta", "estos", "estas", "eso", "esa", "es", "son", "fue",
}


def analyze_phrase_frequency(text: str, *, max_terms: int = 20) -> dict[str, object]:
    tokens = [token.normalized for token in tokenize_language_text(text).tokens]
    content_tokens = [token for token in tokens if token.isalnum() and token not in FUNCTION_WORDS]
    unigrams = Counter(content_tokens)
    bigrams = Counter(" ".join(content_tokens[index:index + 2]) for index in range(max(0, len(content_tokens) - 1)))
    trigrams = Counter(" ".join(content_tokens[index:index + 3]) for index in range(max(0, len(content_tokens) - 2)))
    return {
        "top_unigrams": unigrams.most_common(max_terms),
        "top_bigrams": bigrams.most_common(max_terms),
        "top_trigrams": trigrams.most_common(max_terms),
        "content_token_count": len(content_tokens),
        "normalized_text": normalize_language_text(text).lower(),
    }
