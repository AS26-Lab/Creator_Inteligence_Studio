"""Evaluacion determinista de experiments."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from creator_intelligence_studio.domain.experiments.value_objects import (
    ExperimentConfidenceLevel,
    ExperimentOutcomeStatus,
)
from creator_intelligence_studio.infrastructure.analytics_lab.percentile_calculator import calculate_percentile, robust_z_score


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    status: ExperimentOutcomeStatus
    control_result: float | None
    treatment_result: float | None
    absolute_difference: float | None
    relative_difference: float | None
    confidence_level: ExperimentConfidenceLevel
    warnings: tuple[str, ...]
    contradictions: tuple[str, ...]
    outlier_dominated: bool


def evaluate_guardrails(
    *,
    primary_metric_key: str,
    control_value: float | None,
    treatment_value: float | None,
    guardrails: list[dict[str, object]],
) -> tuple[bool, tuple[str, ...]]:
    warnings: list[str] = []
    for guardrail in guardrails:
        metric_key = str(guardrail.get("metric_key") or "")
        if metric_key != primary_metric_key and metric_key:
            continue
        threshold = guardrail.get("threshold_value")
        allowed_change = guardrail.get("allowed_change")
        operator = str(guardrail.get("comparison_operator") or "")
        if control_value is None or treatment_value is None:
            warnings.append("missing_guardrail_metric")
            return False, tuple(sorted(set(warnings)))
        delta = treatment_value - control_value
        if operator == "<=" and threshold is not None and treatment_value > float(threshold):
            warnings.append("guardrail_failed")
            return False, tuple(sorted(set(warnings)))
        if operator == ">=" and threshold is not None and treatment_value < float(threshold):
            warnings.append("guardrail_failed")
            return False, tuple(sorted(set(warnings)))
        if allowed_change is not None and abs(delta) > abs(float(allowed_change)):
            warnings.append("guardrail_failed")
            return False, tuple(sorted(set(warnings)))
    return True, tuple(sorted(set(warnings)))


def compare_series(
    control_values: list[float],
    treatment_values: list[float],
    *,
    expected_direction: str,
    sample_minimum: int,
) -> EvaluationResult:
    warnings: list[str] = []
    contradictions: list[str] = []
    sample_size = len(control_values) + len(treatment_values)
    if sample_size == 0 or not control_values or not treatment_values:
        return EvaluationResult(
            status=ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE,
            control_result=None,
            treatment_result=None,
            absolute_difference=None,
            relative_difference=None,
            confidence_level=ExperimentConfidenceLevel.VERY_LOW,
            warnings=("insufficient_sample",),
            contradictions=(),
            outlier_dominated=False,
        )
    control_result = mean(control_values)
    treatment_result = mean(treatment_values)
    absolute_difference = treatment_result - control_result
    relative_difference = None if control_result == 0 else absolute_difference / abs(control_result)
    pooled = control_values + treatment_values
    q1 = calculate_percentile(pooled, 25)
    q3 = calculate_percentile(pooled, 75)
    outlier_dominated = False
    if q1 is not None and q3 is not None:
        iqr = q3 - q1
        if iqr == 0:
            outlier_dominated = False
        else:
            outlier_dominated = any(abs(value - mean(pooled)) > 3 * iqr for value in pooled)
    z = robust_z_score(treatment_result, pooled) if treatment_result is not None else None
    if z is not None and abs(z) >= 3:
        warnings.append("outlier_dominated")
        outlier_dominated = True
    expected = expected_direction.lower()
    if expected in {"up", "increase", "higher"} and absolute_difference is not None and absolute_difference < 0:
        contradictions.append("direction_opposite")
    if expected in {"down", "decrease", "lower"} and absolute_difference is not None and absolute_difference > 0:
        contradictions.append("direction_opposite")
    if sample_size < sample_minimum:
        warnings.append("insufficient_sample")
        status = ExperimentOutcomeStatus.INSUFFICIENT_SAMPLE
    elif outlier_dominated:
        status = ExperimentOutcomeStatus.CONFOUNDED
    elif contradictions:
        status = ExperimentOutcomeStatus.CONTRADICTS_HYPOTHESIS
    elif absolute_difference is None:
        status = ExperimentOutcomeStatus.INCONCLUSIVE
    else:
        status = ExperimentOutcomeStatus.SUPPORTS_HYPOTHESIS if absolute_difference != 0 else ExperimentOutcomeStatus.INCONCLUSIVE
    confidence = ExperimentConfidenceLevel.MEDIUM if sample_size >= sample_minimum and not outlier_dominated else ExperimentConfidenceLevel.LOW
    if sample_size >= 10 and not outlier_dominated and not contradictions:
        confidence = ExperimentConfidenceLevel.HIGH
    if sample_size < 4:
        confidence = ExperimentConfidenceLevel.VERY_LOW
    return EvaluationResult(
        status=status,
        control_result=control_result,
        treatment_result=treatment_result,
        absolute_difference=absolute_difference,
        relative_difference=relative_difference,
        confidence_level=confidence,
        warnings=tuple(sorted(set(warnings))),
        contradictions=tuple(sorted(set(contradictions))),
        outlier_dominated=outlier_dominated,
    )
