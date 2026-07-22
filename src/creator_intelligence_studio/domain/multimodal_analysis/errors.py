"""Errores del dominio de analisis multimodal."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class MultimodalAnalysisValidationError(DomainError):
    """Opciones o datos de entrada invalidos."""


class MultimodalAnalysisStateError(DomainError):
    """Estado incompatible para ejecutar analisis multimodal."""

