"""Tipos de confianza."""

from __future__ import annotations

from enum import Enum


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"
