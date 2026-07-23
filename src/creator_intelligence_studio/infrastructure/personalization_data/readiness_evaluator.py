"""Evaluacion de disponibilidad para entrenamiento futuro."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationReadinessStatus

from .quality_analyzer import QualityStats


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    readiness_status: PersonalizationReadinessStatus
    readiness_score: float
    recommendations: tuple[str, ...]


def evaluate_dataset_readiness(stats: QualityStats) -> ReadinessResult:
    return ReadinessResult(
        readiness_status=stats.readiness_status,
        readiness_score=stats.readiness_score,
        recommendations=stats.recommendations,
    )
