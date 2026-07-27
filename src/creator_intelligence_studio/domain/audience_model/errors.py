"""Errores del dominio de audiencia."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class AudienceModelError(DomainError):
    """Error base del modelo de audiencia."""


class AudienceModelNotFoundError(AudienceModelError):
    """No se encontro una entidad de audiencia."""


class AudienceModelStateError(AudienceModelError):
    """Estado invalido para la operacion."""


class AudienceModelValidationError(AudienceModelError):
    """Validacion de audiencia fallida."""

