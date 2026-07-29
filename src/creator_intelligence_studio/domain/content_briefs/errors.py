"""Errores del dominio de Content Brief and Pre-Production Foundation."""

from __future__ import annotations


class ContentBriefError(Exception):
    """Error base del dominio de briefs."""


class ContentBriefValidationError(ContentBriefError):
    """La entrada no cumple las reglas de briefs."""


class ContentBriefNotFoundError(ContentBriefError):
    """La entidad solicitada no existe."""


class ContentBriefStateError(ContentBriefError):
    """La operacion no es valida para el estado actual."""


class ContentBriefConflictError(ContentBriefError):
    """Se detecto un conflicto o duplicado."""
