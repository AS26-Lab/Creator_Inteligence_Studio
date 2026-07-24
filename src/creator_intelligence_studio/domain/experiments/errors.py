"""Errores de dominio para Experiments and Verifiable Learning."""

from __future__ import annotations


class ExperimentsError(Exception):
    """Error base del dominio de experiments."""


class ExperimentsNotFoundError(ExperimentsError):
    """Elemento no encontrado."""


class ExperimentsValidationError(ExperimentsError):
    """Error de validacion."""


class ExperimentsStateError(ExperimentsError):
    """Error de estado o transicion invalida."""

