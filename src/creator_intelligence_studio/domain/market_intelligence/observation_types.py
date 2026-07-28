"""Tipos de observacion y calidad de evidencia."""

from __future__ import annotations

from enum import Enum


class ObservationType(str, Enum):
    TREND = "trend"
    METADATA = "metadata"
    METRIC = "metric"
    PATTERN = "pattern"
    COMPETITOR = "competitor"
    MANUAL_NOTE = "manual_note"
    CONTRADICTION = "contradiction"
    SNAPSHOT = "snapshot"


class SubjectType(str, Enum):
    MARKET = "market"
    TOPIC = "topic"
    SOURCE = "source"
    ENTITY = "entity"
    CONTENT = "content"
    PATTERN = "pattern"
    SIGNAL = "signal"


class EvidenceQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"

