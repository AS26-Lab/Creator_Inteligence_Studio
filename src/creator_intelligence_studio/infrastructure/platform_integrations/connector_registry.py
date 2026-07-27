"""Registry de adaptadores de plataforma."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsImportService
from creator_intelligence_studio.application.services.instagram_integration_service import InstagramIntegrationService
from creator_intelligence_studio.application.services.tiktok_integration_service import TikTokIntegrationService
from creator_intelligence_studio.application.services.youtube_integration_service import YouTubeIntegrationService
from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind

from .connector_adapter import (
    InstagramConnectorAdapter,
    ManualImportConnectorAdapter,
    PlatformConnectorAdapter,
    TikTokConnectorAdapter,
    YouTubeConnectorAdapter,
)


@dataclass(slots=True)
class PlatformConnectorRegistry:
    youtube: YouTubeConnectorAdapter | None = None
    instagram: InstagramConnectorAdapter | None = None
    tiktok: TikTokConnectorAdapter | None = None
    manual: ManualImportConnectorAdapter | None = None

    def adapters(self) -> list[PlatformConnectorAdapter]:
        adapters: list[PlatformConnectorAdapter] = []
        for adapter in (self.youtube, self.instagram, self.tiktok, self.manual):
            if adapter is not None:
                adapters.append(adapter)
        return adapters

    def get(self, platform: PlatformKind):
        return {
            PlatformKind.YOUTUBE: self.youtube,
            PlatformKind.INSTAGRAM: self.instagram,
            PlatformKind.TIKTOK: self.tiktok,
            PlatformKind.MANUAL_OTHER: self.manual,
        }.get(platform)


def build_platform_connector_registry(
    *,
    youtube_service: YouTubeIntegrationService | None = None,
    instagram_service: InstagramIntegrationService | None = None,
    tiktok_service: TikTokIntegrationService | None = None,
    analytics_service: AnalyticsImportService | None = None,
) -> PlatformConnectorRegistry:
    return PlatformConnectorRegistry(
        youtube=YouTubeConnectorAdapter(youtube_service) if youtube_service is not None else None,
        instagram=InstagramConnectorAdapter(instagram_service) if instagram_service is not None else None,
        tiktok=TikTokConnectorAdapter(tiktok_service) if tiktok_service is not None else None,
        manual=ManualImportConnectorAdapter(service=analytics_service) if analytics_service is not None else None,
    )
