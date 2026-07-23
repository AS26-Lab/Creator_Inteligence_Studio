"""Errores de dominio para subtitulos."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class SubtitleError(DomainError):
    """Error base del subsistema de subtitulos."""


class SubtitleValidationError(SubtitleError):
    """La entrada no cumple las reglas de subtitulos."""


class SubtitleStateError(SubtitleError):
    """El estado del track impide la operacion."""


class SubtitleImportError(SubtitleError):
    """No se pudo importar el archivo de subtitulos."""


class SubtitleExportError(SubtitleError):
    """No se pudo exportar el archivo de subtitulos."""

