"""Errores de dominio para Instagram."""

from __future__ import annotations

from creator_intelligence_studio.domain.errors import DomainError


class InstagramIntegrationError(DomainError):
    pass


class InstagramAuthorizationError(InstagramIntegrationError):
    pass


class InstagramConnectionError(InstagramIntegrationError):
    pass


class InstagramSyncError(InstagramIntegrationError):
    pass


class InstagramRateLimitError(InstagramIntegrationError):
    pass


class InstagramContentLinkError(InstagramIntegrationError):
    pass


class InstagramAccountValidationError(InstagramAuthorizationError):
    pass

