"""Errores de dominio compartidos."""

from __future__ import annotations


class DomainError(Exception):
    """Error base del dominio."""


class ValidationError(DomainError):
    """La entrada no cumple las reglas del dominio."""


class NotFoundError(DomainError):
    """La entidad solicitada no existe."""


class ConflictError(DomainError):
    """La entidad no puede crearse o modificarse por conflicto de estado."""


class StateError(DomainError):
    """La entidad existe pero su estado impide la operación."""

