"""Servicio comun de consolidacion de integraciones de plataforma."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creator_intelligence_studio.domain.platform_integrations.connection_types import CommonConnectionStatus, PlatformKind
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
from creator_intelligence_studio.domain.platform_integrations.health_types import HealthStatus, Severity
from creator_intelligence_studio.domain.platform_integrations.sync_types import SyncGroupStatus, SyncMode
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_platform_integration_repository import SQLitePlatformIntegrationRepository
from creator_intelligence_studio.infrastructure.platform_integrations import (
    PlatformConnectorRegistry,
    PlatformSyncOrchestrator,
    build_platform_connector_registry,
    build_platform_health_record,
)
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class PlatformOverviewRow:
    platform: str
    connection_status: str
    selected_account: str | None
    last_successful_sync: str | None
    next_scheduled_sync: str | None
    health_status: str
    warnings: int
    automatic_data_coverage: str
    manual_data_coverage: str
    action_required: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "platform": self.platform,
            "connection_status": self.connection_status,
            "selected_account": self.selected_account,
            "last_successful_sync": self.last_successful_sync,
            "next_scheduled_sync": self.next_scheduled_sync,
            "health_status": self.health_status,
            "warnings": self.warnings,
            "automatic_data_coverage": self.automatic_data_coverage,
            "manual_data_coverage": self.manual_data_coverage,
            "action_required": self.action_required,
        }


class PlatformIntegrationService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        database: SQLiteDatabase,
        repository: SQLitePlatformIntegrationRepository,
        youtube_service: Any | None = None,
        instagram_service: Any | None = None,
        tiktok_service: Any | None = None,
        analytics_service: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.database = database
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.platforms")
        self.registry: PlatformConnectorRegistry = build_platform_connector_registry(
            youtube_service=youtube_service,
            instagram_service=instagram_service,
            tiktok_service=tiktok_service,
            analytics_service=analytics_service,
        )
        self.orchestrator = PlatformSyncOrchestrator(self.registry, self.repository)

    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]:
        connections: list[PlatformConnectionSummary] = []
        for adapter in self.registry.adapters():
            for connection in adapter.list_connections(creator_id):
                connections.append(self.repository.upsert_platform_connection(connection))
        return connections

    def get_connection(self, connection_id: str) -> PlatformConnectionSummary | None:
        for adapter in self.registry.adapters():
            connection = adapter.get_connection(connection_id)
            if connection is not None:
                return connection
        return self.repository.get_platform_connection(connection_id)

    def verify_connection(self, connection_id: str):
        connection = self.get_connection(connection_id)
        if connection is None:
            return None
        adapter = self.registry.get(connection.platform)
        result = adapter.verify_connection(connection.native_connection_id) if adapter is not None else None
        health = build_platform_health_record(creator_id=connection.creator_id, platform_connection=connection)
        self.repository.upsert_platform_connection_health(health)
        return result

    def disconnect_connection(self, connection_id: str):
        connection = self.get_connection(connection_id)
        if connection is None:
            return None
        adapter = self.registry.get(connection.platform)
        result = adapter.disconnect(connection.native_connection_id) if adapter is not None else None
        return result

    def revoke_connection(self, connection_id: str):
        connection = self.get_connection(connection_id)
        if connection is None:
            return None
        adapter = self.registry.get(connection.platform)
        result = adapter.revoke(connection.native_connection_id) if adapter is not None else None
        return result

    def list_health_checks(self, creator_id: str) -> list[PlatformConnectionHealth]:
        records: list[PlatformConnectionHealth] = []
        for connection in self.list_connections(creator_id):
            health = build_platform_health_record(creator_id=creator_id, platform_connection=connection)
            records.append(self.repository.upsert_platform_connection_health(health))
        return records

    def list_capabilities(self, creator_id: str) -> list[PlatformCapabilitySnapshot]:
        snapshots: list[PlatformCapabilitySnapshot] = []
        for connection in self.list_connections(creator_id):
            adapter = self.registry.get(connection.platform)
            if adapter is None:
                continue
            for snapshot in adapter.list_capabilities(connection.id):
                snapshots.append(self.repository.upsert_platform_capability_snapshot(snapshot))
        return snapshots

    def list_data_availability(self, creator_id: str) -> list[PlatformDataAvailability]:
        records: list[PlatformDataAvailability] = []
        for connection in self.list_connections(creator_id):
            adapter = self.registry.get(connection.platform)
            if adapter is None:
                continue
            for record in adapter.list_data_availability(connection.id):
                records.append(self.repository.upsert_platform_data_availability(record))
        return records

    def list_manual_import_status(self, creator_id: str) -> list[PlatformManualImportStatus]:
        return self.repository.list_platform_manual_import_status(creator_id)

    def list_sync_groups(self, creator_id: str) -> list[PlatformSyncGroup]:
        return self.repository.list_platform_sync_groups(creator_id)

    def list_sync_group_items(self, sync_group_id: str) -> list[PlatformSyncGroupItem]:
        return self.repository.list_platform_sync_group_items(sync_group_id)

    def list_schedule_registry(self, creator_id: str) -> list[PlatformScheduleRegistryEntry]:
        return self.repository.list_platform_schedule_registry_entries(creator_id)

    def list_events(self, creator_id: str) -> list[PlatformIntegrationEvent]:
        return self.repository.list_platform_integration_events(creator_id)

    def list_reports(self, creator_id: str) -> list[PlatformReport]:
        return self.repository.list_platform_reports(creator_id)

    def start_sync(
        self,
        *,
        creator_id: str,
        platforms: list[str] | None = None,
        mode: str = "sequential",
        incremental: bool = True,
    ):
        selected = [PlatformKind(platform) for platform in platforms] if platforms else [PlatformKind.YOUTUBE, PlatformKind.INSTAGRAM, PlatformKind.TIKTOK, PlatformKind.MANUAL_OTHER]
        result = self.orchestrator.start_sync(
            creator_id=creator_id,
            platforms=selected,
            sync_mode=SyncMode(mode),
            configuration={"incremental": incremental, "creator_id": creator_id},
        )
        return result

    def resume_sync(self, group_id: str):
        group = self.repository.get_platform_sync_group(group_id)
        if group is None:
            return None
        return group

    def cancel_sync(self, group_id: str):
        group = self.repository.get_platform_sync_group(group_id)
        if group is None:
            return None
        cancelled = self.repository.upsert_platform_sync_group(
            PlatformSyncGroup(
                id=group.id,
                creator_id=group.creator_id,
                name=group.name,
                sync_mode=group.sync_mode,
                status=SyncGroupStatus.CANCELLED,
                configuration_json=group.configuration_json,
                platform_count=group.platform_count,
                started_at=group.started_at,
                completed_at=utc_now(),
                warning_count=group.warning_count,
                error_count=group.error_count,
                created_at=group.created_at,
            )
        )
        return cancelled

    def build_overview(self, creator_id: str) -> list[PlatformOverviewRow]:
        connections = self.list_connections(creator_id)
        health_by_connection = {health.platform_connection_id: health for health in self.list_health_checks(creator_id)}
        schedules = {entry.platform.value: entry for entry in self.list_schedule_registry(creator_id)}
        sync_groups = self.list_sync_groups(creator_id)
        last_sync_by_platform: dict[str, str | None] = {platform.value: None for platform in PlatformKind}
        for group in sync_groups:
            for item in self.list_sync_group_items(group.id):
                if item.completed_at is not None:
                    last_sync_by_platform[item.platform.value] = item.completed_at.isoformat()
        rows: list[PlatformOverviewRow] = []
        for platform in PlatformKind:
            connection = next((item for item in connections if item.platform == platform), None)
            health = health_by_connection.get(connection.id) if connection is not None else None
            schedule = schedules.get(platform.value)
            rows.append(
                PlatformOverviewRow(
                    platform=platform.value,
                    connection_status=connection.status.value if connection is not None else "not_configured",
                    selected_account=connection.account_identifier if connection is not None else None,
                    last_successful_sync=last_sync_by_platform.get(platform.value),
                    next_scheduled_sync=schedule.next_run_at.isoformat() if schedule and schedule.next_run_at else None,
                    health_status=health.status.value if health is not None else "unknown",
                    warnings=0 if health is None else (1 if health.severity != Severity.INFO else 0),
                    automatic_data_coverage="available" if connection is not None else "unknown",
                    manual_data_coverage="manual_import_only" if platform == PlatformKind.TIKTOK else "available" if platform == PlatformKind.MANUAL_OTHER else "partially_available",
                    action_required=None if connection is not None else "connect",
                )
            )
        return rows

    def build_privacy_summary(self, connection_id: str) -> dict[str, object]:
        connection = self.get_connection(connection_id)
        if connection is None:
            return {"connection_id": connection_id, "available": False}
        adapter = self.registry.get(connection.platform)
        summary = adapter.get_privacy_summary(connection.native_connection_id) if adapter is not None else {}
        summary.update(
            {
                "connection_id": connection.id,
                "platform": connection.platform.value,
                "status": connection.status.value,
                "credential_reference": connection.credential_reference,
                "tokens_in_sqlite": False,
                "read_only": True,
                "write_disabled": True,
            }
        )
        return summary

    def build_report(self, creator_id: str, report_type: str, *, period_start: str | None = None, period_end: str | None = None) -> PlatformReport:
        connections = self.list_connections(creator_id)
        health = [health.to_dict() for health in self.list_health_checks(creator_id)]
        capabilities: list[dict[str, object]] = []
        data_availability: list[dict[str, object]] = []
        for connection in connections:
            adapter = self.registry.get(connection.platform)
            if adapter is None:
                continue
            for snapshot in adapter.list_capabilities(connection.id):
                capabilities.append(snapshot.to_dict())
            for record in adapter.list_data_availability(connection.id):
                data_availability.append(record.to_dict())
        payload = {
            "creator_id": creator_id,
            "report_type": report_type,
            "connections": [connection.to_dict() for connection in connections],
            "health": health,
            "capabilities": capabilities,
            "data_availability": data_availability,
            "manual_import_status": [item.to_dict() for item in self.list_manual_import_status(creator_id)],
            "sync_groups": [group.to_dict() for group in self.list_sync_groups(creator_id)],
            "privacy": [self.build_privacy_summary(connection.id) for connection in connections],
        }
        report = PlatformReport(
            id=f"report-{report_type}-{creator_id}",
            creator_id=creator_id,
            report_type=report_type,
            platform_scope_json=json.dumps(["youtube", "instagram", "tiktok", "manual_other"], ensure_ascii=False),
            period_start=period_start,
            period_end=period_end,
            source_fingerprint=f"{creator_id}:{report_type}:{len(payload['connections'])}:{len(payload['sync_groups'])}",
            report_json=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
            created_at=utc_now(),
        )
        return self.repository.upsert_platform_report(report)

    def export_report(self, report_id: str, format_name: str = "json", *, destination: Path | None = None):
        report = self.repository.get_platform_report(report_id)
        if report is None:
            return None
        payload = json.loads(report.report_json)
        if destination is None:
            destination = self.paths.artifacts_directory / "platforms" / f"{report_id}.{format_name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif format_name == "txt":
            lines = [f"{report.report_type}"]
            for key, value in payload.items():
                lines.append(f"{key}: {value}")
            destination.write_text("\n".join(lines), encoding="utf-8")
        elif format_name == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["key", "value"])
            for key, value in payload.items():
                writer.writerow([key, json.dumps(value, ensure_ascii=False, default=str)])
            destination.write_text(buffer.getvalue(), encoding="utf-8", newline="")
        else:
            raise ValueError("Formato de exportacion no soportado.")
        return destination

    def build_background_tasks(self, creator_id: str):
        tasks = []
        for group in self.list_sync_groups(creator_id):
            items = self.list_sync_group_items(group.id)
            tasks.append(
                {
                    "task_id": group.id,
                    "title": f"Platform sync group: {group.name}",
                    "status": group.status.value,
                    "stage_name": group.sync_mode.value,
                    "progress_percent": 100.0 if group.status in {SyncGroupStatus.COMPLETED, SyncGroupStatus.COMPLETED_WITH_WARNINGS} else 50.0 if group.status == SyncGroupStatus.RUNNING else 0.0,
                    "message": f"{len(items)} items",
                    "cancellable": group.status in {SyncGroupStatus.RUNNING, SyncGroupStatus.QUEUED},
                    "payload": {
                        "kind": "platform_sync_group",
                        "group": group.to_dict(),
                        "items": [item.to_dict() for item in items],
                    },
                }
            )
        return tasks
