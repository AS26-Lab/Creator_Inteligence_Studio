"""Tokenizacion y normalizacion deterministas para lenguaje local."""

from __future__ import annotations

import re
import unicodedata

from creator_intelligence_studio.domain.creator_language.linguistic_types import LanguageToken, PauseSpan, SentenceSpan, TokenizationResult

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
TOKEN_PATTERN = re.compile(
    r"https?://\S+|www\.\S+|[@#]\w+|[\wÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][\wÁÉÍÓÚÜÑáéíóúüñ]+)?|[^\w\s]",
    re.UNICODE,
)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?…])\s+|\n+")

SPANISH_HINTS = {
    "el", "la", "de", "que", "y", "para", "por", "con", "sin", "porque", "como", "pero",
    "esto", "eso", "entonces", "bueno", "literal", "o sea", "pues", "eh", "este",
}

ENGLISH_HINTS = {"the", "and", "to", "of", "for", "with", "this", "that", "you", "we", "like"}

ABBREVIATIONS = {"sr.", "sra.", "dr.", "dra.", "etc.", "p.ej.", "ej.", "aprox.", "ud.", "uds."}


def normalize_language_text(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _sentence_segments(text: str) -> list[str]:
    normalized = normalize_language_text(text)
    if not normalized:
        return []
    parts = SENTENCE_PATTERN.split(normalized)
    merged: list[str] = []
    buffer = ""
    for part in parts:
        candidate = part.strip()
        if not candidate:
            continue
        lower = candidate.lower()
        if buffer:
            candidate = f"{buffer} {candidate}".strip()
            buffer = ""
        if any(lower.endswith(abbreviation) for abbreviation in ABBREVIATIONS):
            buffer = candidate
            continue
        merged.append(candidate)
    if buffer:
        merged.append(buffer)
    return merged


def segment_sentences(text: str) -> tuple[SentenceSpan, ...]:
    segments = _sentence_segments(text)
    sentences: list[SentenceSpan] = []
    offset = 0
    for index, segment in enumerate(segments):
        start = text.find(segment, offset)
        if start < 0:
            start = offset
        end = start + len(segment)
        offset = end
        sentences.append(
            SentenceSpan(
                text=segment,
                normalized=normalize_language_text(segment).lower(),
                start_index=index,
                end_index=index,
            )
        )
    return tuple(sentences)


def _language_guess(text: str) -> str:
    normalized = normalize_language_text(text).lower()
    if not normalized:
        return "unknown"
    words = re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+", normalized)
    spanish = sum(1 for word in words if word in SPANISH_HINTS or any(ch in word for ch in "áéíóúñü"))
    english = sum(1 for word in words if word in ENGLISH_HINTS)
    if spanish >= english:
        return "es"
    if english > spanish:
        return "en"
    return "mixed"


def tokenize_language_text(text: str, *, pauses: list[PauseSpan] | None = None) -> TokenizationResult:
    normalized_text = normalize_language_text(text)
    language_guess = _language_guess(normalized_text)
    tokens: list[LanguageToken] = []
    for index, match in enumerate(TOKEN_PATTERN.finditer(normalized_text)):
        token = match.group(0)
        tokens.append(
            LanguageToken(
                text=token,
                normalized=token.casefold(),
                index=index,
            )
        )
    sentences = segment_sentences(normalized_text)
    pause_items = tuple(pauses or ())
    warnings: list[str] = []
    if not normalized_text:
        warnings.append("too_little_text")
    if language_guess == "mixed":
        warnings.append("mixed_language")
    return TokenizationResult(
        original_text=text,
        normalized_text=normalized_text,
        language_guess=language_guess,
        tokens=tuple(tokens),
        sentences=sentences,
        pauses=pause_items,
        warnings=tuple(dict.fromkeys(warnings)),
    )
