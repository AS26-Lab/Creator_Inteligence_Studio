"""Value objects y utilidades de la consolidacion de plataformas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .capability_types import CapabilityAvailabilityStatus, CapabilityCategory, ComparabilityStatus
from .connection_types import CommonConnectionStatus, ConnectorType, PlatformKind
from .data_availability_types import DataAvailabilitySourceType, DataAvailabilityStatus, DataCategory
from .health_types import HealthStatus, Severity
from .sync_types import SyncGroupStatus, SyncItemStatus, SyncMode


PLATFORM_ORDER: tuple[PlatformKind, ...] = (
    PlatformKind.YOUTUBE,
    PlatformKind.INSTAGRAM,
    PlatformKind.TIKTOK,
    PlatformKind.MANUAL_OTHER,
)


@dataclass(frozen=True, slots=True)
class PlatformFingerprint:
    creator_id: str
    platform: PlatformKind
    connection_ids_json: str
    scopes_json: str
    status: str
    configuration_json: str
    mapper_version: str
    last_sync_at: datetime | None
    manual_import_state_json: str

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "platform": self.platform.value,
            "connection_ids_json": self.connection_ids_json,
            "scopes_json": self.scopes_json,
            "status": self.status,
            "configuration_json": self.configuration_json,
            "mapper_version": self.mapper_version,
            "last_sync_at": to_iso_z(self.last_sync_at),
            "manual_import_state_json": self.manual_import_state_json,
        }
