"""Dominio comun para la consolidacion de integraciones de plataforma."""

from __future__ import annotations

from .capability_types import CapabilityAvailabilityStatus, CapabilityCategory, ComparabilityStatus
from .connection_types import CommonConnectionStatus, ConnectorType, PlatformKind
from .data_availability_types import DataAvailabilitySourceType, DataAvailabilityStatus, DataCategory
from .entities import (
    PlatformCapabilitySnapshot,
    PlatformConnectionHealth,
    PlatformConnectionSummary,
    PlatformDataAvailability,
    PlatformIntegrationEvent,
    PlatformManualImportStatus,
    PlatformReport,
    PlatformScheduleRegistryEntry,
    PlatformSyncGroup,
    PlatformSyncGroupItem,
)
from .errors import PlatformIntegrationError, PlatformIntegrationNotAvailableError
from .health_types import HealthStatus, Severity
from .repositories import PlatformIntegrationRepository
from .services import (
    build_platform_fingerprint,
    classify_native_connection_status,
    classify_health_status,
    normalize_platform_identifier,
)
from .sync_types import SyncMode, SyncGroupStatus, SyncItemStatus

__all__ = [
    "CapabilityAvailabilityStatus",
    "CapabilityCategory",
    "ComparabilityStatus",
    "CommonConnectionStatus",
    "ConnectorType",
    "PlatformKind",
    "DataAvailabilitySourceType",
    "DataAvailabilityStatus",
    "DataCategory",
    "PlatformCapabilitySnapshot",
    "PlatformConnectionHealth",
    "PlatformConnectionSummary",
    "PlatformDataAvailability",
    "PlatformIntegrationEvent",
    "PlatformManualImportStatus",
    "PlatformReport",
    "PlatformScheduleRegistryEntry",
    "PlatformSyncGroup",
    "PlatformSyncGroupItem",
    "PlatformIntegrationError",
    "PlatformIntegrationNotAvailableError",
    "HealthStatus",
    "Severity",
    "PlatformIntegrationRepository",
    "build_platform_fingerprint",
    "classify_native_connection_status",
    "classify_health_status",
    "normalize_platform_identifier",
    "SyncMode",
    "SyncGroupStatus",
    "SyncItemStatus",
]
