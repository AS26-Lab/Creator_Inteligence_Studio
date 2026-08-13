"""Closed values for creator preferences."""

from __future__ import annotations

from enum import Enum


class CreatorPreferenceType(str, Enum):
    CONTENT_LENGTH_PREFERENCE = "content_length_preference"


class CreatorPreferenceScope(str, Enum):
    CREATOR_GLOBAL = "creator_global"
    PROJECT_SPECIFIC = "project_specific"
    WORKFLOW_SPECIFIC = "workflow_specific"


class CreatorPreferenceConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreatorPreferenceCandidateStatus(str, Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
