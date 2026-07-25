"""Extraccion determinista de rasgos de titulos."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from statistics import mean

from creator_intelligence_studio.domain.creative_packaging.title_types import (
    TitleAnalysisMetric,
    TitleAnalysisResult,
    TitlePatternType,
)


_STOPWORDS = {
    "de",
    "la",
    "el",
    "y",
    "o",
    "en",
    "a",
    "un",
    "una",
    "que",
    "con",
    "por",
    "para",
    "del",
    "los",
    "las",
    "es",
    "se",
    "al",
    "lo",
    "como",
    "más",
    "mas",
    "mi",
    "tu",
    "su",
}

_DIRECT_ADDRESS = {"tu", "tú", "usted", "ustedes", "vos", "vosotros", "you"}
_FIRST_PERSON = {"yo", "me", "mi", "mio", "mía", "mío", "nosotros", "nos", "nuestro", "we", "i"}
_EMOTIONAL = {"brutal", "increible", "increíble", "wow", "wow!", "bestial", "epico", "épico", "absurdo", "sorprendente"}
_PROHIBITED = {"garantizado", "siempre", "nunca", "secreto", "fácil", "facil", "milagro"}


def _tokens(title: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9_@#]+", title.casefold())


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def classify_title_pattern(title: str) -> TitlePatternType:
    normalized = title.casefold().strip()
    if not normalized:
        return TitlePatternType.OTHER
    if "?" in title:
        return TitlePatternType.QUESTION
    if re.search(r"\b(vs|contra|comparado con)\b", normalized):
        return TitlePatternType.COMPARISON
    if re.search(r"\b(cómo|como|paso a paso|guía|guia|tutorial|aprende)\b", normalized):
        return TitlePatternType.TUTORIAL
    if re.search(r"\b(secreto|nadie te dice|no vas a creer|lo que pasó|lo que paso|ojo)\b", normalized):
        return TitlePatternType.CURIOSITY_GAP
    if re.search(r"\b(resulta|logr[ée]|gan[ée]|funcion[óo])\b", normalized):
        return TitlePatternType.RESULT
    if re.search(r"\b(de .* a .*|transform|cambio)\b", normalized):
        return TitlePatternType.TRANSFORMATION
    if re.search(r"\b(top|5|10|lista|los \d+)\b", normalized):
        return TitlePatternType.LIST
    if re.search(r"\b(reacción|reaccion|mi reacción|mi reaccion)\b", normalized):
        return TitlePatternType.REACTION
    if re.search(r"\b(historia|story)\b", normalized):
        return TitlePatternType.STORY
    if re.search(r"\b(urge|ret[óa]te|haz esto|hazlo)\b", normalized):
        return TitlePatternType.CHALLENGE
    if re.search(r"\b(esto es|así|asi es|explico|explicar)\b", normalized):
        return TitlePatternType.DESCRIPTIVE
    if re.search(r"\b(primero|segundo|tercero|paso)\b", normalized):
        return TitlePatternType.TUTORIAL
    return TitlePatternType.STATEMENT


def analyze_title_text(
    title: str,
    *,
    platform: str | None = None,
    content_type: str | None = None,
    creator_vocabulary: set[str] | None = None,
    creator_style_terms: set[str] | None = None,
    historical_titles: list[str] | None = None,
    rejected_titles: list[str] | None = None,
    prohibited_terms: list[str] | None = None,
) -> TitleAnalysisResult:
    normalized = title.strip()
    token_list = _tokens(normalized)
    content_tokens = [token for token in token_list if token not in _STOPWORDS]
    counts = Counter(token_list)
    repeated = sum(1 for count in counts.values() if count > 1)
    alphabetic = [char for char in normalized if char.isalpha()]
    uppercase = [char for char in normalized if char.isupper()]
    question_presence = "?" in normalized
    number_presence = any(char.isdigit() for char in normalized)
    emotional_term_count = sum(1 for token in token_list if token in _EMOTIONAL)
    prohibited = {term.casefold() for term in (prohibited_terms or [])} | _PROHIBITED
    prohibited_presence = [term for term in sorted(prohibited) if term and term in normalized.casefold()]
    stopword_ratio = _safe_ratio(sum(1 for token in token_list if token in _STOPWORDS), len(token_list))
    clarity_score = _safe_ratio(len(set(content_tokens)) * 2.0, len(content_tokens) + 1.0)
    truncation_risk = 1.0 if len(normalized) > 90 else 0.0 if len(normalized) < 60 else 0.4
    length_warning = None
    if platform == "youtube_short" and len(normalized) > 70:
        length_warning = "platform_length_warning"
    if platform == "youtube_longform" and len(normalized) < 18:
        length_warning = "platform_length_warning"
    overlap_vocab = len(set(content_tokens) & {token.casefold() for token in (creator_vocabulary or set())})
    overlap_style = len(set(content_tokens) & {token.casefold() for token in (creator_style_terms or set())})
    historical_match = 0.0
    rejected_match = 0.0
    if historical_titles:
        historical_match = max(
            (len(set(content_tokens) & set(_tokens(existing))) / max(len(set(content_tokens)) or 1, 1) for existing in historical_titles),
            default=0.0,
        )
    if rejected_titles:
        rejected_match = max(
            (len(set(content_tokens) & set(_tokens(existing))) / max(len(set(content_tokens)) or 1, 1) for existing in rejected_titles),
            default=0.0,
        )
    direct_address_presence = any(token in _DIRECT_ADDRESS for token in token_list)
    first_person_presence = any(token in _FIRST_PERSON for token in token_list)
    pattern = classify_title_pattern(normalized)
    pattern_warning = "title_too_generic" if len(content_tokens) <= 2 else None
    ambiguity_flags = []
    if not content_tokens:
        ambiguity_flags.append("missing_content_terms")
    if any(term in normalized.casefold() for term in ("tal vez", "quizá", "quizas", "posible")):
        ambiguity_flags.append("ambiguous_claim")
    if rejected_match > 0.6:
        ambiguity_flags.append("rejected_pattern_match")
    metrics = (
        TitleAnalysisMetric("character_count", float(len(normalized)), None, "count", "high"),
        TitleAnalysisMetric("word_count", float(len(token_list)), None, "count", "high"),
        TitleAnalysisMetric("average_word_length", mean([len(token) for token in token_list]) if token_list else None, None, "characters", "medium"),
        TitleAnalysisMetric("punctuation_count", float(sum(1 for char in normalized if not char.isalnum() and not char.isspace())), None, "count", "high"),
        TitleAnalysisMetric("question_presence", 1.0 if question_presence else 0.0, None, "bool", "high"),
        TitleAnalysisMetric("number_presence", 1.0 if number_presence else 0.0, None, "bool", "high"),
        TitleAnalysisMetric("capitalization_ratio", _safe_ratio(len(uppercase), len(alphabetic)) or 0.0, None, "ratio", "medium"),
        TitleAnalysisMetric("repeated_word_count", float(repeated), None, "count", "high"),
        TitleAnalysisMetric("stopword_ratio", stopword_ratio, None, "ratio", "medium"),
        TitleAnalysisMetric("direct_address_presence", 1.0 if direct_address_presence else 0.0, None, "bool", "high"),
        TitleAnalysisMetric("first_person_presence", 1.0 if first_person_presence else 0.0, None, "bool", "high"),
        TitleAnalysisMetric("emotional_term_count", float(emotional_term_count), None, "count", "medium"),
        TitleAnalysisMetric("specificity_score", float(clarity_score or 0.0), None, "score", "low"),
        TitleAnalysisMetric("truncation_risk", float(truncation_risk), None, "risk", "medium"),
        TitleAnalysisMetric("creator_vocabulary_overlap", float(overlap_vocab), None, "count", "medium"),
        TitleAnalysisMetric("creator_style_alignment", float(overlap_style), None, "count", "medium"),
        TitleAnalysisMetric("historical_pattern_match", float(historical_match), None, "ratio", "low"),
        TitleAnalysisMetric("rejected_pattern_match", float(rejected_match), None, "ratio", "low"),
    )
    warnings = tuple(flag for flag in [length_warning, pattern_warning, *ambiguity_flags, "prohibited_term_presence" if prohibited_presence else None] if flag)
    summary = (
        f"Patron {pattern.value} con {len(token_list)} palabras y "
        f"{'presencia' if question_presence else 'sin'} de pregunta."
    )
    if prohibited_presence:
        warnings = tuple(sorted(set((*warnings, "prohibited_term_presence"))))
    recommendation_status = "insufficient_evidence"
    if not warnings and len(token_list) >= 3:
        recommendation_status = "approved_as_is" if float(clarity_score or 0.0) >= 0.6 else "approved_with_changes"
    return TitleAnalysisResult(
        pattern_type=pattern,
        metrics=metrics,
        warnings=warnings,
        recommendation_status=recommendation_status,
        summary=summary,
    )

