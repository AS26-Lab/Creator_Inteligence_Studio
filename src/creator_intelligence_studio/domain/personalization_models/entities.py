"""Entidades persistidas de modelos personalizados por creador."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    PersonalizationModelFamily,
    PersonalizationModelRegistryStatus,
    PersonalizationModelTrainingStatus,
)


@dataclass(frozen=True, slots=True)
class PersonalizationTrainingRun:
    id: str
    creator_id: str
    project_id: str | None
    snapshot_id: str
    status: PersonalizationModelTrainingStatus
    model_family: PersonalizationModelFamily
    model_version: str
    trainer_version: str
    feature_schema_version: str
    label_schema_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    train_count: int
    validation_count: int
    test_count: int
    positive_count: int
    negative_count: int
    excluded_count: int
    random_seed: int
    decision_threshold: float
    artifact_path: str | None
    artifact_fingerprint: str | None
    started_at: datetime
    completed_at: datetime | None
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "snapshot_id": self.snapshot_id,
            "status": self.status.value,
            "model_family": self.model_family.value,
            "model_version": self.model_version,
            "trainer_version": self.trainer_version,
            "feature_schema_version": self.feature_schema_version,
            "label_schema_version": self.label_schema_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "excluded_count": self.excluded_count,
            "random_seed": self.random_seed,
            "decision_threshold": self.decision_threshold,
            "artifact_path": self.artifact_path,
            "artifact_fingerprint": self.artifact_fingerprint,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at) if self.completed_at else None,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PersonalizationModelMetric:
    id: str
    training_run_id: str
    split_name: str
    metric_name: str
    metric_value: float | None
    support: int | None
    details_json: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "training_run_id": self.training_run_id,
            "split_name": self.split_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "support": self.support,
            "details_json": dict(self.details_json),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PersonalizationModelPrediction:
    id: str
    training_run_id: str
    dataset_example_id: str
    split_name: str
    true_label: str | None
    predicted_label: str
    positive_score: float
    decision_threshold: float
    is_correct: bool | None
    explanation_json: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "training_run_id": self.training_run_id,
            "dataset_example_id": self.dataset_example_id,
            "split_name": self.split_name,
            "true_label": self.true_label,
            "predicted_label": self.predicted_label,
            "positive_score": self.positive_score,
            "decision_threshold": self.decision_threshold,
            "is_correct": self.is_correct,
            "explanation_json": dict(self.explanation_json),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PersonalizationModelRegistryEntry:
    id: str
    creator_id: str
    project_id: str | None
    training_run_id: str
    model_name: str
    status: PersonalizationModelRegistryStatus
    is_active: bool
    activated_at: datetime | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "training_run_id": self.training_run_id,
            "model_name": self.model_name,
            "status": self.status.value,
            "is_active": self.is_active,
            "activated_at": to_iso_z(self.activated_at) if self.activated_at else None,
            "retired_at": to_iso_z(self.retired_at) if self.retired_at else None,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PersonalizationModelComparison:
    id: str
    creator_id: str
    baseline_run_id: str
    candidate_run_id: str
    comparison_status: str
    primary_metric: str
    baseline_value: float | None
    candidate_value: float | None
    difference: float | None
    warnings_json: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "baseline_run_id": self.baseline_run_id,
            "candidate_run_id": self.candidate_run_id,
            "comparison_status": self.comparison_status,
            "primary_metric": self.primary_metric,
            "baseline_value": self.baseline_value,
            "candidate_value": self.candidate_value,
            "difference": self.difference,
            "warnings_json": dict(self.warnings_json),
            "created_at": to_iso_z(self.created_at),
        }
