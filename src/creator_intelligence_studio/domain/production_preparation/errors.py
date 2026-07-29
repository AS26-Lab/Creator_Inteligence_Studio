"""Errores del dominio de production preparation."""

from __future__ import annotations


class ProductionPreparationError(Exception):
    """Error base del dominio."""


class ProductionPreparationValidationError(ProductionPreparationError):
    """La entrada no cumple las reglas de production preparation."""


class ProductionPreparationNotFoundError(ProductionPreparationError):
    """La entidad solicitada no existe."""


class ProductionPreparationStateError(ProductionPreparationError):
    """La operacion no es valida para el estado actual."""


class ProductionPreparationConflictError(ProductionPreparationError):
    """Se detecto un conflicto o duplicado."""

