"""Tipos de oportunidades y comparabilidad."""

from __future__ import annotations

from enum import Enum


class OpportunityType(str, Enum):
    TOPIC = "topic"
    FORMAT = "format"
    ANGLE = "angle"
    COMPARISON = "comparison"
    AUDIENCE = "audience"
    SATURATION_GAP = "saturation_gap"
    CROSS_PLATFORM_ADAPTATION = "cross_platform_adaptation"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IMMEDIATE = "immediate"


class OpportunityStatus(str, Enum):
    DRAFT = "draft"
    REQUIRES_REVIEW = "requires_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

