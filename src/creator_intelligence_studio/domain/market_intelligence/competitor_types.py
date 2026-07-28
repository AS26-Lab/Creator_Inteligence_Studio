"""Tipos de relación con competidores y referentes."""

from __future__ import annotations

from enum import Enum


class RelationshipType(str, Enum):
    DIRECT_COMPETITOR = "direct_competitor"
    INDIRECT_COMPETITOR = "indirect_competitor"
    COMPARABLE_CREATOR = "comparable_creator"
    ASPIRATIONAL_REFERENCE = "aspirational_reference"
    FORMAT_REFERENCE = "format_reference"
    TOPIC_REFERENCE = "topic_reference"
    PACKAGING_REFERENCE = "packaging_reference"
    AUDIENCE_REFERENCE = "audience_reference"
    ADJACENT_MARKET = "adjacent_market"
    ANTI_REFERENCE = "anti_reference"
    UNKNOWN = "unknown"


class CompetitorApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class CompetitorMonitoringStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"

