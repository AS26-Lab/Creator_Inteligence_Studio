"""Valores y estados para Experiments and Verifiable Learning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExperimentDefinitionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class ExperimentType(str, Enum):
    SINGLE_VARIABLE_TEST = "single_variable_test"
    BEFORE_AFTER_OBSERVATION = "before_after_observation"
    COHORT_COMPARISON = "cohort_comparison"
    SEQUENTIAL_TEST = "sequential_test"
    MANUAL_OBSERVATION = "manual_observation"


class RecommendationType(str, Enum):
    CONTENT_STRUCTURE = "content_structure"
    HOOK = "hook"
    DURATION = "duration"
    PUBLICATION_TIMING = "publication_timing"
    TITLE_DIRECTION = "title_direction"
    THUMBNAIL_DIRECTION = "thumbnail_direction"
    COPY = "copy"
    CAPTION = "caption"
    TEXT_OVERLAY = "text_overlay"
    CLIP_SELECTION = "clip_selection"
    PLATFORM_ADAPTATION = "platform_adaptation"
    PACING = "pacing"
    CALL_TO_ACTION = "call_to_action"
    OTHER = "other"


class RecommendationDecision(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_CHANGES = "accepted_with_changes"
    REJECTED = "rejected"
    POSTPONED = "postponed"
    NOT_APPLICABLE = "not_applicable"
    NEEDS_MORE_DATA = "needs_more_data"


class ExecutionStatus(str, Enum):
    PLANNED = "planned"
    USED_AS_RECOMMENDED = "used_as_recommended"
    USED_WITH_CHANGES = "used_with_changes"
    NOT_USED = "not_used"
    UNKNOWN = "unknown"


class ExperimentEvaluationLifecycle(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExperimentOutcomeStatus(str, Enum):
    SUPPORTS_HYPOTHESIS = "supports_hypothesis"
    CONTRADICTS_HYPOTHESIS = "contradicts_hypothesis"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    INVALID_EXPERIMENT = "invalid_experiment"
    CONFOUNDED = "confounded"
    GUARDRAIL_FAILED = "guardrail_failed"
    NEEDS_MORE_DATA = "needs_more_data"


class ExperimentConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LearningType(str, Enum):
    OBSERVED_PATTERN = "observed_pattern"
    PROVISIONAL_LEARNING = "provisional_learning"
    CONFIRMED_LEARNING = "confirmed_learning"
    REJECTED_LEARNING = "rejected_learning"
    DEPRECATED_LEARNING = "deprecated_learning"
    NEEDS_MORE_DATA = "needs_more_data"


class LearningStatus(str, Enum):
    DRAFT = "draft"
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    NEEDS_MORE_DATA = "needs_more_data"


class LearningReviewDecision(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    NEEDS_MORE_DATA = "needs_more_data"
    DEPRECATE = "deprecate"
    EDIT_STATEMENT = "edit_statement"


@dataclass(frozen=True, slots=True)
class ExperimentLearningStrength:
    sample_size: int
    outcome_status: ExperimentOutcomeStatus
    confidence_level: ExperimentConfidenceLevel
    warnings: tuple[str, ...]

