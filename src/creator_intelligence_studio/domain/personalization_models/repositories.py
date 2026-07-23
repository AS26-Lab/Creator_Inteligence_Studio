"""Contratos de persistencia para modelos personalizados."""

from __future__ import annotations

from typing import Protocol

from .entities import (
    PersonalizationModelComparison,
    PersonalizationModelMetric,
    PersonalizationModelPrediction,
    PersonalizationModelRegistryEntry,
    PersonalizationTrainingRun,
)


class PersonalizationModelRepository(Protocol):
    def upsert_training_run(self, run: PersonalizationTrainingRun) -> PersonalizationTrainingRun:
        ...

    def get_training_run_by_id(self, training_run_id: str) -> PersonalizationTrainingRun | None:
        ...

    def list_training_runs_by_creator_id(self, creator_id: str) -> list[PersonalizationTrainingRun]:
        ...

    def upsert_metrics(self, training_run_id: str, metrics: list[PersonalizationModelMetric]) -> list[PersonalizationModelMetric]:
        ...

    def list_metrics_by_run_id(self, training_run_id: str) -> list[PersonalizationModelMetric]:
        ...

    def upsert_predictions(self, training_run_id: str, predictions: list[PersonalizationModelPrediction]) -> list[PersonalizationModelPrediction]:
        ...

    def list_predictions_by_run_id(self, training_run_id: str) -> list[PersonalizationModelPrediction]:
        ...

    def upsert_registry_entry(self, entry: PersonalizationModelRegistryEntry) -> PersonalizationModelRegistryEntry:
        ...

    def get_active_registry_entry(self, creator_id: str, project_id: str | None = None) -> PersonalizationModelRegistryEntry | None:
        ...

    def get_registry_entry_by_training_run_id(self, training_run_id: str) -> PersonalizationModelRegistryEntry | None:
        ...

    def list_registry_entries_by_creator_id(self, creator_id: str) -> list[PersonalizationModelRegistryEntry]:
        ...

    def upsert_comparison(self, comparison: PersonalizationModelComparison) -> PersonalizationModelComparison:
        ...

    def list_comparisons_by_creator_id(self, creator_id: str) -> list[PersonalizationModelComparison]:
        ...
