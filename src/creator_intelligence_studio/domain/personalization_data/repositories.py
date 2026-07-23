"""Contratos de persistencia para personalizacion de datos."""

from __future__ import annotations

from typing import Protocol

from .entities import (
    CreatorDatasetConflict,
    CreatorDatasetExample,
    CreatorDatasetQualityReport,
    CreatorDatasetSnapshot,
    CreatorFeatureSchema,
)


class PersonalizationDataRepository(Protocol):
    """Repositorio de datasets de personalizacion."""

    def save_snapshot_bundle(
        self,
        snapshot: CreatorDatasetSnapshot,
        examples: list[CreatorDatasetExample],
        conflicts: list[CreatorDatasetConflict],
        quality_report: CreatorDatasetQualityReport,
        feature_schema: CreatorFeatureSchema,
    ) -> CreatorDatasetSnapshot:
        ...

    def upsert_snapshot(self, snapshot: CreatorDatasetSnapshot) -> CreatorDatasetSnapshot:
        ...

    def get_snapshot_by_id(self, snapshot_id: str) -> CreatorDatasetSnapshot | None:
        ...

    def get_latest_snapshot_by_creator_id(self, creator_id: str) -> CreatorDatasetSnapshot | None:
        ...

    def list_snapshots_by_creator_id(self, creator_id: str) -> list[CreatorDatasetSnapshot]:
        ...

    def archive_snapshot(self, snapshot_id: str) -> CreatorDatasetSnapshot | None:
        ...

    def upsert_examples(self, snapshot_id: str, examples: list[CreatorDatasetExample]) -> list[CreatorDatasetExample]:
        ...

    def list_examples_by_snapshot_id(self, snapshot_id: str) -> list[CreatorDatasetExample]:
        ...

    def get_example_by_id(self, example_id: str) -> CreatorDatasetExample | None:
        ...

    def upsert_conflicts(self, snapshot_id: str, conflicts: list[CreatorDatasetConflict]) -> list[CreatorDatasetConflict]:
        ...

    def list_conflicts_by_snapshot_id(self, snapshot_id: str) -> list[CreatorDatasetConflict]:
        ...

    def upsert_quality_report(self, report: CreatorDatasetQualityReport) -> CreatorDatasetQualityReport:
        ...

    def get_quality_report_by_snapshot_id(self, snapshot_id: str) -> CreatorDatasetQualityReport | None:
        ...

    def upsert_feature_schema(self, schema: CreatorFeatureSchema) -> CreatorFeatureSchema:
        ...

    def get_feature_schema(self, schema_version: str) -> CreatorFeatureSchema | None:
        ...

    def list_feature_schemas(self) -> list[CreatorFeatureSchema]:
        ...
