"""Valores cerrados para Creator Language Analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CreatorLanguageConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreatorLanguageScope(str, Enum):
    CREATOR_GENERAL = "creator_general"
    PLATFORM_SPECIFIC = "platform_specific"
    CONTENT_TYPE_SPECIFIC = "content_type_specific"
    TOPIC_SPECIFIC = "topic_specific"
    FORMAT_SPECIFIC = "format_specific"


class CreatorLanguageCorpusStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class CreatorLanguageCorpusSourceIncludeStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
    PENDING = "pending"


class CreatorLanguageAnalysisRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    ANALYZING = "analyzing"
    BUILDING_PROFILE = "building_profile"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreatorLanguagePatternType(str, Enum):
    VOCABULARY_PATTERN = "vocabulary_pattern"
    PHRASE_PATTERN = "phrase_pattern"
    FILLER_PATTERN = "filler_pattern"
    SENTENCE_PATTERN = "sentence_pattern"
    TONE_PATTERN = "tone_pattern"
    OPENING_PATTERN = "opening_pattern"
    DEVELOPMENT_PATTERN = "development_pattern"
    EXPLANATION_PATTERN = "explanation_pattern"
    HUMOR_PATTERN = "humor_pattern"
    PACING_PATTERN = "pacing_pattern"
    PAUSE_PATTERN = "pause_pattern"
    CLOSING_PATTERN = "closing_pattern"
    CTA_PATTERN = "CTA_pattern"
    PLATFORM_DIFFERENCE = "platform_difference"
    CONTENT_TYPE_DIFFERENCE = "content_type_difference"
    TEMPORAL_CHANGE = "temporal_change"
    CONTRADICTION = "contradiction"
    DATA_QUALITY_WARNING = "data_quality_warning"


class CreatorLanguagePatternStatus(str, Enum):
    OBSERVED = "observed"
    PROVISIONAL = "provisional"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"
    DEPRECATED = "deprecated"


class CreatorLanguageCandidateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"
    APPLIED = "applied"


class CreatorLanguageCandidateReviewDecision(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    REJECT = "reject"
    NEEDS_MORE_DATA = "needs_more_data"


class CreatorLanguageSourceType(str, Enum):
    TRANSCRIPTION = "transcription"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    SUBTITLE_TRACK = "subtitle_track"
    SUBTITLE_CUE = "subtitle_cue"
    PUBLICATION_TITLE = "publication_title"
    PUBLICATION_CAPTION = "publication_caption"
    PUBLICATION_COPY = "publication_copy"
    MANUAL_TEXT = "manual_text"
    VIDEO_SEGMENT = "video_segment"
    ACOUSTIC_METADATA = "acoustic_metadata"
    MEMORY_EXAMPLE = "memory_example"
    OTHER = "other"


class CreatorLanguageTargetMemoryType(str, Enum):
    TRAIT = "trait"
    VOCABULARY = "vocabulary"
    EXAMPLE = "example"
    STYLE_RULE = "style_rule"
    LIMIT = "limit"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class CreatorLanguageFillerWord:
    term: str
    examples: tuple[str, ...] = ()

