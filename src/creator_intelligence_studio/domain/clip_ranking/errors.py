"""Errores del dominio de ranking de clips."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class ClipRankingValidationError(DomainError):
    """Datos o configuracion invalidos para ranking de clips."""


class ClipRankingStateError(DomainError):
    """Estado incompatible para ejecutar o modificar un ranking de clips."""
