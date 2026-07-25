"""Tipos auxiliares de analisis linguistico."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanguageToken:
    text: str
    normalized: str
    index: int
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class SentenceSpan:
    text: str
    normalized: str
    start_index: int
    end_index: int
    start_seconds: float | None = None
    end_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class PhraseSpan:
    text: str
    normalized: str
    count: int
    support_count: int


@dataclass(frozen=True, slots=True)
class PauseSpan:
    before_index: int
    after_index: int
    pause_seconds: float


@dataclass(frozen=True, slots=True)
class TokenizationResult:
    original_text: str
    normalized_text: str
    language_guess: str
    tokens: tuple[LanguageToken, ...]
    sentences: tuple[SentenceSpan, ...]
    pauses: tuple[PauseSpan, ...]
    warnings: tuple[str, ...]

