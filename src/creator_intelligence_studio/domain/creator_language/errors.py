"""Errores de Creator Language Analysis."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError, NotFoundError, StateError, ValidationError


class CreatorLanguageError(DomainError):
    """Error base de Creator Language Analysis."""


class CreatorLanguageValidationError(ValidationError, CreatorLanguageError):
    """Error de validacion de Creator Language Analysis."""


class CreatorLanguageStateError(StateError, CreatorLanguageError):
    """Error de estado de Creator Language Analysis."""


class CreatorLanguageNotFoundError(NotFoundError, CreatorLanguageError):
    """Error cuando un recurso de lenguaje no existe."""
