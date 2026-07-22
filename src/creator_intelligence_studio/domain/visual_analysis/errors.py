"""Errores del dominio de analisis visual."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class VisualAnalysisError(DomainError):
    """Error base del analisis visual."""


class VisualAnalysisValidationError(VisualAnalysisError):
    """Error de validacion de configuracion visual."""


class VisualAnalysisStateError(VisualAnalysisError):
    """Error de estado de analisis visual."""
