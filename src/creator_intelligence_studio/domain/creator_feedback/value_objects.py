"""Closed values for creator feedback and learning signals."""

from __future__ import annotations

from enum import Enum


class CreatorFeedbackEventType(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    REGENERATED = "regenerated"
    ADOPTED = "adopted"
    SUPERSEDED = "superseded"


class CreatorFeedbackExplicitness(str, Enum):
    EXPLICIT = "explicit"
    BEHAVIORAL = "behavioral"


class CreatorFeedbackEventSource(str, Enum):
    USER_ACTION = "user_action"
    VERSION_TRANSITION = "version_transition"
    WORKFLOW_ACTION = "workflow_action"
    SYSTEM_OBSERVATION = "system_observation"


class CreatorFeedbackScope(str, Enum):
    CREATOR_GLOBAL = "creator_global"
    PROJECT_SPECIFIC = "project_specific"
    WORKFLOW_SPECIFIC = "workflow_specific"


class CreatorLearningSignalType(str, Enum):
    ACCEPTANCE = "acceptance"
    REJECTION = "rejection"
    REGENERATION = "regeneration"
    EDIT_FREQUENCY = "edit_frequency"
    LENGTH_CHANGE = "length_change"
    CONTENT_REMOVED = "content_removed"
    CONTENT_ADDED = "content_added"
    VERSION_ADOPTION = "version_adoption"


class CreatorLearningSignalPolarity(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CreatorLearningSignalConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreatorLearningSignalStatus(str, Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"

