from __future__ import annotations

from .instagram_integration_service import InstagramIntegrationService


def build_instagram_rate_limit_service(*args, **kwargs) -> InstagramIntegrationService:
    return InstagramIntegrationService(*args, **kwargs)

