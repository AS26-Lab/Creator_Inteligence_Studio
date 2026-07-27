"""Repositorio SQLite para la consolidacion de integraciones de plataforma."""

from __future__ import annotations

import sqlite3

from creator_intelligence_studio.domain.platform_integrations.entities import (
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
from creator_intelligence_studio.domain.platform_integrations.capability_types import CapabilityAvailabilityStatus
from creator_intelligence_studio.domain.platform_integrations.connection_types import CommonConnectionStatus, ConnectorType, PlatformKind
from creator_intelligence_studio.domain.platform_integrations.data_availability_types import DataAvailabilitySourceType, DataAvailabilityStatus, DataCategory
from creator_intelligence_studio.domain.platform_integrations.health_types import HealthStatus, Severity
from creator_intelligence_studio.domain.platform_integrations.sync_types import SyncGroupStatus, SyncItemStatus, SyncMode
from creator_intelligence_studio.domain.platform_integrations.repositories import PlatformIntegrationRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _row(connection: sqlite3.Connection, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
    return connection.execute(query, params).fetchone()


class SQLitePlatformIntegrationRepository(PlatformIntegrationRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_platform_connection(self, record: PlatformConnectionSummary) -> PlatformConnectionSummary:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_connections (
                    id, creator_id, platform, connector_type, native_connection_id, status,
                    display_name, account_identifier, credential_reference, granted_permissions_json,
                    capability_snapshot_json, health_status, health_checked_at, connected_at,
                    disconnected_at, native_status, native_error_code, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform, :connector_type, :native_connection_id, :status,
                    :display_name, :account_identifier, :credential_reference, :granted_permissions_json,
                    :capability_snapshot_json, :health_status, :health_checked_at, :connected_at,
                    :disconnected_at, :native_status, :native_error_code, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, platform, native_connection_id) DO UPDATE SET
                    status = excluded.status,
                    display_name = excluded.display_name,
                    account_identifier = excluded.account_identifier,
                    credential_reference = excluded.credential_reference,
                    granted_permissions_json = excluded.granted_permissions_json,
                    capability_snapshot_json = excluded.capability_snapshot_json,
                    health_status = excluded.health_status,
                    health_checked_at = excluded.health_checked_at,
                    connected_at = excluded.connected_at,
                    disconnected_at = excluded.disconnected_at,
                    native_status = excluded.native_status,
                    native_error_code = excluded.native_error_code,
                    updated_at = excluded.updated_at
                """,
                record.to_dict(),
            )
            row = _row(
                connection,
                "SELECT * FROM platform_connections WHERE creator_id = ? AND platform = ? AND native_connection_id = ?",
                (record.creator_id, record.platform.value, record.native_connection_id),
            )
        return self._row_to_connection(row) if row else record

    def get_platform_connection(self, platform_connection_id: str) -> PlatformConnectionSummary | None:
        with self._database.connect() as connection:
            row = _row(connection, "SELECT * FROM platform_connections WHERE id = ?", (platform_connection_id,))
        return self._row_to_connection(row) if row else None

    def list_platform_connections(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_connections WHERE creator_id = ? ORDER BY platform, updated_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_connection(row) for row in rows]

    def upsert_platform_connection_health(self, record: PlatformConnectionHealth) -> PlatformConnectionHealth:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_connection_health (
                    id, creator_id, platform_connection_id, status, severity, error_code, message,
                    details_json, checked_at, created_at
                ) VALUES (
                    :id, :creator_id, :platform_connection_id, :status, :severity, :error_code, :message,
                    :details_json, :checked_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    severity = excluded.severity,
                    error_code = excluded.error_code,
                    message = excluded.message,
                    details_json = excluded.details_json,
                    checked_at = excluded.checked_at
                """,
                record.to_dict(),
            )
            row = _row(connection, "SELECT * FROM platform_connection_health WHERE id = ?", (record.id,))
        return self._row_to_health(row) if row else record

    def list_platform_connection_health(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_connection_health WHERE creator_id = ? ORDER BY checked_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_health(row) for row in rows]

    def upsert_platform_capability_snapshot(self, record: PlatformCapabilitySnapshot) -> PlatformCapabilitySnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_capability_snapshots (
                    id, creator_id, platform_connection_id, capability_key, availability_status,
                    access_level, permission_required, limitation_code, source_version, observed_at, created_at
                ) VALUES (
                    :id, :creator_id, :platform_connection_id, :capability_key, :availability_status,
                    :access_level, :permission_required, :limitation_code, :source_version, :observed_at, :created_at
                )
                ON CONFLICT(platform_connection_id, capability_key) DO UPDATE SET
                    availability_status = excluded.availability_status,
                    access_level = excluded.access_level,
                    permission_required = excluded.permission_required,
                    limitation_code = excluded.limitation_code,
                    source_version = excluded.source_version,
                    observed_at = excluded.observed_at
                """,
                record.to_dict(),
            )
            row = _row(
                connection,
                "SELECT * FROM platform_capability_snapshots WHERE platform_connection_id = ? AND capability_key = ?",
                (record.platform_connection_id, record.capability_key),
            )
        return self._row_to_capability(row) if row else record

    def list_platform_capability_snapshots(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_capability_snapshots WHERE creator_id = ? ORDER BY observed_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_capability(row) for row in rows]

    def upsert_platform_data_availability(self, record: PlatformDataAvailability) -> PlatformDataAvailability:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_data_availability (
                    id, creator_id, platform_connection_id, data_category, data_key, availability_status,
                    source_type, automatic_available, manual_import_available, period_semantics,
                    cumulative_semantics, limitations_json, observed_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform_connection_id, :data_category, :data_key, :availability_status,
                    :source_type, :automatic_available, :manual_import_available, :period_semantics,
                    :cumulative_semantics, :limitations_json, :observed_at, :created_at, :updated_at
                )
                ON CONFLICT(platform_connection_id, data_category, data_key) DO UPDATE SET
                    availability_status = excluded.availability_status,
                    source_type = excluded.source_type,
                    automatic_available = excluded.automatic_available,
                    manual_import_available = excluded.manual_import_available,
                    period_semantics = excluded.period_semantics,
                    cumulative_semantics = excluded.cumulative_semantics,
                    limitations_json = excluded.limitations_json,
                    observed_at = excluded.observed_at,
                    updated_at = excluded.updated_at
                """,
                record.to_dict(),
            )
            row = _row(
                connection,
                "SELECT * FROM platform_data_availability WHERE platform_connection_id = ? AND data_category = ? AND data_key = ?",
                (record.platform_connection_id, record.data_category.value, record.data_key),
            )
        return self._row_to_availability(row) if row else record

    def list_platform_data_availability(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_data_availability WHERE creator_id = ? ORDER BY data_category, data_key",
                (creator_id,),
            ).fetchall()
        return [self._row_to_availability(row) for row in rows]

    def upsert_platform_sync_group(self, record: PlatformSyncGroup) -> PlatformSyncGroup:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_sync_groups (
                    id, creator_id, name, sync_mode, status, configuration_json, platform_count,
                    started_at, completed_at, warning_count, error_count, created_at
                ) VALUES (
                    :id, :creator_id, :name, :sync_mode, :status, :configuration_json, :platform_count,
                    :started_at, :completed_at, :warning_count, :error_count, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    sync_mode = excluded.sync_mode,
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    platform_count = excluded.platform_count,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_count = excluded.warning_count,
                    error_count = excluded.error_count
                """,
                record.to_dict(),
            )
            row = _row(connection, "SELECT * FROM platform_sync_groups WHERE id = ?", (record.id,))
        return self._row_to_group(row) if row else record

    def get_platform_sync_group(self, sync_group_id: str) -> PlatformSyncGroup | None:
        with self._database.connect() as connection:
            row = _row(connection, "SELECT * FROM platform_sync_groups WHERE id = ?", (sync_group_id,))
        return self._row_to_group(row) if row else None

    def list_platform_sync_groups(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_sync_groups WHERE creator_id = ? ORDER BY started_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_group(row) for row in rows]

    def upsert_platform_sync_group_item(self, record: PlatformSyncGroupItem) -> PlatformSyncGroupItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_sync_group_items (
                    id, sync_group_id, platform, native_connection_id, native_sync_run_id, status,
                    sequence_order, started_at, completed_at, warning_codes_json, error_code, created_at
                ) VALUES (
                    :id, :sync_group_id, :platform, :native_connection_id, :native_sync_run_id, :status,
                    :sequence_order, :started_at, :completed_at, :warning_codes_json, :error_code, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    native_connection_id = excluded.native_connection_id,
                    native_sync_run_id = excluded.native_sync_run_id,
                    status = excluded.status,
                    sequence_order = excluded.sequence_order,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_codes_json = excluded.warning_codes_json,
                    error_code = excluded.error_code
                """,
                record.to_dict(),
            )
            row = _row(connection, "SELECT * FROM platform_sync_group_items WHERE id = ?", (record.id,))
        return self._row_to_group_item(row) if row else record

    def list_platform_sync_group_items(self, sync_group_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_sync_group_items WHERE sync_group_id = ? ORDER BY sequence_order ASC",
                (sync_group_id,),
            ).fetchall()
        return [self._row_to_group_item(row) for row in rows]

    def upsert_platform_schedule_registry_entry(self, record: PlatformScheduleRegistryEntry) -> PlatformScheduleRegistryEntry:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_schedule_registry (
                    id, creator_id, platform, native_schedule_id, enabled, schedule_type, interval_hours,
                    last_run_at, next_run_at, coordination_key, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform, :native_schedule_id, :enabled, :schedule_type, :interval_hours,
                    :last_run_at, :next_run_at, :coordination_key, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, platform, schedule_type) DO UPDATE SET
                    native_schedule_id = excluded.native_schedule_id,
                    enabled = excluded.enabled,
                    schedule_type = excluded.schedule_type,
                    interval_hours = excluded.interval_hours,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    coordination_key = excluded.coordination_key,
                    updated_at = excluded.updated_at
                """,
                record.to_dict(),
            )
            row = _row(
                connection,
                "SELECT * FROM platform_schedule_registry WHERE creator_id = ? AND platform = ? AND schedule_type = ?",
                (record.creator_id, record.platform.value, record.schedule_type),
            )
        return self._row_to_schedule(row) if row else record

    def list_platform_schedule_registry_entries(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_schedule_registry WHERE creator_id = ? ORDER BY platform, created_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_schedule(row) for row in rows]

    def upsert_platform_manual_import_status(self, record: PlatformManualImportStatus) -> PlatformManualImportStatus:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_manual_import_status (
                    id, creator_id, platform, data_category, last_import_at, last_period_start,
                    last_period_end, current_status, missing_periods_json, recommended_action,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform, :data_category, :last_import_at, :last_period_start,
                    :last_period_end, :current_status, :missing_periods_json, :recommended_action,
                    :created_at, :updated_at
                )
                ON CONFLICT(creator_id, platform, data_category) DO UPDATE SET
                    last_import_at = excluded.last_import_at,
                    last_period_start = excluded.last_period_start,
                    last_period_end = excluded.last_period_end,
                    current_status = excluded.current_status,
                    missing_periods_json = excluded.missing_periods_json,
                    recommended_action = excluded.recommended_action,
                    updated_at = excluded.updated_at
                """,
                record.to_dict(),
            )
            row = _row(
                connection,
                "SELECT * FROM platform_manual_import_status WHERE creator_id = ? AND platform = ? AND data_category = ?",
                (record.creator_id, record.platform.value, record.data_category.value),
            )
        return self._row_to_manual_status(row) if row else record

    def list_platform_manual_import_status(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_manual_import_status WHERE creator_id = ? ORDER BY platform, data_category",
                (creator_id,),
            ).fetchall()
        return [self._row_to_manual_status(row) for row in rows]

    def upsert_platform_integration_event(self, record: PlatformIntegrationEvent) -> PlatformIntegrationEvent:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_integration_events (
                    id, creator_id, platform, platform_connection_id, event_type, severity, message,
                    details_json, occurred_at, created_at
                ) VALUES (
                    :id, :creator_id, :platform, :platform_connection_id, :event_type, :severity, :message,
                    :details_json, :occurred_at, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    severity = excluded.severity,
                    message = excluded.message,
                    details_json = excluded.details_json
                """,
                record.to_dict(),
            )
            row = _row(connection, "SELECT * FROM platform_integration_events WHERE id = ?", (record.id,))
        return self._row_to_event(row) if row else record

    def list_platform_integration_events(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_integration_events WHERE creator_id = ? ORDER BY occurred_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def upsert_platform_report(self, record: PlatformReport) -> PlatformReport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_reports (
                    id, creator_id, report_type, platform_scope_json, period_start, period_end,
                    source_fingerprint, report_json, created_at
                ) VALUES (
                    :id, :creator_id, :report_type, :platform_scope_json, :period_start, :period_end,
                    :source_fingerprint, :report_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    report_type = excluded.report_type,
                    platform_scope_json = excluded.platform_scope_json,
                    period_start = excluded.period_start,
                    period_end = excluded.period_end,
                    source_fingerprint = excluded.source_fingerprint,
                    report_json = excluded.report_json
                """,
                record.to_dict(),
            )
            row = _row(connection, "SELECT * FROM platform_reports WHERE id = ?", (record.id,))
        return self._row_to_report(row) if row else record

    def get_platform_report(self, report_id: str) -> PlatformReport | None:
        with self._database.connect() as connection:
            row = _row(connection, "SELECT * FROM platform_reports WHERE id = ?", (report_id,))
        return self._row_to_report(row) if row else None

    def list_platform_reports(self, creator_id: str):
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM platform_reports WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [self._row_to_report(row) for row in rows]

    @staticmethod
    def _row_to_connection(row: sqlite3.Row) -> PlatformConnectionSummary:
        return PlatformConnectionSummary(
            id=row["id"],
            creator_id=row["creator_id"],
            platform=PlatformKind(row["platform"]),
            connector_type=ConnectorType(row["connector_type"]),
            native_connection_id=row["native_connection_id"],
            status=CommonConnectionStatus(row["status"]),
            display_name=row["display_name"],
            account_identifier=row["account_identifier"],
            credential_reference=row["credential_reference"],
            granted_permissions_json=row["granted_permissions_json"],
            capability_snapshot_json=row["capability_snapshot_json"],
            health_status=HealthStatus(row["health_status"]),
            health_checked_at=from_iso_z(row["health_checked_at"]),
            connected_at=from_iso_z(row["connected_at"]),
            disconnected_at=from_iso_z(row["disconnected_at"]),
            native_status=row["native_status"],
            native_error_code=row["native_error_code"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
            updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_health(row: sqlite3.Row) -> PlatformConnectionHealth:
        return PlatformConnectionHealth(
            id=row["id"],
            creator_id=row["creator_id"],
            platform_connection_id=row["platform_connection_id"],
            status=HealthStatus(row["status"]),
            severity=Severity(row["severity"]),
            error_code=row["error_code"],
            message=row["message"],
            details_json=row["details_json"],
            checked_at=from_iso_z(row["checked_at"]) or utc_now(),
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_capability(row: sqlite3.Row) -> PlatformCapabilitySnapshot:
        return PlatformCapabilitySnapshot(
            id=row["id"],
            creator_id=row["creator_id"],
            platform_connection_id=row["platform_connection_id"],
            capability_key=row["capability_key"],
            availability_status=CapabilityAvailabilityStatus(row["availability_status"]),
            access_level=row["access_level"],
            permission_required=row["permission_required"],
            limitation_code=row["limitation_code"],
            source_version=row["source_version"],
            observed_at=from_iso_z(row["observed_at"]) or utc_now(),
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_availability(row: sqlite3.Row) -> PlatformDataAvailability:
        return PlatformDataAvailability(
            id=row["id"],
            creator_id=row["creator_id"],
            platform_connection_id=row["platform_connection_id"],
            data_category=DataCategory(row["data_category"]),
            data_key=row["data_key"],
            availability_status=DataAvailabilityStatus(row["availability_status"]),
            source_type=DataAvailabilitySourceType(row["source_type"]),
            automatic_available=bool(row["automatic_available"]),
            manual_import_available=bool(row["manual_import_available"]),
            period_semantics=row["period_semantics"],
            cumulative_semantics=row["cumulative_semantics"],
            limitations_json=row["limitations_json"],
            observed_at=from_iso_z(row["observed_at"]) or utc_now(),
            created_at=from_iso_z(row["created_at"]) or utc_now(),
            updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_group(row: sqlite3.Row) -> PlatformSyncGroup:
        return PlatformSyncGroup(
            id=row["id"],
            creator_id=row["creator_id"],
            name=row["name"],
            sync_mode=SyncMode(row["sync_mode"]),
            status=SyncGroupStatus(row["status"]),
            configuration_json=row["configuration_json"],
            platform_count=row["platform_count"],
            started_at=from_iso_z(row["started_at"]) or utc_now(),
            completed_at=from_iso_z(row["completed_at"]),
            warning_count=row["warning_count"],
            error_count=row["error_count"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_group_item(row: sqlite3.Row) -> PlatformSyncGroupItem:
        return PlatformSyncGroupItem(
            id=row["id"],
            sync_group_id=row["sync_group_id"],
            platform=PlatformKind(row["platform"]),
            native_connection_id=row["native_connection_id"],
            native_sync_run_id=row["native_sync_run_id"],
            status=SyncItemStatus(row["status"]),
            sequence_order=row["sequence_order"],
            started_at=from_iso_z(row["started_at"]),
            completed_at=from_iso_z(row["completed_at"]),
            warning_codes_json=row["warning_codes_json"],
            error_code=row["error_code"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> PlatformScheduleRegistryEntry:
        return PlatformScheduleRegistryEntry(
            id=row["id"],
            creator_id=row["creator_id"],
            platform=PlatformKind(row["platform"]),
            native_schedule_id=row["native_schedule_id"],
            enabled=bool(row["enabled"]),
            schedule_type=row["schedule_type"],
            interval_hours=row["interval_hours"],
            last_run_at=from_iso_z(row["last_run_at"]),
            next_run_at=from_iso_z(row["next_run_at"]),
            coordination_key=row["coordination_key"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
            updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_manual_status(row: sqlite3.Row) -> PlatformManualImportStatus:
        return PlatformManualImportStatus(
            id=row["id"],
            creator_id=row["creator_id"],
            platform=PlatformKind(row["platform"]),
            data_category=DataCategory(row["data_category"]),
            last_import_at=from_iso_z(row["last_import_at"]),
            last_period_start=from_iso_z(row["last_period_start"]),
            last_period_end=from_iso_z(row["last_period_end"]),
            current_status=row["current_status"],
            missing_periods_json=row["missing_periods_json"],
            recommended_action=row["recommended_action"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
            updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> PlatformIntegrationEvent:
        return PlatformIntegrationEvent(
            id=row["id"],
            creator_id=row["creator_id"],
            platform=PlatformKind(row["platform"]),
            platform_connection_id=row["platform_connection_id"],
            event_type=row["event_type"],
            severity=row["severity"],
            message=row["message"],
            details_json=row["details_json"],
            occurred_at=from_iso_z(row["occurred_at"]) or utc_now(),
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )

    @staticmethod
    def _row_to_report(row: sqlite3.Row) -> PlatformReport:
        return PlatformReport(
            id=row["id"],
            creator_id=row["creator_id"],
            report_type=row["report_type"],
            platform_scope_json=row["platform_scope_json"],
            period_start=from_iso_z(row["period_start"]),
            period_end=from_iso_z(row["period_end"]),
            source_fingerprint=row["source_fingerprint"],
            report_json=row["report_json"],
            created_at=from_iso_z(row["created_at"]) or utc_now(),
        )
