"""Errores de dominio para TikTok."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class TikTokIntegrationError(DomainError):
    pass


class TikTokAuthorizationError(TikTokIntegrationError):
    pass


class TikTokConnectionError(TikTokIntegrationError):
    pass


class TikTokSyncError(TikTokIntegrationError):
    pass


class TikTokRateLimitError(TikTokIntegrationError):
    pass


class TikTokContentLinkError(TikTokIntegrationError):
    pass

