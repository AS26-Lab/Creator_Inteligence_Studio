"""Errores del analisis acustico local."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class AcousticAnalysisError(DomainError):
    """Error base del analisis acustico."""


class AcousticAnalysisValidationError(AcousticAnalysisError):
    """Error de validacion de configuracion o datos de entrada."""


class AcousticAnalysisStateError(AcousticAnalysisError):
    """Error cuando el estado local no permite continuar."""
