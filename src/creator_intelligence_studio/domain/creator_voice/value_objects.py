"""Closed value objects for Creator Voice evidence."""

from __future__ import annotations

from enum import Enum


class CreatorVoiceEvidenceType(str, Enum):
    CREATOR_WRITTEN = "creator_written"
    CREATOR_EDITED = "creator_edited"
    CREATOR_SPOKEN = "creator_spoken"
    CONFIRMED_PREFERENCE = "confirmed_preference"


class CreatorVoiceEvidenceSourceKind(str, Enum):
    CORPUS_VERSION = "corpus_version"
    CORPUS_SEGMENT = "corpus_segment"
    CONFIRMED_PREFERENCE = "confirmed_preference"


class CreatorVoiceEvidenceQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CreatorVoiceScopeMode(str, Enum):
    CREATOR_GLOBAL = "creator_global"
    PROJECT_SPECIFIC = "project_specific"
    WORKFLOW_SPECIFIC = "workflow_specific"


class CreatorVoiceSelectionPolicyVersion(str, Enum):
    V1 = "voice-evidence-policy-v1"


class CreatorVoiceExclusionReason(str, Enum):
    AI_GENERATED = "ai_generated"
    AI_REWRITTEN = "ai_rewritten"
    NOT_VOICE_LEARNING_ELIGIBLE = "not_voice_learning_eligible"
    ARCHIVED = "archived"
    LOW_CONFIDENCE = "low_confidence"
    NEEDS_REVIEW = "needs_review"
    DUPLICATE = "duplicate"
    UNSUPPORTED_AUTHORSHIP = "unsupported_authorship"
    TOO_LITTLE_SIGNAL = "too_little_signal"
    WRONG_SCOPE = "wrong_scope"
    WRONG_LANGUAGE = "wrong_language"
    HISTORICAL_VERSION = "historical_version"
    EVIDENCE_CAP = "evidence_cap"
    SOURCE_CAP = "source_cap"
