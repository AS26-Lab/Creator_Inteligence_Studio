"""Contratos de persistencia para evaluacion operativa."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    OperationalEvaluationArtifact,
    OperationalEvaluationAssertion,
    OperationalEvaluationMetric,
    OperationalEvaluationReport,
    OperationalEvaluationRun,
    OperationalEvaluationScenarioDefinition,
    OperationalEvaluationStage,
)


class OperationalEvaluationRepository(ABC):
    @abstractmethod
    def upsert_run(self, run: OperationalEvaluationRun) -> OperationalEvaluationRun:
        raise NotImplementedError

    @abstractmethod
    def get_run_by_id(self, run_id: str) -> OperationalEvaluationRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_runs(self, scenario_id: str | None = None) -> list[OperationalEvaluationRun]:
        raise NotImplementedError

    @abstractmethod
    def upsert_stages(self, run_id: str, stages: list[OperationalEvaluationStage]) -> list[OperationalEvaluationStage]:
        raise NotImplementedError

    @abstractmethod
    def list_stages(self, run_id: str) -> list[OperationalEvaluationStage]:
        raise NotImplementedError

    @abstractmethod
    def upsert_metrics(self, run_id: str, metrics: list[OperationalEvaluationMetric]) -> list[OperationalEvaluationMetric]:
        raise NotImplementedError

    @abstractmethod
    def list_metrics(self, run_id: str) -> list[OperationalEvaluationMetric]:
        raise NotImplementedError

    @abstractmethod
    def upsert_assertions(self, run_id: str, assertions: list[OperationalEvaluationAssertion]) -> list[OperationalEvaluationAssertion]:
        raise NotImplementedError

    @abstractmethod
    def list_assertions(self, run_id: str) -> list[OperationalEvaluationAssertion]:
        raise NotImplementedError

    @abstractmethod
    def upsert_artifacts(self, run_id: str, artifacts: list[OperationalEvaluationArtifact]) -> list[OperationalEvaluationArtifact]:
        raise NotImplementedError

    @abstractmethod
    def list_artifacts(self, run_id: str) -> list[OperationalEvaluationArtifact]:
        raise NotImplementedError

    @abstractmethod
    def list_scenarios(self) -> list[OperationalEvaluationScenarioDefinition]:
        raise NotImplementedError

    @abstractmethod
    def upsert_scenario(self, scenario: OperationalEvaluationScenarioDefinition) -> OperationalEvaluationScenarioDefinition:
        raise NotImplementedError

    @abstractmethod
    def delete_run(self, run_id: str) -> bool:
        raise NotImplementedError
