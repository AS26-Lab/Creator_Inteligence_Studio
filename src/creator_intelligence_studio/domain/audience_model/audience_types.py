"""Tipos de audiencia observada."""

from __future__ import annotations

from enum import Enum


class AudienceSignalType(str, Enum):
    ACQUISITION = "acquisition"
    CONSUMPTION = "consumption"
    ENGAGEMENT = "engagement"
    CONVERSION = "conversion"
    LOYALTY = "loyalty"
    AFFINITY = "affinity"
    GEOGRAPHY = "geography"
    DEVICE = "device"
    SUBSCRIPTION_STATUS = "subscription_status"
    TRAFFIC_SOURCE = "traffic_source"
    RETURNING_BEHAVIOR = "returning_behavior"
    CROSS_CONTENT_FLOW = "cross_content_flow"
    DATA_QUALITY = "data_quality"


class AudienceConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class AudienceStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"


class AudienceModelRunStatus(str, Enum):
    QUEUED = "queued"
    COLLECTING_SIGNALS = "collecting_signals"
    NORMALIZING = "normalizing"
    BUILDING_SEGMENTS = "building_segments"
    BUILDING_AFFINITIES = "building_affinities"
    BUILDING_JOURNEYS = "building_journeys"
    BUILDING_PROFILE = "building_profile"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AudienceReviewDecision(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    NEEDS_MORE_DATA = "needs_more_data"
    EDIT = "edit"
    MERGE = "merge"
    SPLIT = "split"
    CHANGE_SCOPE = "change_scope"
    DEPRECATE = "deprecate"

