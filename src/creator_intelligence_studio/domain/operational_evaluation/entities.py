"""Entidades para evaluacion operativa."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .value_objects import (
    OperationalEvaluationAssertionSeverity,
    OperationalEvaluationCacheStatus,
    OperationalEvaluationFinalResult,
    OperationalEvaluationRunStatus,
    OperationalEvaluationStageStatus,
)


@dataclass(frozen=True, slots=True)
class OperationalEvaluationScenarioDefinition:
    id: str
    version: str
    name: str
    description: str
    required_stage_names: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "required_stage_names": list(self.required_stage_names),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationRun:
    id: str
    scenario_id: str
    creator_id: str | None
    project_id: str | None
    video_asset_id: str | None
    status: OperationalEvaluationRunStatus
    scenario_version: str
    evaluator_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    started_at: datetime
    completed_at: datetime | None
    total_duration_seconds: float | None
    stage_count: int
    completed_stage_count: int
    failed_stage_count: int
    warning_count: int
    assertion_pass_count: int
    assertion_fail_count: int
    cache_hit_count: int
    cache_miss_count: int
    final_result: OperationalEvaluationFinalResult
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "video_asset_id": self.video_asset_id,
            "status": self.status.value,
            "scenario_version": self.scenario_version,
            "evaluator_version": self.evaluator_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_seconds": self.total_duration_seconds,
            "stage_count": self.stage_count,
            "completed_stage_count": self.completed_stage_count,
            "failed_stage_count": self.failed_stage_count,
            "warning_count": self.warning_count,
            "assertion_pass_count": self.assertion_pass_count,
            "assertion_fail_count": self.assertion_fail_count,
            "cache_hit_count": self.cache_hit_count,
            "cache_miss_count": self.cache_miss_count,
            "final_result": self.final_result.value,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationStage:
    id: str
    evaluation_run_id: str
    stage_index: int
    stage_name: str
    status: OperationalEvaluationStageStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    input_summary_json: dict[str, object]
    output_summary_json: dict[str, object]
    cache_status: OperationalEvaluationCacheStatus
    retry_count: int
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "evaluation_run_id": self.evaluation_run_id,
            "stage_index": self.stage_index,
            "stage_name": self.stage_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "input_summary_json": dict(self.input_summary_json),
            "output_summary_json": dict(self.output_summary_json),
            "cache_status": self.cache_status.value,
            "retry_count": self.retry_count,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationMetric:
    id: str
    evaluation_run_id: str
    stage_name: str | None
    metric_name: str
    metric_value: float | None
    metric_unit: str | None
    details_json: dict[str, object]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "evaluation_run_id": self.evaluation_run_id,
            "stage_name": self.stage_name,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "details_json": dict(self.details_json),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationAssertion:
    id: str
    evaluation_run_id: str
    stage_name: str | None
    assertion_name: str
    status: str
    expected_json: dict[str, object]
    actual_json: dict[str, object]
    severity: OperationalEvaluationAssertionSeverity
    message: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "evaluation_run_id": self.evaluation_run_id,
            "stage_name": self.stage_name,
            "assertion_name": self.assertion_name,
            "status": self.status,
            "expected_json": dict(self.expected_json),
            "actual_json": dict(self.actual_json),
            "severity": self.severity.value,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationArtifact:
    id: str
    evaluation_run_id: str
    stage_name: str
    artifact_type: str
    managed_path: str
    fingerprint: str
    size_bytes: int | None
    exists_at_completion: bool
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "evaluation_run_id": self.evaluation_run_id,
            "stage_name": self.stage_name,
            "artifact_type": self.artifact_type,
            "managed_path": self.managed_path,
            "fingerprint": self.fingerprint,
            "size_bytes": self.size_bytes,
            "exists_at_completion": self.exists_at_completion,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OperationalEvaluationReport:
    run: OperationalEvaluationRun
    scenario: OperationalEvaluationScenarioDefinition
    stages: tuple[OperationalEvaluationStage, ...] = ()
    metrics: tuple[OperationalEvaluationMetric, ...] = ()
    assertions: tuple[OperationalEvaluationAssertion, ...] = ()
    artifacts: tuple[OperationalEvaluationArtifact, ...] = ()
    resources_json: dict[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "scenario": self.scenario.to_dict(),
            "stages": [stage.to_dict() for stage in self.stages],
            "metrics": [metric.to_dict() for metric in self.metrics],
            "assertions": [assertion.to_dict() for assertion in self.assertions],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "resources_json": dict(self.resources_json),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
