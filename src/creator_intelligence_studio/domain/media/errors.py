"""Errores del dominio media."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class MediaInspectionError(DomainError):
    """Error general de inspeccion tecnica."""


class MediaToolUnavailableError(MediaInspectionError):
    """FFmpeg o ffprobe no estan disponibles."""

