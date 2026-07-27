"""Servicio principal de integracion de solo lectura con TikTok."""

from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.analytics.entities import AnalyticsChannel, AnalyticsImport, AnalyticsMetricDefinition, AnalyticsMetricSnapshot, AnalyticsPlatform, AnalyticsPublication
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsAggregationType, AnalyticsContentType, AnalyticsImportStatus, AnalyticsMetricCategory, AnalyticsPlatformStatus, AnalyticsQualityStatus, AnalyticsSourceType, AnalyticsValueType
from creator_intelligence_studio.domain.creative_packaging.entities import PackagingAsset
from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokAccessLevel, TikTokConnectionStatus, TikTokLinkMethod, TikTokProductApprovalState, TikTokRemoteStatus
from creator_intelligence_studio.domain.tiktok_integration.entities import (
    TikTokConnection,
    TikTokContentLink,
    TikTokCoverVersion,
    TikTokMetricImport,
    TikTokMetricValue,
    TikTokProfile,
    TikTokRateLimitUsage,
    TikTokRemoteVideo,
    TikTokSyncItem,
    TikTokSyncReport,
    TikTokSyncRun,
    TikTokSyncSchedule,
    TikTokVideoTextVersion,
)
from creator_intelligence_studio.domain.tiktok_integration.errors import (
    TikTokAuthorizationError,
    TikTokConnectionError,
    TikTokContentLinkError,
    TikTokIntegrationError,
    TikTokRateLimitError,
    TikTokSyncError,
)
from creator_intelligence_studio.domain.tiktok_integration.metric_types import TikTokMetricScope, TikTokMetricSourceType, TikTokMetricStatus
from creator_intelligence_studio.domain.tiktok_integration.repositories import TikTokIntegrationRepository
from creator_intelligence_studio.domain.tiktok_integration.sync_types import TikTokSyncStatus, TikTokSyncType
from creator_intelligence_studio.domain.tiktok_integration.value_objects import (
    DEFAULT_TIKTOK_API_VERSION,
    FORBIDDEN_WRITE_SCOPES,
    READ_ONLY_SCOPES,
    TikTokOAuthAuthorizationResult,
    TikTokOAuthTokenResult,
    TikTokProductApprovalSummary,
    build_tiktok_fingerprint,
    is_write_scope,
    normalize_scopes,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.infrastructure.tiktok.api_version import DEFAULT_TIKTOK_API_VERSION as TIKTOK_API_VERSION
from creator_intelligence_studio.infrastructure.tiktok.credential_store import (
    DevelopmentTikTokCredentialStore,
    EncryptedLocalTikTokCredentialStore,
    TikTokCredentialBundle,
    TikTokCredentialStore,
)
from creator_intelligence_studio.infrastructure.tiktok.display_api_client import TikTokDisplayApiClient
from creator_intelligence_studio.infrastructure.tiktok.metric_mapper import map_metric_import, map_metric_value
from creator_intelligence_studio.infrastructure.tiktok.oauth_client import TikTokDesktopOAuthClient
from creator_intelligence_studio.infrastructure.tiktok.pagination import extract_cursor, extract_has_more, extract_items
from creator_intelligence_studio.infrastructure.tiktok.profile_mapper import map_profile_payload
from creator_intelligence_studio.infrastructure.tiktok.rate_limit_tracker import TikTokRateLimitSnapshot, TikTokRateLimitTracker
from creator_intelligence_studio.infrastructure.tiktok.retry_policy import backoff_delay, is_retryable_status
from creator_intelligence_studio.infrastructure.tiktok.video_mapper import map_cover_version, map_remote_video_payload, map_text_version
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback):
    if not payload:
        return fallback
    try:
        parsed = json.loads(payload)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _now() -> datetime:
    return utc_now()


def _csv_safe_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] in "=+-@" and not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
        return "'" + value
    return value


def _safe_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: object | None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class TikTokConnectionResult:
    connection: TikTokConnection
    authorization_url: str | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "connection": self.connection.to_dict(),
            "authorization_url": self.authorization_url,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class TikTokSyncResult:
    run: TikTokSyncRun
    report: TikTokSyncReport
    connections: tuple[TikTokConnection, ...]
    profiles: tuple[TikTokProfile, ...]
    remote_videos: tuple[TikTokRemoteVideo, ...]
    text_versions: tuple[TikTokVideoTextVersion, ...]
    cover_versions: tuple[TikTokCoverVersion, ...]
    metric_imports: tuple[TikTokMetricImport, ...]
    metric_values: tuple[TikTokMetricValue, ...]
    links: tuple[TikTokContentLink, ...]
    sync_items: tuple[TikTokSyncItem, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "report": self.report.to_dict(),
            "connections": [item.to_dict() for item in self.connections],
            "profiles": [item.to_dict() for item in self.profiles],
            "remote_videos": [item.to_dict() for item in self.remote_videos],
            "text_versions": [item.to_dict() for item in self.text_versions],
            "cover_versions": [item.to_dict() for item in self.cover_versions],
            "metric_imports": [item.to_dict() for item in self.metric_imports],
            "metric_values": [item.to_dict() for item in self.metric_values],
            "links": [item.to_dict() for item in self.links],
            "sync_items": [item.to_dict() for item in self.sync_items],
            "warnings": list(self.warnings),
        }


