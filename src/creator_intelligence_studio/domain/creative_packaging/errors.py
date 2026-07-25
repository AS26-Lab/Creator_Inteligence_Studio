"""Errores del dominio de packaging creativo."""

from __future__ import annotations


class CreativePackagingError(RuntimeError):
    """Error base de packaging creativo."""


class CreativePackagingNotFoundError(CreativePackagingError):
    """Elemento no encontrado."""


class CreativePackagingValidationError(CreativePackagingError):
    """Datos de packaging invalidos."""


class CreativePackagingStateError(CreativePackagingError):
    """Estado incoherente del packaging."""

