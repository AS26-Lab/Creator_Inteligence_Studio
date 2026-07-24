"""Comandos de aplicacion para Experiments and Verifiable Learning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListExperimentsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateExperimentCommand:
    creator_id: str
    name: str
    description: str
    experiment_type: str
    hypothesis: str
    rationale: str
    primary_metric_key: str
    expected_direction: str
    minimum_sample_size: int
    platform: str | None = None
    content_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass(frozen=True, slots=True)
class ShowExperimentCommand:
    experiment_id: str


@dataclass(frozen=True, slots=True)
class UpdateExperimentCommand:
    experiment_id: str


@dataclass(frozen=True, slots=True)
class ArchiveExperimentCommand:
    experiment_id: str


@dataclass(frozen=True, slots=True)
class AddExperimentVariableCommand:
    experiment_id: str
    variable_key: str
    variable_type: str
    description: str
    control_value_json: str
    treatment_value_json: str
    allowed_values_json: str


@dataclass(frozen=True, slots=True)
class AddExperimentGuardrailCommand:
    experiment_id: str
    metric_key: str
    comparison_operator: str
    description: str
    threshold_value: float | None = None
    allowed_change: float | None = None


@dataclass(frozen=True, slots=True)
class AssignExperimentCommand:
    experiment_id: str
    publication_id: str
    variant: str
    actual_variant: str | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class RecordExecutionCommand:
    creator_id: str
    recommendation_id: str | None
    experiment_assignment_id: str | None
    publication_id: str | None
    execution_status: str
    executed_value_json: str
    deviation_from_recommendation_json: str


@dataclass(frozen=True, slots=True)
class EvaluateExperimentCommand:
    experiment_id: str


@dataclass(frozen=True, slots=True)
class ShowExperimentEvaluationCommand:
    evaluation_id: str


@dataclass(frozen=True, slots=True)
class GenerateExperimentReportCommand:
    experiment_id: str
    evaluation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExportExperimentReportCommand:
    report_id: str
    format: str


@dataclass(frozen=True, slots=True)
class ListRecommendationsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateRecommendationCommand:
    creator_id: str
    source_type: str
    source_id: str | None
    recommendation_type: str
    title: str
    recommendation_text: str
    evidence_json: str
    confidence_level: str
    platform: str | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class ShowRecommendationCommand:
    recommendation_id: str


@dataclass(frozen=True, slots=True)
class DecideRecommendationCommand:
    recommendation_id: str
    decision: str
    reason: str
    modified_value_json: str | None = None


@dataclass(frozen=True, slots=True)
class ListLearningsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowLearningCommand:
    learning_id: str


@dataclass(frozen=True, slots=True)
class ReviewLearningCommand:
    learning_id: str


@dataclass(frozen=True, slots=True)
class ConfirmLearningCommand:
    learning_id: str


@dataclass(frozen=True, slots=True)
class RejectLearningCommand:
    learning_id: str


@dataclass(frozen=True, slots=True)
class NeedsMoreDataLearningCommand:
    learning_id: str


@dataclass(frozen=True, slots=True)
class DeprecateLearningCommand:
    learning_id: str
