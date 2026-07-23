"""Repositorio SQLite para evaluacion operativa."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace

from creator_intelligence_studio.domain.operational_evaluation.entities import (
    OperationalEvaluationArtifact,
    OperationalEvaluationAssertion,
    OperationalEvaluationMetric,
    OperationalEvaluationReport,
    OperationalEvaluationRun,
    OperationalEvaluationScenarioDefinition,
    OperationalEvaluationStage,
)
from creator_intelligence_studio.domain.operational_evaluation.repositories import OperationalEvaluationRepository
from creator_intelligence_studio.domain.operational_evaluation.value_objects import (
    OperationalEvaluationAssertionSeverity,
    OperationalEvaluationCacheStatus,
    OperationalEvaluationFinalResult,
    OperationalEvaluationRunStatus,
    OperationalEvaluationStageStatus,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _row_to_run(row: sqlite3.Row) -> OperationalEvaluationRun:
    return OperationalEvaluationRun(
        id=row["id"],
        scenario_id=row["scenario_id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        video_asset_id=row["video_asset_id"],
        status=OperationalEvaluationRunStatus(row["status"]),
        scenario_version=row["scenario_version"],
        evaluator_version=row["evaluator_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        total_duration_seconds=row["total_duration_seconds"],
        stage_count=row["stage_count"],
        completed_stage_count=row["completed_stage_count"],
        failed_stage_count=row["failed_stage_count"],
        warning_count=row["warning_count"],
        assertion_pass_count=row["assertion_pass_count"],
        assertion_fail_count=row["assertion_fail_count"],
        cache_hit_count=row["cache_hit_count"],
        cache_miss_count=row["cache_miss_count"],
        final_result=OperationalEvaluationFinalResult(row["final_result"]),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_stage(row: sqlite3.Row) -> OperationalEvaluationStage:
    return OperationalEvaluationStage(
        id=row["id"],
        evaluation_run_id=row["evaluation_run_id"],
        stage_index=row["stage_index"],
        stage_name=row["stage_name"],
        status=OperationalEvaluationStageStatus(row["status"]),
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        duration_seconds=row["duration_seconds"],
        input_summary_json=_json_loads(row["input_summary_json"], {}),
        output_summary_json=_json_loads(row["output_summary_json"], {}),
        cache_status=OperationalEvaluationCacheStatus(row["cache_status"]),
        retry_count=row["retry_count"],
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric(row: sqlite3.Row) -> OperationalEvaluationMetric:
    return OperationalEvaluationMetric(
        id=row["id"],
        evaluation_run_id=row["evaluation_run_id"],
        stage_name=row["stage_name"],
        metric_name=row["metric_name"],
        metric_value=row["metric_value"],
        metric_unit=row["metric_unit"],
        details_json=_json_loads(row["details_json"], {}),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_assertion(row: sqlite3.Row) -> OperationalEvaluationAssertion:
    return OperationalEvaluationAssertion(
        id=row["id"],
        evaluation_run_id=row["evaluation_run_id"],
        stage_name=row["stage_name"],
        assertion_name=row["assertion_name"],
        status=row["status"],
        expected_json=_json_loads(row["expected_json"], {}),
        actual_json=_json_loads(row["actual_json"], {}),
        severity=OperationalEvaluationAssertionSeverity(row["severity"]),
        message=row["message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_artifact(row: sqlite3.Row) -> OperationalEvaluationArtifact:
    return OperationalEvaluationArtifact(
        id=row["id"],
        evaluation_run_id=row["evaluation_run_id"],
        stage_name=row["stage_name"],
        artifact_type=row["artifact_type"],
        managed_path=row["managed_path"],
        fingerprint=row["fingerprint"],
        size_bytes=row["size_bytes"],
        exists_at_completion=bool(row["exists_at_completion"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteOperationalEvaluationRepository(OperationalEvaluationRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_run(self, run: OperationalEvaluationRun) -> OperationalEvaluationRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO operational_evaluation_runs (
                    id, scenario_id, creator_id, project_id, video_asset_id, status,
                    scenario_version, evaluator_version, configuration_fingerprint,
                    source_fingerprint, started_at, completed_at, total_duration_seconds,
                    stage_count, completed_stage_count, failed_stage_count, warning_count,
                    assertion_pass_count, assertion_fail_count, cache_hit_count,
                    cache_miss_count, final_result, warning_code, warning_message,
                    error_code, error_message, created_at, updated_at
                ) VALUES (
                    :id, :scenario_id, :creator_id, :project_id, :video_asset_id, :status,
                    :scenario_version, :evaluator_version, :configuration_fingerprint,
                    :source_fingerprint, :started_at, :completed_at, :total_duration_seconds,
                    :stage_count, :completed_stage_count, :failed_stage_count, :warning_count,
                    :assertion_pass_count, :assertion_fail_count, :cache_hit_count,
                    :cache_miss_count, :final_result, :warning_code, :warning_message,
                    :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    completed_at = excluded.completed_at,
                    total_duration_seconds = excluded.total_duration_seconds,
                    stage_count = excluded.stage_count,
                    completed_stage_count = excluded.completed_stage_count,
                    failed_stage_count = excluded.failed_stage_count,
                    warning_count = excluded.warning_count,
                    assertion_pass_count = excluded.assertion_pass_count,
                    assertion_fail_count = excluded.assertion_fail_count,
                    cache_hit_count = excluded.cache_hit_count,
                    cache_miss_count = excluded.cache_miss_count,
                    final_result = excluded.final_result,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                {
                    **run.to_dict(),
                    "started_at": run.started_at.isoformat(),
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "created_at": run.created_at.isoformat(),
                    "updated_at": run.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM operational_evaluation_runs WHERE id = ?", (run.id,)).fetchone()
        return _row_to_run(row)

    def get_run_by_id(self, run_id: str) -> OperationalEvaluationRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM operational_evaluation_runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def list_runs(self, scenario_id: str | None = None) -> list[OperationalEvaluationRun]:
        with self._database.connect() as connection:
            if scenario_id is None:
                rows = connection.execute("SELECT * FROM operational_evaluation_runs ORDER BY created_at DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM operational_evaluation_runs WHERE scenario_id = ? ORDER BY created_at DESC",
                    (scenario_id,),
                ).fetchall()
        return [_row_to_run(row) for row in rows]

    def upsert_stages(self, run_id: str, stages: list[OperationalEvaluationStage]) -> list[OperationalEvaluationStage]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM operational_evaluation_stages WHERE evaluation_run_id = ?", (run_id,))
            for stage in stages:
                connection.execute(
                    """
                    INSERT INTO operational_evaluation_stages (
                        id, evaluation_run_id, stage_index, stage_name, status,
                        started_at, completed_at, duration_seconds, input_summary_json,
                        output_summary_json, cache_status, retry_count, warning_code,
                        warning_message, error_code, error_message, created_at
                    ) VALUES (
                        :id, :evaluation_run_id, :stage_index, :stage_name, :status,
                        :started_at, :completed_at, :duration_seconds, :input_summary_json,
                        :output_summary_json, :cache_status, :retry_count, :warning_code,
                        :warning_message, :error_code, :error_message, :created_at
                    )
                    """,
                    {
                        **stage.to_dict(),
                        "status": stage.status.value,
                        "cache_status": stage.cache_status.value,
                        "input_summary_json": _json_dumps(stage.input_summary_json),
                        "output_summary_json": _json_dumps(stage.output_summary_json),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_stages WHERE evaluation_run_id = ? ORDER BY stage_index ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_stage(row) for row in rows]

    def list_stages(self, run_id: str) -> list[OperationalEvaluationStage]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_stages WHERE evaluation_run_id = ? ORDER BY stage_index ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_stage(row) for row in rows]

    def upsert_metrics(self, run_id: str, metrics: list[OperationalEvaluationMetric]) -> list[OperationalEvaluationMetric]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM operational_evaluation_metrics WHERE evaluation_run_id = ?", (run_id,))
            for metric in metrics:
                connection.execute(
                    """
                    INSERT INTO operational_evaluation_metrics (
                        id, evaluation_run_id, stage_name, metric_name, metric_value,
                        metric_unit, details_json, created_at
                    ) VALUES (
                        :id, :evaluation_run_id, :stage_name, :metric_name, :metric_value,
                        :metric_unit, :details_json, :created_at
                    )
                    """,
                    {
                        **metric.to_dict(),
                        "details_json": _json_dumps(metric.details_json),
                        "created_at": metric.created_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_metrics WHERE evaluation_run_id = ? ORDER BY stage_name, metric_name",
                (run_id,),
            ).fetchall()
        return [_row_to_metric(row) for row in rows]

    def list_metrics(self, run_id: str) -> list[OperationalEvaluationMetric]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_metrics WHERE evaluation_run_id = ? ORDER BY stage_name, metric_name",
                (run_id,),
            ).fetchall()
        return [_row_to_metric(row) for row in rows]

    def upsert_assertions(self, run_id: str, assertions: list[OperationalEvaluationAssertion]) -> list[OperationalEvaluationAssertion]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM operational_evaluation_assertions WHERE evaluation_run_id = ?", (run_id,))
            for assertion in assertions:
                connection.execute(
                    """
                    INSERT INTO operational_evaluation_assertions (
                        id, evaluation_run_id, stage_name, assertion_name, status,
                        expected_json, actual_json, severity, message, created_at
                    ) VALUES (
                        :id, :evaluation_run_id, :stage_name, :assertion_name, :status,
                        :expected_json, :actual_json, :severity, :message, :created_at
                    )
                    """,
                    {
                        **assertion.to_dict(),
                        "severity": assertion.severity.value,
                        "expected_json": _json_dumps(assertion.expected_json),
                        "actual_json": _json_dumps(assertion.actual_json),
                        "created_at": assertion.created_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_assertions WHERE evaluation_run_id = ? ORDER BY created_at ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_assertion(row) for row in rows]

    def list_assertions(self, run_id: str) -> list[OperationalEvaluationAssertion]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_assertions WHERE evaluation_run_id = ? ORDER BY created_at ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_assertion(row) for row in rows]

    def upsert_artifacts(self, run_id: str, artifacts: list[OperationalEvaluationArtifact]) -> list[OperationalEvaluationArtifact]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM operational_evaluation_artifacts WHERE evaluation_run_id = ?", (run_id,))
            for artifact in artifacts:
                connection.execute(
                    """
                    INSERT INTO operational_evaluation_artifacts (
                        id, evaluation_run_id, stage_name, artifact_type, managed_path,
                        fingerprint, size_bytes, exists_at_completion, created_at
                    ) VALUES (
                        :id, :evaluation_run_id, :stage_name, :artifact_type, :managed_path,
                        :fingerprint, :size_bytes, :exists_at_completion, :created_at
                    )
                    """,
                    {
                        **artifact.to_dict(),
                        "exists_at_completion": int(artifact.exists_at_completion),
                        "created_at": artifact.created_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_artifacts WHERE evaluation_run_id = ? ORDER BY stage_name, artifact_type",
                (run_id,),
            ).fetchall()
        return [_row_to_artifact(row) for row in rows]

    def list_artifacts(self, run_id: str) -> list[OperationalEvaluationArtifact]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM operational_evaluation_artifacts WHERE evaluation_run_id = ? ORDER BY stage_name, artifact_type",
                (run_id,),
            ).fetchall()
        return [_row_to_artifact(row) for row in rows]

    def list_scenarios(self) -> list[OperationalEvaluationScenarioDefinition]:
        from creator_intelligence_studio.infrastructure.operational_evaluation.scenario_builder import list_operational_scenarios

        return list_operational_scenarios()

    def upsert_scenario(self, scenario: OperationalEvaluationScenarioDefinition) -> OperationalEvaluationScenarioDefinition:
        return scenario

    def delete_run(self, run_id: str) -> bool:
        with self._database.connect() as connection:
            deleted = connection.execute("DELETE FROM operational_evaluation_runs WHERE id = ?", (run_id,)).rowcount
        return bool(deleted)
