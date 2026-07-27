"""Orquestador unificado de sincronizacion por plataforma."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind
from creator_intelligence_studio.domain.platform_integrations.entities import PlatformSyncGroup, PlatformSyncGroupItem
from creator_intelligence_studio.domain.platform_integrations.sync_types import SyncGroupStatus, SyncItemStatus, SyncMode
from creator_intelligence_studio.shared.dates import utc_now

from .connector_registry import PlatformConnectorRegistry


@dataclass(slots=True)
class PlatformSyncResult:
    group: PlatformSyncGroup
    items: list[PlatformSyncGroupItem]
    warnings: list[str]
    errors: list[str]


class PlatformSyncOrchestrator:
    def __init__(self, registry: PlatformConnectorRegistry, repository) -> None:
        self.registry = registry
        self.repository = repository

    def start_sync(
        self,
        *,
        creator_id: str,
        platforms: list[PlatformKind],
        sync_mode: SyncMode = SyncMode.SEQUENTIAL,
        configuration: dict[str, object] | None = None,
    ) -> PlatformSyncResult:
        now = utc_now()
        group = PlatformSyncGroup(
            id=str(uuid4()),
            creator_id=creator_id,
            name="Unified platform sync",
            sync_mode=sync_mode,
            status=SyncGroupStatus.RUNNING,
            configuration_json=json.dumps(configuration or {}, ensure_ascii=False, sort_keys=True),
            platform_count=len(platforms),
            started_at=now,
            completed_at=None,
            warning_count=0,
            error_count=0,
            created_at=now,
        )
        self.repository.upsert_platform_sync_group(group)
        warnings: list[str] = []
        errors: list[str] = []
        items: list[PlatformSyncGroupItem] = []
        for index, platform in enumerate(platforms):
            adapter = self.registry.get(platform)
            native_connections = adapter.list_connections(creator_id) if adapter is not None else []
            native_connection_id = native_connections[0].native_connection_id if native_connections else None
            sync_item = PlatformSyncGroupItem(
                id=str(uuid4()),
                sync_group_id=group.id,
                platform=platform,
                native_connection_id=native_connection_id,
                native_sync_run_id=None,
                status=SyncItemStatus.QUEUED,
                sequence_order=index,
                started_at=None,
                completed_at=None,
                warning_codes_json="[]",
                error_code=None,
                created_at=now,
            )
            self.repository.upsert_platform_sync_group_item(sync_item)
            if adapter is None or native_connection_id is None:
                sync_item = self.repository.upsert_platform_sync_group_item(
                    PlatformSyncGroupItem(
                        id=sync_item.id,
                        sync_group_id=sync_item.sync_group_id,
                        platform=sync_item.platform,
                        native_connection_id=sync_item.native_connection_id,
                        native_sync_run_id=None,
                        status=SyncItemStatus.SKIPPED,
                        sequence_order=sync_item.sequence_order,
                        started_at=sync_item.started_at,
                        completed_at=utc_now(),
                        warning_codes_json=json.dumps(["connection_missing"], ensure_ascii=False),
                        error_code=None,
                        created_at=sync_item.created_at,
                    )
                )
                warnings.append(f"{platform.value}: connection_missing")
                items.append(sync_item)
                continue
            try:
                sync_item = self.repository.upsert_platform_sync_group_item(
                    PlatformSyncGroupItem(
                        id=sync_item.id,
                        sync_group_id=sync_item.sync_group_id,
                        platform=sync_item.platform,
                        native_connection_id=sync_item.native_connection_id,
                        native_sync_run_id=sync_item.native_sync_run_id,
                        status=SyncItemStatus.RUNNING,
                        sequence_order=sync_item.sequence_order,
                        started_at=now,
                        completed_at=None,
                        warning_codes_json="[]",
                        error_code=None,
                        created_at=sync_item.created_at,
                    )
                )
                result = adapter.start_sync(creator_id=creator_id, connection_id=native_connection_id, sync_type="incremental" if configuration and configuration.get("incremental") else "profile")
                native_run = getattr(result, "run", None)
                sync_item = self.repository.upsert_platform_sync_group_item(
                    PlatformSyncGroupItem(
                        id=sync_item.id,
                        sync_group_id=sync_item.sync_group_id,
                        platform=sync_item.platform,
                        native_connection_id=sync_item.native_connection_id,
                        native_sync_run_id=getattr(native_run, "id", None),
                        status=SyncItemStatus.COMPLETED,
                        sequence_order=sync_item.sequence_order,
                        started_at=sync_item.started_at,
                        completed_at=utc_now(),
                        warning_codes_json=json.dumps(list(getattr(result, "warnings", ())), ensure_ascii=False),
                        error_code=None,
                        created_at=sync_item.created_at,
                    )
                )
                if getattr(result, "warnings", None):
                    warnings.extend(list(getattr(result, "warnings")))
            except Exception as exc:
                errors.append(f"{platform.value}: {exc}")
                sync_item = self.repository.upsert_platform_sync_group_item(
                    PlatformSyncGroupItem(
                        id=sync_item.id,
                        sync_group_id=sync_item.sync_group_id,
                        platform=sync_item.platform,
                        native_connection_id=sync_item.native_connection_id,
                        native_sync_run_id=sync_item.native_sync_run_id,
                        status=SyncItemStatus.FAILED,
                        sequence_order=sync_item.sequence_order,
                        started_at=sync_item.started_at,
                        completed_at=utc_now(),
                        warning_codes_json="[]",
                        error_code=type(exc).__name__,
                        created_at=sync_item.created_at,
                    )
                )
            items.append(sync_item)
        group = self.repository.upsert_platform_sync_group(
            PlatformSyncGroup(
                id=group.id,
                creator_id=group.creator_id,
                name=group.name,
                sync_mode=group.sync_mode,
                status=SyncGroupStatus.COMPLETED if not errors and not warnings else SyncGroupStatus.COMPLETED_WITH_WARNINGS if not errors else SyncGroupStatus.PARTIALLY_COMPLETED,
                configuration_json=group.configuration_json,
                platform_count=group.platform_count,
                started_at=group.started_at,
                completed_at=utc_now(),
                warning_count=len(warnings),
                error_count=len(errors),
                created_at=group.created_at,
            )
        )
        return PlatformSyncResult(group=group, items=items, warnings=warnings, errors=errors)
