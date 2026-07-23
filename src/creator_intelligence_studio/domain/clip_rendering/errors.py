"""Errores del dominio de renderizado de clips."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class ClipRenderValidationError(DomainError):
    """La entrada o configuracion de render no es valida."""


class ClipRenderStateError(DomainError):
    """El estado actual no permite renderizar o reutilizar la salida."""


class ClipRenderExecutionError(DomainError):
    """El render local fallo durante la ejecucion o verificacion."""


class ClipRenderCapabilityError(DomainError):
    """El entorno no dispone de la capacidad necesaria."""
