"""Entidades persistidas para Experiments and Verifiable Learning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    ExperimentConfidenceLevel,
    ExperimentDefinitionStatus,
    ExperimentEvaluationLifecycle,
    ExperimentOutcomeStatus,
    ExperimentType,
    ExecutionStatus,
    LearningReviewDecision,
    LearningStatus,
    LearningType,
    RecommendationDecision,
    RecommendationType,
)


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    id: str
    creator_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    platform: str | None
    content_type: str | None
    status: ExperimentDefinitionStatus
    hypothesis: str
    rationale: str
    primary_metric_key: str
    expected_direction: str
    minimum_sample_size: int
    start_date: str | None
    end_date: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "status": self.status.value,
            "hypothesis": self.hypothesis,
            "rationale": self.rationale,
            "primary_metric_key": self.primary_metric_key,
            "expected_direction": self.expected_direction,
            "minimum_sample_size": self.minimum_sample_size,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentVariable:
    id: str
    experiment_id: str
    variable_key: str
    variable_type: str
    description: str
    control_value_json: str
    treatment_value_json: str
    allowed_values_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "variable_key": self.variable_key,
            "variable_type": self.variable_type,
            "description": self.description,
            "control_value_json": self.control_value_json,
            "treatment_value_json": self.treatment_value_json,
            "allowed_values_json": self.allowed_values_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentGuardrail:
    id: str
    experiment_id: str
    metric_key: str
    comparison_operator: str
    threshold_value: float | None
    allowed_change: float | None
    description: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "metric_key": self.metric_key,
            "comparison_operator": self.comparison_operator,
            "threshold_value": self.threshold_value,
            "allowed_change": self.allowed_change,
            "description": self.description,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentAssignment:
    id: str
    experiment_id: str
    publication_id: str | None
    planned_variant: str
    actual_variant: str | None
    assignment_status: str
    assigned_at: datetime
    executed_at: datetime | None
    notes: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "publication_id": self.publication_id,
            "planned_variant": self.planned_variant,
            "actual_variant": self.actual_variant,
            "assignment_status": self.assignment_status,
            "assigned_at": to_iso_z(self.assigned_at),
            "executed_at": to_iso_z(self.executed_at),
            "notes": self.notes,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class RecommendationRecord:
    id: str
    creator_id: str
    source_type: str
    source_id: str | None
    recommendation_type: RecommendationType
    platform: str | None
    content_type: str | None
    title: str
    recommendation_text: str
    evidence_json: str
    confidence_level: ExperimentConfidenceLevel
    confidence_score: float | None
    status: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "recommendation_type": self.recommendation_type.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "title": self.title,
            "recommendation_text": self.recommendation_text,
            "evidence_json": self.evidence_json,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class RecommendationDecisionRecord:
    id: str
    recommendation_id: str
    decision: RecommendationDecision
    reason: str
    modified_value_json: str | None
    decided_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "modified_value_json": self.modified_value_json,
            "decided_at": to_iso_z(self.decided_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    id: str
    creator_id: str
    recommendation_id: str | None
    experiment_assignment_id: str | None
    publication_id: str | None
    execution_status: ExecutionStatus
    executed_value_json: str
    deviation_from_recommendation_json: str
    executed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "recommendation_id": self.recommendation_id,
            "experiment_assignment_id": self.experiment_assignment_id,
            "publication_id": self.publication_id,
            "execution_status": self.execution_status.value,
            "executed_value_json": self.executed_value_json,
            "deviation_from_recommendation_json": self.deviation_from_recommendation_json,
            "executed_at": to_iso_z(self.executed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentEvaluation:
    id: str
    experiment_id: str
    evaluation_status: ExperimentEvaluationLifecycle
    sample_size: int
    control_count: int
    treatment_count: int
    primary_metric_key: str
    control_result: float | None
    treatment_result: float | None
    absolute_difference: float | None
    relative_difference: float | None
    confidence_level: ExperimentConfidenceLevel
    uncertainty_json: str
    warnings_json: str
    evaluated_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "evaluation_status": self.evaluation_status.value,
            "sample_size": self.sample_size,
            "control_count": self.control_count,
            "treatment_count": self.treatment_count,
            "primary_metric_key": self.primary_metric_key,
            "control_result": self.control_result,
            "treatment_result": self.treatment_result,
            "absolute_difference": self.absolute_difference,
            "relative_difference": self.relative_difference,
            "confidence_level": self.confidence_level.value,
            "uncertainty_json": self.uncertainty_json,
            "warnings_json": self.warnings_json,
            "evaluated_at": to_iso_z(self.evaluated_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentOutcome:
    id: str
    evaluation_id: str
    publication_id: str
    assignment_id: str | None
    variant: str
    metric_key: str
    observed_value: float | None
    comparable_window: str
    quality_status: str
    warnings_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "evaluation_id": self.evaluation_id,
            "publication_id": self.publication_id,
            "assignment_id": self.assignment_id,
            "variant": self.variant,
            "metric_key": self.metric_key,
            "observed_value": self.observed_value,
            "comparable_window": self.comparable_window,
            "quality_status": self.quality_status,
            "warnings_json": self.warnings_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class LearningRecord:
    id: str
    creator_id: str
    source_type: str
    source_id: str
    learning_type: LearningType
    scope: str
    platform: str | None
    content_type: str | None
    topic: str | None
    statement: str
    evidence_json: str
    supporting_example_count: int
    contradicting_example_count: int
    confidence_level: ExperimentConfidenceLevel
    confidence_score: float | None
    status: LearningStatus
    first_observed_at: datetime
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "learning_type": self.learning_type.value,
            "scope": self.scope,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "statement": self.statement,
            "evidence_json": self.evidence_json,
            "supporting_example_count": self.supporting_example_count,
            "contradicting_example_count": self.contradicting_example_count,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "status": self.status.value,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_reviewed_at": to_iso_z(self.last_reviewed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class LearningReview:
    id: str
    learning_id: str
    decision: LearningReviewDecision
    reason: str
    reviewed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "learning_id": self.learning_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ExperimentReport:
    id: str
    experiment_id: str
    evaluation_id: str | None
    source_fingerprint: str
    configuration_json: str
    status: str
    title: str
    summary: str
    output_json_path: str | None
    output_txt_path: str | None
    output_csv_path: str | None
    created_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "evaluation_id": self.evaluation_id,
            "source_fingerprint": self.source_fingerprint,
            "configuration_json": self.configuration_json,
            "status": self.status,
            "title": self.title,
            "summary": self.summary,
            "output_json_path": self.output_json_path,
            "output_txt_path": self.output_txt_path,
            "output_csv_path": self.output_csv_path,
            "created_at": to_iso_z(self.created_at),
            "completed_at": to_iso_z(self.completed_at),
        }
