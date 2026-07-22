"""Errores del dominio de preparacion de audio."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class AudioPreparationError(DomainError):
    """Error base para la preparacion de audio."""


class AudioValidationError(AudioPreparationError):
    """La entrada de audio no cumple las reglas esperadas."""


class AudioToolUnavailableError(AudioPreparationError):
    """FFmpeg no esta disponible o no puede ejecutarse."""


class AudioStateError(AudioPreparationError):
    """El estado actual impide preparar o verificar audio."""
