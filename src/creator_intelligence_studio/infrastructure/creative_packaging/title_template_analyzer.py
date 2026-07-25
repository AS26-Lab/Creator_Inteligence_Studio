"""Clasificacion heuristica de titulos."""

from __future__ import annotations

from creator_intelligence_studio.domain.creative_packaging.title_types import TitlePatternType

from .title_feature_extractor import classify_title_pattern

__all__ = ["classify_title_pattern", "TitlePatternType"]

