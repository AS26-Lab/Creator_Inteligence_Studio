"""Entidades persistidas para la consolidacion de integraciones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .capability_types import CapabilityAvailabilityStatus, CapabilityCategory, ComparabilityStatus
from .connection_types import CommonConnectionStatus, ConnectorType, PlatformKind
from .data_availability_types import DataAvailabilitySourceType, DataAvailabilityStatus, DataCategory
from .health_types import HealthStatus, Severity
from .sync_types import SyncGroupStatus, SyncItemStatus, SyncMode


@dataclass(frozen=True, slots=True)
class PlatformConnectionSummary:
    id: str
    creator_id: str
    platform: PlatformKind
    connector_type: ConnectorType
    native_connection_id: str
    status: CommonConnectionStatus
    display_name: str | None
    account_identifier: str | None
    credential_reference: str | None
    granted_permissions_json: str
    capability_snapshot_json: str
    health_status: HealthStatus
    health_checked_at: datetime | None
    connected_at: datetime | None
    disconnected_at: datetime | None
    native_status: str
    native_error_code: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform.value,
            "connector_type": self.connector_type.value,
            "native_connection_id": self.native_connection_id,
            "status": self.status.value,
            "display_name": self.display_name,
            "account_identifier": self.account_identifier,
            "credential_reference": self.credential_reference,
            "granted_permissions_json": self.granted_permissions_json,
            "capability_snapshot_json": self.capability_snapshot_json,
            "health_status": self.health_status.value,
            "health_checked_at": to_iso_z(self.health_checked_at),
            "connected_at": to_iso_z(self.connected_at),
            "disconnected_at": to_iso_z(self.disconnected_at),
            "native_status": self.native_status,
            "native_error_code": self.native_error_code,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformConnectionHealth:
    id: str
    creator_id: str
    platform_connection_id: str
    status: HealthStatus
    severity: Severity
    error_code: str | None
    message: str | None
    details_json: str
    checked_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform_connection_id": self.platform_connection_id,
            "status": self.status.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "message": self.message,
            "details_json": self.details_json,
            "checked_at": to_iso_z(self.checked_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformCapabilitySnapshot:
    id: str
    creator_id: str
    platform_connection_id: str
    capability_key: str
    availability_status: CapabilityAvailabilityStatus
    access_level: str | None
    permission_required: str | None
    limitation_code: str | None
    source_version: str | None
    observed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform_connection_id": self.platform_connection_id,
            "capability_key": self.capability_key,
            "availability_status": self.availability_status.value,
            "access_level": self.access_level,
            "permission_required": self.permission_required,
            "limitation_code": self.limitation_code,
            "source_version": self.source_version,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformDataAvailability:
    id: str
    creator_id: str
    platform_connection_id: str
    data_category: DataCategory
    data_key: str
    availability_status: DataAvailabilityStatus
    source_type: DataAvailabilitySourceType
    automatic_available: bool
    manual_import_available: bool
    period_semantics: str | None
    cumulative_semantics: str | None
    limitations_json: str
    observed_at: datetime
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform_connection_id": self.platform_connection_id,
            "data_category": self.data_category.value,
            "data_key": self.data_key,
            "availability_status": self.availability_status.value,
            "source_type": self.source_type.value,
            "automatic_available": 1 if self.automatic_available else 0,
            "manual_import_available": 1 if self.manual_import_available else 0,
            "period_semantics": self.period_semantics,
            "cumulative_semantics": self.cumulative_semantics,
            "limitations_json": self.limitations_json,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformSyncGroup:
    id: str
    creator_id: str
    name: str
    sync_mode: SyncMode
    status: SyncGroupStatus
    configuration_json: str
    platform_count: int
    started_at: datetime
    completed_at: datetime | None
    warning_count: int
    error_count: int
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "sync_mode": self.sync_mode.value,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "platform_count": self.platform_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformSyncGroupItem:
    id: str
    sync_group_id: str
    platform: PlatformKind
    native_connection_id: str | None
    native_sync_run_id: str | None
    status: SyncItemStatus
    sequence_order: int
    started_at: datetime | None
    completed_at: datetime | None
    warning_codes_json: str
    error_code: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "sync_group_id": self.sync_group_id,
            "platform": self.platform.value,
            "native_connection_id": self.native_connection_id,
            "native_sync_run_id": self.native_sync_run_id,
            "status": self.status.value,
            "sequence_order": self.sequence_order,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_codes_json": self.warning_codes_json,
            "error_code": self.error_code,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformScheduleRegistryEntry:
    id: str
    creator_id: str
    platform: PlatformKind
    native_schedule_id: str | None
    enabled: bool
    schedule_type: str
    interval_hours: int | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    coordination_key: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform.value,
            "native_schedule_id": self.native_schedule_id,
            "enabled": 1 if self.enabled else 0,
            "schedule_type": self.schedule_type,
            "interval_hours": self.interval_hours,
            "last_run_at": to_iso_z(self.last_run_at),
            "next_run_at": to_iso_z(self.next_run_at),
            "coordination_key": self.coordination_key,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformManualImportStatus:
    id: str
    creator_id: str
    platform: PlatformKind
    data_category: DataCategory
    last_import_at: datetime | None
    last_period_start: datetime | None
    last_period_end: datetime | None
    current_status: str
    missing_periods_json: str
    recommended_action: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform.value,
            "data_category": self.data_category.value,
            "last_import_at": to_iso_z(self.last_import_at),
            "last_period_start": to_iso_z(self.last_period_start),
            "last_period_end": to_iso_z(self.last_period_end),
            "current_status": self.current_status,
            "missing_periods_json": self.missing_periods_json,
            "recommended_action": self.recommended_action,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformIntegrationEvent:
    id: str
    creator_id: str
    platform: PlatformKind
    platform_connection_id: str | None
    event_type: str
    severity: Severity
    message: str
    details_json: str
    occurred_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform.value,
            "platform_connection_id": self.platform_connection_id,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "message": self.message,
            "details_json": self.details_json,
            "occurred_at": to_iso_z(self.occurred_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PlatformReport:
    id: str
    creator_id: str
    report_type: str
    platform_scope_json: str
    period_start: datetime | None
    period_end: datetime | None
    source_fingerprint: str
    report_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "report_type": self.report_type,
            "platform_scope_json": self.platform_scope_json,
            "period_start": to_iso_z(self.period_start),
            "period_end": to_iso_z(self.period_end),
            "source_fingerprint": self.source_fingerprint,
            "report_json": self.report_json,
            "created_at": to_iso_z(self.created_at),
        }
