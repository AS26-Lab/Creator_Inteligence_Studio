"""Servicio central para Experiments and Verifiable Learning."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from statistics import mean
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService
from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricSnapshot, AnalyticsPublication
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.domain.experiments.entities import (
    ExecutionRecord,
    ExperimentAssignment,
    ExperimentDefinition,
    ExperimentEvaluation,
    ExperimentGuardrail,
    ExperimentOutcome,
    ExperimentReport,
    ExperimentVariable,
    LearningRecord,
    LearningReview,
    RecommendationDecisionRecord,
    RecommendationRecord,
)
from creator_intelligence_studio.domain.experiments.errors import ExperimentsNotFoundError, ExperimentsStateError, ExperimentsValidationError
from creator_intelligence_studio.domain.experiments.repositories import ExperimentRepository
from creator_intelligence_studio.domain.experiments.services import build_experiment_fingerprint
from creator_intelligence_studio.domain.experiments.value_objects import (
    ExperimentConfidenceLevel,
    ExperimentDefinitionStatus,
    ExperimentEvaluationLifecycle,
    ExperimentOutcomeStatus,
    ExperimentType,
    ExecutionStatus,
    LearningReviewDecision,
    LearningStatus,
    LearningType,
    RecommendationDecision,
    RecommendationType,
)
from creator_intelligence_studio.infrastructure.experiments.confidence_calculator import calculate_confidence_level
from creator_intelligence_studio.infrastructure.experiments.contradiction_detector import detect_contradictions
from creator_intelligence_studio.infrastructure.experiments.evaluator import compare_series, evaluate_guardrails
from creator_intelligence_studio.infrastructure.experiments.experiment_report_builder import build_report_payload, write_report
from creator_intelligence_studio.infrastructure.experiments.learning_generator import build_learning_payload
from creator_intelligence_studio.infrastructure.experiments.outcome_matcher import ComparableOutcome, select_comparable_snapshot
from creator_intelligence_studio.infrastructure.analytics_lab.percentile_calculator import calculate_percentile
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(payload: str | None) -> dict[str, object]:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _json_list(payload: str | None) -> list[dict[str, object]]:
    if not payload:
        return []
    try:
        value = json.loads(payload)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


class ExperimentService:
    def __init__(
        self,
        *,
        analytics_service: AnalyticsQueryService,
        analytics_lab_service: AnalyticsLabService,
        repository: ExperimentRepository,
        paths: ProjectPaths,
        logger: logging.Logger | None = None,
    ) -> None:
        self.analytics_service = analytics_service
        self.analytics_lab_service = analytics_lab_service
        self.repository = repository
        self.paths = paths
        self.logger = logger or logging.getLogger("creator_intelligence_studio.experiments")
        self._reports_root = self.paths.data_directory / "experiments" / "reports"

    def _publication_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        try:
            return self.analytics_service.list_publication_snapshots(publication_id)
        except Exception:
            return []

    def _publication(self, publication_id: str) -> AnalyticsPublication | None:
        try:
            return self.analytics_service.get_publication(publication_id)
        except Exception:
            return None

    def list_experiments(self, creator_id: str) -> list[ExperimentDefinition]:
        return self.repository.list_experiments(creator_id)

    def get_experiment(self, experiment_id: str) -> ExperimentDefinition | None:
        return self.repository.get_experiment_by_id(experiment_id)

    def create_experiment(
        self,
        *,
        creator_id: str,
        name: str,
        description: str,
        experiment_type: str,
        hypothesis: str,
        rationale: str,
        primary_metric_key: str,
        expected_direction: str,
        minimum_sample_size: int,
        platform: str | None = None,
        content_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ExperimentDefinition:
        experiment = ExperimentDefinition(
            id=str(uuid4()),
            creator_id=creator_id,
            name=name,
            description=description,
            experiment_type=ExperimentType(experiment_type),
            platform=platform,
            content_type=content_type,
            status=ExperimentDefinitionStatus.DRAFT,
            hypothesis=hypothesis,
            rationale=rationale,
            primary_metric_key=primary_metric_key,
            expected_direction=expected_direction,
            minimum_sample_size=minimum_sample_size,
            start_date=start_date,
            end_date=end_date,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_experiment(experiment)

    def update_experiment(self, experiment_id: str, **changes) -> ExperimentDefinition:
        experiment = self.repository.get_experiment_by_id(experiment_id)
        if experiment is None:
            raise ExperimentsNotFoundError("El experimento no existe.")
        updated = replace(
            experiment,
            name=changes.get("name", experiment.name),
            description=changes.get("description", experiment.description),
            experiment_type=ExperimentType(changes.get("experiment_type", experiment.experiment_type.value)),
            platform=changes.get("platform", experiment.platform),
            content_type=changes.get("content_type", experiment.content_type),
            status=ExperimentDefinitionStatus(changes.get("status", experiment.status.value)),
            hypothesis=changes.get("hypothesis", experiment.hypothesis),
            rationale=changes.get("rationale", experiment.rationale),
            primary_metric_key=changes.get("primary_metric_key", experiment.primary_metric_key),
            expected_direction=changes.get("expected_direction", experiment.expected_direction),
            minimum_sample_size=int(changes.get("minimum_sample_size", experiment.minimum_sample_size)),
            start_date=changes.get("start_date", experiment.start_date),
            end_date=changes.get("end_date", experiment.end_date),
            updated_at=utc_now(),
        )
        return self.repository.upsert_experiment(updated)

    def archive_experiment(self, experiment_id: str) -> ExperimentDefinition:
        experiment = self.repository.get_experiment_by_id(experiment_id)
        if experiment is None:
            raise ExperimentsNotFoundError("El experimento no existe.")
        return self.repository.upsert_experiment(replace(experiment, status=ExperimentDefinitionStatus.ARCHIVED, updated_at=utc_now()))

    def add_variable(
        self,
        *,
        experiment_id: str,
        variable_key: str,
        variable_type: str,
        description: str,
        control_value_json: str,
        treatment_value_json: str,
        allowed_values_json: str,
    ) -> ExperimentVariable:
        variable = ExperimentVariable(
            id=str(uuid4()),
            experiment_id=experiment_id,
            variable_key=variable_key,
            variable_type=variable_type,
            description=description,
            control_value_json=control_value_json,
            treatment_value_json=treatment_value_json,
            allowed_values_json=allowed_values_json,
            created_at=utc_now(),
        )
        return self.repository.upsert_variable(variable)

    def add_guardrail(
        self,
        *,
        experiment_id: str,
        metric_key: str,
        comparison_operator: str,
        threshold_value: float | None = None,
        allowed_change: float | None = None,
        description: str,
    ) -> ExperimentGuardrail:
        guardrail = ExperimentGuardrail(
            id=str(uuid4()),
            experiment_id=experiment_id,
            metric_key=metric_key,
            comparison_operator=comparison_operator,
            threshold_value=threshold_value,
            allowed_change=allowed_change,
            description=description,
            created_at=utc_now(),
        )
        return self.repository.upsert_guardrail(guardrail)

    def assign_publication(self, *, experiment_id: str, publication_id: str, variant: str, notes: str = "", actual_variant: str | None = None, assignment_status: str = "planned") -> ExperimentAssignment:
        assignment = ExperimentAssignment(
            id=str(uuid4()),
            experiment_id=experiment_id,
            publication_id=publication_id,
            planned_variant=variant,
            actual_variant=actual_variant,
            assignment_status=assignment_status,
            assigned_at=utc_now(),
            executed_at=utc_now() if actual_variant else None,
            notes=notes,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_assignment(assignment)

    def list_assignments(self, experiment_id: str) -> list[ExperimentAssignment]:
        return self.repository.list_assignments(experiment_id)

    def list_variables(self, experiment_id: str) -> list[ExperimentVariable]:
        return self.repository.list_variables(experiment_id)

    def list_guardrails(self, experiment_id: str) -> list[ExperimentGuardrail]:
        return self.repository.list_guardrails(experiment_id)

    def list_recommendations(self, creator_id: str) -> list[RecommendationRecord]:
        return self.repository.list_recommendations(creator_id)

    def list_recommendation_decisions(self, recommendation_id: str):
        return self.repository.list_recommendation_decisions(recommendation_id)

    def get_recommendation(self, recommendation_id: str) -> RecommendationRecord | None:
        return self.repository.get_recommendation_by_id(recommendation_id)

    def create_recommendation(
        self,
        *,
        creator_id: str,
        source_type: str,
        source_id: str | None,
        recommendation_type: str,
        title: str,
        recommendation_text: str,
        evidence_json: str,
        confidence_level: str = "medium",
        confidence_score: float | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        status: str = "draft",
    ) -> RecommendationRecord:
        recommendation = RecommendationRecord(
            id=str(uuid4()),
            creator_id=creator_id,
            source_type=source_type,
            source_id=source_id,
            recommendation_type=RecommendationType(recommendation_type),
            platform=platform,
            content_type=content_type,
            title=title,
            recommendation_text=recommendation_text,
            evidence_json=evidence_json,
            confidence_level=ExperimentConfidenceLevel(confidence_level),
            confidence_score=confidence_score,
            status=status,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_recommendation(recommendation)

    def decide_recommendation(
        self,
        recommendation_id: str,
        *,
        decision: str,
        reason: str,
        modified_value_json: str | None = None,
    ) -> RecommendationDecisionRecord:
        recommendation = self.repository.get_recommendation_by_id(recommendation_id)
        if recommendation is None:
            raise ExperimentsNotFoundError("La recomendacion no existe.")
        record = RecommendationDecisionRecord(
            id=str(uuid4()),
            recommendation_id=recommendation_id,
            decision=RecommendationDecision(decision),
            reason=reason,
            modified_value_json=modified_value_json,
            decided_at=utc_now(),
            created_at=utc_now(),
        )
        self.repository.upsert_recommendation_decision(record)
        updated = replace(recommendation, status=decision, updated_at=utc_now())
        self.repository.upsert_recommendation(updated)
        return record

    def list_executions(self, creator_id: str) -> list[ExecutionRecord]:
        return self.repository.list_executions(creator_id)

    def record_execution(
        self,
        *,
        creator_id: str,
        recommendation_id: str | None,
        experiment_assignment_id: str | None,
        publication_id: str | None,
        execution_status: str,
        executed_value_json: str,
        deviation_from_recommendation_json: str,
    ) -> ExecutionRecord:
        execution = ExecutionRecord(
            id=str(uuid4()),
            creator_id=creator_id,
            recommendation_id=recommendation_id,
            experiment_assignment_id=experiment_assignment_id,
            publication_id=publication_id,
            execution_status=ExecutionStatus(execution_status),
            executed_value_json=executed_value_json,
            deviation_from_recommendation_json=deviation_from_recommendation_json,
            executed_at=utc_now(),
            created_at=utc_now(),
        )
        if recommendation_id:
            recommendation = self.repository.get_recommendation_by_id(recommendation_id)
            if recommendation is not None:
                self.repository.upsert_recommendation(replace(recommendation, status="executed", updated_at=utc_now()))
        return self.repository.upsert_execution(execution)

    def _evaluation_fingerprint(self, *, experiment: ExperimentDefinition, assignments: list[ExperimentAssignment], configuration: dict[str, object], outcomes: list[ComparableOutcome]) -> str:
        payload = {
            "experiment": experiment.to_dict(),
            "assignments": [assignment.to_dict() for assignment in assignments],
            "configuration": configuration,
            "outcomes": [
                {
                    "publication_id": outcome.publication_id,
                    "metric_key": outcome.metric_key,
                    "observed_value": outcome.observed_value,
                    "window": outcome.comparable_window,
                }
                for outcome in outcomes
            ],
            "evaluator_version": "v1",
        }
        return build_experiment_fingerprint(payload)

    def _collect_outcomes(self, experiment: ExperimentDefinition, assignments: list[ExperimentAssignment]) -> tuple[list[ComparableOutcome], list[str]]:
        outcomes: list[ComparableOutcome] = []
        warnings: list[str] = []
        for assignment in assignments:
            if not assignment.publication_id:
                warnings.append("unlinked_publication")
                continue
            publication = self._publication(assignment.publication_id)
            if publication is None:
                warnings.append("unlinked_publication")
                continue
            snapshots = self._publication_snapshots(publication.id)
            comparable = select_comparable_snapshot(publication, snapshots, experiment.primary_metric_key)
            if comparable.observed_value is None:
                warnings.extend(comparable.warnings)
            outcomes.append(comparable)
        return outcomes, list(sorted(set(warnings)))

    def evaluate_experiment(self, experiment_id: str) -> ExperimentEvaluation:
        experiment = self.repository.get_experiment_by_id(experiment_id)
        if experiment is None:
            raise ExperimentsNotFoundError("El experimento no existe.")
        assignments = self.repository.list_assignments(experiment_id)
        variables = self.repository.list_variables(experiment_id)
        guardrails = self.repository.list_guardrails(experiment_id)
        outcomes, warnings = self._collect_outcomes(experiment, assignments)
        configuration = {
            "experiment": experiment.to_dict(),
            "variables": [variable.to_dict() for variable in variables],
            "guardrails": [guardrail.to_dict() for guardrail in guardrails],
            "assignment_ids": [assignment.id for assignment in assignments],
        }
        fingerprint = self._evaluation_fingerprint(
            experiment=experiment,
            assignments=assignments,
            configuration=configuration,
            outcomes=outcomes,
        )
        existing = self.repository.get_evaluation_by_fingerprint(fingerprint, experiment.id)
        if existing and existing.evaluation_status in {ExperimentEvaluationLifecycle.COMPLETED, ExperimentEvaluationLifecycle.COMPLETED_WITH_WARNINGS}:
            return existing
        variant_values: dict[str, list[float]] = {}
        variant_counts: dict[str, int] = {}
        comparable_count = 0
        outcome_rows: list[ExperimentOutcome] = []
        for assignment, outcome in zip(assignments, outcomes):
            variant = assignment.actual_variant or assignment.planned_variant
            if outcome.observed_value is None:
                continue
            variant_values.setdefault(variant, []).append(float(outcome.observed_value))
            variant_counts[variant] = variant_counts.get(variant, 0) + 1
            comparable_count += 1
            outcome_rows.append(
                ExperimentOutcome(
                    id=str(uuid4()),
                    evaluation_id="",  # filled after evaluation id exists
                    publication_id=outcome.publication_id,
                    assignment_id=assignment.id,
                    variant=variant,
                    metric_key=outcome.metric_key,
                    observed_value=outcome.observed_value,
                    comparable_window=outcome.comparable_window,
                    quality_status=outcome.quality_status,
                    warnings_json=_json_dumps(list(outcome.warnings)),
                    created_at=utc_now(),
                )
            )
        control_values = variant_values.get("control", [])
        treatment_values = variant_values.get("treatment", [])
        if not control_values and variant_values:
            control_values = next(iter(variant_values.values()))
        if not treatment_values and len(variant_values) >= 2:
            treatment_values = list(variant_values.values())[1]
        evaluation_result = compare_series(
            control_values,
            treatment_values,
            expected_direction=experiment.expected_direction,
            sample_minimum=experiment.minimum_sample_size,
        )
        guardrail_ok, guardrail_warnings = evaluate_guardrails(
            primary_metric_key=experiment.primary_metric_key,
            control_value=evaluation_result.control_result,
            treatment_value=evaluation_result.treatment_result,
            guardrails=[guardrail.to_dict() for guardrail in guardrails],
        )
        warnings.extend(evaluation_result.warnings)
        warnings.extend(guardrail_warnings)
        result_status = evaluation_result.status
        if not guardrail_ok:
            result_status = ExperimentOutcomeStatus.GUARDRAIL_FAILED
        elif evaluation_result.status == ExperimentOutcomeStatus.CONFOUNDED:
            result_status = ExperimentOutcomeStatus.CONFOUNDED
        elif evaluation_result.status == ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE:
            result_status = ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE
        confidence_level = calculate_confidence_level(
            sample_size=len(control_values) + len(treatment_values),
            comparable_count=comparable_count,
            contradiction_count=len(evaluation_result.contradictions),
            outlier_dominated=evaluation_result.outlier_dominated,
            execution_deviation=any(
                assignment.actual_variant is not None and assignment.actual_variant != assignment.planned_variant
                for assignment in assignments
            ),
        )
        evaluation = ExperimentEvaluation(
            id=str(uuid4()),
            experiment_id=experiment.id,
            evaluation_status=ExperimentEvaluationLifecycle.COMPLETED_WITH_WARNINGS if warnings else ExperimentEvaluationLifecycle.COMPLETED,
            sample_size=len(control_values) + len(treatment_values),
            control_count=len(control_values),
            treatment_count=len(treatment_values),
            primary_metric_key=experiment.primary_metric_key,
            control_result=evaluation_result.control_result,
            treatment_result=evaluation_result.treatment_result,
            absolute_difference=evaluation_result.absolute_difference,
            relative_difference=evaluation_result.relative_difference,
            confidence_level=confidence_level,
            uncertainty_json=_json_dumps(
                {
                    "source_fingerprint": fingerprint,
                    "result_status": result_status.value,
                    "warnings": list(sorted(set(warnings))),
                    "contradictions": list(evaluation_result.contradictions),
                    "guardrail_ok": guardrail_ok,
                    "outlier_dominated": evaluation_result.outlier_dominated,
                }
            ),
            warnings_json=_json_dumps(sorted(set(warnings))),
            evaluated_at=utc_now(),
            created_at=utc_now(),
        )
        evaluation = self.repository.upsert_evaluation(evaluation)
        outcome_rows = [replace(outcome, evaluation_id=evaluation.id) for outcome in outcome_rows]
        self.repository.upsert_outcomes(evaluation.id, outcome_rows)
        self._maybe_generate_learning(experiment, evaluation, outcome_rows)
        return evaluation

    def _maybe_generate_learning(self, experiment: ExperimentDefinition, evaluation: ExperimentEvaluation, outcomes: list[ExperimentOutcome]) -> None:
        payload = _json_loads(evaluation.uncertainty_json)
        result_status = str(payload.get("result_status") or "")
        if result_status not in {
            ExperimentOutcomeStatus.SUPPORTS_HYPOTHESIS.value,
            ExperimentOutcomeStatus.CONTRADICTS_HYPOTHESIS.value,
            ExperimentOutcomeStatus.INCONCLUSIVE.value,
            ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE.value,
            ExperimentOutcomeStatus.CONFOUNDED.value,
        }:
            return
        supporting = len([outcome for outcome in outcomes if outcome.observed_value is not None])
        contradicting = 0 if result_status == ExperimentOutcomeStatus.SUPPORTS_HYPOTHESIS.value else max(1, supporting // 2)
        statement = (
            f"{experiment.name}: {experiment.hypothesis} ({result_status})."
        )
        learning_payload = build_learning_payload(
            experiment_id=experiment.id,
            source_type="experiment_evaluation",
            source_id=evaluation.id,
            statement=statement,
            evidence={
                "experiment_id": experiment.id,
                "evaluation_id": evaluation.id,
                "outcomes": [outcome.to_dict() for outcome in outcomes],
                "result_status": result_status,
                "confidence_level": evaluation.confidence_level.value,
            },
            supporting_example_count=supporting,
            contradicting_example_count=contradicting,
            confidence_level=evaluation.confidence_level.value,
            scope="creator_general",
            platform=experiment.platform,
            content_type=experiment.content_type,
            topic=None,
        )
        learning = LearningRecord(
            id=str(uuid4()),
            creator_id=experiment.creator_id,
            source_type=learning_payload["source_type"],
            source_id=learning_payload["source_id"],
            learning_type=LearningType(learning_payload["learning_type"]),
            scope=learning_payload["scope"],
            platform=learning_payload["platform"],
            content_type=learning_payload["content_type"],
            topic=learning_payload["topic"],
            statement=learning_payload["statement"],
            evidence_json=learning_payload["evidence_json"],
            supporting_example_count=int(learning_payload["supporting_example_count"]),
            contradicting_example_count=int(learning_payload["contradicting_example_count"]),
            confidence_level=ExperimentConfidenceLevel(learning_payload["confidence_level"]),
            confidence_score=learning_payload["confidence_score"],
            status=LearningStatus(learning_payload["status"]),
            first_observed_at=utc_now(),
            last_reviewed_at=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.upsert_learning(learning)

    def get_evaluation(self, evaluation_id: str) -> ExperimentEvaluation | None:
        return self.repository.get_evaluation_by_id(evaluation_id)

    def list_evaluations(self, experiment_id: str) -> list[ExperimentEvaluation]:
        return self.repository.list_evaluations(experiment_id)

    def get_evaluation_detail(self, evaluation_id: str) -> dict[str, object]:
        evaluation = self.repository.get_evaluation_by_id(evaluation_id)
        if evaluation is None:
            raise ExperimentsNotFoundError("La evaluacion no existe.")
        outcomes = self.repository.list_outcomes(evaluation_id)
        return {"evaluation": evaluation.to_dict(), "outcomes": [outcome.to_dict() for outcome in outcomes]}

    def list_learnings(self, creator_id: str) -> list[LearningRecord]:
        return self.repository.list_learnings(creator_id)

    def get_learning(self, learning_id: str) -> LearningRecord | None:
        return self.repository.get_learning_by_id(learning_id)

    def confirm_learning(self, learning_id: str) -> LearningRecord:
        return self._review_learning(learning_id, LearningReviewDecision.CONFIRM, LearningStatus.CONFIRMED)

    def reject_learning(self, learning_id: str) -> LearningRecord:
        return self._review_learning(learning_id, LearningReviewDecision.REJECT, LearningStatus.REJECTED)

    def needs_more_data(self, learning_id: str) -> LearningRecord:
        return self._review_learning(learning_id, LearningReviewDecision.NEEDS_MORE_DATA, LearningStatus.NEEDS_MORE_DATA)

    def deprecate_learning(self, learning_id: str) -> LearningRecord:
        return self._review_learning(learning_id, LearningReviewDecision.DEPRECATE, LearningStatus.DEPRECATED)

    def edit_learning_statement(self, learning_id: str, statement: str, reason: str) -> LearningRecord:
        learning = self.repository.get_learning_by_id(learning_id)
        if learning is None:
            raise ExperimentsNotFoundError("El aprendizaje no existe.")
        review = LearningReview(
            id=str(uuid4()),
            learning_id=learning_id,
            decision=LearningReviewDecision.EDIT_STATEMENT,
            reason=reason,
            reviewed_at=utc_now(),
            created_at=utc_now(),
        )
        self.repository.upsert_learning_review(review)
        updated = replace(learning, statement=statement, updated_at=utc_now(), last_reviewed_at=utc_now())
        return self.repository.upsert_learning(updated)

    def _review_learning(self, learning_id: str, decision: LearningReviewDecision, status: LearningStatus) -> LearningRecord:
        learning = self.repository.get_learning_by_id(learning_id)
        if learning is None:
            raise ExperimentsNotFoundError("El aprendizaje no existe.")
        review = LearningReview(
            id=str(uuid4()),
            learning_id=learning_id,
            decision=decision,
            reason=decision.value,
            reviewed_at=utc_now(),
            created_at=utc_now(),
        )
        self.repository.upsert_learning_review(review)
        updated = replace(learning, status=status, last_reviewed_at=utc_now(), updated_at=utc_now())
        return self.repository.upsert_learning(updated)

    def list_learning_reviews(self, learning_id: str) -> list[LearningReview]:
        return self.repository.list_learning_reviews(learning_id)

    def generate_report(self, experiment_id: str, evaluation_id: str | None = None) -> ExperimentReport:
        experiment = self.repository.get_experiment_by_id(experiment_id)
        if experiment is None:
            raise ExperimentsNotFoundError("El experimento no existe.")
        evaluation = self.repository.get_evaluation_by_id(evaluation_id) if evaluation_id else (self.repository.list_evaluations(experiment_id)[0] if self.repository.list_evaluations(experiment_id) else None)
        assignments = self.repository.list_assignments(experiment_id)
        learnings = self.repository.list_learnings(experiment.creator_id)
        configuration = {
            "experiment": experiment.to_dict(),
            "evaluation_id": evaluation.id if evaluation else None,
            "assignment_ids": [assignment.id for assignment in assignments],
            "learning_ids": [learning.id for learning in learnings],
            "report_version": "v1",
        }
        fingerprint = build_experiment_fingerprint(configuration)
        title = f"Experiment report: {experiment.name}"
        summary = f"Reporte reproducible del experimento {experiment.name}. fingerprint:{fingerprint}"
        existing = self.repository.get_report_by_fingerprint(fingerprint, experiment.id)
        if existing and existing.status in {"completed", "completed_with_warnings"}:
            return existing
        report = ExperimentReport(
            id=str(uuid4()),
            experiment_id=experiment.id,
            evaluation_id=evaluation.id if evaluation else None,
            source_fingerprint=fingerprint,
            configuration_json=_json_dumps(configuration),
            status="running",
            title=title,
            summary=summary,
            output_json_path=None,
            output_txt_path=None,
            output_csv_path=None,
            created_at=utc_now(),
            completed_at=None,
        )
        report = self.repository.upsert_report(report)
        sections = [
            {"name": "Hipotesis", "title": "Hipotesis", "body": experiment.hypothesis},
            {"name": "Variable probada", "title": "Variable", "body": ", ".join(variable.variable_key for variable in self.list_variables(experiment.id)) or "Sin variables"},
            {"name": "Control y variantes", "title": "Variantes", "body": ", ".join(sorted({assignment.planned_variant for assignment in assignments})) or "Sin asignaciones"},
            {"name": "Publicaciones incluidas", "title": "Publicaciones", "body": ", ".join(assignment.publication_id or "" for assignment in assignments) or "Sin publicaciones"},
            {"name": "Desviaciones de ejecucion", "title": "Desviaciones", "body": ", ".join(record.deviation_from_recommendation_json for record in self.list_executions(experiment.creator_id)) or "Sin desviaciones"},
            {"name": "Metrica primaria", "title": "Metrica", "body": experiment.primary_metric_key},
            {"name": "Guardrails", "title": "Guardrails", "body": ", ".join(guardrail.metric_key for guardrail in self.list_guardrails(experiment.id)) or "Sin guardrails"},
            {"name": "Resultado", "title": "Resultado", "body": evaluation.uncertainty_json if evaluation else "Sin evaluacion"},
            {"name": "Evidencia", "title": "Evidencia", "body": json.dumps([outcome.to_dict() for outcome in self.repository.list_outcomes(evaluation.id)] if evaluation else [], ensure_ascii=False)},
            {"name": "Contradicciones", "title": "Contradicciones", "body": ", ".join(_json_loads(evaluation.uncertainty_json).get("contradictions", [])) if evaluation else "Sin contradicciones"},
            {"name": "Limitaciones", "title": "Limitaciones", "body": "No se afirma causalidad ni se promueven reglas automaticamente."},
            {"name": "Confianza", "title": "Confianza", "body": evaluation.confidence_level.value if evaluation else "very_low"},
            {"name": "Decision", "title": "Decision", "body": self._suggest_decision(evaluation)},
            {"name": "Aprendizaje", "title": "Aprendizaje", "body": ", ".join(learning.statement for learning in learnings[:5]) or "Sin aprendizajes"},
        ]
        json_path = self._reports_root / f"{report.id}.json"
        txt_path = self._reports_root / f"{report.id}.txt"
        csv_path = self._reports_root / f"{report.id}.csv"
        payload = build_report_payload(report, evaluation, [], sections=sections, warnings=[], confidence=[], limitations=["no_causalidad", "no_auto_promocion"])
        write_report(json_path, payload, format_name="json")
        write_report(txt_path, payload, format_name="txt")
        write_report(csv_path, payload, format_name="csv")
        completed = replace(report, status="completed", output_json_path=str(json_path), output_txt_path=str(txt_path), output_csv_path=str(csv_path), completed_at=utc_now())
        return self.repository.upsert_report(completed)

    def _suggest_decision(self, evaluation: ExperimentEvaluation | None) -> str:
        if evaluation is None:
            return "needs_more_data"
        payload = _json_loads(evaluation.uncertainty_json)
        result_status = str(payload.get("result_status") or "")
        mapping = {
            ExperimentOutcomeStatus.SUPPORTS_HYPOTHESIS.value: "adopt",
            ExperimentOutcomeStatus.CONTRADICTS_HYPOTHESIS.value: "discard",
            ExperimentOutcomeStatus.CONFOUNDED.value: "repeat",
            ExperimentOutcomeStatus.GUARDRAIL_FAILED.value: "segment",
            ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE.value: "needs_more_data",
            ExperimentOutcomeStatus.INVALID_EXPERIMENT.value: "discard",
            ExperimentOutcomeStatus.NEEDS_MORE_DATA.value: "needs_more_data",
            ExperimentOutcomeStatus.INCONCLUSIVE.value: "repeat",
        }
        return mapping.get(result_status, "needs_more_data")

    def list_reports(self, creator_id: str) -> list[ExperimentReport]:
        return self.repository.list_reports(creator_id)

    def get_report(self, report_id: str) -> ExperimentReport | None:
        return self.repository.get_report_by_id(report_id)

    def get_report_detail(self, report_id: str) -> dict[str, object]:
        report = self.repository.get_report_by_id(report_id)
        if report is None:
            raise ExperimentsNotFoundError("El reporte no existe.")
        evaluation = self.repository.get_evaluation_by_id(report.evaluation_id) if report.evaluation_id else None
        experiment = self.repository.get_experiment_by_id(report.experiment_id)
        return {
            "report": report.to_dict(),
            "evaluation": None if evaluation is None else evaluation.to_dict(),
            "learning": [learning.to_dict() for learning in self.list_learnings(experiment.creator_id)] if experiment else [],
        }

    def export_report(self, report_id: str, format_name: str) -> Path:
        report = self.repository.get_report_by_id(report_id)
        if report is None:
            raise ExperimentsNotFoundError("El reporte no existe.")
        output_path = {
            "json": report.output_json_path,
            "txt": report.output_txt_path,
            "csv": report.output_csv_path,
        }.get(format_name)
        if not output_path:
            raise ExperimentsStateError("El reporte no tiene esa salida.")
        return Path(output_path)


def build_experiment_services(
    *,
    analytics_service: AnalyticsQueryService,
    analytics_lab_service: AnalyticsLabService,
    repository: ExperimentRepository,
    paths: ProjectPaths,
    logger: logging.Logger | None = None,
):
    service = ExperimentService(
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        repository=repository,
        paths=paths,
        logger=logger,
    )
    from creator_intelligence_studio.application.services.recommendation_tracking_service import RecommendationTrackingService
    from creator_intelligence_studio.application.services.execution_tracking_service import ExecutionTrackingService
    from creator_intelligence_studio.application.services.experiment_evaluation_service import ExperimentEvaluationService
    from creator_intelligence_studio.application.services.learning_memory_service import LearningMemoryService

    return (
        service,
        RecommendationTrackingService(service),
        ExecutionTrackingService(service),
        ExperimentEvaluationService(service),
        LearningMemoryService(service),
    )
