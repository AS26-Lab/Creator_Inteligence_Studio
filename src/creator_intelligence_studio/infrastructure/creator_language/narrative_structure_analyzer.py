"""Analizador heuristico de estructura narrativa."""

from __future__ import annotations

from collections import Counter

from creator_intelligence_studio.domain.creator_language.narrative_types import NarrativeSectionSummary
from .tokenizer import segment_sentences, tokenize_language_text

OPENING_PATTERNS = {
    "saludo": {"hola", "buenos", "buenas", "hey"},
    "pregunta": {"?", "quieres", "sabes", "has"},
    "conflicto_directo": {"problema", "ojo", "cuidado", "nunca", "siempre", "mal"},
    "promesa": {"te voy a", "vamos a", "hoy te", "en este video"},
    "contexto": {"contexto", "hoy", "primero", "antes"},
    "cold_open": {"empezamos", "arranque", "mira esto", "fija"},
    "declaracion": {"voy a", "quiero", "esto es"},
    "reaccion": {"no puede ser", "en serio", "wow", "madre mia"},
}

EXPLANATION_MARKERS = {"primero", "segundo", "tercero", "por ejemplo", "significa", "o sea", "es decir", "similar"}
HUMOR_MARKERS = {"jaja", "jeje", "meme", "absurdo", "risa", "ironia", "ironia", "remate", "callback"}
CLOSING_MARKERS = {"gracias", "suscribete", "sígueme", "sigue", "nos vemos", "hasta luego", "recuerda", "comenta"}


def _sentence_texts(text: str) -> list[str]:
    return [sentence.text for sentence in segment_sentences(text)]


def _score_markers(sentences: list[str], markers: set[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    count = 0
    joined = " ".join(sentence.casefold() for sentence in sentences)
    for marker in markers:
        if marker in joined:
            count += joined.count(marker)
            hits.append(marker)
    return count, hits


def _build_section(label: str, pattern_key: str, sentences: list[str], markers: set[str], *, confidence_boost: int = 0) -> NarrativeSectionSummary:
    count, hits = _score_markers(sentences, markers)
    examples = tuple({"text": sentence} for sentence in sentences[:3] if sentence)
    confidence = "low"
    if count >= 6 + confidence_boost:
        confidence = "high"
    elif count >= 3:
        confidence = "medium"
    return NarrativeSectionSummary(
        label=label,
        pattern_key=pattern_key,
        description=f"Patron heuristico de {label.lower()}",
        frequency_count=count,
        supporting_example_count=min(count, len(examples)),
        contradicting_example_count=max(0, len(sentences) - count),
        confidence_level=confidence,
        examples=examples,
        warnings=tuple(["insufficient_sample"] if len(sentences) < 3 else []),
    )


def analyze_narrative_structure(text: str, *, platform: str | None = None, content_type: str | None = None) -> dict[str, object]:
    sentences = _sentence_texts(text)
    normalized = " ".join(token.normalized for token in tokenize_language_text(text).tokens)
    opening_sentences = sentences[:2]
    middle_sentences = sentences[1:-1] if len(sentences) > 2 else sentences
    closing_sentences = sentences[-2:] if len(sentences) > 1 else sentences
    opening = []
    if opening_sentences:
        opening_text = " ".join(s.casefold() for s in opening_sentences)
        for label, markers in OPENING_PATTERNS.items():
            if any(marker in opening_text for marker in markers):
                opening.append(_build_section("Apertura", label, opening_sentences, markers))
    if not opening and opening_sentences:
        opening.append(_build_section("Apertura", "declaracion", opening_sentences, {"."}, confidence_boost=1))
    development_count = sum(1 for sentence in middle_sentences if any(marker in sentence.casefold() for marker in {"porque", "por ejemplo", "ademas", "además", "luego", "despues", "después"}))
    explanation = _build_section("Explicacion", "explanation", sentences, EXPLANATION_MARKERS)
    humor = _build_section("Humor", "humor", sentences, HUMOR_MARKERS)
    closing = _build_section("Cierre", "closing", closing_sentences, CLOSING_MARKERS)
    pacing_score = sum(1 for sentence in sentences if len(sentence.split()) <= 10)
    platform_hint = None
    if platform in {"youtube_short", "tiktok"} and any(len(sentence.split()) <= 8 for sentence in opening_sentences):
        platform_hint = "apertura_directa"
    elif platform in {"youtube_longform"} and any(len(sentence.split()) >= 12 for sentence in middle_sentences):
        platform_hint = "explicacion_extensa"
    return {
        "opening": [item.to_dict() for item in opening],
        "development": [
            NarrativeSectionSummary(
                label="Desarrollo",
                pattern_key="development",
                description="Patron heuristico de desarrollo",
                frequency_count=development_count,
                supporting_example_count=min(development_count, len(middle_sentences)),
                contradicting_example_count=max(0, len(middle_sentences) - development_count),
                confidence_level="medium" if development_count >= 3 else "low",
                examples=tuple({"text": sentence} for sentence in middle_sentences[:3]),
                warnings=tuple(["insufficient_sample"] if len(sentences) < 4 else []),
            ).to_dict()
        ],
        "explanation": [explanation.to_dict()],
        "humor": [humor.to_dict()],
        "pacing": [
            NarrativeSectionSummary(
                label="Ritmo",
                pattern_key="pacing",
                description="Patron heuristico de ritmo verbal",
                frequency_count=pacing_score,
                supporting_example_count=min(pacing_score, len(sentences)),
                contradicting_example_count=max(0, len(sentences) - pacing_score),
                confidence_level="low" if len(sentences) < 4 else "medium",
                examples=tuple({"text": sentence} for sentence in sentences[:3]),
                warnings=tuple(["duration_missing"] if not text.strip() else []),
            ).to_dict()
        ],
        "closing": [closing.to_dict()],
        "platform_differences": [
            NarrativeSectionSummary(
                label="Plataforma",
                pattern_key=platform_hint or "platform_difference",
                description="Diferencia heuristica por plataforma",
                frequency_count=1 if platform_hint else 0,
                supporting_example_count=1 if platform_hint else 0,
                contradicting_example_count=0 if platform_hint else len(sentences),
                confidence_level="low" if platform_hint else "very_low",
                examples=tuple({"text": sentence} for sentence in opening_sentences[:2]),
                warnings=tuple(["mixed_platform"] if platform is None else []),
            ).to_dict()
        ],
        "content_type_differences": [
            NarrativeSectionSummary(
                label="Contenido",
                pattern_key="content_type_difference",
                description="Diferencia heuristica por tipo de contenido",
                frequency_count=1 if content_type else 0,
                supporting_example_count=1 if content_type else 0,
                contradicting_example_count=0,
                confidence_level="low" if content_type else "very_low",
                examples=tuple({"text": sentence} for sentence in sentences[:2]),
                warnings=tuple(["mixed_content_type"] if content_type is None else []),
            ).to_dict()
        ],
        "limitations": [warning for warning in ["punctuation_unreliable" if "." not in normalized else "", "mixed_language" if any(word in normalized for word in {"ok", "cool", "bro"}) else ""] if warning],
        "summary": "Perfil narrativo heuristico construido a partir de aperturas, desarrollo, explicacion, humor, ritmo y cierre.",
    }
