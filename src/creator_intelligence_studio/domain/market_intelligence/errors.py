"""Errores del dominio de mercado."""

from __future__ import annotations


class MarketIntelligenceError(RuntimeError):
    """Error base del dominio."""


class InvalidMarketSourceError(MarketIntelligenceError):
    """Fuente invalida o no permitida."""


class UnsupportedResearchSourceError(MarketIntelligenceError):
    """La fuente de investigacion no esta soportada en esta fase."""


class MarketResearchError(MarketIntelligenceError):
    """Error al procesar investigacion o señales."""


class MarketPermissionError(MarketIntelligenceError):
    """La fuente requiere permisos no disponibles."""

