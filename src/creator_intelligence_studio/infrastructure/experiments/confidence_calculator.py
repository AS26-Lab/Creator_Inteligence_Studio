"""Calculo de confianza interpretable para experiments."""

from __future__ import annotations

from creator_intelligence_studio.domain.experiments.value_objects import ExperimentConfidenceLevel


def calculate_confidence_level(
    *,
    sample_size: int,
    comparable_count: int,
    contradiction_count: int,
    outlier_dominated: bool,
    execution_deviation: bool,
) -> ExperimentConfidenceLevel:
    score = 0.0
    if sample_size >= 8:
        score += 0.35
    elif sample_size >= 4:
        score += 0.2
    elif sample_size >= 2:
        score += 0.08
    score += min(comparable_count, 10) * 0.04
    score -= min(contradiction_count, 5) * 0.08
    if outlier_dominated:
        score -= 0.2
    if execution_deviation:
        score -= 0.15
    if sample_size < 2:
        return ExperimentConfidenceLevel.VERY_LOW
    if score >= 0.8:
        return ExperimentConfidenceLevel.HIGH
    if score >= 0.45:
        return ExperimentConfidenceLevel.MEDIUM
    if score >= 0.2:
        return ExperimentConfidenceLevel.LOW
    return ExperimentConfidenceLevel.VERY_LOW

