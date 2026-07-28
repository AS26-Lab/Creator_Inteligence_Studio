"""Tipos de patrones y evidencia de patrones."""

from __future__ import annotations

from enum import Enum


class PatternType(str, Enum):
    TOPIC = "topic"
    FORMAT = "format"
    SERIES = "series"
    HOOK = "hook"
    PACING = "pacing"
    EDITING = "editing"
    PACKAGING = "packaging"
    AUDIENCE = "audience"
    COUNTER_PATTERN = "counter_pattern"


class PatternStatus(str, Enum):
    ACTIVE = "active"
    OBSERVED = "observed"
    CONTRADICTED = "contradicted"
    ARCHIVED = "archived"


class EvidenceRole(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXEMPLIFIES = "exemplifies"
    ANCHORS = "anchors"

