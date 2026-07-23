"""Repositorio SQLite para datasets de personalizacion por creador."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.personalization_data.entities import (
    CreatorDatasetConflict,
    CreatorDatasetExample,
    CreatorDatasetQualityReport,
    CreatorDatasetSnapshot,
    CreatorFeatureSchema,
)
from creator_intelligence_studio.domain.personalization_data.repositories import PersonalizationDataRepository
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetStatus, PersonalizationLabel, PersonalizationReadinessStatus, PersonalizationSplitName
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z, utc_now


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _row_to_snapshot(row: sqlite3.Row) -> CreatorDatasetSnapshot:
    return CreatorDatasetSnapshot(
        id=row["id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        name=row["name"],
        status=PersonalizationDatasetStatus(row["status"]),
        dataset_version=row["dataset_version"],
        feature_schema_version=row["feature_schema_version"],
        label_schema_version=row["label_schema_version"],
        source_fingerprint=row["source_fingerprint"],
        configuration_fingerprint=row["configuration_fingerprint"],
        example_count=row["example_count"],
        positive_count=row["positive_count"],
        negative_count=row["negative_count"],
        neutral_count=row["neutral_count"],
        excluded_count=row["excluded_count"],
        conflict_count=row["conflict_count"],
        train_count=row["train_count"],
        validation_count=row["validation_count"],
        test_count=row["test_count"],
        readiness_status=PersonalizationReadinessStatus(row["readiness_status"]),
        readiness_score=row["readiness_score"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]) or utc_now(),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_example(row: sqlite3.Row) -> CreatorDatasetExample:
    return CreatorDatasetExample(
        id=row["id"],
        snapshot_id=row["snapshot_id"],
        creator_id=row["creator_id"],
        video_asset_id=row["video_asset_id"],
        ranking_run_id=row["ranking_run_id"],
        ranked_clip_candidate_id=row["ranked_clip_candidate_id"],
        multimodal_candidate_id=row["multimodal_candidate_id"],
        group_key=row["group_key"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        duration_seconds=row["duration_seconds"],
        label=PersonalizationLabel(row["label"]),
        label_source=tuple(_json_loads(row["label_source_json"], [])),
        label_confidence=row["label_confidence"],
        human_review_status=row["human_review_status"],
        human_rating=row["human_rating"],
        human_tags=tuple(_json_loads(row["human_tags_json"], [])),
        feature_vector=_json_loads(row["feature_vector_json"], {}),
        feature_schema_version=row["feature_schema_version"],
        quality_flags=_json_loads(row["quality_flags_json"], {}),
        exclusion_reason=row["exclusion_reason"],
        split_name=PersonalizationSplitName(row["split_name"]),
        sample_weight=row["sample_weight"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_conflict(row: sqlite3.Row) -> CreatorDatasetConflict:
    return CreatorDatasetConflict(
        id=row["id"],
        snapshot_id=row["snapshot_id"],
        creator_id=row["creator_id"],
        conflict_type=row["conflict_type"],
        candidate_a_id=row["candidate_a_id"],
        candidate_b_id=row["candidate_b_id"],
        description=row["description"],
        evidence_json=_json_loads(row["evidence_json"], {}),
        resolution_status=row["resolution_status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        resolved_at=from_iso_z(row["resolved_at"]),
    )


def _row_to_quality_report(row: sqlite3.Row) -> CreatorDatasetQualityReport:
    return CreatorDatasetQualityReport(
        id=row["id"],
        snapshot_id=row["snapshot_id"],
        report_version=row["report_version"],
        duplicate_ratio=row["duplicate_ratio"],
        overlap_ratio=row["overlap_ratio"],
        missing_feature_ratio=row["missing_feature_ratio"],
        class_balance_score=row["class_balance_score"],
        creator_coverage_score=row["creator_coverage_score"],
        temporal_coverage_score=row["temporal_coverage_score"],
        source_diversity_score=row["source_diversity_score"],
        label_consistency_score=row["label_consistency_score"],
        leakage_risk_score=row["leakage_risk_score"],
        readiness_score=row["readiness_score"],
        readiness_status=PersonalizationReadinessStatus(row["readiness_status"]),
        recommendations=tuple(_json_loads(row["recommendations_json"], [])),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_feature_schema(row: sqlite3.Row) -> CreatorFeatureSchema:
    return CreatorFeatureSchema(
        id=row["id"],
        schema_version=row["schema_version"],
        name=row["name"],
        description=row["description"],
        feature_names=tuple(_json_loads(row["feature_names_json"], [])),
        feature_definitions=_json_loads(row["feature_definitions_json"], {}),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLitePersonalizationRepository(PersonalizationDataRepository):
    """Repositorio SQLite para datasets de personalizacion."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def save_snapshot_bundle(
        self,
        snapshot: CreatorDatasetSnapshot,
        examples: list[CreatorDatasetExample],
        conflicts: list[CreatorDatasetConflict],
        quality_report: CreatorDatasetQualityReport,
        feature_schema: CreatorFeatureSchema,
    ) -> CreatorDatasetSnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_feature_schemas (
                    id, schema_version, name, description, feature_names_json,
                    feature_definitions_json, created_at
                ) VALUES (
                    :id, :schema_version, :name, :description, :feature_names_json,
                    :feature_definitions_json, :created_at
                )
                ON CONFLICT(schema_version) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    feature_names_json = excluded.feature_names_json,
                    feature_definitions_json = excluded.feature_definitions_json,
                    created_at = excluded.created_at
                """,
                {
                    **feature_schema.to_dict(),
                    "feature_names_json": json.dumps(list(feature_schema.feature_names), ensure_ascii=False, sort_keys=True),
                    "feature_definitions_json": json.dumps(feature_schema.feature_definitions, ensure_ascii=False, sort_keys=True, default=str),
                },
            )
            connection.execute(
                """
                INSERT INTO creator_dataset_snapshots (
                    id, creator_id, project_id, name, status, dataset_version,
                    feature_schema_version, label_schema_version, source_fingerprint,
                    configuration_fingerprint, example_count, positive_count, negative_count,
                    neutral_count, excluded_count, conflict_count, train_count, validation_count,
                    test_count, readiness_status, readiness_score, started_at, completed_at,
                    warning_code, warning_message, error_code, error_message, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :project_id, :name, :status, :dataset_version,
                    :feature_schema_version, :label_schema_version, :source_fingerprint,
                    :configuration_fingerprint, :example_count, :positive_count, :negative_count,
                    :neutral_count, :excluded_count, :conflict_count, :train_count, :validation_count,
                    :test_count, :readiness_status, :readiness_score, :started_at, :completed_at,
                    :warning_code, :warning_message, :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    dataset_version = excluded.dataset_version,
                    feature_schema_version = excluded.feature_schema_version,
                    label_schema_version = excluded.label_schema_version,
                    source_fingerprint = excluded.source_fingerprint,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    example_count = excluded.example_count,
                    positive_count = excluded.positive_count,
                    negative_count = excluded.negative_count,
                    neutral_count = excluded.neutral_count,
                    excluded_count = excluded.excluded_count,
                    conflict_count = excluded.conflict_count,
                    train_count = excluded.train_count,
                    validation_count = excluded.validation_count,
                    test_count = excluded.test_count,
                    readiness_status = excluded.readiness_status,
                    readiness_score = excluded.readiness_score,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                snapshot.to_dict(),
            )
            connection.execute("DELETE FROM creator_dataset_examples WHERE snapshot_id = ?", (snapshot.id,))
            connection.execute("DELETE FROM creator_dataset_conflicts WHERE snapshot_id = ?", (snapshot.id,))
            connection.execute("DELETE FROM creator_dataset_quality_reports WHERE snapshot_id = ?", (snapshot.id,))
            for example in sorted(examples, key=lambda item: (item.video_asset_id, item.start_seconds, item.end_seconds, item.id)):
                connection.execute(
                    """
                    INSERT INTO creator_dataset_examples (
                        id, snapshot_id, creator_id, video_asset_id, ranking_run_id,
                        ranked_clip_candidate_id, multimodal_candidate_id, group_key,
                        start_seconds, end_seconds, duration_seconds, label, label_source_json,
                        label_confidence, human_review_status, human_rating, human_tags_json,
                        feature_vector_json, feature_schema_version, quality_flags_json,
                        exclusion_reason, split_name, sample_weight, created_at
                    ) VALUES (
                        :id, :snapshot_id, :creator_id, :video_asset_id, :ranking_run_id,
                        :ranked_clip_candidate_id, :multimodal_candidate_id, :group_key,
                        :start_seconds, :end_seconds, :duration_seconds, :label, :label_source_json,
                        :label_confidence, :human_review_status, :human_rating, :human_tags_json,
                        :feature_vector_json, :feature_schema_version, :quality_flags_json,
                        :exclusion_reason, :split_name, :sample_weight, :created_at
                    )
                    """,
                    {
                        **example.to_dict(),
                        "label": example.label.value,
                        "label_source_json": json.dumps(list(example.label_source), ensure_ascii=False, sort_keys=True),
                        "human_tags_json": json.dumps(list(example.human_tags), ensure_ascii=False, sort_keys=True),
                        "feature_vector_json": json.dumps(example.feature_vector, ensure_ascii=False, sort_keys=True, default=str),
                        "quality_flags_json": json.dumps(example.quality_flags, ensure_ascii=False, sort_keys=True, default=str),
                        "split_name": example.split_name.value,
                    },
                )
            for conflict in sorted(conflicts, key=lambda item: (item.created_at, item.id)):
                connection.execute(
                    """
                    INSERT INTO creator_dataset_conflicts (
                        id, snapshot_id, creator_id, conflict_type, candidate_a_id,
                        candidate_b_id, description, evidence_json, resolution_status,
                        created_at, resolved_at
                    ) VALUES (
                        :id, :snapshot_id, :creator_id, :conflict_type, :candidate_a_id,
                        :candidate_b_id, :description, :evidence_json, :resolution_status,
                        :created_at, :resolved_at
                    )
                    """,
                    {
                        **conflict.to_dict(),
                        "evidence_json": json.dumps(conflict.evidence_json, ensure_ascii=False, sort_keys=True, default=str),
                    },
                )
            connection.execute(
                """
                INSERT INTO creator_dataset_quality_reports (
                    id, snapshot_id, report_version, duplicate_ratio, overlap_ratio,
                    missing_feature_ratio, class_balance_score, creator_coverage_score,
                    temporal_coverage_score, source_diversity_score, label_consistency_score,
                    leakage_risk_score, readiness_score, readiness_status, recommendations_json,
                    created_at
                ) VALUES (
                    :id, :snapshot_id, :report_version, :duplicate_ratio, :overlap_ratio,
                    :missing_feature_ratio, :class_balance_score, :creator_coverage_score,
                    :temporal_coverage_score, :source_diversity_score, :label_consistency_score,
                    :leakage_risk_score, :readiness_score, :readiness_status, :recommendations_json,
                    :created_at
                )
                ON CONFLICT(snapshot_id) DO UPDATE SET
                    report_version = excluded.report_version,
                    duplicate_ratio = excluded.duplicate_ratio,
                    overlap_ratio = excluded.overlap_ratio,
                    missing_feature_ratio = excluded.missing_feature_ratio,
                    class_balance_score = excluded.class_balance_score,
                    creator_coverage_score = excluded.creator_coverage_score,
                    temporal_coverage_score = excluded.temporal_coverage_score,
                    source_diversity_score = excluded.source_diversity_score,
                    label_consistency_score = excluded.label_consistency_score,
                    leakage_risk_score = excluded.leakage_risk_score,
                    readiness_score = excluded.readiness_score,
                    readiness_status = excluded.readiness_status,
                    recommendations_json = excluded.recommendations_json,
                    created_at = excluded.created_at
                """,
                {
                    **quality_report.to_dict(),
                    "recommendations_json": json.dumps(list(quality_report.recommendations), ensure_ascii=False, sort_keys=True),
                    "readiness_status": quality_report.readiness_status.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_dataset_snapshots WHERE id = ?", (snapshot.id,)).fetchone()
        if row is None:
            raise sqlite3.DatabaseError("No se pudo persistir el snapshot de personalizacion.")
        return _row_to_snapshot(row)

    def upsert_snapshot(self, snapshot: CreatorDatasetSnapshot) -> CreatorDatasetSnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_dataset_snapshots (
                    id, creator_id, project_id, name, status, dataset_version,
                    feature_schema_version, label_schema_version, source_fingerprint,
                    configuration_fingerprint, example_count, positive_count, negative_count,
                    neutral_count, excluded_count, conflict_count, train_count, validation_count,
                    test_count, readiness_status, readiness_score, started_at, completed_at,
                    warning_code, warning_message, error_code, error_message, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :project_id, :name, :status, :dataset_version,
                    :feature_schema_version, :label_schema_version, :source_fingerprint,
                    :configuration_fingerprint, :example_count, :positive_count, :negative_count,
                    :neutral_count, :excluded_count, :conflict_count, :train_count, :validation_count,
                    :test_count, :readiness_status, :readiness_score, :started_at, :completed_at,
                    :warning_code, :warning_message, :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    dataset_version = excluded.dataset_version,
                    feature_schema_version = excluded.feature_schema_version,
                    label_schema_version = excluded.label_schema_version,
                    source_fingerprint = excluded.source_fingerprint,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    example_count = excluded.example_count,
                    positive_count = excluded.positive_count,
                    negative_count = excluded.negative_count,
                    neutral_count = excluded.neutral_count,
                    excluded_count = excluded.excluded_count,
                    conflict_count = excluded.conflict_count,
                    train_count = excluded.train_count,
                    validation_count = excluded.validation_count,
                    test_count = excluded.test_count,
                    readiness_status = excluded.readiness_status,
                    readiness_score = excluded.readiness_score,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                snapshot.to_dict(),
            )
            row = connection.execute("SELECT * FROM creator_dataset_snapshots WHERE id = ?", (snapshot.id,)).fetchone()
        return _row_to_snapshot(row)

    def get_snapshot_by_id(self, snapshot_id: str) -> CreatorDatasetSnapshot | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_dataset_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return _row_to_snapshot(row) if row else None

    def get_latest_snapshot_by_creator_id(self, creator_id: str) -> CreatorDatasetSnapshot | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_dataset_snapshots WHERE creator_id = ? ORDER BY created_at DESC, updated_at DESC LIMIT 1",
                (creator_id,),
            ).fetchone()
        return _row_to_snapshot(row) if row else None

    def list_snapshots_by_creator_id(self, creator_id: str) -> list[CreatorDatasetSnapshot]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_dataset_snapshots WHERE creator_id = ? ORDER BY created_at DESC, updated_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def archive_snapshot(self, snapshot_id: str) -> CreatorDatasetSnapshot | None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE creator_dataset_snapshots
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (PersonalizationDatasetStatus.ARCHIVED.value, to_iso_z(utc_now()), snapshot_id),
            )
            row = connection.execute("SELECT * FROM creator_dataset_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return _row_to_snapshot(row) if row else None

    def upsert_examples(self, snapshot_id: str, examples: list[CreatorDatasetExample]) -> list[CreatorDatasetExample]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM creator_dataset_examples WHERE snapshot_id = ?", (snapshot_id,))
            for example in examples:
                connection.execute(
                    """
                    INSERT INTO creator_dataset_examples (
                        id, snapshot_id, creator_id, video_asset_id, ranking_run_id,
                        ranked_clip_candidate_id, multimodal_candidate_id, group_key,
                        start_seconds, end_seconds, duration_seconds, label, label_source_json,
                        label_confidence, human_review_status, human_rating, human_tags_json,
                        feature_vector_json, feature_schema_version, quality_flags_json,
                        exclusion_reason, split_name, sample_weight, created_at
                    ) VALUES (
                        :id, :snapshot_id, :creator_id, :video_asset_id, :ranking_run_id,
                        :ranked_clip_candidate_id, :multimodal_candidate_id, :group_key,
                        :start_seconds, :end_seconds, :duration_seconds, :label, :label_source_json,
                        :label_confidence, :human_review_status, :human_rating, :human_tags_json,
                        :feature_vector_json, :feature_schema_version, :quality_flags_json,
                        :exclusion_reason, :split_name, :sample_weight, :created_at
                    )
                    """,
                    {
                        **example.to_dict(),
                        "label": example.label.value,
                        "label_source_json": json.dumps(list(example.label_source), ensure_ascii=False, sort_keys=True),
                        "human_tags_json": json.dumps(list(example.human_tags), ensure_ascii=False, sort_keys=True),
                        "feature_vector_json": json.dumps(example.feature_vector, ensure_ascii=False, sort_keys=True, default=str),
                        "quality_flags_json": json.dumps(example.quality_flags, ensure_ascii=False, sort_keys=True, default=str),
                        "split_name": example.split_name.value,
                    },
                )
            rows = connection.execute(
                "SELECT * FROM creator_dataset_examples WHERE snapshot_id = ? ORDER BY video_asset_id ASC, start_seconds ASC, id ASC",
                (snapshot_id,),
            ).fetchall()
        return [_row_to_example(row) for row in rows]

    def list_examples_by_snapshot_id(self, snapshot_id: str) -> list[CreatorDatasetExample]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_dataset_examples WHERE snapshot_id = ? ORDER BY video_asset_id ASC, start_seconds ASC, id ASC",
                (snapshot_id,),
            ).fetchall()
        return [_row_to_example(row) for row in rows]

    def get_example_by_id(self, example_id: str) -> CreatorDatasetExample | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_dataset_examples WHERE id = ?", (example_id,)).fetchone()
        return _row_to_example(row) if row else None

    def upsert_conflicts(self, snapshot_id: str, conflicts: list[CreatorDatasetConflict]) -> list[CreatorDatasetConflict]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM creator_dataset_conflicts WHERE snapshot_id = ?", (snapshot_id,))
            for conflict in conflicts:
                connection.execute(
                    """
                    INSERT INTO creator_dataset_conflicts (
                        id, snapshot_id, creator_id, conflict_type, candidate_a_id,
                        candidate_b_id, description, evidence_json, resolution_status,
                        created_at, resolved_at
                    ) VALUES (
                        :id, :snapshot_id, :creator_id, :conflict_type, :candidate_a_id,
                        :candidate_b_id, :description, :evidence_json, :resolution_status,
                        :created_at, :resolved_at
                    )
                    """,
                    {
                        **conflict.to_dict(),
                        "evidence_json": json.dumps(conflict.evidence_json, ensure_ascii=False, sort_keys=True, default=str),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM creator_dataset_conflicts WHERE snapshot_id = ? ORDER BY created_at ASC, id ASC",
                (snapshot_id,),
            ).fetchall()
        return [_row_to_conflict(row) for row in rows]

    def list_conflicts_by_snapshot_id(self, snapshot_id: str) -> list[CreatorDatasetConflict]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_dataset_conflicts WHERE snapshot_id = ? ORDER BY created_at ASC, id ASC",
                (snapshot_id,),
            ).fetchall()
        return [_row_to_conflict(row) for row in rows]

    def upsert_quality_report(self, report: CreatorDatasetQualityReport) -> CreatorDatasetQualityReport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_dataset_quality_reports (
                    id, snapshot_id, report_version, duplicate_ratio, overlap_ratio,
                    missing_feature_ratio, class_balance_score, creator_coverage_score,
                    temporal_coverage_score, source_diversity_score, label_consistency_score,
                    leakage_risk_score, readiness_score, readiness_status, recommendations_json,
                    created_at
                ) VALUES (
                    :id, :snapshot_id, :report_version, :duplicate_ratio, :overlap_ratio,
                    :missing_feature_ratio, :class_balance_score, :creator_coverage_score,
                    :temporal_coverage_score, :source_diversity_score, :label_consistency_score,
                    :leakage_risk_score, :readiness_score, :readiness_status, :recommendations_json,
                    :created_at
                )
                ON CONFLICT(snapshot_id) DO UPDATE SET
                    report_version = excluded.report_version,
                    duplicate_ratio = excluded.duplicate_ratio,
                    overlap_ratio = excluded.overlap_ratio,
                    missing_feature_ratio = excluded.missing_feature_ratio,
                    class_balance_score = excluded.class_balance_score,
                    creator_coverage_score = excluded.creator_coverage_score,
                    temporal_coverage_score = excluded.temporal_coverage_score,
                    source_diversity_score = excluded.source_diversity_score,
                    label_consistency_score = excluded.label_consistency_score,
                    leakage_risk_score = excluded.leakage_risk_score,
                    readiness_score = excluded.readiness_score,
                    readiness_status = excluded.readiness_status,
                    recommendations_json = excluded.recommendations_json,
                    created_at = excluded.created_at
                """,
                {
                    **report.to_dict(),
                    "readiness_status": report.readiness_status.value,
                    "recommendations_json": json.dumps(list(report.recommendations), ensure_ascii=False, sort_keys=True),
                },
            )
            row = connection.execute("SELECT * FROM creator_dataset_quality_reports WHERE snapshot_id = ?", (report.snapshot_id,)).fetchone()
        return _row_to_quality_report(row)

    def get_quality_report_by_snapshot_id(self, snapshot_id: str) -> CreatorDatasetQualityReport | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_dataset_quality_reports WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
        return _row_to_quality_report(row) if row else None

    def upsert_feature_schema(self, schema: CreatorFeatureSchema) -> CreatorFeatureSchema:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_feature_schemas (
                    id, schema_version, name, description, feature_names_json,
                    feature_definitions_json, created_at
                ) VALUES (
                    :id, :schema_version, :name, :description, :feature_names_json,
                    :feature_definitions_json, :created_at
                )
                ON CONFLICT(schema_version) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    feature_names_json = excluded.feature_names_json,
                    feature_definitions_json = excluded.feature_definitions_json,
                    created_at = excluded.created_at
                """,
                {
                    **schema.to_dict(),
                    "feature_names_json": json.dumps(list(schema.feature_names), ensure_ascii=False, sort_keys=True),
                    "feature_definitions_json": json.dumps(schema.feature_definitions, ensure_ascii=False, sort_keys=True, default=str),
                },
            )
            row = connection.execute("SELECT * FROM creator_feature_schemas WHERE schema_version = ?", (schema.schema_version,)).fetchone()
        return _row_to_feature_schema(row)

    def get_feature_schema(self, schema_version: str) -> CreatorFeatureSchema | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_feature_schemas WHERE schema_version = ?", (schema_version,)).fetchone()
        return _row_to_feature_schema(row) if row else None

    def list_feature_schemas(self) -> list[CreatorFeatureSchema]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_feature_schemas ORDER BY schema_version ASC").fetchall()
        return [_row_to_feature_schema(row) for row in rows]
