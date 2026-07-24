"""Contratos de persistencia para Experiments and Verifiable Learning."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    ExecutionRecord,
    ExperimentAssignment,
    ExperimentDefinition,
    ExperimentEvaluation,
    ExperimentOutcome,
    ExperimentReport,
    ExperimentVariable,
    ExperimentGuardrail,
    LearningRecord,
    LearningReview,
    RecommendationDecisionRecord,
    RecommendationRecord,
)


class ExperimentRepository(ABC):
    @abstractmethod
    def upsert_experiment(self, experiment: ExperimentDefinition) -> ExperimentDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_experiment_by_id(self, experiment_id: str) -> ExperimentDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def get_experiment_by_name(self, creator_id: str, name: str) -> ExperimentDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_experiments(self, creator_id: str) -> list[ExperimentDefinition]:
        raise NotImplementedError

    @abstractmethod
    def upsert_variable(self, variable: ExperimentVariable) -> ExperimentVariable:
        raise NotImplementedError

    @abstractmethod
    def list_variables(self, experiment_id: str) -> list[ExperimentVariable]:
        raise NotImplementedError

    @abstractmethod
    def upsert_guardrail(self, guardrail: ExperimentGuardrail) -> ExperimentGuardrail:
        raise NotImplementedError

    @abstractmethod
    def list_guardrails(self, experiment_id: str) -> list[ExperimentGuardrail]:
        raise NotImplementedError

    @abstractmethod
    def upsert_assignment(self, assignment: ExperimentAssignment) -> ExperimentAssignment:
        raise NotImplementedError

    @abstractmethod
    def list_assignments(self, experiment_id: str) -> list[ExperimentAssignment]:
        raise NotImplementedError

    @abstractmethod
    def upsert_recommendation(self, recommendation: RecommendationRecord) -> RecommendationRecord:
        raise NotImplementedError

    @abstractmethod
    def get_recommendation_by_id(self, recommendation_id: str) -> RecommendationRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_recommendations(self, creator_id: str) -> list[RecommendationRecord]:
        raise NotImplementedError

    @abstractmethod
    def upsert_recommendation_decision(self, decision: RecommendationDecisionRecord) -> RecommendationDecisionRecord:
        raise NotImplementedError

    @abstractmethod
    def list_recommendation_decisions(self, recommendation_id: str) -> list[RecommendationDecisionRecord]:
        raise NotImplementedError

    @abstractmethod
    def upsert_execution(self, execution: ExecutionRecord) -> ExecutionRecord:
        raise NotImplementedError

    @abstractmethod
    def list_executions(self, creator_id: str) -> list[ExecutionRecord]:
        raise NotImplementedError

    @abstractmethod
    def upsert_evaluation(self, evaluation: ExperimentEvaluation) -> ExperimentEvaluation:
        raise NotImplementedError

    @abstractmethod
    def get_evaluation_by_id(self, evaluation_id: str) -> ExperimentEvaluation | None:
        raise NotImplementedError

    @abstractmethod
    def get_evaluation_by_fingerprint(self, source_fingerprint: str, experiment_id: str) -> ExperimentEvaluation | None:
        raise NotImplementedError

    @abstractmethod
    def list_evaluations(self, experiment_id: str) -> list[ExperimentEvaluation]:
        raise NotImplementedError

    @abstractmethod
    def upsert_outcomes(self, evaluation_id: str, outcomes: list[ExperimentOutcome]) -> list[ExperimentOutcome]:
        raise NotImplementedError

    @abstractmethod
    def list_outcomes(self, evaluation_id: str) -> list[ExperimentOutcome]:
        raise NotImplementedError

    @abstractmethod
    def upsert_learning(self, learning: LearningRecord) -> LearningRecord:
        raise NotImplementedError

    @abstractmethod
    def get_learning_by_id(self, learning_id: str) -> LearningRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_learnings(self, creator_id: str) -> list[LearningRecord]:
        raise NotImplementedError

    @abstractmethod
    def upsert_learning_review(self, review: LearningReview) -> LearningReview:
        raise NotImplementedError

    @abstractmethod
    def list_learning_reviews(self, learning_id: str) -> list[LearningReview]:
        raise NotImplementedError

    @abstractmethod
    def upsert_report(self, report: ExperimentReport) -> ExperimentReport:
        raise NotImplementedError

    @abstractmethod
    def get_report_by_id(self, report_id: str) -> ExperimentReport | None:
        raise NotImplementedError

    @abstractmethod
    def get_report_by_fingerprint(self, source_fingerprint: str, experiment_id: str | None = None) -> ExperimentReport | None:
        raise NotImplementedError

    @abstractmethod
    def list_reports(self, creator_id: str) -> list[ExperimentReport]:
        raise NotImplementedError

