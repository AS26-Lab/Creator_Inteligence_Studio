"""Errores del dominio de evaluacion operativa."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class OperationalEvaluationError(DomainError):
    """Error base de evaluacion operativa."""


class OperationalEvaluationValidationError(OperationalEvaluationError):
    """La configuracion o el escenario son invalidos."""


class OperationalEvaluationStateError(OperationalEvaluationError):
    """El estado de una ejecucion no permite la operacion solicitada."""
