"""Contrato y adaptadores nativos para integraciones de plataforma."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from creator_intelligence_studio.application.services.instagram_integration_service import InstagramIntegrationService
from creator_intelligence_studio.application.services.tiktok_integration_service import TikTokIntegrationService
from creator_intelligence_studio.application.services.youtube_integration_service import YouTubeIntegrationService
from creator_intelligence_studio.domain.analytics.entities import AnalyticsPlatform
from creator_intelligence_studio.domain.platform_integrations.capability_types import CapabilityCategory
from creator_intelligence_studio.domain.platform_integrations.connection_types import CommonConnectionStatus, ConnectorType, PlatformKind
from creator_intelligence_studio.domain.platform_integrations.entities import PlatformConnectionSummary
from creator_intelligence_studio.domain.platform_integrations.health_types import HealthStatus
from creator_intelligence_studio.shared.dates import utc_now

from .capability_mapper import build_capability_snapshots
from .data_availability_mapper import build_data_availability_records
from .health_checker import build_platform_health_record


class PlatformConnectorAdapter(Protocol):
    platform: PlatformKind
    connector_name: str

    def is_available(self) -> bool: ...
    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]: ...
    def get_connection(self, connection_id: str) -> PlatformConnectionSummary | None: ...
    def verify_connection(self, connection_id: str): ...
    def disconnect(self, connection_id: str): ...
    def revoke(self, connection_id: str): ...
    def list_accounts_or_channels(self, creator_id: str): ...
    def list_capabilities(self, connection_id: str): ...
    def list_data_availability(self, connection_id: str): ...
    def start_sync(self, **kwargs): ...
    def resume_sync(self, run_id: str): ...
    def cancel_sync(self, run_id: str): ...
    def get_sync_run(self, run_id: str): ...
    def list_sync_history(self, creator_id: str): ...
    def estimate_sync_cost(self, **kwargs): ...
    def export_report(self, run_id: str, format_name: str = "json", *, destination=None): ...
    def get_privacy_summary(self, connection_id: str) -> dict[str, Any]: ...


def _json_scopes(value: str | None) -> str:
    if not value:
        return "[]"
    try:
        parsed = json.loads(value)
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    except Exception:
        return "[]"


def _to_common_status(value: str) -> CommonConnectionStatus:
    lowered = str(value or "").lower()
    if lowered in {"connected", "verified", "active"}:
        return CommonConnectionStatus.CONNECTED
    if lowered in {"connected_with_warnings"}:
        return CommonConnectionStatus.CONNECTED_WITH_WARNINGS
    if lowered in {"disconnected"}:
        return CommonConnectionStatus.DISCONNECTED
    if lowered in {"revoked", "token_revoked"}:
        return CommonConnectionStatus.REVOKED
    if lowered in {"expired", "token_expired"}:
        return CommonConnectionStatus.EXPIRED
    if lowered in {"insufficient_scope", "insufficient_permissions"}:
        return CommonConnectionStatus.INSUFFICIENT_PERMISSIONS
    if lowered in {"app_review_required"}:
        return CommonConnectionStatus.APP_REVIEW_REQUIRED
    if lowered in {"product_not_approved", "scope_not_approved"}:
        return CommonConnectionStatus.PRODUCT_APPROVAL_REQUIRED
    if lowered in {"unavailable"}:
        return CommonConnectionStatus.UNAVAILABLE
    if lowered in {"error", "failed"}:
        return CommonConnectionStatus.ERROR
    return CommonConnectionStatus.UNKNOWN


def _build_connection_summary(
    *,
    creator_id: str,
    platform: PlatformKind,
    connector_type: ConnectorType,
    native_id: str,
    native_status: str,
    credential_reference: str | None,
    granted_permissions_json: str | None,
    display_name: str | None = None,
    account_identifier: str | None = None,
    health_status: HealthStatus | None = None,
    connected_at: datetime | None = None,
    disconnected_at: datetime | None = None,
    native_error_code: str | None = None,
) -> PlatformConnectionSummary:
    now = utc_now()
    return PlatformConnectionSummary(
        id=f"{platform.value}:{native_id}",
        creator_id=creator_id,
        platform=platform,
        connector_type=connector_type,
        native_connection_id=native_id,
        status=_to_common_status(native_status),
        display_name=display_name,
        account_identifier=account_identifier,
        credential_reference=credential_reference,
        granted_permissions_json=granted_permissions_json or "[]",
        capability_snapshot_json="{}",
        health_status=health_status or HealthStatus.UNKNOWN,
        health_checked_at=None,
        connected_at=connected_at,
        disconnected_at=disconnected_at,
        native_status=native_status,
        native_error_code=native_error_code,
        created_at=now,
        updated_at=now,
    )


@dataclass(slots=True)
class _BaseAdapter:
    service: Any

    def is_available(self) -> bool:
        return self.service is not None

    def get_connection(self, connection_id: str):
        if hasattr(self.service, "get_connection"):
            return self.service.get_connection(connection_id)
        return next((connection for connection in self.list_connections(connection_id) if connection.id == connection_id), None)

    def estimate_sync_cost(self, **kwargs):
        return {"estimated_usage": None, "warnings": []}

    def get_privacy_summary(self, connection_id: str) -> dict[str, Any]:
        return {
            "connection_id": connection_id,
            "read_only": True,
            "write_disabled": True,
            "downloaded_content": False,
            "tokens_in_sqlite": False,
        }


@dataclass(slots=True)
class YouTubeConnectorAdapter(_BaseAdapter):
    platform: PlatformKind = PlatformKind.YOUTUBE
    connector_name: str = "youtube_native"

    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]:
        if self.service is None:
            return []
        connections = []
        for native in self.service.list_connections(creator_id):
            connections.append(
                _build_connection_summary(
                    creator_id=native.creator_id,
                    platform=self.platform,
                    connector_type=ConnectorType.NATIVE,
                    native_id=native.id,
                    native_status=native.status.value,
                    credential_reference=getattr(native, "credential_reference", None),
                    granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
                    account_identifier=getattr(native, "google_account_identifier", None),
                    connected_at=getattr(native, "connected_at", None),
                    disconnected_at=getattr(native, "disconnected_at", None),
                )
            )
        return connections

    def get_connection(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        native = self.service.get_connection(native_id) if hasattr(self.service, "get_connection") else None
        if native is None:
            return None
        return _build_connection_summary(
            creator_id=native.creator_id,
            platform=self.platform,
            connector_type=ConnectorType.NATIVE,
            native_id=native.id,
            native_status=native.status.value,
            credential_reference=getattr(native, "credential_reference", None),
            granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
            account_identifier=getattr(native, "google_account_identifier", None),
            connected_at=getattr(native, "connected_at", None),
            disconnected_at=getattr(native, "disconnected_at", None),
            native_error_code=getattr(native, "native_error_code", None),
        )

    def verify_connection(self, connection_id: str):
        return self.service.verify_connection(connection_id)

    def disconnect(self, connection_id: str):
        return self.service.disconnect_connection(connection_id)

    def revoke(self, connection_id: str):
        return self.service.revoke_connection(connection_id)

    def list_accounts_or_channels(self, creator_id: str):
        return self.service.list_channels(creator_id)

    def list_capabilities(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        connection = self.service.get_connection(native_id)
        if connection is None:
            return []
        return build_capability_snapshots(
            creator_id=connection.creator_id,
            platform_connection_id=connection_id if connection_id.startswith(f"{self.platform.value}:") else f"{self.platform.value}:{native_id}",
            platform=self.platform,
            source_version=getattr(connection, "created_at", None).isoformat() if getattr(connection, "created_at", None) else None,
        )

    def list_data_availability(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        connection = self.service.get_connection(native_id)
        if connection is None:
            return []
        return build_data_availability_records(
            creator_id=connection.creator_id,
            platform_connection_id=connection_id if connection_id.startswith(f"{self.platform.value}:") else f"{self.platform.value}:{native_id}",
            platform=self.platform,
        )

    def start_sync(self, **kwargs):
        creator_id = kwargs.get("creator_id")
        connection_id = kwargs.get("connection_id")
        sync_type = kwargs.get("sync_type") or "incremental"
        cursor = kwargs.get("cursor")
        full_resync = bool(kwargs.get("full_resync", False))
        include_analytics = bool(kwargs.get("include_analytics", True))
        include_thumbnails = bool(kwargs.get("include_thumbnails", False))
        metrics = kwargs.get("metrics")
        channels = self.service.list_channels(creator_id) if creator_id else []
        channel_id = kwargs.get("channel_id")
        if channel_id is None and channels:
            selected = next((channel for channel in channels if getattr(channel, "selected_for_sync", False)), channels[0])
            channel_id = selected.id
        if sync_type == "content":
            return self.service.sync_content(creator_id=creator_id, channel_id=channel_id, cursor=cursor)
        if sync_type == "analytics":
            return self.service.sync_analytics(creator_id=creator_id, channel_id=channel_id, cursor=cursor, metrics=metrics)
        if sync_type == "thumbnail_metadata":
            return self.service.sync_thumbnail_metadata(creator_id=creator_id, channel_id=channel_id, cursor=cursor)
        if sync_type == "repair":
            return self.service.sync_repair(creator_id=creator_id, channel_id=channel_id)
        return self.service.sync_channel(
            creator_id=creator_id,
            channel_id=channel_id,
            sync_type=kwargs.get("native_sync_type", "incremental_sync"),
            cursor=cursor,
            full_resync=full_resync,
            include_analytics=include_analytics,
            include_thumbnails=include_thumbnails,
            metrics=metrics,
        )

    def resume_sync(self, run_id: str):
        return self.service.resume_sync(run_id)

    def cancel_sync(self, run_id: str):
        return self.service.interrupt_sync_run(run_id, reason="sync_group_cancelled")

    def get_sync_run(self, run_id: str):
        return self.service.get_sync_run(run_id)

    def list_sync_history(self, creator_id: str):
        return self.service.list_sync_runs(creator_id)

    def export_report(self, run_id: str, format_name: str = "json", *, destination=None):
        return self.service.export_sync_report(run_id, format_name, destination=destination)


@dataclass(slots=True)
class InstagramConnectorAdapter(_BaseAdapter):
    platform: PlatformKind = PlatformKind.INSTAGRAM
    connector_name: str = "instagram_native"

    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]:
        if self.service is None:
            return []
        connections = []
        for native in self.service.list_connections(creator_id):
            connections.append(
                _build_connection_summary(
                    creator_id=native.creator_id,
                    platform=self.platform,
                    connector_type=ConnectorType.NATIVE,
                    native_id=native.id,
                    native_status=native.status.value,
                    credential_reference=getattr(native, "credential_reference", None),
                    granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
                    account_identifier=getattr(native, "account_identifier", None),
                    connected_at=getattr(native, "connected_at", None),
                    disconnected_at=getattr(native, "disconnected_at", None),
                    native_error_code=getattr(native, "native_error_code", None),
                )
            )
        return connections

    def get_connection(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        native = self.service.show_connection(native_id)
        if native is None:
            return None
        return _build_connection_summary(
            creator_id=native.creator_id,
            platform=self.platform,
            connector_type=ConnectorType.NATIVE,
            native_id=native.id,
            native_status=native.status.value,
            credential_reference=getattr(native, "credential_reference", None),
            granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
            account_identifier=getattr(native, "account_identifier", None),
            connected_at=getattr(native, "connected_at", None),
            disconnected_at=getattr(native, "disconnected_at", None),
            native_error_code=getattr(native, "native_error_code", None),
        )

    def verify_connection(self, connection_id: str):
        return self.service.verify_connection(connection_id)

    def disconnect(self, connection_id: str):
        return self.service.disconnect_connection(connection_id)

    def revoke(self, connection_id: str):
        return self.service.revoke_connection(connection_id)

    def list_accounts_or_channels(self, creator_id: str):
        return self.service.list_accounts(creator_id)

    def list_capabilities(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        connection = self.service.show_connection(native_id)
        if connection is None:
            return []
        return build_capability_snapshots(creator_id=connection.creator_id, platform_connection_id=connection_id if connection_id.startswith(f"{self.platform.value}:") else f"{self.platform.value}:{native_id}", platform=self.platform)

    def list_data_availability(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        connection = self.service.show_connection(native_id)
        if connection is None:
            return []
        return build_data_availability_records(
            creator_id=connection.creator_id,
            platform_connection_id=connection_id if connection_id.startswith(f"{self.platform.value}:") else f"{self.platform.value}:{native_id}",
            platform=self.platform,
        )

    def start_sync(self, **kwargs):
        creator_id = kwargs.get("creator_id")
        account_id = kwargs.get("account_id")
        sync_type = kwargs.get("sync_type") or "incremental"
        cursor = kwargs.get("cursor")
        full_resync = bool(kwargs.get("full_resync", False))
        period = kwargs.get("period")
        remote_media_id = kwargs.get("remote_media_id")
        if account_id is None and creator_id:
            accounts = self.service.list_accounts(creator_id)
            selected = next((account for account in accounts if getattr(account, "selected_for_sync", False)), accounts[0] if accounts else None)
            account_id = getattr(selected, "id", None)
        if sync_type == "insights":
            return self.service.sync_insights(account_id=account_id, remote_media_id=remote_media_id, period=period)
        if sync_type == "media":
            return self.service.sync_media(account_id=account_id, cursor=cursor)
        if sync_type == "repair":
            return self.service.sync_repair(account_id=account_id)
        if sync_type == "account":
            return self.service.sync_account(account_id=account_id, cursor=cursor, full_resync=full_resync)
        return self.service.sync_incremental(account_id=account_id, cursor=cursor)

    def resume_sync(self, run_id: str):
        return self.service.resume_sync(run_id)

    def cancel_sync(self, run_id: str):
        return self.service.interrupt_background_task(run_id, reason="sync_group_cancelled")

    def get_sync_run(self, run_id: str):
        return self.service.show_sync_run(run_id)

    def list_sync_history(self, creator_id: str):
        return self.service.list_sync_runs(creator_id)

    def export_report(self, run_id: str, format_name: str = "json", *, destination=None):
        return self.service.export_report(run_id, format_name, destination=destination)


@dataclass(slots=True)
class TikTokConnectorAdapter(_BaseAdapter):
    platform: PlatformKind = PlatformKind.TIKTOK
    connector_name: str = "tiktok_native"

    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]:
        if self.service is None:
            return []
        connections = []
        for native in self.service.list_connections(creator_id):
            connections.append(
                _build_connection_summary(
                    creator_id=native.creator_id,
                    platform=self.platform,
                    connector_type=ConnectorType.NATIVE,
                    native_id=native.id,
                    native_status=native.status.value,
                    credential_reference=getattr(native, "credential_reference", None),
                    granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
                    account_identifier=getattr(native, "account_identifier", None),
                    connected_at=getattr(native, "connected_at", None),
                    disconnected_at=getattr(native, "disconnected_at", None),
                    native_error_code=getattr(native, "native_error_code", None),
                )
            )
        return connections

    def get_connection(self, connection_id: str):
        native_id = connection_id.split(":", 1)[1] if connection_id.startswith(f"{self.platform.value}:") else connection_id
        native = self.service.show_connection(native_id)
        if native is None:
            return None
        return _build_connection_summary(
            creator_id=native.creator_id,
            platform=self.platform,
            connector_type=ConnectorType.NATIVE,
            native_id=native.id,
            native_status=native.status.value,
            credential_reference=getattr(native, "credential_reference", None),
            granted_permissions_json=_json_scopes(getattr(native, "granted_scopes_json", None)),
            account_identifier=getattr(native, "account_identifier", None),
            connected_at=getattr(native, "connected_at", None),
            disconnected_at=getattr(native, "disconnected_at", None),
            native_error_code=getattr(native, "native_error_code", None),
        )

    def verify_connection(self, connection_id: str):
        return self.service.verify_connection(connection_id)

    def disconnect(self, connection_id: str):
        return self.service.disconnect_connection(connection_id)

    def revoke(self, connection_id: str):
        return self.service.revoke_connection(connection_id)

    def list_accounts_or_channels(self, creator_id: str):
        return self.service.list_profiles(creator_id)

    def list_capabilities(self, connection_id: str):
        connection = self.service.show_connection(connection_id)
        if connection is None:
            return []
        return build_capability_snapshots(creator_id=connection.creator_id, platform_connection_id=connection_id, platform=self.platform)

    def list_data_availability(self, connection_id: str):
        connection = self.service.show_connection(connection_id)
        if connection is None:
            return []
        return build_data_availability_records(creator_id=connection.creator_id, platform_connection_id=connection_id, platform=self.platform)

    def start_sync(self, **kwargs):
        creator_id = kwargs.get("creator_id")
        profile_id = kwargs.get("profile_id")
        sync_type = kwargs.get("sync_type") or "incremental"
        cursor = kwargs.get("cursor")
        max_count = int(kwargs.get("max_count", 20))
        full_resync = bool(kwargs.get("full_resync", False))
        if profile_id is None and creator_id:
            profiles = self.service.list_profiles(creator_id)
            selected = next((profile for profile in profiles if getattr(profile, "selected_for_sync", False)), profiles[0] if profiles else None)
            profile_id = getattr(selected, "id", None)
        if sync_type == "profile":
            return self.service.sync_profile(profile_id=profile_id, cursor=cursor)
        if sync_type == "videos":
            return self.service.sync_videos(profile_id=profile_id, cursor=cursor, max_count=max_count, full_resync=full_resync)
        if sync_type == "public_metrics":
            return self.service.sync_public_metrics(profile_id=profile_id, cursor=cursor)
        if sync_type == "repair":
            return self.service.sync_repair(profile_id=profile_id)
        return self.service.sync_incremental(profile_id=profile_id, cursor=cursor, max_count=max_count)

    def resume_sync(self, run_id: str):
        return self.service.resume_sync(run_id)

    def cancel_sync(self, run_id: str):
        return self.service.interrupt_sync_run(run_id, reason="sync_group_cancelled")

    def get_sync_run(self, run_id: str):
        return self.service.show_sync_run(run_id)

    def list_sync_history(self, creator_id: str):
        return self.service.list_sync_runs(creator_id)

    def export_report(self, run_id: str, format_name: str = "json", *, destination=None):
        return self.service.export_report(run_id, format_name, destination=destination)


@dataclass(slots=True)
class ManualImportConnectorAdapter:
    platform: PlatformKind = PlatformKind.MANUAL_OTHER
    connector_name: str = "manual_import"
    service: Any | None = None

    def is_available(self) -> bool:
        return self.service is not None

    def list_connections(self, creator_id: str) -> list[PlatformConnectionSummary]:
        now = utc_now()
        if self.service is None:
            return []
        has_manual_data = bool(self.service.list_imports(creator_id))
        status = CommonConnectionStatus.CONNECTED if has_manual_data else CommonConnectionStatus.NOT_CONFIGURED
        return [
            PlatformConnectionSummary(
                id=f"manual-{creator_id}",
                creator_id=creator_id,
                platform=self.platform,
                connector_type=ConnectorType.MANUAL,
                native_connection_id="manual_imports",
                status=status,
                display_name="Manual imports",
                account_identifier=creator_id,
                credential_reference=None,
                granted_permissions_json="[]",
                capability_snapshot_json="{}",
                health_status=HealthStatus.HEALTHY_WITH_WARNINGS if has_manual_data else HealthStatus.UNKNOWN,
                health_checked_at=now,
                connected_at=now if has_manual_data else None,
                disconnected_at=None,
                native_status="manual",
                native_error_code=None,
                created_at=now,
                updated_at=now,
            )
        ]

    def get_connection(self, connection_id: str):
        if not connection_id.startswith("manual-"):
            return None
        creator_id = connection_id.removeprefix("manual-")
        return next((connection for connection in self.list_connections(creator_id) if connection.id == connection_id), None)

    def verify_connection(self, connection_id: str):
        return {"connection_id": connection_id, "status": "manual"}

    def disconnect(self, connection_id: str):
        return {"connection_id": connection_id, "status": "manual"}

    def revoke(self, connection_id: str):
        return {"connection_id": connection_id, "status": "manual"}

    def list_accounts_or_channels(self, creator_id: str):
        if self.service is None:
            return []
        return self.service.list_channels(creator_id)

    def list_capabilities(self, connection_id: str):
        return []

    def list_data_availability(self, connection_id: str):
        return []

    def start_sync(self, **kwargs):
        return {"status": "manual_only"}

    def resume_sync(self, run_id: str):
        return {"run_id": run_id, "status": "manual_only"}

    def cancel_sync(self, run_id: str):
        return {"run_id": run_id, "status": "manual_only"}

    def get_sync_run(self, run_id: str):
        return None

    def list_sync_history(self, creator_id: str):
        return []

    def estimate_sync_cost(self, **kwargs):
        return {"estimated_usage": "manual_only", "warnings": []}

    def export_report(self, run_id: str, format_name: str = "json", *, destination=None):
        return destination

    def get_privacy_summary(self, connection_id: str) -> dict[str, Any]:
        return {
            "connection_id": connection_id,
            "read_only": True,
            "write_disabled": True,
            "manual_import_only": True,
            "tokens_in_sqlite": False,
        }
