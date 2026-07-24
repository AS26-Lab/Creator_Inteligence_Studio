"""Errores del dominio de analytics."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class AnalyticsValidationError(DomainError):
    """La entrada o mapeo de analytics no es valido."""


class AnalyticsStateError(DomainError):
    """El estado actual impide la operacion solicitada."""


class AnalyticsImportError(DomainError):
    """La importacion de analytics fallo de forma controlada."""
