"""Errores del dominio de Strategic Planning."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import ConflictError, DomainError, NotFoundError, StateError, ValidationError


class StrategicPlanningError(DomainError):
    """Error base de la fase estrategica."""


class StrategicPlanningValidationError(ValidationError, StrategicPlanningError):
    """La entrada no cumple las reglas estrategicas."""


class StrategicPlanningNotFoundError(NotFoundError, StrategicPlanningError):
    """La entidad estrategica no existe."""


class StrategicPlanningStateError(StateError, StrategicPlanningError):
    """El estado de la entidad impide la operacion."""


class StrategicPlanningConflictError(ConflictError, StrategicPlanningError):
    """Existe un conflicto estrategico no resuelto."""
