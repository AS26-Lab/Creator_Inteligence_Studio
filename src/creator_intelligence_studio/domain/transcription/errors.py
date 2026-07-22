"""Errores del dominio de transcripcion."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError, StateError, ValidationError


class TranscriptionError(DomainError):
    """Error base de transcripcion."""


class TranscriptionValidationError(ValidationError, TranscriptionError):
    """La entrada de transcripcion no cumple las reglas."""


class TranscriptionStateError(StateError, TranscriptionError):
    """El estado actual impide continuar con la transcripcion."""


class TranscriptionBackendError(TranscriptionError):
    """La infraestructura de transcripcion no esta disponible o falla."""


