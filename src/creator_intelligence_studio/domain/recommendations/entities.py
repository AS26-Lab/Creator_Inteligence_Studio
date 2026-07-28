"""Entidades del motor de recomendaciones."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from .alternative_types import AlternativeType
from .confidence_types import ConfidenceLevel
from .constraint_types import ConstraintType
from .evidence_types import EvidenceQuality, EvidenceStrength, EvidenceType, FactInferenceHypothesis
from .freshness_types import FreshnessStatus
from .lifecycle_types import RecommendationLifecycleStatus, RecommendationRunStatus
from .metric_types import MetricAvailabilityStatus, MetricRole
from .recommendation_types import FeedbackType, LifecycleStage, ObjectiveType, PriorityLevel, RecommendationType, ReviewDecision
from .risk_types import RiskSeverity, RiskType


def _to_dict(instance: object) -> dict[str, object]:
    payload = asdict(instance)
    for key, value in list(payload.items()):
        if hasattr(value, "value"):
            payload[key] = value.value
    return payload


@dataclass(frozen=True, slots=True)
class RecommendationContextSnapshot:
    id: str
    creator_id: str
    context_type: str
    context_version: str
    source_fingerprint: str
    context_json: str
    created_at: str
    creator_memory_snapshot_id: str | None = None
    creator_language_snapshot_id: str | None = None
    audience_snapshot_id: str | None = None
    analytics_snapshot_id: str | None = None
    market_snapshot_id: str | None = None
    platform_snapshot_id: str | None = None
    experiment_snapshot_id: str | None = None
    packaging_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationRequest:
    id: str
    creator_id: str
    request_type: str
    status: str
    requested_at: str
    created_at: str
    updated_at: str
    objective_type: ObjectiveType | None = None
    platform_scope_json: str = "[]"
    content_type_scope_json: str = "[]"
    market_id: str | None = None
    topic_id: str | None = None
    time_horizon: str | None = None
    constraints_json: str = "{}"
    preferences_json: str = "{}"

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationRun:
    id: str
    creator_id: str
    context_snapshot_id: str
    status: RecommendationRunStatus
    configuration_json: str
    candidate_count: int
    generated_count: int
    skipped_count: int
    warning_count: int
    error_count: int
    started_at: str
    created_at: str
    request_id: str | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationRunItem:
    id: str
    recommendation_run_id: str
    source_candidate_type: str
    action: str
    status: str
    created_at: str
    source_candidate_id: str | None = None
    warning_codes_json: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    id: str
    creator_id: str
    recommendation_run_id: str
    recommendation_type: RecommendationType
    objective_type: ObjectiveType
    title: str
    summary: str
    platform_scope_json: str
    content_type_scope_json: str
    audience_scope_json: str
    market_scope_json: str
    topic_scope_json: str
    status: RecommendationLifecycleStatus
    priority_level: PriorityLevel
    confidence_level: ConfidenceLevel
    freshness_status: FreshnessStatus
    creator_fit: float
    audience_fit: float
    historical_fit: float
    market_fit: float
    platform_fit: float
    strategic_fit: float
    authenticity_fit: float
    timing_fit: float
    differentiation_potential: float
    operational_feasibility: float
    expected_learning_value: float
    copying_risk: float
    overall_risk: float
    created_at: str
    updated_at: str
    source_opportunity_candidate_id: str | None = None
    priority_score: float | None = None
    confidence_score: float | None = None
    time_horizon: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationEvidence:
    id: str
    recommendation_candidate_id: str
    evidence_type: EvidenceType
    source_domain: str
    supports_recommendation: bool
    evidence_strength: EvidenceStrength
    evidence_quality: EvidenceQuality
    weight: float
    description: str
    created_at: str
    source_id: str | None = None
    source_snapshot_id: str | None = None
    fact_inference_hypothesis: FactInferenceHypothesis = FactInferenceHypothesis.INFERENCE
    limitations_json: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationContradiction:
    id: str
    recommendation_candidate_id: str
    contradiction_type: str
    severity: str
    description: str
    created_at: str
    source_id: str | None = None
    resolution_status: str = "open"

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationRisk:
    id: str
    recommendation_candidate_id: str
    risk_type: RiskType
    severity: RiskSeverity
    description: str
    blocking: bool
    created_at: str
    likelihood: float | None = None
    impact: float | None = None
    mitigation: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationConstraint:
    id: str
    recommendation_candidate_id: str
    constraint_type: ConstraintType
    source: str
    description: str
    satisfied: bool
    blocking: bool
    created_at: str
    resolution_action: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationAction:
    id: str
    recommendation_candidate_id: str
    sequence_order: int
    action_type: str
    title: str
    description: str
    required: bool
    created_at: str
    updated_at: str
    estimated_effort: str | None = None
    dependency_ids_json: str | None = None
    status: str = "proposed"

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationMetric:
    id: str
    recommendation_candidate_id: str
    metric_role: MetricRole
    platform: str
    metric_key: str
    availability_status: MetricAvailabilityStatus
    created_at: str
    internal_metric_key: str | None = None
    unit: str | None = None
    period_semantics: str | None = None
    target_direction: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    minimum_detectable_change: float | None = None
    measurement_window: str | None = None
    source_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationInvalidationCriterion:
    id: str
    recommendation_candidate_id: str
    criterion_type: str
    description: str
    severity: str
    created_at: str
    metric_key: str | None = None
    operator: str | None = None
    threshold_value: str | None = None
    evaluation_window: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationAlternative:
    id: str
    recommendation_candidate_id: str
    alternative_type: AlternativeType
    title: str
    summary: str
    reason: str
    platform_scope_json: str
    confidence_level: ConfidenceLevel
    created_at: str
    tradeoffs_json: str = "[]"

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationReview:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    decision: ReviewDecision
    previous_status: str
    new_status: str
    reason: str
    reviewed_at: str
    created_at: str
    reviewer: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationFeedback:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    feedback_type: FeedbackType
    created_at: str
    rating: int | None = None
    feedback_text: str | None = None
    reason_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationExperimentLink:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    experiment_id: str
    link_type: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationExecutionRecord:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    execution_status: str
    created_at: str
    updated_at: str
    internal_content_id: str | None = None
    platform: str | None = None
    publication_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationOutcomeSnapshot:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    source_fingerprint: str
    metrics_json: str
    interpretation_json: str
    created_at: str
    experiment_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationSnapshot:
    id: str
    creator_id: str
    recommendation_candidate_id: str
    snapshot_type: str
    source_fingerprint: str
    snapshot_json: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RecommendationReport:
    id: str
    creator_id: str
    report_type: str
    recommendation_scope_json: str
    source_fingerprint: str
    report_json: str
    created_at: str
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)
