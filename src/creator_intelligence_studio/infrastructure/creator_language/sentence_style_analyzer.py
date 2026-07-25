"""Analisis heuristico de estilo de frase."""

from __future__ import annotations

from statistics import median

from .tokenizer import tokenize_language_text


def analyze_sentence_style(text: str) -> dict[str, object]:
    result = tokenize_language_text(text)
    sentence_lengths = [len(sentence.normalized.split()) for sentence in result.sentences if sentence.normalized.strip()]
    token_text = [token.normalized for token in result.tokens]
    question_count = sum(1 for sentence in result.sentences if "?" in sentence.text)
    exclamation_count = sum(1 for sentence in result.sentences if "!" in sentence.text)
    first_person = sum(1 for token in token_text if token in {"yo", "me", "mi", "mio", "mía", "mio", "nos", "nosotros", "nosotras"})
    second_person = sum(1 for token in token_text if token in {"tu", "tú", "usted", "ustedes", "te", "ti", "vos"})
    imperative_markers = sum(1 for token in token_text if token in {"haz", "mira", "fíjate", "escucha", "vamos", "ve", "dime", "abre"})
    repeated_tokens = len(token_text) - len(set(token_text))
    return {
        "total_tokens": len(token_text),
        "unique_tokens": len(set(token_text)),
        "vocabulary_diversity": (len(set(token_text)) / max(1, len(token_text))) if token_text else 0.0,
        "average_sentence_length": (sum(sentence_lengths) / len(sentence_lengths)) if sentence_lengths else 0.0,
        "median_sentence_length": median(sentence_lengths) if sentence_lengths else 0.0,
        "sentence_length_distribution": sentence_lengths,
        "short_sentence_ratio": sum(1 for length in sentence_lengths if length <= 8) / max(1, len(sentence_lengths)),
        "long_sentence_ratio": sum(1 for length in sentence_lengths if length >= 20) / max(1, len(sentence_lengths)),
        "question_ratio": question_count / max(1, len(sentence_lengths)),
        "exclamation_ratio": exclamation_count / max(1, len(sentence_lengths)),
        "first_person_ratio": first_person / max(1, len(token_text)),
        "second_person_ratio": second_person / max(1, len(token_text)),
        "imperative_ratio": imperative_markers / max(1, len(token_text)),
        "repetition_rate": repeated_tokens / max(1, len(token_text)),
        "lexical_repetition": repeated_tokens,
        "average_clause_estimate": max(1.0, (sum(sentence_lengths) / max(1, len(sentence_lengths))) / 1.8) if sentence_lengths else 0.0,
    }
