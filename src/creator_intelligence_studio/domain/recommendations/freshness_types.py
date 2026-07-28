"""Tipos de frescura."""

from __future__ import annotations

from enum import Enum


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    RECENT = "recent"
    AGING = "aging"
    STALE = "stale"
    EXPIRED = "expired"
    EVERGREEN = "evergreen"
    SEASONAL = "seasonal"
    UNKNOWN = "unknown"
