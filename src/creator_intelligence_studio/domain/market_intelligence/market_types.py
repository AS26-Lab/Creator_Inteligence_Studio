"""Tipos generales de mercado."""

from __future__ import annotations

from enum import Enum


class MarketStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class MarketType(str, Enum):
    MARKET = "market"
    NICHE = "niche"
    SUBNICHE = "subniche"
    TOPIC_CLUSTER = "topic_cluster"


class TopicType(str, Enum):
    TOPIC = "topic"
    SUBTOPIC = "subtopic"
    EXCLUDED = "excluded"
    ALIAS = "alias"
    REFERENCE = "reference"

