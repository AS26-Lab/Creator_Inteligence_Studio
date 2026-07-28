"""Dominio de Opportunity and Recommendation Engine Foundation."""

from __future__ import annotations

from .alternative_types import AlternativeType
from .confidence_types import ConfidenceLevel
from .constraint_types import ConstraintType
from .evidence_types import EvidenceQuality, EvidenceStrength, EvidenceType, FactInferenceHypothesis
from .explanation_types import ExplanationType
from .freshness_types import FreshnessStatus
from .lifecycle_types import RecommendationLifecycleStatus, RecommendationRunStatus
from .metric_types import MetricAvailabilityStatus, MetricRole
from .recommendation_types import FeedbackType, LifecycleStage, ObjectiveType, PriorityLevel, RecommendationType, ReviewDecision
from .risk_types import RiskSeverity, RiskType
from .entities import (
    RecommendationAction,
    RecommendationAlternative,
    RecommendationCandidate,
    RecommendationConstraint,
    RecommendationContextSnapshot,
    RecommendationContradiction,
    RecommendationEvidence,
    RecommendationExperimentLink,
    RecommendationExecutionRecord,
    RecommendationFeedback,
    RecommendationInvalidationCriterion,
    RecommendationMetric,
    RecommendationOutcomeSnapshot,
    RecommendationRequest,
    RecommendationReview,
    RecommendationRun,
    RecommendationRunItem,
    RecommendationSnapshot,
    RecommendationReport,
    RecommendationRisk,
)

__all__ = [
    "AlternativeType",
    "ConfidenceLevel",
    "ConstraintType",
    "EvidenceQuality",
    "EvidenceStrength",
    "EvidenceType",
    "FactInferenceHypothesis",
    "ExplanationType",
    "FreshnessStatus",
    "RecommendationLifecycleStatus",
    "RecommendationRunStatus",
    "MetricAvailabilityStatus",
    "MetricRole",
    "FeedbackType",
    "LifecycleStage",
    "ObjectiveType",
    "PriorityLevel",
    "RecommendationType",
    "ReviewDecision",
    "RiskSeverity",
    "RiskType",
    "RecommendationAction",
    "RecommendationAlternative",
    "RecommendationCandidate",
    "RecommendationConstraint",
    "RecommendationContextSnapshot",
    "RecommendationContradiction",
    "RecommendationEvidence",
    "RecommendationExperimentLink",
    "RecommendationExecutionRecord",
    "RecommendationFeedback",
    "RecommendationInvalidationCriterion",
    "RecommendationMetric",
    "RecommendationOutcomeSnapshot",
    "RecommendationRequest",
    "RecommendationReview",
    "RecommendationRun",
    "RecommendationRunItem",
    "RecommendationSnapshot",
    "RecommendationReport",
    "RecommendationRisk",
]
