"""Errores comunes para la consolidacion de integraciones."""

from __future__ import annotations


class PlatformIntegrationError(Exception):
    """Error base de la capa comun de integraciones."""


class PlatformIntegrationNotAvailableError(PlatformIntegrationError):
    """La integracion solicitada no esta disponible."""
