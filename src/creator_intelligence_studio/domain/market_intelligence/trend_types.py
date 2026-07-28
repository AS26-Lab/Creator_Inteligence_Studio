"""Tipos de señales de tendencia."""

from __future__ import annotations

from enum import Enum

from .lifecycle_types import LifecycleStage


class TrendSignalType(str, Enum):
    TOPIC_GROWTH = "topic_growth"
    TOPIC_DECLINE = "topic_decline"
    FORMAT_GROWTH = "format_growth"
    FORMAT_DECLINE = "format_decline"
    SEARCH_INTEREST_PROXY = "search_interest_proxy"
    PUBLIC_VIEW_GROWTH = "public_view_growth"
    ENGAGEMENT_GROWTH = "engagement_growth"
    SATURATION = "saturation"
    NOVELTY = "novelty"
    PERSISTENCE = "persistence"
    ACCELERATION = "acceleration"
    CONTRADICTION = "contradiction"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    MIXED = "mixed"
    UNKNOWN = "unknown"

