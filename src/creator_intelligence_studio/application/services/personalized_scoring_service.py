"""Servicio separado para puntuar candidatos con un modelo personalizado activo."""

from __future__ import annotations

from creator_intelligence_studio.application.services.personalization_training_service import (
    PersonalizedScoreReport,
    PersonalizationTrainingService,
)


class PersonalizedScoringService(PersonalizationTrainingService):
    """Alias tecnico del servicio de entrenamiento con foco en scoring."""


def build_personalized_scoring_service(**kwargs) -> PersonalizedScoringService:
    return PersonalizedScoringService(**kwargs)


__all__ = [
    "PersonalizedScoreReport",
    "PersonalizedScoringService",
    "build_personalized_scoring_service",
]
