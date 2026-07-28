"""Estados de ciclo de vida."""

from __future__ import annotations

from enum import Enum


class RecommendationLifecycleStatus(str, Enum):
    GENERATED = "generated"
    NEEDS_REVIEW = "needs_review"
    NEEDS_MORE_DATA = "needs_more_data"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    EXECUTED = "executed"
    MEASURING = "measuring"
    VALIDATED = "validated"
    PARTIALLY_VALIDATED = "partially_validated"
    INVALIDATED = "invalidated"
    INCONCLUSIVE = "inconclusive"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class RecommendationRunStatus(str, Enum):
    QUEUED = "queued"
    ASSEMBLING_CONTEXT = "assembling_context"
    VALIDATING_CONTEXT = "validating_context"
    GATHERING_CANDIDATES = "gathering_candidates"
    AGGREGATING_EVIDENCE = "aggregating_evidence"
    EVALUATING_CONSTRAINTS = "evaluating_constraints"
    DETECTING_CONTRADICTIONS = "detecting_contradictions"
    CALCULATING_FIT = "calculating_fit"
    CALCULATING_RISK = "calculating_risk"
    RANKING = "ranking"
    BUILDING_EXPLANATIONS = "building_explanations"
    SELECTING_METRICS = "selecting_metrics"
    BUILDING_ALTERNATIVES = "building_alternatives"
    SAVING = "saving"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    FAILED = "failed"
