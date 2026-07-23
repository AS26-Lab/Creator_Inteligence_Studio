"""Repositorio SQLite para modelos personalizados por creador."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.personalization_models.entities import (
    PersonalizationModelComparison,
    PersonalizationModelMetric,
    PersonalizationModelPrediction,
    PersonalizationModelRegistryEntry,
    PersonalizationTrainingRun,
)
from creator_intelligence_studio.domain.personalization_models.repositories import PersonalizationModelRepository
from creator_intelligence_studio.domain.personalization_models.value_objects import PersonalizationModelRegistryStatus, PersonalizationModelTrainingStatus, PersonalizationModelFamily
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


def _row_to_training_run(row: sqlite3.Row) -> PersonalizationTrainingRun:
    return PersonalizationTrainingRun(
        id=row["id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        snapshot_id=row["snapshot_id"],
        status=PersonalizationModelTrainingStatus(row["status"]),
        model_family=PersonalizationModelFamily(row["model_family"]),
        model_version=row["model_version"],
        trainer_version=row["trainer_version"],
        feature_schema_version=row["feature_schema_version"],
        label_schema_version=row["label_schema_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        train_count=row["train_count"],
        validation_count=row["validation_count"],
        test_count=row["test_count"],
        positive_count=row["positive_count"],
        negative_count=row["negative_count"],
        excluded_count=row["excluded_count"],
        random_seed=row["random_seed"],
        decision_threshold=row["decision_threshold"],
        artifact_path=row["artifact_path"],
        artifact_fingerprint=row["artifact_fingerprint"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_metric(row: sqlite3.Row) -> PersonalizationModelMetric:
    return PersonalizationModelMetric(
        id=row["id"],
        training_run_id=row["training_run_id"],
        split_name=row["split_name"],
        metric_name=row["metric_name"],
        metric_value=row["metric_value"],
        support=row["support"],
        details_json=_json_loads(row["details_json"], {}),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_prediction(row: sqlite3.Row) -> PersonalizationModelPrediction:
    return PersonalizationModelPrediction(
        id=row["id"],
        training_run_id=row["training_run_id"],
        dataset_example_id=row["dataset_example_id"],
        split_name=row["split_name"],
        true_label=row["true_label"],
        predicted_label=row["predicted_label"],
        positive_score=row["positive_score"],
        decision_threshold=row["decision_threshold"],
        is_correct=bool(row["is_correct"]) if row["is_correct"] is not None else None,
        explanation_json=_json_loads(row["explanation_json"], {}),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_registry(row: sqlite3.Row) -> PersonalizationModelRegistryEntry:
    return PersonalizationModelRegistryEntry(
        id=row["id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        training_run_id=row["training_run_id"],
        model_name=row["model_name"],
        status=PersonalizationModelRegistryStatus(row["status"]),
        is_active=bool(row["is_active"]),
        activated_at=from_iso_z(row["activated_at"]),
        retired_at=from_iso_z(row["retired_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_comparison(row: sqlite3.Row) -> PersonalizationModelComparison:
    return PersonalizationModelComparison(
        id=row["id"],
        creator_id=row["creator_id"],
        baseline_run_id=row["baseline_run_id"],
        candidate_run_id=row["candidate_run_id"],
        comparison_status=row["comparison_status"],
        primary_metric=row["primary_metric"],
        baseline_value=row["baseline_value"],
        candidate_value=row["candidate_value"],
        difference=row["difference"],
        warnings_json=_json_loads(row["warnings_json"], {}),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLitePersonalizationModelRepository(PersonalizationModelRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_training_run(self, run: PersonalizationTrainingRun) -> PersonalizationTrainingRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO personalization_training_runs (
                    id, creator_id, project_id, snapshot_id, status, model_family,
                    model_version, trainer_version, feature_schema_version, label_schema_version,
                    configuration_fingerprint, source_fingerprint, train_count, validation_count,
                    test_count, positive_count, negative_count, excluded_count, random_seed,
                    decision_threshold, artifact_path, artifact_fingerprint, started_at,
                    completed_at, warning_code, warning_message, error_code, error_message,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :project_id, :snapshot_id, :status, :model_family,
                    :model_version, :trainer_version, :feature_schema_version, :label_schema_version,
                    :configuration_fingerprint, :source_fingerprint, :train_count, :validation_count,
                    :test_count, :positive_count, :negative_count, :excluded_count, :random_seed,
                    :decision_threshold, :artifact_path, :artifact_fingerprint, :started_at,
                    :completed_at, :warning_code, :warning_message, :error_code, :error_message,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    model_version = excluded.model_version,
                    trainer_version = excluded.trainer_version,
                    feature_schema_version = excluded.feature_schema_version,
                    label_schema_version = excluded.label_schema_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_fingerprint = excluded.source_fingerprint,
                    train_count = excluded.train_count,
                    validation_count = excluded.validation_count,
                    test_count = excluded.test_count,
                    positive_count = excluded.positive_count,
                    negative_count = excluded.negative_count,
                    excluded_count = excluded.excluded_count,
                    random_seed = excluded.random_seed,
                    decision_threshold = excluded.decision_threshold,
                    artifact_path = excluded.artifact_path,
                    artifact_fingerprint = excluded.artifact_fingerprint,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                run.to_dict(),
            )
            row = connection.execute("SELECT * FROM personalization_training_runs WHERE id = ?", (run.id,)).fetchone()
        return _row_to_training_run(row)

    def get_training_run_by_id(self, training_run_id: str) -> PersonalizationTrainingRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM personalization_training_runs WHERE id = ?", (training_run_id,)).fetchone()
        return _row_to_training_run(row) if row else None

    def list_training_runs_by_creator_id(self, creator_id: str) -> list[PersonalizationTrainingRun]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM personalization_training_runs WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_training_run(row) for row in rows]

    def upsert_metrics(self, training_run_id: str, metrics: list[PersonalizationModelMetric]) -> list[PersonalizationModelMetric]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM personalization_model_metrics WHERE training_run_id = ?", (training_run_id,))
            for metric in metrics:
                connection.execute(
                    """
                    INSERT INTO personalization_model_metrics (
                        id, training_run_id, split_name, metric_name, metric_value, support,
                        details_json, created_at
                    ) VALUES (
                        :id, :training_run_id, :split_name, :metric_name, :metric_value, :support,
                        :details_json, :created_at
                    )
                    """,
                    metric.to_dict() | {"details_json": json.dumps(metric.details_json, ensure_ascii=False, sort_keys=True, default=str)},
                )
            rows = connection.execute("SELECT * FROM personalization_model_metrics WHERE training_run_id = ? ORDER BY split_name, metric_name", (training_run_id,)).fetchall()
        return [_row_to_metric(row) for row in rows]

    def list_metrics_by_run_id(self, training_run_id: str) -> list[PersonalizationModelMetric]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM personalization_model_metrics WHERE training_run_id = ? ORDER BY split_name, metric_name",
                (training_run_id,),
            ).fetchall()
        return [_row_to_metric(row) for row in rows]

    def upsert_predictions(self, training_run_id: str, predictions: list[PersonalizationModelPrediction]) -> list[PersonalizationModelPrediction]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM personalization_model_predictions WHERE training_run_id = ?", (training_run_id,))
            for prediction in predictions:
                connection.execute(
                    """
                    INSERT INTO personalization_model_predictions (
                        id, training_run_id, dataset_example_id, split_name, true_label,
                        predicted_label, positive_score, decision_threshold, is_correct,
                        explanation_json, created_at
                    ) VALUES (
                        :id, :training_run_id, :dataset_example_id, :split_name, :true_label,
                        :predicted_label, :positive_score, :decision_threshold, :is_correct,
                        :explanation_json, :created_at
                    )
                    """,
                    prediction.to_dict() | {"explanation_json": json.dumps(prediction.explanation_json, ensure_ascii=False, sort_keys=True, default=str)},
                )
            rows = connection.execute("SELECT * FROM personalization_model_predictions WHERE training_run_id = ? ORDER BY split_name, dataset_example_id", (training_run_id,)).fetchall()
        return [_row_to_prediction(row) for row in rows]

    def list_predictions_by_run_id(self, training_run_id: str) -> list[PersonalizationModelPrediction]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM personalization_model_predictions WHERE training_run_id = ? ORDER BY split_name, dataset_example_id",
                (training_run_id,),
            ).fetchall()
        return [_row_to_prediction(row) for row in rows]

    def upsert_registry_entry(self, entry: PersonalizationModelRegistryEntry) -> PersonalizationModelRegistryEntry:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO personalization_model_registry (
                    id, creator_id, project_id, training_run_id, model_name, status,
                    is_active, activated_at, retired_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :project_id, :training_run_id, :model_name, :status,
                    :is_active, :activated_at, :retired_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    is_active = excluded.is_active,
                    activated_at = excluded.activated_at,
                    retired_at = excluded.retired_at,
                    updated_at = excluded.updated_at
                """,
                entry.to_dict() | {"status": entry.status.value},
            )
            row = connection.execute("SELECT * FROM personalization_model_registry WHERE id = ?", (entry.id,)).fetchone()
        return _row_to_registry(row)

    def get_active_registry_entry(self, creator_id: str, project_id: str | None = None) -> PersonalizationModelRegistryEntry | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM personalization_model_registry
                WHERE creator_id = ? AND is_active = 1 AND (? IS NULL OR project_id IS ?)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (creator_id, project_id, project_id),
            ).fetchone()
        return _row_to_registry(row) if row else None

    def get_registry_entry_by_training_run_id(self, training_run_id: str) -> PersonalizationModelRegistryEntry | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM personalization_model_registry WHERE training_run_id = ? ORDER BY created_at DESC LIMIT 1",
                (training_run_id,),
            ).fetchone()
        return _row_to_registry(row) if row else None

    def list_registry_entries_by_creator_id(self, creator_id: str) -> list[PersonalizationModelRegistryEntry]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM personalization_model_registry WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_registry(row) for row in rows]

    def upsert_comparison(self, comparison: PersonalizationModelComparison) -> PersonalizationModelComparison:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO personalization_model_comparisons (
                    id, creator_id, baseline_run_id, candidate_run_id, comparison_status,
                    primary_metric, baseline_value, candidate_value, difference, warnings_json,
                    created_at
                ) VALUES (
                    :id, :creator_id, :baseline_run_id, :candidate_run_id, :comparison_status,
                    :primary_metric, :baseline_value, :candidate_value, :difference, :warnings_json,
                    :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    comparison_status = excluded.comparison_status,
                    primary_metric = excluded.primary_metric,
                    baseline_value = excluded.baseline_value,
                    candidate_value = excluded.candidate_value,
                    difference = excluded.difference,
                    warnings_json = excluded.warnings_json
                """,
                comparison.to_dict() | {"warnings_json": json.dumps(comparison.warnings_json, ensure_ascii=False, sort_keys=True, default=str)},
            )
            row = connection.execute("SELECT * FROM personalization_model_comparisons WHERE id = ?", (comparison.id,)).fetchone()
        return _row_to_comparison(row)

    def list_comparisons_by_creator_id(self, creator_id: str) -> list[PersonalizationModelComparison]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM personalization_model_comparisons WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_comparison(row) for row in rows]
