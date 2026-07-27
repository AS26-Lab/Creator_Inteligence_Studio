"""Infraestructura comun para consolidacion de integraciones de plataforma."""

from __future__ import annotations

from .capability_mapper import build_capability_snapshots
from .connector_adapter import (
    PlatformConnectorAdapter,
    YouTubeConnectorAdapter,
    InstagramConnectorAdapter,
    TikTokConnectorAdapter,
    ManualImportConnectorAdapter,
)
from .connector_registry import PlatformConnectorRegistry, build_platform_connector_registry
from .data_availability_mapper import build_data_availability_records
from .health_checker import build_platform_health_record
from .sync_orchestrator import PlatformSyncOrchestrator

__all__ = [
    "PlatformConnectorAdapter",
    "YouTubeConnectorAdapter",
    "InstagramConnectorAdapter",
    "TikTokConnectorAdapter",
    "ManualImportConnectorAdapter",
    "PlatformConnectorRegistry",
    "build_platform_connector_registry",
    "build_capability_snapshots",
    "build_data_availability_records",
    "build_platform_health_record",
    "PlatformSyncOrchestrator",
]
