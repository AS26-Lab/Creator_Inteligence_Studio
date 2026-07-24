"""Errores del dominio de Analytics Lab."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class AnalyticsLabValidationError(DomainError):
    """La entrada o configuracion de Analytics Lab no es valida."""


class AnalyticsLabStateError(DomainError):
    """El estado actual impide la operacion solicitada."""


class AnalyticsLabNotFoundError(DomainError):
    """No se encontro una entidad de Analytics Lab."""

