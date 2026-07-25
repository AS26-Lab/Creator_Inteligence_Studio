"""Errores del dominio de integracion con YouTube."""

from __future__ import annotations


class YouTubeIntegrationError(RuntimeError):
    """Error base de la integracion con YouTube."""


class YouTubeAuthorizationError(YouTubeIntegrationError):
    """Error durante OAuth o validacion de scopes."""


class YouTubeConnectionError(YouTubeIntegrationError):
    """Error al gestionar una conexion de YouTube."""


class YouTubeSyncError(YouTubeIntegrationError):
    """Error durante una sincronizacion de YouTube."""


class YouTubeQuotaError(YouTubeIntegrationError):
    """Error o limitacion de cuota estimada."""

