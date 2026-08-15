"""Infrastructure for provider-neutral integrations."""

from __future__ import annotations

from .fake_connector import FakeIntegrationConnector
from .local_connector import LocalNoAuthIntegrationConnector
from .youtube_connector import YouTubeIntegrationConnector, build_default_youtube_connector
from .registry import IntegrationRegistry, build_default_integration_registry, build_default_integration_registry_summary

__all__ = [
    "FakeIntegrationConnector",
    "IntegrationRegistry",
    "LocalNoAuthIntegrationConnector",
    "YouTubeIntegrationConnector",
    "build_default_integration_registry",
    "build_default_integration_registry_summary",
    "build_default_youtube_connector",
]
