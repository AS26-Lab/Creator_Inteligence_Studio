"""Errores del dominio de personalizacion de datos."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import StateError, ValidationError


class PersonalizationDataValidationError(ValidationError):
    """La configuracion o los datos no cumplen las reglas esperadas."""


class PersonalizationDataStateError(StateError):
    """El estado actual impide la operacion solicitada."""