class TikTokIntegrationService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: TikTokIntegrationRepository,
        database: SQLiteDatabase,
        analytics_repository: SQLiteAnalyticsRepository | None = None,
        creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
        oauth_client: TikTokDesktopOAuthClient | None = None,
        credential_store: TikTokCredentialStore | None = None,
        display_api_client: TikTokDisplayApiClient | None = None,
        rate_limit_tracker: TikTokRateLimitTracker | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.analytics_repository = analytics_repository
        self.creative_packaging_repository = creative_packaging_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.tiktok")
        self.oauth_client = oauth_client or TikTokDesktopOAuthClient()
        self.credential_store = credential_store or self._build_default_credential_store()
        self.display_api_client = display_api_client or TikTokDisplayApiClient(api_version=TIKTOK_API_VERSION.configured_version)
        self.rate_limit_tracker = rate_limit_tracker or TikTokRateLimitTracker()
        self._exports_root = self.paths.data_directory / "tiktok" / "exports"
        self._exports_root.mkdir(parents=True, exist_ok=True)
        self._authorized_scopes = set(READ_ONLY_SCOPES)

    def _build_default_credential_store(self) -> TikTokCredentialStore:
        credential_root = self.paths.data_directory / "tiktok" / "credentials"
        try:
            return EncryptedLocalTikTokCredentialStore(credential_root)
        except Exception as exc:
            if self.settings.environment in {"development", "test"}:
                self.logger.warning("Usando desarrollo para credenciales de TikTok: %s", exc)
                return DevelopmentTikTokCredentialStore(self.paths.data_directory / "tiktok" / "development_credentials")
            raise TikTokAuthorizationError("No se pudo inicializar el almacenamiento seguro de credenciales de TikTok.") from exc

    def _assert_creator_isolation(self, connection: TikTokConnection, creator_id: str) -> None:
        if connection.creator_id != creator_id:
            raise TikTokConnectionError("La conexion no pertenece al creador solicitado.")

    def _ensure_read_only_scopes(self, scopes: tuple[str, ...]) -> None:
        scopes = normalize_scopes(scopes)
        forbidden = [scope for scope in scopes if is_write_scope(scope)]
        if forbidden:
            raise TikTokAuthorizationError(f"Se detectaron scopes de escritura no permitidos: {forbidden}")
        unknown = [scope for scope in scopes if scope not in READ_ONLY_SCOPES]
        if unknown:
            raise TikTokAuthorizationError(f"Scopes no aprobados o no permitidos: {unknown}")

    def _credential_bundle(self, connection: TikTokConnection) -> TikTokCredentialBundle | None:
        return self.credential_store.load(connection.credential_reference)

    def _load_connection_bundle(self, connection: TikTokConnection) -> TikTokCredentialBundle:
        bundle = self._credential_bundle(connection)
        if bundle is None or not bundle.access_token:
            raise TikTokAuthorizationError("No hay credenciales disponibles para la conexion.")
        return bundle

    def _connection_with_updates(
        self,
        connection: TikTokConnection,
        *,
        status: TikTokConnectionStatus | None = None,
        verified: bool = False,
        disconnected: bool = False,
        open_id: str | None = None,
        union_id: str | None = None,
        account_identifier: str | None = None,
        access_level: TikTokAccessLevel | None = None,
    ) -> TikTokConnection:
        now = _now()
        return replace(
            connection,
            status=status or connection.status,
            open_id=open_id if open_id is not None else connection.open_id,
            union_id=union_id if union_id is not None else connection.union_id,
            account_identifier=account_identifier if account_identifier is not None else connection.account_identifier,
            access_level=access_level if access_level is not None else connection.access_level,
            last_verified_at=now if verified else connection.last_verified_at,
            disconnected_at=now if disconnected else connection.disconnected_at,
            updated_at=now,
        )

    def _build_connection(
        self,
        *,
        creator_id: str,
        granted_scopes: tuple[str, ...],
        credential_reference: str,
        authorization_url: str | None = None,
        open_id: str | None = None,
        union_id: str | None = None,
        account_identifier: str | None = None,
        access_level: TikTokAccessLevel | None = None,
    ) -> TikTokConnectionResult:
        connection = TikTokConnection(
            id=str(uuid4()),
            creator_id=creator_id,
            status=TikTokConnectionStatus.CONNECTED,
            open_id=open_id,
            union_id=union_id,
            account_identifier=account_identifier,
            granted_scopes_json=_json_dumps(list(granted_scopes)),
            credential_reference=credential_reference,
            api_version=TIKTOK_API_VERSION.configured_version,
            access_level=access_level,
            connected_at=_now(),
            last_verified_at=None,
            disconnected_at=None,
            created_at=_now(),
            updated_at=_now(),
        )
        return TikTokConnectionResult(connection=self.repository.upsert_connection(connection), authorization_url=authorization_url, warnings=())

    def _store_credential_bundle(
        self,
        *,
        credential_reference: str,
        client_id: str,
        token_result: TikTokOAuthTokenResult,
        account_identifier: str | None,
    ) -> None:
        self.credential_store.save(
            credential_reference,
            TikTokCredentialBundle(
                client_id=client_id,
                access_token=token_result.access_token,
                refresh_token=token_result.refresh_token,
                token_type=token_result.token_type,
                expires_at=token_result.expires_at,
                refresh_expires_at=None if token_result.refresh_expires_in is None else str(token_result.refresh_expires_in),
                granted_scopes=token_result.granted_scopes,
                open_id=token_result.open_id,
                union_id=token_result.union_id,
                account_identifier=account_identifier,
                provider="tiktok_login",
            ),
        )

    def connect_account(
        self,
        *,
        creator_id: str,
        client_id: str,
        client_secret: str | None = None,
        authorization_code: str | None = None,
        redirect_uri: str | None = None,
        scopes: tuple[str, ...] = READ_ONLY_SCOPES,
        account_identifier: str | None = None,
    ) -> TikTokConnectionResult:
        self._ensure_read_only_scopes(scopes)
        authorization = self.oauth_client.begin_authorization(
            client_id=client_id,
            scopes=scopes,
            redirect_uri=redirect_uri,
        )
        credential_reference = uuid4().hex
        if authorization_code is None:
            return self._build_connection(
                creator_id=creator_id,
                granted_scopes=scopes,
                credential_reference=credential_reference,
                authorization_url=authorization.authorization_url,
                account_identifier=account_identifier,
                access_level=TikTokAccessLevel.DEVELOPMENT_MODE if self.settings.environment != "production" else TikTokAccessLevel.PRODUCTION_MODE,
            )
        token_result = self.oauth_client.exchange_code(
            client_id=client_id,
            client_secret=client_secret or os.environ.get("CIS_TIKTOK_CLIENT_SECRET"),
            code=authorization_code,
            redirect_uri=authorization.redirect_uri,
            code_verifier=authorization.code_verifier,
        )
        self._ensure_read_only_scopes(token_result.granted_scopes)
        missing = [scope for scope in scopes if scope not in token_result.granted_scopes]
        if missing:
            raise TikTokAuthorizationError(f"Faltan scopes concedidos: {missing}")
        self._store_credential_bundle(
            credential_reference=credential_reference,
            client_id=client_id,
            token_result=token_result,
            account_identifier=account_identifier or token_result.open_id,
        )
        result = self._build_connection(
            creator_id=creator_id,
            granted_scopes=token_result.granted_scopes,
            credential_reference=credential_reference,
            authorization_url=authorization.authorization_url,
            open_id=token_result.open_id,
            union_id=token_result.union_id,
            account_identifier=account_identifier or token_result.open_id,
            access_level=TikTokAccessLevel.DEVELOPMENT_MODE if self.settings.environment != "production" else TikTokAccessLevel.PRODUCTION_MODE,
        )
        verified = self.verify_connection(result.connection.id)
        return replace(result, connection=verified.connection, warnings=verified.warnings)

    def verify_connection(self, connection_id: str) -> TikTokConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        bundle = self._load_connection_bundle(connection)
        payload = self.display_api_client.get_user_info(token=bundle.access_token or "", fields=("open_id", "union_id", "display_name"))
        user = payload.get("data", {}).get("user") if isinstance(payload.get("data"), dict) else {}
        if not isinstance(user, dict):
            user = {}
        updated = self._connection_with_updates(
            connection,
            status=TikTokConnectionStatus.VERIFIED,
            verified=True,
            open_id=_safe_str(user.get("open_id")) or connection.open_id,
            union_id=_safe_str(user.get("union_id")) or connection.union_id,
            account_identifier=_safe_str(user.get("username")) or connection.account_identifier,
        )
        persisted = self.repository.upsert_connection(updated)
        self._record_rate_limit(connection.id, "connection_verify", "/v2/user/info/", payload)
        return TikTokConnectionResult(connection=persisted, authorization_url=None, warnings=())

    def disconnect_connection(self, connection_id: str) -> TikTokConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        self.credential_store.delete(connection.credential_reference)
        updated = self._connection_with_updates(connection, status=TikTokConnectionStatus.DISCONNECTED, disconnected=True)
        return TikTokConnectionResult(connection=self.repository.upsert_connection(updated), authorization_url=None, warnings=())

    def revoke_connection(self, connection_id: str) -> TikTokConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        bundle = self._credential_bundle(connection)
        if bundle and bundle.access_token:
            self.oauth_client.revoke(client_id=bundle.client_id or connection.id, client_secret=os.environ.get("CIS_TIKTOK_CLIENT_SECRET"), token=bundle.access_token)
        self.credential_store.delete(connection.credential_reference)
        updated = self._connection_with_updates(connection, status=TikTokConnectionStatus.REVOKED, disconnected=True)
        return TikTokConnectionResult(connection=self.repository.upsert_connection(updated), authorization_url=None, warnings=())

    def refresh_connection(self, connection_id: str) -> TikTokConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        bundle = self._credential_bundle(connection)
        if bundle is None or not bundle.refresh_token:
            raise TikTokAuthorizationError("No hay refresh token disponible.")
        refreshed = self.oauth_client.refresh_token(
            client_id=bundle.client_id or connection.id,
            client_secret=os.environ.get("CIS_TIKTOK_CLIENT_SECRET"),
            refresh_token=bundle.refresh_token,
        )
        self._ensure_read_only_scopes(refreshed.granted_scopes)
        self._store_credential_bundle(
            credential_reference=connection.credential_reference,
            client_id=bundle.client_id or connection.id,
            token_result=refreshed,
            account_identifier=connection.account_identifier,
        )
        updated = self._connection_with_updates(connection, status=TikTokConnectionStatus.VERIFIED, verified=True)
        return TikTokConnectionResult(connection=self.repository.upsert_connection(updated), authorization_url=None, warnings=())

    def list_connections(self, creator_id: str) -> list[TikTokConnection]:
        return self.repository.list_connections(creator_id)

    def show_connection(self, connection_id: str) -> TikTokConnection | None:
        return self.repository.get_connection(connection_id)

    def list_profiles(self, creator_id: str) -> list[TikTokProfile]:
        return self.repository.list_profiles(creator_id)

    def show_profile(self, profile_id: str) -> TikTokProfile | None:
        return self.repository.get_profile(profile_id)

    def select_profile(self, profile_id: str) -> TikTokProfile:
        profile = self.repository.get_profile(profile_id)
        if profile is None:
            raise TikTokConnectionError("El perfil no existe.")
        updated = replace(profile, selected_for_sync=True, updated_at=_now())
        return self.repository.upsert_profile(updated)

    def _prepare_sync_run(
        self,
        *,
        creator_id: str,
        connection: TikTokConnection,
        profile_id: str | None,
        sync_type: TikTokSyncType,
        configuration: dict[str, object],
        cursor: str | None = None,
    ) -> TikTokSyncRun:
        return self.repository.upsert_sync_run(
            TikTokSyncRun(
                id=str(uuid4()),
                creator_id=creator_id,
                connection_id=connection.id,
                profile_id=profile_id,
                sync_type=sync_type,
                status=TikTokSyncStatus.VERIFYING_PROFILE if sync_type == TikTokSyncType.CONNECTION_VERIFY else TikTokSyncStatus.QUEUED,
                configuration_json=_json_dumps(configuration),
                cursor_json=_json_dumps({"cursor": cursor}) if cursor is not None else None,
                discovered_count=0,
                imported_count=0,
                updated_count=0,
                unchanged_count=0,
                skipped_count=0,
                warning_count=0,
                error_count=0,
                estimated_usage=None,
                started_at=_now(),
                completed_at=None,
                error_code=None,
                error_message=None,
                created_at=_now(),
            )
        )

    def _finalize_sync_run(
        self,
        run: TikTokSyncRun,
        *,
        discovered: int,
        imported: int,
        updated: int,
        unchanged: int,
        skipped: int,
        warnings: list[str],
        errors: list[str],
        cursor: str | None = None,
        status: TikTokSyncStatus | None = None,
        estimated_usage: str | None = None,
    ) -> TikTokSyncRun:
        return self.repository.upsert_sync_run(
            replace(
                run,
                status=status or (TikTokSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else TikTokSyncStatus.COMPLETED),
                discovered_count=discovered,
                imported_count=imported,
                updated_count=updated,
                unchanged_count=unchanged,
                skipped_count=skipped,
                warning_count=len(warnings),
                error_count=len(errors),
                estimated_usage=estimated_usage,
                completed_at=_now(),
                error_code=errors[0] if errors else None,
                error_message=errors[0] if errors else None,
                cursor_json=_json_dumps({"cursor": cursor}) if cursor is not None else run.cursor_json,
            )
        )

    def _record_rate_limit(
        self,
        connection_id: str,
        operation_key: str,
        endpoint: str,
        payload: dict[str, object] | None = None,
    ) -> TikTokRateLimitUsage:
        snapshot = self.rate_limit_tracker.record(
            operation_key=operation_key,
            endpoint=endpoint,
            request_count=1,
            estimated_usage=None,
            response_headers={},
        )
        return self.repository.upsert_rate_limit_usage(
            TikTokRateLimitUsage(
                id=str(uuid4()),
                connection_id=connection_id,
                operation_key=operation_key,
                endpoint=endpoint,
                request_count=snapshot.request_count,
                estimated_usage=snapshot.estimated_usage,
                window_started_at=snapshot.window_started_at,
                response_headers_json=snapshot.response_headers_json,
                usage_date=snapshot.usage_date,
                created_at=_now(),
            )
        )

    def _upsert_publication_snapshot(
        self,
        *,
        creator_id: str,
        profile_id: str,
        remote_video: TikTokRemoteVideo,
        source_type: AnalyticsSourceType,
    ) -> None:
        if self.analytics_repository is None:
            return
        platform = self.analytics_repository.get_platform_by_key("tiktok")
        if platform is None:
            platform = self.analytics_repository.upsert_platform(
                AnalyticsPlatform(
                    id=str(uuid4()),
                    platform_key="tiktok",
                    display_name="TikTok",
                    status=AnalyticsPlatformStatus.ACTIVE,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
        channel = self.analytics_repository.upsert_channel(
            AnalyticsChannel(
                id=str(uuid4()),
                creator_id=creator_id,
                platform_id=platform.id,
                platform_key=platform.platform_key,
                external_channel_id=remote_video.profile_id,
                channel_name=f"tiktok:{profile_id}",
                channel_url=remote_video.share_url,
                timezone_name="UTC",
                is_primary=True,
                metadata_json=_json_dumps({"profile_id": profile_id, "open_id": remote_video.creator_id}),
                created_at=_now(),
                updated_at=_now(),
            )
        )
        import_fingerprint = build_tiktok_fingerprint({"creator_id": creator_id, "profile_id": profile_id, "tiktok_video_id": remote_video.tiktok_video_id, "source": "tiktok_display_api"})
        import_record = self.analytics_repository.get_import_by_fingerprint(import_fingerprint)
        if import_record is None:
            import_record = self.analytics_repository.upsert_import(
                AnalyticsImport(
                    id=import_fingerprint,
                    creator_id=creator_id,
                    channel_id=channel.id,
                    platform="tiktok",
                    source_filename="tiktok_display_api",
                    source_path=None,
                    source_fingerprint=import_fingerprint,
                    source_type=AnalyticsSourceType.MANUAL,
                    schema_version="v1",
                    status=AnalyticsImportStatus.COMPLETED,
                    total_rows=1,
                    accepted_rows=1,
                    rejected_rows=0,
                    warning_rows=0,
                    duplicate_rows=0,
                    source_sheet_name=None,
                    timezone_name="UTC",
                    delimiter=None,
                    mapping_json="{}",
                    report_path=None,
                    started_at=_now(),
                    completed_at=_now(),
                    error_code=None,
                    error_message=None,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
        publication_dedupe_key = build_tiktok_fingerprint({"creator_id": creator_id, "tiktok_video_id": remote_video.tiktok_video_id, "platform": "tiktok"})
        existing_publication = self.analytics_repository.get_publication_by_dedupe_key(publication_dedupe_key)
        publication = AnalyticsPublication(
            id=existing_publication.id if existing_publication is not None else (remote_video.publication_id or str(uuid4())),
            creator_id=creator_id,
            channel_id=channel.id,
            video_asset_id=remote_video.video_asset_id,
            external_publication_id=remote_video.tiktok_video_id,
            platform="tiktok",
            content_type=AnalyticsContentType.TIKTOK,
            title=remote_video.title or remote_video.tiktok_video_id,
            description=remote_video.video_description,
            published_at=remote_video.create_time,
            duration_seconds=float(remote_video.duration_seconds) if remote_video.duration_seconds is not None else None,
            url=remote_video.share_url,
            thumbnail_path=None,
            status=remote_video.remote_status.value,
            source_type=source_type,
            source_fingerprint=remote_video.remote_fingerprint,
            dedupe_key=publication_dedupe_key,
            created_at=_now(),
            updated_at=_now(),
        )
        self.analytics_repository.upsert_publication(publication)
        def _ensure_metric_definition(metric_key: str, display_name: str, unit: str = "count") -> None:
            if self.analytics_repository.get_metric_definition_by_key(metric_key) is None:
                self.analytics_repository.upsert_metric_definition(
                    AnalyticsMetricDefinition(
                        id=str(uuid4()),
                        metric_key=metric_key,
                        display_name=display_name,
                        category=AnalyticsMetricCategory.ATTENTION,
                        unit=unit,
                        value_type=AnalyticsValueType.NUMERIC,
                        aggregation_type=AnalyticsAggregationType.LATEST,
                        higher_is_better=True,
                        description=f"Metrica publica oficial de TikTok: {display_name}.",
                        aliases_json=_json_dumps([metric_key]),
                        applicability_json=_json_dumps({"platform": "tiktok", "source": "display_api"}),
                        created_at=_now(),
                    )
                )

        for metric_key, display_name, value in (
            ("tiktok_public_view_count", "Public View Count", remote_video.view_count),
            ("tiktok_public_like_count", "Public Like Count", remote_video.like_count),
            ("tiktok_public_comment_count", "Public Comment Count", remote_video.comment_count),
            ("tiktok_public_share_count", "Public Share Count", remote_video.share_count),
        ):
            if value is None:
                continue
            _ensure_metric_definition(metric_key, display_name)
            snapshot = AnalyticsMetricSnapshot(
                id=str(uuid4()),
                publication_id=publication.id,
                snapshot_date=remote_video.create_time.date().isoformat(),
                captured_at=_now(),
                metric_key=metric_key,
                numeric_value=float(value),
                text_value=None,
                unit="views" if metric_key.endswith("view_count") else "count",
                source_import_id=import_record.id,
                source_row_number=None,
                is_derived=False,
                quality_status=AnalyticsQualityStatus.ACCEPTED,
                warning_codes_json="[]",
                created_at=_now(),
                row_fingerprint=build_tiktok_fingerprint({"publication_id": publication.id, "metric_key": metric_key, "value": value}),
                dedupe_key=build_tiktok_fingerprint({"publication_id": publication.id, "metric_key": metric_key, "source": "tiktok"}),
            )
            self.analytics_repository.upsert_metric_snapshot(snapshot)

    def _sync_profile_payload(
        self,
        *,
        creator_id: str,
        connection: TikTokConnection,
        profile: TikTokProfile | None,
        payload: dict[str, object],
        api_version: str,
    ) -> TikTokProfile:
        open_id = _safe_str(payload.get("open_id")) or connection.open_id or ""
        mapped = map_profile_payload(
            payload,
            creator_id=creator_id,
            connection_id=connection.id,
            open_id=open_id,
            api_version=api_version,
            selected_for_sync=True,
        )
        if profile is not None:
            mapped = replace(mapped, id=profile.id, created_at=profile.created_at, remote_fingerprint=mapped.remote_fingerprint)
        return self.repository.upsert_profile(mapped)

    def _store_text_and_cover_history(
        self,
        *,
        remote_video: TikTokRemoteVideo,
        payload: dict[str, object],
        previous_text: TikTokVideoTextVersion | None,
        previous_cover: TikTokCoverVersion | None,
    ) -> tuple[TikTokVideoTextVersion | None, TikTokCoverVersion | None]:
        text_version = previous_text
        new_text_fingerprint = build_tiktok_fingerprint({"title": payload.get("title"), "video_description": payload.get("video_description"), "video_id": remote_video.tiktok_video_id})
        if previous_text is None or previous_text.source_fingerprint != new_text_fingerprint:
            text_version = self.repository.upsert_video_text_version(
                map_text_version(
                    remote_video.id,
                    payload,
                    version_number=1 if previous_text is None else previous_text.version_number + 1,
                    is_current=True,
                )
            )
        cover_version = previous_cover
        new_cover_fingerprint = build_tiktok_fingerprint({"cover_image_url": payload.get("cover_image_url"), "video_id": remote_video.tiktok_video_id})
        if previous_cover is None or previous_cover.remote_fingerprint != new_cover_fingerprint:
            cover_version = self.repository.upsert_cover_version(
                map_cover_version(
                    remote_video.id,
                    payload,
                    version_number=1 if previous_cover is None else previous_cover.version_number + 1,
                    packaging_asset_id=remote_video.packaging_asset_id,
                    is_current=True,
                )
            )
        return text_version, cover_version

    def _sync_videos_page(
        self,
        *,
        creator_id: str,
        connection: TikTokConnection,
        profile: TikTokProfile,
        bundle: TikTokCredentialBundle,
        sync_run_id: str,
        cursor: int | None,
        max_count: int,
    ) -> tuple[list[TikTokRemoteVideo], list[TikTokVideoTextVersion], list[TikTokCoverVersion], list[TikTokSyncItem], list[str], list[str], str | None, bool]:
        response = self.display_api_client.list_videos(token=bundle.access_token or "", cursor=cursor, max_count=max_count, fields=("id", "create_time", "cover_image_url", "share_url", "video_description", "duration", "height", "width", "title", "embed_link", "like_count", "comment_count", "share_count", "view_count"))
        self._record_rate_limit(connection.id, "video_catalog", "/v2/video/list/", response)
        items = extract_items(response)
        next_cursor = extract_cursor(response)
        has_more = extract_has_more(response)
        remote_videos: list[TikTokRemoteVideo] = []
        text_versions: list[TikTokVideoTextVersion] = []
        cover_versions: list[TikTokCoverVersion] = []
        sync_items: list[TikTokSyncItem] = []
        warnings: list[str] = []
        errors: list[str] = []
        for item in items:
            remote = self.repository.get_remote_video_by_tiktok_id(creator_id, _safe_str(item.get("id")) or "")
            mapped = map_remote_video_payload(item, creator_id=creator_id, profile_id=profile.id, publication_id=remote.publication_id if remote else None, video_asset_id=remote.video_asset_id if remote else None, packaging_asset_id=remote.packaging_asset_id if remote else None)
            if remote is not None:
                mapped = replace(mapped, id=remote.id, created_at=remote.created_at, first_seen_at=remote.first_seen_at)
            persisted = self.repository.upsert_remote_video(replace(mapped, last_seen_at=_now(), created_at=remote.created_at if remote else mapped.created_at, first_seen_at=remote.first_seen_at if remote else mapped.first_seen_at))
            previous_texts = self.repository.list_video_text_versions(persisted.id)
            previous_covers = self.repository.list_cover_versions(persisted.id)
            previous_text = previous_texts[-1] if previous_texts else None
            previous_cover = previous_covers[-1] if previous_covers else None
            text_version, cover_version = self._store_text_and_cover_history(remote_video=persisted, payload=item, previous_text=previous_text, previous_cover=previous_cover)
            if text_version:
                text_versions.append(text_version)
            if cover_version:
                cover_versions.append(cover_version)
            remote_videos.append(persisted)
            sync_items.append(
                self.repository.upsert_sync_item(
                    TikTokSyncItem(
                        id=str(uuid4()),
                        sync_run_id=sync_run_id,
                        remote_type="video",
                        remote_id=persisted.tiktok_video_id,
                        local_type="remote_video",
                        local_id=persisted.id,
                        action="upsert",
                        status="completed",
                        warnings_json="[]",
                        error_code=None,
                        error_message=None,
                        created_at=_now(),
                    )
                )
            )
            self._upsert_publication_snapshot(creator_id=creator_id, profile_id=profile.id, remote_video=persisted, source_type=AnalyticsSourceType.MANUAL)
            if persisted.cover_image_url is None:
                warnings.append(f"video {persisted.tiktok_video_id} sin cover_image_url")
        return remote_videos, text_versions, cover_versions, sync_items, warnings, errors, next_cursor, has_more

    def sync_profile(self, *, profile_id: str, cursor: str | None = None) -> TikTokSyncResult:
        profile = self.repository.get_profile(profile_id)
        if profile is None:
            raise TikTokConnectionError("El perfil no existe.")
        connection = self.repository.get_connection(profile.connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, profile.creator_id)
        if connection.status in {TikTokConnectionStatus.DISCONNECTED, TikTokConnectionStatus.REVOKED}:
            raise TikTokAuthorizationError("La conexion no esta activa.")
        bundle = self._load_connection_bundle(connection)
        run = self._prepare_sync_run(
            creator_id=profile.creator_id,
            connection=connection,
            profile_id=profile.id,
            sync_type=TikTokSyncType.PROFILE_METADATA,
            configuration={"cursor": cursor},
            cursor=cursor,
        )
        warnings: list[str] = []
        errors: list[str] = []
        response = self.display_api_client.get_user_info(token=bundle.access_token or "", fields=("open_id", "union_id", "avatar_url", "avatar_url_100", "avatar_large_url", "display_name", "bio_description", "profile_deep_link", "profile_web_link", "is_verified", "username", "follower_count", "following_count", "likes_count", "video_count"))
        self._record_rate_limit(connection.id, "profile_metadata", "/v2/user/info/", response)
        user = response.get("data", {}).get("user") if isinstance(response.get("data"), dict) else {}
        if not isinstance(user, dict):
            user = {}
        updated_profile = self._sync_profile_payload(creator_id=profile.creator_id, connection=connection, profile=profile, payload=user, api_version=connection.api_version)
        updated_profile = replace(updated_profile, selected_for_sync=profile.selected_for_sync)
        updated_profile = self.repository.upsert_profile(updated_profile)
        if updated_profile.follower_count is None:
            warnings.append("follower_count no retornado por la API")
        run = self._finalize_sync_run(run, discovered=1, imported=1, updated=1, unchanged=0, skipped=0, warnings=warnings, errors=errors, status=TikTokSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else TikTokSyncStatus.COMPLETED)
        report = TikTokSyncReport(
            connection_id=connection.id,
            profile_id=updated_profile.id,
            granted_scopes=tuple(_json_loads(connection.granted_scopes_json, [])),
            access_level=None if connection.access_level is None else connection.access_level.value,
            sync_type=run.sync_type.value,
            period=None,
            discovered_count=1,
            imported_count=1,
            updated_count=1,
            unchanged_count=0,
            skipped_count=0,
            linked_count=0,
            unlinked_count=0,
            profile_metrics=("follower_count", "following_count", "likes_count", "video_count"),
            video_metrics=(),
            unavailable_metrics=("watch_time", "average_watch_time", "completion_rate", "retention", "traffic_source", "demographics", "saves", "profile_views"),
            manual_import_recommendation="watch_time/completion/retention remain manual",
            warnings=tuple(sorted(set(warnings))),
            errors=tuple(sorted(set(errors))),
            estimated_usage=None,
            duration_seconds=None,
            next_action="sync_videos" if not errors else "review",
        )
        return TikTokSyncResult(run=run, report=report, connections=(connection,), profiles=(updated_profile,), remote_videos=tuple(), text_versions=tuple(), cover_versions=tuple(), metric_imports=tuple(), metric_values=tuple(), links=tuple(), sync_items=tuple(self.repository.list_sync_items(run.id)), warnings=tuple(sorted(set(warnings))))

    def sync_videos(self, *, profile_id: str, cursor: str | None = None, max_count: int = 20, full_resync: bool = False) -> TikTokSyncResult:
        profile = self.repository.get_profile(profile_id)
        if profile is None:
            raise TikTokConnectionError("El perfil no existe.")
        connection = self.repository.get_connection(profile.connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, profile.creator_id)
        if connection.status in {TikTokConnectionStatus.DISCONNECTED, TikTokConnectionStatus.REVOKED}:
            raise TikTokAuthorizationError("La conexion no esta activa.")
        bundle = self._load_connection_bundle(connection)
        run = self._prepare_sync_run(
            creator_id=profile.creator_id,
            connection=connection,
            profile_id=profile.id,
            sync_type=TikTokSyncType.FULL_RESYNC if full_resync else TikTokSyncType.VIDEO_CATALOG,
            configuration={"cursor": cursor, "max_count": max_count, "full_resync": full_resync},
            cursor=cursor,
        )
        cursor_value = _safe_int(cursor) if cursor is not None else None
        remote_videos: list[TikTokRemoteVideo] = []
        text_versions: list[TikTokVideoTextVersion] = []
        cover_versions: list[TikTokCoverVersion] = []
        sync_items: list[TikTokSyncItem] = []
        warnings: list[str] = []
        errors: list[str] = []
        has_more = True
        discovered = imported = updated = unchanged = skipped = 0
        page_cursor = cursor_value
        while has_more:
            page_remote_videos, page_text_versions, page_cover_versions, page_sync_items, page_warnings, page_errors, next_cursor, has_more = self._sync_videos_page(
                creator_id=profile.creator_id,
                connection=connection,
                profile=profile,
                bundle=bundle,
                sync_run_id=run.id,
                cursor=page_cursor,
                max_count=max_count,
            )
            remote_videos.extend(page_remote_videos)
            text_versions.extend(page_text_versions)
            cover_versions.extend(page_cover_versions)
            sync_items.extend(page_sync_items)
            warnings.extend(page_warnings)
            errors.extend(page_errors)
            discovered += len(page_remote_videos)
            imported += len(page_remote_videos)
            page_cursor = _safe_int(next_cursor) if next_cursor is not None else None
            if not has_more:
                break
        run = self._finalize_sync_run(run, discovered=discovered, imported=imported, updated=updated, unchanged=unchanged, skipped=skipped, warnings=warnings, errors=errors, cursor=str(page_cursor) if page_cursor is not None else cursor, status=TikTokSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else TikTokSyncStatus.COMPLETED)
        report = TikTokSyncReport(
            connection_id=connection.id,
            profile_id=profile.id,
            granted_scopes=tuple(_json_loads(connection.granted_scopes_json, [])),
            access_level=None if connection.access_level is None else connection.access_level.value,
            sync_type=run.sync_type.value,
            period=None,
            discovered_count=discovered,
            imported_count=imported,
            updated_count=updated,
            unchanged_count=unchanged,
            skipped_count=skipped,
            linked_count=len([link for link in self.repository.list_content_links(profile.creator_id) if link.status == "approved"]),
            unlinked_count=len([link for link in self.repository.list_content_links(profile.creator_id) if link.status == "unlinked"]),
            profile_metrics=("follower_count", "following_count", "likes_count", "video_count"),
            video_metrics=("view_count", "like_count", "comment_count", "share_count"),
            unavailable_metrics=("watch_time", "average_watch_time", "completion_rate", "retention", "saves", "profile_views", "traffic_source", "follower_conversion", "demographics", "for_you_traffic"),
            manual_import_recommendation="manual CSV/XLSX remains required for private analytics metrics",
            warnings=tuple(sorted(set(warnings))),
            errors=tuple(sorted(set(errors))),
            estimated_usage=None,
            duration_seconds=None,
            next_action="incremental_sync" if not errors else "review",
        )
        return TikTokSyncResult(run=run, report=report, connections=(connection,), profiles=(profile,), remote_videos=tuple(remote_videos), text_versions=tuple(text_versions), cover_versions=tuple(cover_versions), metric_imports=tuple(), metric_values=tuple(), links=tuple(self.repository.list_content_links(profile.creator_id)), sync_items=tuple(self.repository.list_sync_items(run.id)), warnings=tuple(sorted(set(warnings))))

    def sync_public_metrics(self, *, profile_id: str, cursor: str | None = None) -> TikTokSyncResult:
        profile = self.repository.get_profile(profile_id)
        if profile is None:
            raise TikTokConnectionError("El perfil no existe.")
        connection = self.repository.get_connection(profile.connection_id)
        if connection is None:
            raise TikTokConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, profile.creator_id)
        if connection.status in {TikTokConnectionStatus.DISCONNECTED, TikTokConnectionStatus.REVOKED}:
            raise TikTokAuthorizationError("La conexion no esta activa.")
        bundle = self._load_connection_bundle(connection)
        run = self._prepare_sync_run(
            creator_id=profile.creator_id,
            connection=connection,
            profile_id=profile.id,
            sync_type=TikTokSyncType.PUBLIC_METRICS,
            configuration={"cursor": cursor},
            cursor=cursor,
        )
        metric_imports: list[TikTokMetricImport] = []
        metric_values: list[TikTokMetricValue] = []
        warnings: list[str] = []
        errors: list[str] = []
        videos = self.repository.list_remote_videos(profile.creator_id, profile_id=profile.id)
        for offset in range(0, len(videos), 20):
            batch = videos[offset : offset + 20]
            if not batch:
                continue
            response = self.display_api_client.query_videos(
                token=bundle.access_token or "",
                video_ids=tuple(video.tiktok_video_id for video in batch),
                fields=("id", "view_count", "like_count", "comment_count", "share_count", "cover_image_url", "title", "video_description"),
            )
            self._record_rate_limit(connection.id, "public_metrics", "/v2/video/query/", response)
            for item in extract_items(response):
                remote = self.repository.get_remote_video_by_tiktok_id(profile.creator_id, _safe_str(item.get("id")) or "")
                if remote is None:
                    continue
                metric_import = self.repository.upsert_metric_import(
                    map_metric_import(
                        creator_id=profile.creator_id,
                        profile_id=profile.id,
                        sync_run_id=run.id,
                        remote_video_id=remote.id,
                        metric_scope=TikTokMetricScope.VIDEO,
                        source_type=TikTokMetricSourceType.TIKTOK_DISPLAY_API,
                        source_payload=item,
                    )
                )
                metric_imports.append(metric_import)
                for metric_key, raw_name in (
                    ("view_count", "view_count"),
                    ("like_count", "like_count"),
                    ("comment_count", "comment_count"),
                    ("share_count", "share_count"),
                ):
                    value = item.get(raw_name)
                    if value is None:
                        continue
                    metric_values.append(
                        self.repository.upsert_metric_value(
                            map_metric_value(
                                metric_import.id,
                                metric_key,
                                raw_name,
                                {"value": value, "unit": "count", "quality_status": "accepted"},
                            )
                        )
                    )
        run = self._finalize_sync_run(
            run,
            discovered=len(videos),
            imported=len(metric_imports),
            updated=0,
            unchanged=0,
            skipped=0,
            warnings=warnings,
            errors=errors,
            status=TikTokSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else TikTokSyncStatus.COMPLETED,
        )
        report = TikTokSyncReport(
            connection_id=connection.id,
            profile_id=profile.id,
            granted_scopes=tuple(_json_loads(connection.granted_scopes_json, [])),
            access_level=None if connection.access_level is None else connection.access_level.value,
            sync_type=run.sync_type.value,
            period=None,
            discovered_count=len(videos),
            imported_count=len(metric_imports),
            updated_count=0,
            unchanged_count=0,
            skipped_count=0,
            linked_count=len(self.repository.list_content_links(profile.creator_id)),
            unlinked_count=0,
            profile_metrics=("follower_count", "following_count", "likes_count", "video_count"),
            video_metrics=("view_count", "like_count", "comment_count", "share_count"),
            unavailable_metrics=("watch_time", "average_watch_time", "completion_rate", "retention", "saves", "profile_views", "traffic_source", "follower_conversion", "demographics", "for_you_traffic"),
            manual_import_recommendation="manual CSV/XLSX remains required for private analytics metrics",
            warnings=tuple(sorted(set(warnings))),
            errors=tuple(sorted(set(errors))),
            estimated_usage=None,
            duration_seconds=None,
            next_action="incremental_sync" if not errors else "review",
        )
        return TikTokSyncResult(
            run=run,
            report=report,
            connections=(connection,),
            profiles=(profile,),
            remote_videos=tuple(videos),
            text_versions=tuple(),
            cover_versions=tuple(),
            metric_imports=tuple(metric_imports),
            metric_values=tuple(metric_values),
            links=tuple(self.repository.list_content_links(profile.creator_id)),
            sync_items=tuple(self.repository.list_sync_items(run.id)),
            warnings=tuple(sorted(set(warnings))),
        )

    def sync_incremental(self, *, profile_id: str, cursor: str | None = None, max_count: int = 20) -> TikTokSyncResult:
        return self.sync_videos(profile_id=profile_id, cursor=cursor, max_count=max_count, full_resync=False)

    def sync_repair(self, *, profile_id: str) -> TikTokSyncResult:
        return self.sync_videos(profile_id=profile_id, full_resync=True)

    def sync_cover_refresh(self, *, remote_video_id: str) -> TikTokSyncResult:
        remote = self.repository.get_remote_video(remote_video_id)
        if remote is None:
            raise TikTokConnectionError("El video remoto no existe.")
        profile = self.repository.get_profile(remote.profile_id)
        connection = self.repository.get_connection(profile.connection_id) if profile else None
        if profile is None or connection is None:
            raise TikTokConnectionError("No se encontro la conexion o el perfil.")
        bundle = self._load_connection_bundle(connection)
        response = self.display_api_client.query_videos(token=bundle.access_token or "", video_ids=(remote.tiktok_video_id,), fields=("id", "cover_image_url", "title", "video_description"))
        self._record_rate_limit(connection.id, "cover_refresh", "/v2/video/query/", response)
        videos = extract_items(response)
        if not videos:
            raise TikTokSyncError("No se pudo refrescar el cover del video.")
        item = videos[0]
        remote = self.repository.upsert_remote_video(replace(remote, cover_image_url=_safe_str(item.get("cover_image_url")) or remote.cover_image_url, updated_at=_now(), last_seen_at=_now()))
        cover = self.repository.upsert_cover_version(map_cover_version(remote.id, item, version_number=len(self.repository.list_cover_versions(remote.id)) + 1, packaging_asset_id=remote.packaging_asset_id, is_current=True))
        run = self._prepare_sync_run(creator_id=remote.creator_id, connection=connection, profile_id=profile.id, sync_type=TikTokSyncType.COVER_REFRESH, configuration={"remote_video_id": remote.id}, cursor=None)
        run = self._finalize_sync_run(run, discovered=1, imported=1, updated=1, unchanged=0, skipped=0, warnings=[], errors=[], status=TikTokSyncStatus.COMPLETED)
        report = TikTokSyncReport(connection_id=connection.id, profile_id=profile.id, granted_scopes=tuple(_json_loads(connection.granted_scopes_json, [])), access_level=None if connection.access_level is None else connection.access_level.value, sync_type=run.sync_type.value, period=None, discovered_count=1, imported_count=1, updated_count=1, unchanged_count=0, skipped_count=0, linked_count=0, unlinked_count=0, profile_metrics=(), video_metrics=("cover_image_url",), unavailable_metrics=(), manual_import_recommendation=None, warnings=tuple(), errors=tuple(), estimated_usage=None, duration_seconds=None, next_action="review")
        return TikTokSyncResult(run=run, report=report, connections=(connection,), profiles=(profile,), remote_videos=(remote,), text_versions=tuple(self.repository.list_video_text_versions(remote.id)), cover_versions=(cover,), metric_imports=tuple(), metric_values=tuple(), links=tuple(), sync_items=tuple(self.repository.list_sync_items(run.id)), warnings=tuple())

    def sync_history(self, creator_id: str) -> list[TikTokSyncRun]:
        return self.repository.list_sync_runs(creator_id)

    def list_sync_items(self, run_id: str) -> list[TikTokSyncItem]:
        return self.repository.list_sync_items(run_id)

    def list_metric_imports(self, creator_id: str, *, profile_id: str | None = None) -> list[TikTokMetricImport]:
        return self.repository.list_metric_imports(creator_id, profile_id=profile_id)

    def list_metric_values(self, metric_import_id: str) -> list[TikTokMetricValue]:
        return self.repository.list_metric_values(metric_import_id)

    def show_sync_run(self, run_id: str) -> TikTokSyncRun | None:
        return self.repository.get_sync_run(run_id)

    def resume_sync(self, run_id: str) -> TikTokSyncResult:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise TikTokSyncError("La corrida no existe.")
        cursor = _json_loads(run.cursor_json, {}).get("cursor") if run.cursor_json else None
        if run.profile_id is None:
            raise TikTokSyncError("No hay perfil para reanudar.")
        return self.sync_incremental(profile_id=run.profile_id, cursor=str(cursor) if cursor is not None else None)

    def interrupt_sync_run(self, run_id: str, reason: str | None = None) -> TikTokSyncRun:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise TikTokSyncError("La corrida no existe.")
        updated = replace(
            run,
            status=TikTokSyncStatus.INTERRUPTED,
            error_code="interrupted",
            error_message=reason or run.error_message or "Interrumpida localmente",
            completed_at=_now(),
        )
        return self.repository.upsert_sync_run(updated)

    def link_content(
        self,
        *,
        remote_video_id: str,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        packaging_asset_id: str | None = None,
        link_method: TikTokLinkMethod = TikTokLinkMethod.MANUAL,
        confidence_level: str = "low",
        status: str = "pending",
    ) -> TikTokContentLink:
        remote = self.repository.get_remote_video(remote_video_id)
        if remote is None:
            raise TikTokContentLinkError("El video remoto no existe.")
        link = TikTokContentLink(
            id=str(uuid4()),
            creator_id=remote.creator_id,
            remote_video_id=remote.id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            packaging_asset_id=packaging_asset_id,
            link_method=link_method,
            confidence_level=confidence_level,
            status=status,
            reviewed_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        return self.repository.upsert_content_link(link)

    def unlink_content(self, *, remote_video_id: str) -> TikTokContentLink:
        remote = self.repository.get_remote_video(remote_video_id)
        if remote is None:
            raise TikTokContentLinkError("El video remoto no existe.")
        existing = next((item for item in self.repository.list_content_links(remote.creator_id) if item.remote_video_id == remote.id), None)
        if existing is None:
            raise TikTokContentLinkError("No existe un enlace para desvincular.")
        updated = replace(existing, status="unlinked", updated_at=_now())
        return self.repository.upsert_content_link(updated)

    def list_remote_videos(self, profile_id: str) -> list[TikTokRemoteVideo]:
        profile = self.repository.get_profile(profile_id)
        if profile is None:
            return []
        return self.repository.list_remote_videos(profile.creator_id, profile_id=profile_id)

    def show_remote_video(self, remote_video_id: str) -> TikTokRemoteVideo | None:
        return self.repository.get_remote_video(remote_video_id)

    def list_content_links(self, creator_id: str) -> list[TikTokContentLink]:
        return self.repository.list_content_links(creator_id)

    def list_rate_limit_usage(self, connection_id: str) -> list[TikTokRateLimitUsage]:
        return self.repository.list_rate_limit_usage(connection_id)

    def export_report(self, run_id: str, format_name: str, *, destination: Path | None = None) -> Path:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise TikTokSyncError("La corrida no existe.")
        connection = self.repository.get_connection(run.connection_id)
        report = TikTokSyncReport(
            connection_id=run.connection_id,
            profile_id=run.profile_id,
            granted_scopes=tuple(_json_loads(connection.granted_scopes_json, [])) if connection else READ_ONLY_SCOPES,
            access_level=None if connection is None or connection.access_level is None else connection.access_level.value,
            sync_type=run.sync_type.value,
            period=None,
            discovered_count=run.discovered_count,
            imported_count=run.imported_count,
            updated_count=run.updated_count,
            unchanged_count=run.unchanged_count,
            skipped_count=run.skipped_count,
            linked_count=len(self.repository.list_content_links(run.creator_id)),
            unlinked_count=0,
            profile_metrics=("follower_count", "following_count", "likes_count", "video_count"),
            video_metrics=("view_count", "like_count", "comment_count", "share_count"),
            unavailable_metrics=("watch_time", "average_watch_time", "completion_rate", "retention", "saves", "profile_views", "traffic_source", "follower_conversion", "demographics", "for_you_traffic"),
            manual_import_recommendation="manual CSV/XLSX continues for private analytics metrics",
            warnings=tuple(),
            errors=tuple(),
            estimated_usage=run.estimated_usage,
            duration_seconds=None,
            next_action=None,
        )
        export_root = destination or self._exports_root
        export_root.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path = export_root / f"{run_id}_tiktok_sync.json"
            path.write_text(_json_dumps(report.to_dict()), encoding="utf-8")
            return path
        if format_name == "txt":
            path = export_root / f"{run_id}_tiktok_sync.txt"
            path.write_text("\n".join(f"{key}: {value}" for key, value in report.to_dict().items()), encoding="utf-8")
            return path
        if format_name == "csv":
            path = export_root / f"{run_id}_tiktok_sync.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["field", "value"])
                for key, value in report.to_dict().items():
                    writer.writerow([key, _csv_safe_value(value)])
            return path
        raise TikTokSyncError("Formato de exportacion no soportado.")

    def get_product_approval_summary(self, *, development_mode: bool | None = None) -> TikTokProductApprovalSummary:
        development = self.settings.environment != "production" if development_mode is None else development_mode
        return TikTokProductApprovalSummary(
            login_kit_enabled=True,
            display_api_enabled=True,
            scope_approved=True,
            development_mode=development,
            production_mode=not development,
            app_review_required=not development,
            product_not_approved=False,
            scope_not_approved=False,
            unknown=False,
        )

    def upsert_sync_schedule(self, schedule: TikTokSyncSchedule) -> TikTokSyncSchedule:
        return self.repository.upsert_sync_schedule(schedule)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[TikTokSyncSchedule]:
        return self.repository.list_sync_schedules(creator_id, connection_id=connection_id)


def build_tiktok_integration_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: TikTokIntegrationRepository,
    database: SQLiteDatabase,
    analytics_repository: SQLiteAnalyticsRepository | None = None,
    creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
    oauth_client: TikTokDesktopOAuthClient | None = None,
    credential_store: TikTokCredentialStore | None = None,
    display_api_client: TikTokDisplayApiClient | None = None,
    rate_limit_tracker: TikTokRateLimitTracker | None = None,
    logger: logging.Logger | None = None,
) -> TikTokIntegrationService:
    return TikTokIntegrationService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=oauth_client,
        credential_store=credential_store,
        display_api_client=display_api_client,
        rate_limit_tracker=rate_limit_tracker,
        logger=logger,
    )
