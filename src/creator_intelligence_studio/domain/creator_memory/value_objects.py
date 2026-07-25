"""Valores cerrados para Creator Memory."""

from __future__ import annotations

from enum import Enum


class CreatorProfileStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CreatorMemoryScope(str, Enum):
    CREATOR_GENERAL = "creator_general"
    PLATFORM_SPECIFIC = "platform_specific"
    CONTENT_TYPE_SPECIFIC = "content_type_specific"
    TOPIC_SPECIFIC = "topic_specific"
    FORMAT_SPECIFIC = "format_specific"


class CreatorMemoryConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CreatorTraitType(str, Enum):
    TONE = "tone"
    FORMALITY = "formality"
    HUMOR = "humor"
    VOCABULARY = "vocabulary"
    PHRASE_PATTERN = "phrase_pattern"
    FILLER_WORD = "filler_word"
    NARRATIVE_RHYTHM = "narrative_rhythm"
    SENTENCE_LENGTH = "sentence_length"
    EXPLANATION_STYLE = "explanation_style"
    ANALOGY_STYLE = "analogy_style"
    OPENING_STYLE = "opening_style"
    CLOSING_STYLE = "closing_style"
    CALLBACK_STYLE = "callback_style"
    PUNCHLINE_STYLE = "punchline_style"
    EXAGGERATION_LEVEL = "exaggeration_level"
    EMOTIONAL_EXPRESSION = "emotional_expression"
    CALL_TO_ACTION_STYLE = "call_to_action_style"
    EDITING_PREFERENCE = "editing_preference"
    VISUAL_PREFERENCE = "visual_preference"
    PACING_PREFERENCE = "pacing_preference"
    TOPIC_PREFERENCE = "topic_preference"
    PLATFORM_BEHAVIOR = "platform_behavior"
    CONTENT_STRUCTURE = "content_structure"
    PERSONAL_BOUNDARY = "personal_boundary"
    OTHER = "other"


class CreatorTraitStatus(str, Enum):
    OBSERVED = "observed"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NEEDS_MORE_DATA = "needs_more_data"


class CreatorExampleType(str, Enum):
    REPRESENTS_CREATOR = "represents_creator"
    DOES_NOT_REPRESENT_CREATOR = "does_not_represent_creator"
    APPROVED_STYLE = "approved_style"
    REJECTED_STYLE = "rejected_style"
    GOOD_HOOK = "good_hook"
    BAD_HOOK = "bad_hook"
    GOOD_EXPLANATION = "good_explanation"
    BAD_EXPLANATION = "bad_explanation"
    GOOD_HUMOR = "good_humor"
    FORCED_HUMOR = "forced_humor"
    PREFERRED_EDIT = "preferred_edit"
    REJECTED_EDIT = "rejected_edit"
    PREFERRED_COPY = "preferred_copy"
    REJECTED_COPY = "rejected_copy"
    PREFERRED_TITLE_DIRECTION = "preferred_title_direction"
    REJECTED_TITLE_DIRECTION = "rejected_title_direction"
    OTHER = "other"


class CreatorExampleApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"


class CreatorVocabularyType(str, Enum):
    FREQUENT_TERM = "frequent_term"
    CATCHPHRASE = "catchphrase"
    FILLER_WORD = "filler_word"
    RECURRING_EXPRESSION = "recurring_expression"
    REFERENCE = "reference"
    PREFERRED_TERM = "preferred_term"
    AVOIDED_TERM = "avoided_term"
    PROHIBITED_TERM = "prohibited_term"
    PLATFORM_SPECIFIC_TERM = "platform_specific_term"


class CreatorVocabularyStatus(str, Enum):
    ACTIVE = "active"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NEEDS_MORE_DATA = "needs_more_data"


class CreatorStyleRuleType(str, Enum):
    OBSERVED = "observed"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NEEDS_MORE_DATA = "needs_more_data"


class CreatorRuleStatus(str, Enum):
    OBSERVED = "observed"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NEEDS_MORE_DATA = "needs_more_data"


class CreatorRuleReviewDecision(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    NEED_MORE_DATA = "needs_more_data"
    DEPRECATE = "deprecate"
    EDIT = "edit"
    MERGE = "merge"
    SPLIT = "split"
    CHANGE_SCOPE = "change_scope"


class CreatorLimitType(str, Enum):
    PERSONAL_BOUNDARY = "personal_boundary"
    SENSITIVE_TOPIC = "sensitive_topic"
    PROHIBITED_CLAIM = "prohibited_claim"
    PROHIBITED_PHRASE = "prohibited_phrase"
    BRAND_SAFETY = "brand_safety"
    PRIVACY = "privacy"
    LEGAL = "legal"
    PLATFORM_SPECIFIC = "platform_specific"
    OTHER = "other"


class CreatorLimitSeverity(str, Enum):
    NOTE = "note"
    CAUTION = "caution"
    STRONG = "strong"
    ABSOLUTE = "absolute"


class CreatorLimitStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class CreatorObjectiveType(str, Enum):
    LONGFORM_GROWTH = "longform_growth"
    SHORTFORM_DISCOVERY = "shortform_discovery"
    RETURNING_AUDIENCE = "returning_audience"
    SUBSCRIBER_GROWTH = "subscriber_growth"
    FOLLOWER_GROWTH = "follower_growth"
    COMMUNITY = "community"
    AUTHORITY = "authority"
    EXPERIMENTATION = "experimentation"
    CONSISTENCY = "consistency"
    PLATFORM_EXPANSION = "platform_expansion"
    CUSTOM = "custom"


class CreatorObjectiveStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CreatorFeedbackType(str, Enum):
    SOUNDS_LIKE_ME = "sounds_like_me"
    DOES_NOT_SOUND_LIKE_ME = "does_not_sound_like_me"
    CORRECT_OBSERVATION = "correct_observation"
    INCORRECT_OBSERVATION = "incorrect_observation"
    TOO_GENERIC = "too_generic"
    TOO_EXAGGERATED = "too_exaggerated"
    TOO_FORMAL = "too_formal"
    TOO_INFORMAL = "too_informal"
    WRONG_PLATFORM_STYLE = "wrong_platform_style"
    OUTDATED = "outdated"
    MISSING_CONTEXT = "missing_context"
    OTHER = "other"


class CreatorEvidenceType(str, Enum):
    TRANSCRIPT_QUOTE = "transcript_quote"
    VIDEO_SEGMENT = "video_segment"
    PUBLICATION = "publication"
    CREATOR_FEEDBACK = "creator_feedback"
    EXPERIMENT_RESULT = "experiment_result"
    ANALYTICS_FINDING = "analytics_finding"
    MANUAL_OBSERVATION = "manual_observation"
    APPROVED_EXAMPLE = "approved_example"
    REJECTED_EXAMPLE = "rejected_example"


class CreatorSnapshotStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    RESTORED = "restored"

