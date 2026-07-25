"""Segmentador determinista de oraciones."""

from __future__ import annotations

from creator_intelligence_studio.domain.creator_language.linguistic_types import SentenceSpan

from .tokenizer import segment_sentences

__all__ = ["segment_sentences", "SentenceSpan"]
