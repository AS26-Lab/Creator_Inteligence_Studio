"""Repositorio SQLite para Experiments and Verifiable Learning."""

from __future__ import annotations

import json
import sqlite3

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
from creator_intelligence_studio.domain.experiments.repositories import ExperimentRepository
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


def _row_to_experiment(row: sqlite3.Row) -> ExperimentDefinition:
    return ExperimentDefinition(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        description=row["description"],
        experiment_type=ExperimentType(row["experiment_type"]),
        platform=row["platform"],
        content_type=row["content_type"],
        status=ExperimentDefinitionStatus(row["status"]),
        hypothesis=row["hypothesis"],
        rationale=row["rationale"],
        primary_metric_key=row["primary_metric_key"],
        expected_direction=row["expected_direction"],
        minimum_sample_size=row["minimum_sample_size"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_variable(row: sqlite3.Row) -> ExperimentVariable:
    return ExperimentVariable(
        id=row["id"],
        experiment_id=row["experiment_id"],
        variable_key=row["variable_key"],
        variable_type=row["variable_type"],
        description=row["description"],
        control_value_json=row["control_value_json"],
        treatment_value_json=row["treatment_value_json"],
        allowed_values_json=row["allowed_values_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_guardrail(row: sqlite3.Row) -> ExperimentGuardrail:
    return ExperimentGuardrail(
        id=row["id"],
        experiment_id=row["experiment_id"],
        metric_key=row["metric_key"],
        comparison_operator=row["comparison_operator"],
        threshold_value=row["threshold_value"],
        allowed_change=row["allowed_change"],
        description=row["description"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_assignment(row: sqlite3.Row) -> ExperimentAssignment:
    return ExperimentAssignment(
        id=row["id"],
        experiment_id=row["experiment_id"],
        publication_id=row["publication_id"],
        planned_variant=row["planned_variant"],
        actual_variant=row["actual_variant"],
        assignment_status=row["assignment_status"],
        assigned_at=from_iso_z(row["assigned_at"]) or utc_now(),
        executed_at=from_iso_z(row["executed_at"]),
        notes=row["notes"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_recommendation(row: sqlite3.Row) -> RecommendationRecord:
    return RecommendationRecord(
        id=row["id"],
        creator_id=row["creator_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        recommendation_type=RecommendationType(row["recommendation_type"]),
        platform=row["platform"],
        content_type=row["content_type"],
        title=row["title"],
        recommendation_text=row["recommendation_text"],
        evidence_json=row["evidence_json"],
        confidence_level=ExperimentConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_recommendation_decision(row: sqlite3.Row) -> RecommendationDecisionRecord:
    return RecommendationDecisionRecord(
        id=row["id"],
        recommendation_id=row["recommendation_id"],
        decision=RecommendationDecision(row["decision"]),
        reason=row["reason"],
        modified_value_json=row["modified_value_json"],
        decided_at=from_iso_z(row["decided_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_execution(row: sqlite3.Row) -> ExecutionRecord:
    return ExecutionRecord(
        id=row["id"],
        creator_id=row["creator_id"],
        recommendation_id=row["recommendation_id"],
        experiment_assignment_id=row["experiment_assignment_id"],
        publication_id=row["publication_id"],
        execution_status=ExecutionStatus(row["execution_status"]),
        executed_value_json=row["executed_value_json"],
        deviation_from_recommendation_json=row["deviation_from_recommendation_json"],
        executed_at=from_iso_z(row["executed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_evaluation(row: sqlite3.Row) -> ExperimentEvaluation:
    uncertainty = _json_loads(row["uncertainty_json"], {})
    status = uncertainty.get("result_status", row["evaluation_status"])
    return ExperimentEvaluation(
        id=row["id"],
        experiment_id=row["experiment_id"],
        evaluation_status=ExperimentEvaluationLifecycle(row["evaluation_status"]),
        sample_size=row["sample_size"],
        control_count=row["control_count"],
        treatment_count=row["treatment_count"],
        primary_metric_key=row["primary_metric_key"],
        control_result=row["control_result"],
        treatment_result=row["treatment_result"],
        absolute_difference=row["absolute_difference"],
        relative_difference=row["relative_difference"],
        confidence_level=ExperimentConfidenceLevel(row["confidence_level"]),
        uncertainty_json=row["uncertainty_json"],
        warnings_json=row["warnings_json"],
        evaluated_at=from_iso_z(row["evaluated_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_outcome(row: sqlite3.Row) -> ExperimentOutcome:
    return ExperimentOutcome(
        id=row["id"],
        evaluation_id=row["evaluation_id"],
        publication_id=row["publication_id"],
        assignment_id=row["assignment_id"],
        variant=row["variant"],
        metric_key=row["metric_key"],
        observed_value=row["observed_value"],
        comparable_window=row["comparable_window"],
        quality_status=row["quality_status"],
        warnings_json=row["warnings_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_learning(row: sqlite3.Row) -> LearningRecord:
    return LearningRecord(
        id=row["id"],
        creator_id=row["creator_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        learning_type=LearningType(row["learning_type"]),
        scope=row["scope"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        statement=row["statement"],
        evidence_json=row["evidence_json"],
        supporting_example_count=row["supporting_example_count"],
        contradicting_example_count=row["contradicting_example_count"],
        confidence_level=ExperimentConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        status=LearningStatus(row["status"]),
        first_observed_at=from_iso_z(row["first_observed_at"]) or utc_now(),
        last_reviewed_at=from_iso_z(row["last_reviewed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_learning_review(row: sqlite3.Row) -> LearningReview:
    return LearningReview(
        id=row["id"],
        learning_id=row["learning_id"],
        decision=LearningReviewDecision(row["decision"]),
        reason=row["reason"],
        reviewed_at=from_iso_z(row["reviewed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_report(row: sqlite3.Row) -> ExperimentReport:
    return ExperimentReport(
        id=row["id"],
        experiment_id=row["experiment_id"],
        evaluation_id=row["evaluation_id"],
        source_fingerprint=row["source_fingerprint"],
        configuration_json=row["configuration_json"],
        status=row["status"],
        title=row["title"],
        summary=row["summary"],
        output_json_path=row["output_json_path"],
        output_txt_path=row["output_txt_path"],
        output_csv_path=row["output_csv_path"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
    )


class SQLiteExperimentRepository(ExperimentRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_experiment(self, experiment: ExperimentDefinition) -> ExperimentDefinition:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_definitions (
                    id, creator_id, name, description, experiment_type, platform, content_type, status,
                    hypothesis, rationale, primary_metric_key, expected_direction, minimum_sample_size,
                    start_date, end_date, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :name, :description, :experiment_type, :platform, :content_type, :status,
                    :hypothesis, :rationale, :primary_metric_key, :expected_direction, :minimum_sample_size,
                    :start_date, :end_date, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    experiment_type = excluded.experiment_type,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    status = excluded.status,
                    hypothesis = excluded.hypothesis,
                    rationale = excluded.rationale,
                    primary_metric_key = excluded.primary_metric_key,
                    expected_direction = excluded.expected_direction,
                    minimum_sample_size = excluded.minimum_sample_size,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    updated_at = excluded.updated_at
                """,
                {
                    **experiment.to_dict(),
                    "experiment_type": experiment.experiment_type.value,
                    "status": experiment.status.value,
                    "created_at": experiment.created_at.isoformat(),
                    "updated_at": experiment.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM experiment_definitions WHERE id = ?", (experiment.id,)).fetchone()
        return _row_to_experiment(row)

    def get_experiment_by_id(self, experiment_id: str) -> ExperimentDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM experiment_definitions WHERE id = ?", (experiment_id,)).fetchone()
        return _row_to_experiment(row) if row else None

    def get_experiment_by_name(self, creator_id: str, name: str) -> ExperimentDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM experiment_definitions WHERE creator_id = ? AND name = ?",
                (creator_id, name),
            ).fetchone()
        return _row_to_experiment(row) if row else None

    def list_experiments(self, creator_id: str) -> list[ExperimentDefinition]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_definitions WHERE creator_id = ? ORDER BY updated_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_experiment(row) for row in rows]

    def upsert_variable(self, variable: ExperimentVariable) -> ExperimentVariable:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_variables (
                    id, experiment_id, variable_key, variable_type, description,
                    control_value_json, treatment_value_json, allowed_values_json, created_at
                ) VALUES (
                    :id, :experiment_id, :variable_key, :variable_type, :description,
                    :control_value_json, :treatment_value_json, :allowed_values_json, :created_at
                )
                ON CONFLICT(experiment_id, variable_key) DO UPDATE SET
                    variable_type = excluded.variable_type,
                    description = excluded.description,
                    control_value_json = excluded.control_value_json,
                    treatment_value_json = excluded.treatment_value_json,
                    allowed_values_json = excluded.allowed_values_json
                """,
                {**variable.to_dict(), "created_at": variable.created_at.isoformat()},
            )
            row = connection.execute(
                "SELECT * FROM experiment_variables WHERE experiment_id = ? AND variable_key = ?",
                (variable.experiment_id, variable.variable_key),
            ).fetchone()
        return _row_to_variable(row)

    def list_variables(self, experiment_id: str) -> list[ExperimentVariable]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_variables WHERE experiment_id = ? ORDER BY created_at ASC",
                (experiment_id,),
            ).fetchall()
        return [_row_to_variable(row) for row in rows]

    def upsert_guardrail(self, guardrail: ExperimentGuardrail) -> ExperimentGuardrail:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_guardrails (
                    id, experiment_id, metric_key, comparison_operator, threshold_value,
                    allowed_change, description, created_at
                ) VALUES (
                    :id, :experiment_id, :metric_key, :comparison_operator, :threshold_value,
                    :allowed_change, :description, :created_at
                )
                ON CONFLICT(experiment_id, metric_key) DO UPDATE SET
                    comparison_operator = excluded.comparison_operator,
                    threshold_value = excluded.threshold_value,
                    allowed_change = excluded.allowed_change,
                    description = excluded.description
                """,
                {**guardrail.to_dict(), "created_at": guardrail.created_at.isoformat()},
            )
            row = connection.execute(
                "SELECT * FROM experiment_guardrails WHERE experiment_id = ? AND metric_key = ?",
                (guardrail.experiment_id, guardrail.metric_key),
            ).fetchone()
        return _row_to_guardrail(row)

    def list_guardrails(self, experiment_id: str) -> list[ExperimentGuardrail]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_guardrails WHERE experiment_id = ? ORDER BY created_at ASC",
                (experiment_id,),
            ).fetchall()
        return [_row_to_guardrail(row) for row in rows]

    def upsert_assignment(self, assignment: ExperimentAssignment) -> ExperimentAssignment:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_assignments (
                    id, experiment_id, publication_id, planned_variant, actual_variant,
                    assignment_status, assigned_at, executed_at, notes, created_at, updated_at
                ) VALUES (
                    :id, :experiment_id, :publication_id, :planned_variant, :actual_variant,
                    :assignment_status, :assigned_at, :executed_at, :notes, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    publication_id = excluded.publication_id,
                    planned_variant = excluded.planned_variant,
                    actual_variant = excluded.actual_variant,
                    assignment_status = excluded.assignment_status,
                    assigned_at = excluded.assigned_at,
                    executed_at = excluded.executed_at,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                {**assignment.to_dict(), "assigned_at": assignment.assigned_at.isoformat(), "executed_at": assignment.executed_at.isoformat() if assignment.executed_at else None, "created_at": assignment.created_at.isoformat(), "updated_at": assignment.updated_at.isoformat()},
            )
            row = connection.execute("SELECT * FROM experiment_assignments WHERE id = ?", (assignment.id,)).fetchone()
        return _row_to_assignment(row)

    def list_assignments(self, experiment_id: str) -> list[ExperimentAssignment]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_assignments WHERE experiment_id = ? ORDER BY assigned_at ASC",
                (experiment_id,),
            ).fetchall()
        return [_row_to_assignment(row) for row in rows]

    def upsert_recommendation(self, recommendation: RecommendationRecord) -> RecommendationRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO recommendation_records (
                    id, creator_id, source_type, source_id, recommendation_type, platform, content_type,
                    title, recommendation_text, evidence_json, confidence_level, confidence_score,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :source_type, :source_id, :recommendation_type, :platform, :content_type,
                    :title, :recommendation_text, :evidence_json, :confidence_level, :confidence_score,
                    :status, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    recommendation_type = excluded.recommendation_type,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    title = excluded.title,
                    recommendation_text = excluded.recommendation_text,
                    evidence_json = excluded.evidence_json,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                {
                    **recommendation.to_dict(),
                    "recommendation_type": recommendation.recommendation_type.value,
                    "confidence_level": recommendation.confidence_level.value,
                    "created_at": recommendation.created_at.isoformat(),
                    "updated_at": recommendation.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM recommendation_records WHERE id = ?", (recommendation.id,)).fetchone()
        return _row_to_recommendation(row)

    def get_recommendation_by_id(self, recommendation_id: str) -> RecommendationRecord | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM recommendation_records WHERE id = ?", (recommendation_id,)).fetchone()
        return _row_to_recommendation(row) if row else None

    def list_recommendations(self, creator_id: str) -> list[RecommendationRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM recommendation_records WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_recommendation(row) for row in rows]

    def upsert_recommendation_decision(self, decision: RecommendationDecisionRecord) -> RecommendationDecisionRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO recommendation_decisions (
                    id, recommendation_id, decision, reason, modified_value_json, decided_at, created_at
                ) VALUES (
                    :id, :recommendation_id, :decision, :reason, :modified_value_json, :decided_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    decision = excluded.decision,
                    reason = excluded.reason,
                    modified_value_json = excluded.modified_value_json,
                    decided_at = excluded.decided_at
                """,
                {
                    **decision.to_dict(),
                    "decision": decision.decision.value,
                    "decided_at": decision.decided_at.isoformat(),
                    "created_at": decision.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM recommendation_decisions WHERE id = ?", (decision.id,)).fetchone()
        return _row_to_recommendation_decision(row)

    def list_recommendation_decisions(self, recommendation_id: str) -> list[RecommendationDecisionRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM recommendation_decisions WHERE recommendation_id = ? ORDER BY decided_at DESC",
                (recommendation_id,),
            ).fetchall()
        return [_row_to_recommendation_decision(row) for row in rows]

    def upsert_execution(self, execution: ExecutionRecord) -> ExecutionRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO execution_records (
                    id, creator_id, recommendation_id, experiment_assignment_id, publication_id,
                    execution_status, executed_value_json, deviation_from_recommendation_json,
                    executed_at, created_at
                ) VALUES (
                    :id, :creator_id, :recommendation_id, :experiment_assignment_id, :publication_id,
                    :execution_status, :executed_value_json, :deviation_from_recommendation_json,
                    :executed_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    recommendation_id = excluded.recommendation_id,
                    experiment_assignment_id = excluded.experiment_assignment_id,
                    publication_id = excluded.publication_id,
                    execution_status = excluded.execution_status,
                    executed_value_json = excluded.executed_value_json,
                    deviation_from_recommendation_json = excluded.deviation_from_recommendation_json,
                    executed_at = excluded.executed_at
                """,
                {**execution.to_dict(), "execution_status": execution.execution_status.value, "executed_at": execution.executed_at.isoformat(), "created_at": execution.created_at.isoformat()},
            )
            row = connection.execute("SELECT * FROM execution_records WHERE id = ?", (execution.id,)).fetchone()
        return _row_to_execution(row)

    def list_executions(self, creator_id: str) -> list[ExecutionRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM execution_records WHERE creator_id = ? ORDER BY executed_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_execution(row) for row in rows]

    def upsert_evaluation(self, evaluation: ExperimentEvaluation) -> ExperimentEvaluation:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_evaluations (
                    id, experiment_id, evaluation_status, sample_size, control_count, treatment_count,
                    primary_metric_key, control_result, treatment_result, absolute_difference,
                    relative_difference, confidence_level, uncertainty_json, warnings_json,
                    evaluated_at, created_at
                ) VALUES (
                    :id, :experiment_id, :evaluation_status, :sample_size, :control_count, :treatment_count,
                    :primary_metric_key, :control_result, :treatment_result, :absolute_difference,
                    :relative_difference, :confidence_level, :uncertainty_json, :warnings_json,
                    :evaluated_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_status = excluded.evaluation_status,
                    sample_size = excluded.sample_size,
                    control_count = excluded.control_count,
                    treatment_count = excluded.treatment_count,
                    primary_metric_key = excluded.primary_metric_key,
                    control_result = excluded.control_result,
                    treatment_result = excluded.treatment_result,
                    absolute_difference = excluded.absolute_difference,
                    relative_difference = excluded.relative_difference,
                    confidence_level = excluded.confidence_level,
                    uncertainty_json = excluded.uncertainty_json,
                    warnings_json = excluded.warnings_json,
                    evaluated_at = excluded.evaluated_at
                """,
                {
                    **evaluation.to_dict(),
                    "evaluation_status": evaluation.evaluation_status.value,
                    "confidence_level": evaluation.confidence_level.value,
                    "evaluated_at": evaluation.evaluated_at.isoformat(),
                    "created_at": evaluation.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM experiment_evaluations WHERE id = ?", (evaluation.id,)).fetchone()
        return _row_to_evaluation(row)

    def get_evaluation_by_id(self, evaluation_id: str) -> ExperimentEvaluation | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM experiment_evaluations WHERE id = ?", (evaluation_id,)).fetchone()
        return _row_to_evaluation(row) if row else None

    def get_evaluation_by_fingerprint(self, source_fingerprint: str, experiment_id: str) -> ExperimentEvaluation | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT e.* FROM experiment_evaluations e WHERE e.experiment_id = ? AND e.uncertainty_json LIKE ? ORDER BY e.created_at DESC LIMIT 1",
                (experiment_id, f'%"{source_fingerprint}"%'),
            ).fetchone()
        return _row_to_evaluation(row) if row else None

    def list_evaluations(self, experiment_id: str) -> list[ExperimentEvaluation]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_evaluations WHERE experiment_id = ? ORDER BY evaluated_at DESC",
                (experiment_id,),
            ).fetchall()
        return [_row_to_evaluation(row) for row in rows]

    def upsert_outcomes(self, evaluation_id: str, outcomes: list[ExperimentOutcome]) -> list[ExperimentOutcome]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM experiment_outcomes WHERE evaluation_id = ?", (evaluation_id,))
            for outcome in outcomes:
                connection.execute(
                    """
                    INSERT INTO experiment_outcomes (
                        id, evaluation_id, publication_id, assignment_id, variant, metric_key,
                        observed_value, comparable_window, quality_status, warnings_json, created_at
                    ) VALUES (
                        :id, :evaluation_id, :publication_id, :assignment_id, :variant, :metric_key,
                        :observed_value, :comparable_window, :quality_status, :warnings_json, :created_at
                    )
                    """,
                    {**outcome.to_dict(), "created_at": outcome.created_at.isoformat()},
                )
            rows = connection.execute(
                "SELECT * FROM experiment_outcomes WHERE evaluation_id = ? ORDER BY variant, metric_key",
                (evaluation_id,),
            ).fetchall()
        return [_row_to_outcome(row) for row in rows]

    def list_outcomes(self, evaluation_id: str) -> list[ExperimentOutcome]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiment_outcomes WHERE evaluation_id = ? ORDER BY variant, metric_key",
                (evaluation_id,),
            ).fetchall()
        return [_row_to_outcome(row) for row in rows]

    def upsert_learning(self, learning: LearningRecord) -> LearningRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO learning_records (
                    id, creator_id, source_type, source_id, learning_type, scope, platform, content_type, topic,
                    statement, evidence_json, supporting_example_count, contradicting_example_count,
                    confidence_level, confidence_score, status, first_observed_at, last_reviewed_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :source_type, :source_id, :learning_type, :scope, :platform, :content_type, :topic,
                    :statement, :evidence_json, :supporting_example_count, :contradicting_example_count,
                    :confidence_level, :confidence_score, :status, :first_observed_at, :last_reviewed_at,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    learning_type = excluded.learning_type,
                    scope = excluded.scope,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    statement = excluded.statement,
                    evidence_json = excluded.evidence_json,
                    supporting_example_count = excluded.supporting_example_count,
                    contradicting_example_count = excluded.contradicting_example_count,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    status = excluded.status,
                    last_reviewed_at = excluded.last_reviewed_at,
                    updated_at = excluded.updated_at
                """,
                {
                    **learning.to_dict(),
                    "learning_type": learning.learning_type.value,
                    "confidence_level": learning.confidence_level.value,
                    "status": learning.status.value,
                    "first_observed_at": learning.first_observed_at.isoformat(),
                    "last_reviewed_at": learning.last_reviewed_at.isoformat() if learning.last_reviewed_at else None,
                    "created_at": learning.created_at.isoformat(),
                    "updated_at": learning.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM learning_records WHERE id = ?", (learning.id,)).fetchone()
        return _row_to_learning(row)

    def get_learning_by_id(self, learning_id: str) -> LearningRecord | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM learning_records WHERE id = ?", (learning_id,)).fetchone()
        return _row_to_learning(row) if row else None

    def list_learnings(self, creator_id: str) -> list[LearningRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learning_records WHERE creator_id = ? ORDER BY updated_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_learning(row) for row in rows]

    def upsert_learning_review(self, review: LearningReview) -> LearningReview:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO learning_reviews (
                    id, learning_id, decision, reason, reviewed_at, created_at
                ) VALUES (
                    :id, :learning_id, :decision, :reason, :reviewed_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    decision = excluded.decision,
                    reason = excluded.reason,
                    reviewed_at = excluded.reviewed_at
                """,
                {
                    **review.to_dict(),
                    "decision": review.decision.value,
                    "reviewed_at": review.reviewed_at.isoformat(),
                    "created_at": review.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM learning_reviews WHERE id = ?", (review.id,)).fetchone()
        return _row_to_learning_review(row)

    def list_learning_reviews(self, learning_id: str) -> list[LearningReview]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learning_reviews WHERE learning_id = ? ORDER BY reviewed_at DESC",
                (learning_id,),
            ).fetchall()
        return [_row_to_learning_review(row) for row in rows]

    def upsert_report(self, report: ExperimentReport) -> ExperimentReport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO experiment_reports (
                    id, experiment_id, evaluation_id, source_fingerprint, configuration_json, status, title, summary,
                    output_json_path, output_txt_path, output_csv_path, created_at, completed_at
                ) VALUES (
                    :id, :experiment_id, :evaluation_id, :source_fingerprint, :configuration_json, :status, :title, :summary,
                    :output_json_path, :output_txt_path, :output_csv_path, :created_at, :completed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_id = excluded.evaluation_id,
                    source_fingerprint = excluded.source_fingerprint,
                    configuration_json = excluded.configuration_json,
                    status = excluded.status,
                    title = excluded.title,
                    summary = excluded.summary,
                    output_json_path = excluded.output_json_path,
                    output_txt_path = excluded.output_txt_path,
                    output_csv_path = excluded.output_csv_path,
                    completed_at = excluded.completed_at
                """,
                {**report.to_dict(), "created_at": report.created_at.isoformat(), "completed_at": report.completed_at.isoformat() if report.completed_at else None},
            )
            row = connection.execute("SELECT * FROM experiment_reports WHERE id = ?", (report.id,)).fetchone()
        return _row_to_report(row)

    def get_report_by_id(self, report_id: str) -> ExperimentReport | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM experiment_reports WHERE id = ?", (report_id,)).fetchone()
        return _row_to_report(row) if row else None

    def get_report_by_fingerprint(self, source_fingerprint: str, experiment_id: str | None = None) -> ExperimentReport | None:
        query = "SELECT * FROM experiment_reports WHERE source_fingerprint = ? AND status IN ('completed', 'completed_with_warnings') ORDER BY created_at DESC LIMIT 1"
        params: list[object] = [source_fingerprint]
        with self._database.connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
        return _row_to_report(row) if row else None

    def list_reports(self, creator_id: str) -> list[ExperimentReport]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*
                FROM experiment_reports r
                JOIN experiment_definitions e ON e.id = r.experiment_id
                WHERE e.creator_id = ?
                ORDER BY r.created_at DESC
                """,
                (creator_id,),
            ).fetchall()
        return [_row_to_report(row) for row in rows]
