"""Infrastructure for provider-neutral integrations."""

from __future__ import annotations

from .fake_connector import FakeIntegrationConnector
from .local_connector import LocalNoAuthIntegrationConnector
from .registry import IntegrationRegistry, build_default_integration_registry, build_default_integration_registry_summary

__all__ = [
    "FakeIntegrationConnector",
    "IntegrationRegistry",
    "LocalNoAuthIntegrationConnector",
    "build_default_integration_registry",
    "build_default_integration_registry_summary",
]
