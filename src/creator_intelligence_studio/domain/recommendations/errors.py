"""Errores del dominio de recomendaciones."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class RecommendationDomainError(DomainError):
    """Error base del dominio."""


class RecommendationNotFoundError(RecommendationDomainError):
    """No se encontro una recomendacion o entidad relacionada."""


class RecommendationValidationError(RecommendationDomainError):
    """La entidad no cumple validaciones de dominio."""
