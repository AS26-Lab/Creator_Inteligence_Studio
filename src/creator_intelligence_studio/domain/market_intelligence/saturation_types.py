"""Niveles de saturación."""

from __future__ import annotations

from enum import Enum


class SaturationLevel(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

