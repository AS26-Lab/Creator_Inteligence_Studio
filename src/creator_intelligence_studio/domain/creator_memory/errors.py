"""Errores del dominio de memoria del creador."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class CreatorMemoryError(DomainError):
    """Error base de Creator Memory."""


class CreatorMemoryNotFoundError(CreatorMemoryError):
    """No se encontro el recurso solicitado."""


class CreatorMemoryValidationError(CreatorMemoryError):
    """Los datos de memoria no cumplen las reglas del dominio."""


class CreatorMemoryStateError(CreatorMemoryError):
    """El recurso no puede transitar al estado solicitado."""

