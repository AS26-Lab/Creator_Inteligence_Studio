"""Niveles de confianza para señales y oportunidades."""

from __future__ import annotations

from enum import Enum


class ConfidenceLevel(str, Enum):
    UNKNOWN = "unknown"
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

