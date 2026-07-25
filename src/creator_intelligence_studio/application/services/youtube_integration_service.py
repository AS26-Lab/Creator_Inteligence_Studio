"""Servicio principal de integracion YouTube de solo lectura."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.application.services.creative_packaging_service import CreativePackagingService
from creator_intelligence_studio.domain.analytics.entities import (
    AnalyticsChannel,
    AnalyticsMetricSnapshot,
    AnalyticsPlatform,
    AnalyticsPublication,
)
from creator_intelligence_studio.domain.analytics.services import (
    build_metric_snapshot_dedupe_key,
    build_publication_dedupe_key,
    normalize_content_type,
    normalize_text,
    normalize_url,
)
from creator_intelligence_studio.domain.analytics.value_objects import (
    AnalyticsContentType,
    AnalyticsPlatformStatus,
    AnalyticsQualityStatus,
    AnalyticsSourceType,
)
from creator_intelligence_studio.domain.creative_packaging.entities import (
    PackagingAsset,
    ThumbnailVersion,
    TitleVersion,
)
from creator_intelligence_studio.domain.creative_packaging.value_objects import (
    PackagingAssetStatus,
    PackagingAssetType,
)
from creator_intelligence_studio.domain.youtube_integration.connection_types import (
    YouTubeConnectionStatus,
    YouTubeCredentialBackend,
    YouTubeLinkMethod,
    YouTubeRemoteContentType,
)
from creator_intelligence_studio.domain.youtube_integration.entities import (
    YouTubeChannel,
    YouTubeConnection,
    YouTubeContentLink,
    YouTubeMetricImport,
    YouTubeMetricValue,
    YouTubeQuotaUsage,
    YouTubeRemoteVideo,
    YouTubeSyncItem,
    YouTubeSyncReport,
    YouTubeSyncRun,
    YouTubeSyncSchedule,
    YouTubeVideoThumbnail,
)
from creator_intelligence_studio.domain.youtube_integration.errors import (
    YouTubeAuthorizationError,
    YouTubeConnectionError,
    YouTubeIntegrationError,
    YouTubeQuotaError,
    YouTubeSyncError,
)
from creator_intelligence_studio.domain.youtube_integration.metric_types import (
    YouTubeMetricAvailability,
)
from creator_intelligence_studio.domain.youtube_integration.repositories import YouTubeIntegrationRepository
from creator_intelligence_studio.domain.youtube_integration.services import (
    build_youtube_fingerprint,
    classify_remote_content_type,
    READ_ONLY_SCOPES,
    map_official_metric,
    is_write_scope,
)
from creator_intelligence_studio.domain.youtube_integration.sync_types import (
    YouTubeSyncStatus,
    YouTubeSyncType,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.infrastructure.youtube.analytics_api_client import YouTubeAnalyticsApiClient
from creator_intelligence_studio.infrastructure.youtube.channel_mapper import map_channel_payload
from creator_intelligence_studio.infrastructure.youtube.credential_store import (
    CredentialBundle,
    CredentialStore,
    DevelopmentCredentialStore,
    EncryptedLocalCredentialStore,
)
from creator_intelligence_studio.infrastructure.youtube.data_api_client import YouTubeDataApiClient
from creator_intelligence_studio.infrastructure.youtube.metric_mapper import map_metric_values
from creator_intelligence_studio.infrastructure.youtube.oauth_client import (
    DesktopYouTubeOAuthClient,
    OAuthAuthorizationResult,
    OAuthTokenResult,
    YouTubeOAuthClient,
)
from creator_intelligence_studio.infrastructure.youtube.quota_tracker import QuotaEstimate, QuotaTracker
from creator_intelligence_studio.infrastructure.youtube.retry_policy import backoff_delay, is_retryable_status
from creator_intelligence_studio.infrastructure.youtube.video_mapper import map_remote_video, map_video_thumbnails
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


def _safe_int(value: object | None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _safe_float(value: object | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return utc_now()


@dataclass(frozen=True, slots=True)
class YouTubeConnectionResult:
    connection: YouTubeConnection
    authorization_url: str | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "connection": self.connection.to_dict(),
            "authorization_url": self.authorization_url,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class YouTubeSyncResult:
    run: YouTubeSyncRun
    report: YouTubeSyncReport
    channels: tuple[YouTubeChannel, ...]
    videos: tuple[YouTubeRemoteVideo, ...]
    metric_imports: tuple[YouTubeMetricImport, ...]
    items: tuple[YouTubeSyncItem, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "report": self.report.to_dict(),
            "channels": [item.to_dict() for item in self.channels],
            "videos": [item.to_dict() for item in self.videos],
            "metric_imports": [item.to_dict() for item in self.metric_imports],
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
        }


class YouTubeIntegrationService:
    """Orquesta OAuth, sincronizacion y almacenamiento local."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: YouTubeIntegrationRepository,
        database: SQLiteDatabase,
        analytics_repository: SQLiteAnalyticsRepository | None = None,
        creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
        oauth_client: YouTubeOAuthClient | None = None,
        credential_store: CredentialStore | None = None,
        data_api_client: YouTubeDataApiClient | None = None,
        analytics_api_client: YouTubeAnalyticsApiClient | None = None,
        quota_tracker: QuotaTracker | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.analytics_repository = analytics_repository
        self.creative_packaging_repository = creative_packaging_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.youtube")
        self.oauth_client = oauth_client or DesktopYouTubeOAuthClient()
        self.credential_store = credential_store or self._build_default_credential_store()
        self.data_api_client = data_api_client or YouTubeDataApiClient()
        self.analytics_api_client = analytics_api_client or YouTubeAnalyticsApiClient()
        self.quota_tracker = quota_tracker or QuotaTracker()
        self._exports_root = self.paths.data_directory / "youtube" / "exports"
        self._exports_root.mkdir(parents=True, exist_ok=True)
        self._thumbnails_root = self.paths.data_directory / "youtube" / "thumbnails"
        self._thumbnails_root.mkdir(parents=True, exist_ok=True)
        self._download_thumbnails_locally = False

    def _build_default_credential_store(self) -> CredentialStore:
        credential_root = self.paths.data_directory / "youtube" / "credentials"
        try:
            return EncryptedLocalCredentialStore(credential_root)
        except Exception as exc:
            if self.settings.environment in {"development", "test"}:
                self.logger.warning("Cayendo a almacenamiento de desarrollo para credenciales de YouTube: %s", exc)
                return DevelopmentCredentialStore(self.paths.data_directory / "youtube" / "development_credentials")
            raise YouTubeAuthorizationError("No se pudo inicializar el almacenamiento seguro de credenciales de YouTube.") from exc

    def _credential_bundle(self, connection: YouTubeConnection) -> CredentialBundle | None:
        return self.credential_store.load(connection.credential_reference)

    def _assert_creator_isolation(self, connection: YouTubeConnection, creator_id: str) -> None:
        if connection.creator_id != creator_id:
            raise YouTubeConnectionError("La conexion no pertenece al creador solicitado.")

    def _ensure_read_only_scopes(self, scopes: tuple[str, ...]) -> None:
        forbidden = [scope for scope in scopes if is_write_scope(scope)]
        if forbidden:
            raise YouTubeAuthorizationError(f"Se detectaron scopes de escritura no permitidos: {forbidden}")
        if not set(scopes).issubset(set(READ_ONLY_SCOPES)):
            raise YouTubeAuthorizationError("Solo se permiten scopes de lectura oficiales de YouTube.")

    def estimate_quota(self, operation_key: str, *, estimated_cost: float, request_count: int = 1) -> QuotaEstimate:
        return self.quota_tracker.estimate(operation_key, estimated_cost=estimated_cost, request_count=request_count)

    def record_quota_usage(self, connection_id: str, operation_key: str, estimated_cost: float, request_count: int = 1, usage_date: str | None = None) -> YouTubeQuotaUsage:
        quota = YouTubeQuotaUsage(
            id=str(uuid4()),
            connection_id=connection_id,
            operation_key=operation_key,
            estimated_cost=estimated_cost,
            request_count=request_count,
            usage_date=usage_date or _now().date().isoformat(),
            created_at=_now(),
        )
        return self.repository.upsert_quota_usage(quota)

    def connect_account(
        self,
        *,
        creator_id: str,
        client_id: str,
        client_secret: str | None = None,
        authorization_code: str | None = None,
        redirect_uri: str | None = None,
        scopes: tuple[str, ...] = READ_ONLY_SCOPES,
        google_account_identifier: str | None = None,
    ) -> YouTubeConnectionResult:
        self._ensure_read_only_scopes(scopes)
        connection = self.repository.upsert_connection(
            YouTubeConnection(
                id=str(uuid4()),
                creator_id=creator_id,
                google_account_identifier=google_account_identifier,
                status=YouTubeConnectionStatus.PENDING if authorization_code is None else YouTubeConnectionStatus.CONNECTED,
                granted_scopes_json=_json_dumps(scopes),
                credential_reference=f"youtube_{creator_id}_{uuid4().hex}",
                connected_at=_now(),
                last_verified_at=None,
                disconnected_at=None,
                created_at=_now(),
                updated_at=_now(),
            )
        )
        if authorization_code is None:
            auth = self.oauth_client.begin_authorization(client_id=client_id, scopes=scopes, redirect_uri=redirect_uri)
            return YouTubeConnectionResult(connection=connection, authorization_url=auth.authorization_url, warnings=("pending_authorization",))
        token = self.oauth_client.exchange_code(client_id=client_id, client_secret=client_secret, code=authorization_code, redirect_uri=redirect_uri or "http://127.0.0.1:8765/callback")
        self.credential_store.save(
            connection.credential_reference,
            CredentialBundle(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                token_type=token.token_type,
                expires_at=None,
                granted_scopes=token.granted_scopes,
                google_account_identifier=google_account_identifier,
            ),
        )
        verified = self.verify_connection(connection.id)
        return YouTubeConnectionResult(connection=verified, authorization_url=None, warnings=())

    def verify_connection(self, connection_id: str) -> YouTubeConnection:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise YouTubeConnectionError("La conexion no existe.")
        bundle = self._credential_bundle(connection)
        if bundle is None:
            raise YouTubeAuthorizationError("No hay credenciales almacenadas para esta conexion.")
        if bundle.refresh_token and self.oauth_client is not None:
            try:
                refreshed = self.oauth_client.refresh_token(client_id="", client_secret=None, refresh_token=bundle.refresh_token)
                bundle = CredentialBundle(
                    access_token=refreshed.access_token,
                    refresh_token=refreshed.refresh_token,
                    token_type=refreshed.token_type,
                    expires_at=None,
                    granted_scopes=refreshed.granted_scopes,
                    google_account_identifier=bundle.google_account_identifier,
                )
                self.credential_store.save(connection.credential_reference, bundle)
            except Exception:
                pass
        verified = self.oauth_client.verify_token(bundle.access_token or "", tuple(_json_loads(connection.granted_scopes_json, [])))
        granted_scopes = tuple(verified.get("granted_scopes") or bundle.granted_scopes)
        self._ensure_read_only_scopes(granted_scopes)
        updated = replace(
            connection,
            status=YouTubeConnectionStatus.VERIFIED,
            google_account_identifier=str(verified.get("google_account_identifier")) if verified.get("google_account_identifier") else connection.google_account_identifier,
            granted_scopes_json=_json_dumps(granted_scopes),
            last_verified_at=_now(),
            updated_at=_now(),
        )
        return self.repository.upsert_connection(updated)

    def disconnect_connection(self, connection_id: str) -> YouTubeConnection:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise YouTubeConnectionError("La conexion no existe.")
        updated = replace(connection, status=YouTubeConnectionStatus.DISCONNECTED, disconnected_at=_now(), updated_at=_now())
        return self.repository.upsert_connection(updated)

    def revoke_connection(self, connection_id: str) -> YouTubeConnection:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise YouTubeConnectionError("La conexion no existe.")
        bundle = self._credential_bundle(connection)
        token = bundle.refresh_token if bundle and bundle.refresh_token else (bundle.access_token if bundle else None)
        if token:
            try:
                self.oauth_client.revoke(token)
            finally:
                self.credential_store.delete(connection.credential_reference)
        updated = replace(connection, status=YouTubeConnectionStatus.REVOKED, disconnected_at=_now(), updated_at=_now())
        return self.repository.upsert_connection(updated)

    def list_connections(self, creator_id: str) -> list[YouTubeConnection]:
        return self.repository.list_connections(creator_id)

    def get_connection(self, connection_id: str) -> YouTubeConnection | None:
        return self.repository.get_connection(connection_id)

    def list_channels(self, creator_id: str) -> list[YouTubeChannel]:
        return self.repository.list_channels(creator_id)

    def select_channel(self, channel_id: str) -> YouTubeChannel:
        channel = self.repository.get_channel(channel_id)
        if channel is None:
            raise YouTubeConnectionError("El canal remoto no existe.")
        return self.repository.upsert_channel(replace(channel, selected_for_sync=True, updated_at=_now()))

    def get_channel(self, channel_id: str) -> YouTubeChannel | None:
        return self.repository.get_channel(channel_id)

    def list_remote_videos(self, channel_id: str) -> list[YouTubeRemoteVideo]:
        return self.repository.list_remote_videos(channel_id)

    def get_remote_video(self, remote_video_id: str) -> YouTubeRemoteVideo | None:
        return self.repository.get_remote_video(remote_video_id)

    def list_sync_runs(self, creator_id: str, *, channel_id: str | None = None) -> list[YouTubeSyncRun]:
        return self.repository.list_sync_runs(creator_id, channel_id=channel_id)

    def get_sync_run(self, run_id: str) -> YouTubeSyncRun | None:
        return self.repository.get_sync_run(run_id)

    def list_sync_items(self, sync_run_id: str) -> list[YouTubeSyncItem]:
        return self.repository.list_sync_items(sync_run_id)

    def list_metric_imports(self, creator_id: str, *, channel_id: str | None = None) -> list[YouTubeMetricImport]:
        return self.repository.list_metric_imports(creator_id, channel_id=channel_id)

    def get_metric_import(self, metric_import_id: str) -> YouTubeMetricImport | None:
        return self.repository.get_metric_import(metric_import_id)

    def list_metric_values(self, metric_import_id: str) -> list[YouTubeMetricValue]:
        return self.repository.list_metric_values(metric_import_id)

    def list_content_links(self, creator_id: str) -> list[YouTubeContentLink]:
        return self.repository.list_content_links(creator_id)

    def list_video_thumbnails(self, remote_video_id: str) -> list[YouTubeVideoThumbnail]:
        return self.repository.list_video_thumbnails(remote_video_id)

    def list_quota_usage(self, connection_id: str) -> list[YouTubeQuotaUsage]:
        return self.repository.list_quota_usage(connection_id)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[YouTubeSyncSchedule]:
        return self.repository.list_sync_schedules(creator_id, connection_id=connection_id)

    def upsert_sync_schedule(self, schedule: YouTubeSyncSchedule) -> YouTubeSyncSchedule:
        return self.repository.upsert_sync_schedule(schedule)

    def interrupt_sync_run(self, run_id: str, *, reason: str | None = None) -> YouTubeSyncRun:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise YouTubeSyncError("La corrida no existe.")
        if run.status in {YouTubeSyncStatus.COMPLETED, YouTubeSyncStatus.COMPLETED_WITH_WARNINGS, YouTubeSyncStatus.CANCELLED}:
            return run
        updated = replace(
            run,
            status=YouTubeSyncStatus.INTERRUPTED,
            error_code=reason or run.error_code,
            error_message=reason or run.error_message,
            completed_at=_now(),
        )
        return self.repository.upsert_sync_run(updated)

    def link_content(
        self,
        *,
        creator_id: str,
        remote_video_id: str,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        link_method: str = YouTubeLinkMethod.MANUAL.value,
        confidence_level: str = "low",
        status: str = "pending",
    ) -> YouTubeContentLink:
        remote_video = self.repository.get_remote_video(remote_video_id)
        if remote_video is None or remote_video.creator_id != creator_id:
            raise YouTubeConnectionError("El video remoto no existe para el creador solicitado.")
        link = YouTubeContentLink(
            id=str(uuid4()),
            creator_id=creator_id,
            remote_video_id=remote_video_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            link_method=YouTubeLinkMethod(link_method),
            confidence_level=confidence_level,
            status=status,
            reviewed_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        return self.repository.upsert_content_link(link)

    def unlink_content(self, *, creator_id: str, remote_video_id: str) -> YouTubeContentLink:
        links = [item for item in self.repository.list_content_links(creator_id) if item.remote_video_id == remote_video_id]
        if not links:
            raise YouTubeConnectionError("No existe un enlace para el video remoto.")
        link = replace(links[0], publication_id=None, video_asset_id=None, status="unlinked", updated_at=_now())
        return self.repository.upsert_content_link(link)

    def _ensure_analytics_platform(self, platform_key: str) -> AnalyticsPlatform | None:
        if self.analytics_repository is None:
            return None
        existing = self.analytics_repository.get_platform_by_key(platform_key)
        if existing is not None:
            return existing
        platform = AnalyticsPlatform(
            id=str(uuid4()),
            platform_key=platform_key,
            display_name=platform_key.replace("_", " ").title(),
            status=AnalyticsPlatformStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )
        return self.analytics_repository.upsert_platform(platform)

    def _ensure_analytics_channel(self, *, creator_id: str, connection: YouTubeConnection, youtube_channel: YouTubeChannel) -> AnalyticsChannel | None:
        if self.analytics_repository is None:
            return None
        platform = self._ensure_analytics_platform(youtube_channel.platform_key if hasattr(youtube_channel, "platform_key") else "youtube_longform")
        if platform is None:
            return None
        existing = next((item for item in self.analytics_repository.list_channels(creator_id) if item.external_channel_id == youtube_channel.youtube_channel_id), None)
        channel = AnalyticsChannel(
            id=existing.id if existing else str(uuid4()),
            creator_id=creator_id,
            platform_id=platform.id,
            platform_key=platform.platform_key,
            external_channel_id=youtube_channel.youtube_channel_id,
            channel_name=youtube_channel.title,
            channel_url=youtube_channel.custom_url,
            timezone_name="UTC",
            is_primary=youtube_channel.selected_for_sync,
            metadata_json=_json_dumps(youtube_channel.to_dict()),
            created_at=existing.created_at if existing else _now(),
            updated_at=_now(),
        )
        return self.analytics_repository.upsert_channel(channel)

    def _ensure_publication(self, *, creator_id: str, channel_id: str | None, remote_video: YouTubeRemoteVideo) -> AnalyticsPublication | None:
        if self.analytics_repository is None:
            return None
        platform = "youtube_longform" if remote_video.content_type == YouTubeRemoteContentType.YOUTUBE_LONGFORM else "youtube_short"
        content_type = normalize_content_type(
            {
                YouTubeRemoteContentType.YOUTUBE_LONGFORM: "longform_video",
                YouTubeRemoteContentType.YOUTUBE_SHORT: "short_video",
                YouTubeRemoteContentType.PROBABLE_SHORT: "short_video",
                YouTubeRemoteContentType.LIVE: "live_replay",
                YouTubeRemoteContentType.UPCOMING: "live_replay",
                YouTubeRemoteContentType.UNKNOWN: "other",
            }.get(remote_video.content_type, "other")
        )
        existing = next(
            (
                publication
                for publication in self.analytics_repository.list_publications(
                    creator_id,
                    filters={"platform": platform, "channel_id": channel_id} if channel_id else {"platform": platform},
                )
                if publication.external_publication_id == remote_video.youtube_video_id
            ),
            None,
        )
        dedupe_key = existing.dedupe_key if existing is not None else build_publication_dedupe_key(
            platform=platform,
            external_publication_id=remote_video.youtube_video_id,
            url=f"https://www.youtube.com/watch?v={remote_video.youtube_video_id}",
            title=remote_video.title,
            published_at=remote_video.published_at,
            channel_id=channel_id,
        )
        publication = AnalyticsPublication(
            id=existing.id if existing else str(uuid4()),
            creator_id=creator_id,
            channel_id=channel_id,
            video_asset_id=remote_video.video_asset_id,
            external_publication_id=remote_video.youtube_video_id,
            platform=platform,
            content_type=content_type,
            title=remote_video.title,
            description=remote_video.description,
            published_at=remote_video.published_at,
            duration_seconds=remote_video.duration_seconds,
            url=f"https://www.youtube.com/watch?v={remote_video.youtube_video_id}",
            thumbnail_path=None,
            status="observed",
            source_type=AnalyticsSourceType.MANUAL,
            source_fingerprint=remote_video.remote_fingerprint,
            dedupe_key=dedupe_key,
            created_at=existing.created_at if existing else _now(),
            updated_at=_now(),
        )
        return self.analytics_repository.upsert_publication(publication)

    def _query_analytics_metric_rows(
        self,
        *,
        connection: YouTubeConnection,
        remote_video: YouTubeRemoteVideo,
        metrics: tuple[str, ...] | None,
    ) -> tuple[list[dict[str, object]], list[str]]:
        if self.analytics_api_client is None:
            return [], ["analytics_api_unavailable"]
        metric_names = tuple(metrics or ("views", "averageViewDuration", "averagePercentageViewed", "likes", "comments", "shares", "subscribersGained", "subscribersLost", "impressions", "impressionClickThroughRate", "returningViewers", "uniqueViewers"))
        rows: list[dict[str, object]] = []
        warnings: list[str] = []
        for metric_name in metric_names:
            try:
                page = self.analytics_api_client.query(
                    ids="channel==MINE",
                    metrics=metric_name,
                    dimensions=None,
                    filters=f"video=={remote_video.youtube_video_id}",
                    start_date=remote_video.published_at.date().isoformat(),
                    end_date=_now().date().isoformat(),
                    max_results=200,
                )
                raw_page = _json_loads(page.raw_json, {})
                metric_rows = raw_page.get("rows") if isinstance(raw_page, dict) else None
                if isinstance(metric_rows, list) and metric_rows:
                    for row in metric_rows:
                        value = row[0] if isinstance(row, list) and row else row
                        rows.append({"raw_metric_name": metric_name, "numeric_value": _safe_float(value), "dimensions": {"scope": "video"}})
                else:
                    warnings.append(f"metric_not_available:{metric_name}")
            except Exception as exc:
                warnings.append(f"metric_query_failed:{metric_name}")
                self.logger.debug("Fallo consulta de metricas para %s: %s", remote_video.youtube_video_id, exc)
        return rows, warnings

    def _store_remote_thumbnails(self, remote_video: YouTubeRemoteVideo, payload: dict[str, object]) -> tuple[YouTubeVideoThumbnail, ...]:
        if self.repository is None:
            return tuple()
        thumbnails = map_video_thumbnails(remote_video.id, payload, imported_at=_now(), local_cache_path=None)
        stored_items: list[YouTubeVideoThumbnail] = []
        for thumbnail in thumbnails:
            stored_items.append(self.repository.upsert_video_thumbnail(thumbnail))
        return tuple(stored_items)

    def _ensure_title_version(self, *, creator_id: str, publication: AnalyticsPublication | None, remote_video: YouTubeRemoteVideo) -> TitleVersion | None:
        if self.creative_packaging_repository is None:
            return None
        asset = next((item for item in self.creative_packaging_repository.list_assets(creator_id) if item.asset_type == PackagingAssetType.TITLE and item.publication_id == (publication.id if publication else None)), None)
        if asset is None:
            asset = self.creative_packaging_repository.upsert_asset(
                PackagingAsset(
                    id=str(uuid4()),
                    creator_id=creator_id,
                    publication_id=publication.id if publication else None,
                    video_asset_id=publication.video_asset_id if publication else remote_video.video_asset_id,
                    asset_type=PackagingAssetType.TITLE,
                    platform=publication.platform if publication else ("youtube_short" if remote_video.content_type != YouTubeRemoteContentType.YOUTUBE_LONGFORM else "youtube_longform"),
                    content_type=publication.content_type.value if publication else "other",
                    topic=None,
                    status=PackagingAssetStatus.ACTIVE,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
        last = self.creative_packaging_repository.list_title_versions(asset.id)
        if last and last[0].source_fingerprint == remote_video.remote_fingerprint and last[0].title_text == remote_video.title:
            return last[0]
        version = TitleVersion(
            id=str(uuid4()),
            packaging_asset_id=asset.id,
            version_number=(last[0].version_number + 1 if last else 1),
            title_text=remote_video.title,
            source_type="youtube_sync",
            language=remote_video.default_language or "und",
            platform=publication.platform if publication else ("youtube_short" if remote_video.content_type != YouTubeRemoteContentType.YOUTUBE_LONGFORM else "youtube_longform"),
            content_type=publication.content_type.value if publication else "other",
            topic=None,
            is_published=True,
            is_selected=True,
            creator_approval_status="imported",
            creator_feedback=None,
            source_fingerprint=remote_video.remote_fingerprint,
            created_at=_now(),
            updated_at=_now(),
        )
        return self.creative_packaging_repository.upsert_title_version(version)

    def _ensure_thumbnail_version(self, *, creator_id: str, publication: AnalyticsPublication | None, remote_video: YouTubeRemoteVideo) -> ThumbnailVersion | None:
        if self.creative_packaging_repository is None:
            return None
        asset = next((item for item in self.creative_packaging_repository.list_assets(creator_id) if item.asset_type == PackagingAssetType.THUMBNAIL and item.publication_id == (publication.id if publication else None)), None)
        if asset is None:
            asset = self.creative_packaging_repository.upsert_asset(
                PackagingAsset(
                    id=str(uuid4()),
                    creator_id=creator_id,
                    publication_id=publication.id if publication else None,
                    video_asset_id=publication.video_asset_id if publication else remote_video.video_asset_id,
                    asset_type=PackagingAssetType.THUMBNAIL,
                    platform=publication.platform if publication else ("youtube_short" if remote_video.content_type != YouTubeRemoteContentType.YOUTUBE_LONGFORM else "youtube_longform"),
                    content_type=publication.content_type.value if publication else "other",
                    topic=None,
                    status=PackagingAssetStatus.ACTIVE,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
        thumbnails = _json_loads(remote_video.thumbnail_metadata_json, {})
        primary = None
        if isinstance(thumbnails, dict):
            thumbs = thumbnails.get("thumbnails")
            if isinstance(thumbs, dict):
                primary = next(iter(thumbs.values()), None)
        file_fingerprint = remote_video.remote_fingerprint
        existing = self.creative_packaging_repository.list_thumbnail_versions(asset.id)
        if existing and existing[0].file_fingerprint == file_fingerprint:
            return existing[0]
        thumbnail = ThumbnailVersion(
            id=str(uuid4()),
            packaging_asset_id=asset.id,
            version_number=(existing[0].version_number + 1 if existing else 1),
            image_path=None,
            source_type="youtube_sync",
            width=_safe_int(primary.get("width") if isinstance(primary, dict) else None) if primary else None,
            height=_safe_int(primary.get("height") if isinstance(primary, dict) else None) if primary else None,
            file_fingerprint=file_fingerprint,
            concept_id=None,
            is_published=True,
            is_selected=True,
            creator_approval_status="imported",
            creator_feedback=None,
            created_at=_now(),
            updated_at=_now(),
        )
        return self.creative_packaging_repository.upsert_thumbnail_version(thumbnail)

    def _ensure_metrics(
        self,
        *,
        creator_id: str,
        channel_id: str,
        publication: AnalyticsPublication,
        remote_video: YouTubeRemoteVideo,
        sync_run_id: str,
        metric_scope: str,
        rows: list[dict[str, object]],
        date_start: str,
        date_end: str,
    ) -> tuple[YouTubeMetricImport, tuple[YouTubeMetricValue, ...]]:
        fingerprint = build_youtube_fingerprint({
            "creator_id": creator_id,
            "channel_id": channel_id,
            "remote_video_id": remote_video.id,
            "sync_run_id": sync_run_id,
            "metric_scope": metric_scope,
            "date_start": date_start,
            "date_end": date_end,
            "rows": rows,
        })
        metric_import = self.repository.upsert_metric_import(
            YouTubeMetricImport(
                id=str(uuid4()),
                creator_id=creator_id,
                channel_id=channel_id,
                remote_video_id=remote_video.id,
                sync_run_id=sync_run_id,
                metric_scope=metric_scope,
                date_start=date_start,
                date_end=date_end,
                comparable_window=None,
                source_fingerprint=fingerprint,
                status="completed",
                created_at=_now(),
            )
        )
        values = tuple(
            self.repository.upsert_metric_value(value)
            for row in rows
            for value in map_metric_values(metric_import_id=metric_import.id, raw_metric_name=row.get("raw_metric_name") or row.get("metric_name") or "", rows=[row], dimensions=row.get("dimensions") if isinstance(row.get("dimensions"), dict) else None)
        )
        return metric_import, values

    def _fetch_remote_channels(self, connection: YouTubeConnection, *, cursor: str | None = None) -> tuple[list[dict[str, object]], str | None]:
        page_token = cursor
        items: list[dict[str, object]] = []
        next_cursor = None
        attempts = 0
        while True:
            attempts += 1
            page = self.data_api_client.list_channels(mine=True, page_token=page_token)
            items.extend(page.items)
            next_cursor = page.next_page_token
            if not next_cursor:
                break
            page_token = next_cursor
            if attempts > 20:
                break
        return items, next_cursor

    def _fetch_remote_videos(self, channel_youtube_id: str, *, cursor: str | None = None) -> tuple[list[dict[str, object]], str | None]:
        page_token = cursor
        items: list[dict[str, object]] = []
        next_cursor = None
        attempts = 0
        while True:
            attempts += 1
            page = self.data_api_client.list_videos(channel_id=channel_youtube_id, page_token=page_token)
            items.extend(page.items)
            next_cursor = page.next_page_token
            if not next_cursor:
                break
            page_token = next_cursor
            if attempts > 20:
                break
        return items, next_cursor

    def _sync_channel_payload(
        self,
        *,
        creator_id: str,
        connection: YouTubeConnection,
        channel_payload: dict[str, object],
        sync_type: YouTubeSyncType,
        sync_run: YouTubeSyncRun,
        metrics: tuple[str, ...] | None = None,
    ) -> tuple[YouTubeChannel, list[YouTubeRemoteVideo], list[YouTubeMetricImport], list[YouTubeSyncItem], list[str], list[str]]:
        channel = map_channel_payload(payload=channel_payload, creator_id=creator_id, connection_id=connection.id, remote_fingerprint=build_youtube_fingerprint(channel_payload))
        stored_channel = self.repository.upsert_channel(channel)
        analytics_channel = self._ensure_analytics_channel(creator_id=creator_id, connection=connection, youtube_channel=stored_channel)
        if analytics_channel is not None:
            self.record_quota_usage(connection.id, "channel_metadata", 1.0)
        video_items, _ = self._fetch_remote_videos(stored_channel.youtube_channel_id)
        sync_items: list[YouTubeSyncItem] = []
        remote_videos: list[YouTubeRemoteVideo] = []
        metric_imports: list[YouTubeMetricImport] = []
        warnings: list[str] = []
        errors: list[str] = []
        for video_payload in video_items:
            remote_video = map_remote_video(video_payload, creator_id=creator_id, channel_id=stored_channel.id)
            existing_video = self.repository.get_remote_video_by_youtube_id(creator_id, remote_video.youtube_video_id)
            if existing_video and existing_video.remote_fingerprint == remote_video.remote_fingerprint:
                stored_video = existing_video
                action = "unchanged"
                status = "skipped"
            else:
                stored_video = self.repository.upsert_remote_video(replace(remote_video, first_seen_at=existing_video.first_seen_at if existing_video else remote_video.first_seen_at, created_at=existing_video.created_at if existing_video else remote_video.created_at))
                action = "upserted"
                status = "completed"
            remote_videos.append(stored_video)
            sync_items.append(
                self.repository.upsert_sync_item(
                    YouTubeSyncItem(
                        id=str(uuid4()),
                        sync_run_id=sync_run.id,
                        remote_type="video",
                        remote_id=stored_video.youtube_video_id,
                        local_type="youtube_remote_video",
                        local_id=stored_video.id,
                        action=action,
                        status=status,
                        warnings_json=_json_dumps(list(_json_loads(stored_video.thumbnail_metadata_json, {}).get("warnings", [])) if stored_video.thumbnail_metadata_json else []),
                        error_code=None,
                        error_message=None,
                        created_at=_now(),
                    )
                )
            )
            stored_thumbnails = self._store_remote_thumbnails(stored_video, video_payload)
            for thumbnail in stored_thumbnails:
                sync_items.append(
                    self.repository.upsert_sync_item(
                        YouTubeSyncItem(
                            id=str(uuid4()),
                            sync_run_id=sync_run.id,
                            remote_type="thumbnail",
                            remote_id=stored_video.youtube_video_id,
                            local_type="youtube_video_thumbnail",
                            local_id=thumbnail.id,
                            action="upserted",
                            status="completed",
                            warnings_json="[]",
                            error_code=None,
                            error_message=None,
                            created_at=_now(),
                        )
                    )
                )
            publication = self._ensure_publication(creator_id=creator_id, channel_id=analytics_channel.id if analytics_channel else None, remote_video=stored_video)
            if publication is not None:
                stored_video = self.repository.upsert_remote_video(replace(stored_video, publication_id=publication.id, updated_at=_now()))
                title_version = self._ensure_title_version(creator_id=creator_id, publication=publication, remote_video=stored_video)
                thumbnail_version = self._ensure_thumbnail_version(creator_id=creator_id, publication=publication, remote_video=stored_video)
                if title_version is not None:
                    sync_items.append(
                        self.repository.upsert_sync_item(
                            YouTubeSyncItem(
                                id=str(uuid4()),
                                sync_run_id=sync_run.id,
                                remote_type="title",
                                remote_id=stored_video.youtube_video_id,
                                local_type="title_version",
                                local_id=title_version.id,
                                action="upserted",
                                status="completed",
                                warnings_json="[]",
                                error_code=None,
                                error_message=None,
                                created_at=_now(),
                            )
                        )
                    )
                if thumbnail_version is not None:
                    sync_items.append(
                        self.repository.upsert_sync_item(
                            YouTubeSyncItem(
                                id=str(uuid4()),
                                sync_run_id=sync_run.id,
                                remote_type="thumbnail",
                                remote_id=stored_video.youtube_video_id,
                                local_type="thumbnail_version",
                                local_id=thumbnail_version.id,
                                action="upserted",
                                status="completed",
                                warnings_json="[]",
                                error_code=None,
                                error_message=None,
                                created_at=_now(),
                            )
                        )
                    )
                metric_rows, metric_warnings = self._query_analytics_metric_rows(
                    connection=connection,
                    remote_video=stored_video,
                    metrics=metrics,
                )
                warnings.extend(metric_warnings)
                if metric_rows:
                    metric_import, metric_values = self._ensure_metrics(
                        creator_id=creator_id,
                        channel_id=stored_channel.id,
                        publication=publication,
                        remote_video=stored_video,
                        sync_run_id=sync_run.id,
                        metric_scope="video",
                        rows=metric_rows,
                        date_start=stored_video.published_at.date().isoformat(),
                        date_end=_now().date().isoformat(),
                    )
                    metric_imports.append(metric_import)
                    for metric_value in metric_values:
                        self.repository.upsert_metric_value(metric_value)
            if stored_video.content_type == YouTubeRemoteContentType.PROBABLE_SHORT:
                warnings.append("probable_short")
        updated_channel = self.repository.upsert_channel(replace(stored_channel, last_synced_at=_now(), updated_at=_now()))
        if analytics_channel is not None:
            self.analytics_repository.upsert_channel(AnalyticsChannel(
                id=analytics_channel.id,
                creator_id=creator_id,
                platform_id=analytics_channel.platform_id,
                platform_key=analytics_channel.platform_key,
                external_channel_id=updated_channel.youtube_channel_id,
                channel_name=updated_channel.title,
                channel_url=updated_channel.custom_url,
                timezone_name="UTC",
                is_primary=updated_channel.selected_for_sync,
                metadata_json=analytics_channel.metadata_json,
                created_at=analytics_channel.created_at,
                updated_at=_now(),
            ))
        return updated_channel, remote_videos, metric_imports, sync_items, warnings, errors

    def sync_channel(self, *, creator_id: str, channel_id: str, sync_type: str = "incremental_sync", cursor: str | None = None, full_resync: bool = False, include_analytics: bool = True, include_thumbnails: bool = False, metrics: tuple[str, ...] | None = None) -> YouTubeSyncResult:
        channel = self.repository.get_channel(channel_id)
        if channel is None:
            raise YouTubeSyncError("El canal no existe.")
        connection = self.repository.get_connection(channel.connection_id)
        if connection is None:
            raise YouTubeSyncError("La conexion asociada no existe.")
        self._assert_creator_isolation(connection, creator_id)
        if connection.status in {YouTubeConnectionStatus.REVOKED, YouTubeConnectionStatus.DISCONNECTED}:
            raise YouTubeAuthorizationError("La conexion no esta activa.")
        self.verify_connection(connection.id)
        run = self.repository.upsert_sync_run(
            YouTubeSyncRun(
                id=str(uuid4()),
                creator_id=creator_id,
                connection_id=connection.id,
                channel_id=channel_id,
                sync_type=YouTubeSyncType(sync_type),
                status=YouTubeSyncStatus.AUTHENTICATING,
                configuration_json=_json_dumps({"full_resync": full_resync, "include_analytics": include_analytics, "include_thumbnails": include_thumbnails, "metrics": list(metrics or [])}),
                cursor_json=_json_dumps({"page_token": cursor}) if cursor else None,
                discovered_count=0,
                imported_count=0,
                updated_count=0,
                skipped_count=0,
                warning_count=0,
                error_count=0,
                quota_cost_estimate=None,
                started_at=_now(),
                completed_at=None,
                error_code=None,
                error_message=None,
                created_at=_now(),
            )
        )
        channel_payloads, next_cursor = self._fetch_remote_channels(connection, cursor=cursor)
        selected_payload = next((payload for payload in channel_payloads if str(payload.get("id") or "") == channel.youtube_channel_id), None)
        if selected_payload is None and channel_payloads:
            selected_payload = channel_payloads[0]
        if selected_payload is None:
            selected_payload = {
                "id": channel.youtube_channel_id,
                "snippet": {
                    "title": channel.title,
                    "description": channel.description,
                    "publishedAt": channel.published_at.isoformat(),
                    "country": channel.country,
                },
                "statistics": {
                    "subscriberCount": channel.subscriber_count,
                    "videoCount": channel.video_count,
                    "viewCount": channel.view_count,
                    "hiddenSubscriberCount": channel.hidden_subscriber_count,
                },
            }
        sync_items: list[YouTubeSyncItem] = []
        remote_videos: list[YouTubeRemoteVideo] = []
        metric_imports: list[YouTubeMetricImport] = []
        warnings: list[str] = []
        errors: list[str] = []
        discovered = 0
        imported = 0
        updated = 0
        skipped = 0
        linked = 0
        unlinked = 0
        for channel_payload in (selected_payload,):
            discovered += 1
            try:
                stored_channel, videos, imports, items, item_warnings, item_errors = self._sync_channel_payload(
                    creator_id=creator_id,
                    connection=connection,
                    channel_payload=channel_payload,
                    sync_type=YouTubeSyncType(sync_type),
                    sync_run=run,
                    metrics=metrics,
                )
                remote_videos.extend(videos)
                metric_imports.extend(imports)
                sync_items.extend(items)
                warnings.extend(item_warnings)
                errors.extend(item_errors)
                imported += len(videos)
                updated += int(bool(videos))
                skipped += 0
                run = replace(run, channel_id=stored_channel.id)
            except Exception as exc:
                errors.append(str(exc))
                sync_items.append(
                    self.repository.upsert_sync_item(
                        YouTubeSyncItem(
                            id=str(uuid4()),
                            sync_run_id=run.id,
                            remote_type="channel",
                            remote_id=channel_id,
                            local_type=None,
                            local_id=None,
                            action="failed",
                            status="failed",
                            warnings_json="[]",
                            error_code=type(exc).__name__,
                            error_message=str(exc),
                            created_at=_now(),
                        )
                    )
                )
        final_status = YouTubeSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else YouTubeSyncStatus.COMPLETED
        completed = self.repository.upsert_sync_run(
            replace(
                run,
                status=final_status,
                discovered_count=discovered,
                imported_count=imported,
                updated_count=updated,
                skipped_count=skipped,
                warning_count=len(warnings),
                error_count=len(errors),
                quota_cost_estimate=self.quota_tracker.get("channel_metadata").estimated_cost if self.quota_tracker.get("channel_metadata") else None,
                completed_at=_now(),
                error_code=errors[0] if errors else None,
                error_message=errors[0] if errors else None,
                cursor_json=_json_dumps({"page_token": next_cursor}) if next_cursor else run.cursor_json,
            )
        )
        report = YouTubeSyncReport(
            connection_id=connection.id,
            channel_id=channel_id,
            sync_type=sync_type,
            status=completed.status.value,
            discovered_count=discovered,
            imported_count=imported,
            updated_count=updated,
            unchanged_count=0,
            skipped_count=skipped,
            linked_count=linked,
            unlinked_count=unlinked,
            unavailable_metrics=tuple(sorted({"metric_not_available"} if not include_analytics else set())),
            warnings=tuple(sorted(set(warnings))),
            errors=tuple(sorted(set(errors))),
            quota_estimate=completed.quota_cost_estimate,
            duration_seconds=None,
            next_recommended_action="resume" if completed.status == YouTubeSyncStatus.INTERRUPTED else "review",
        )
        return YouTubeSyncResult(completed, report, tuple(self.repository.list_channels(creator_id)), tuple(remote_videos), tuple(metric_imports), tuple(sync_items), tuple(sorted(set(warnings))))

    def sync_incremental(self, *, creator_id: str, channel_id: str, cursor: str | None = None) -> YouTubeSyncResult:
        return self.sync_channel(creator_id=creator_id, channel_id=channel_id, sync_type="incremental_sync", cursor=cursor)

    def sync_content(self, *, creator_id: str, channel_id: str, cursor: str | None = None) -> YouTubeSyncResult:
        return self.sync_channel(creator_id=creator_id, channel_id=channel_id, sync_type="content_catalog", cursor=cursor)

    def sync_analytics(self, *, creator_id: str, channel_id: str, cursor: str | None = None, metrics: tuple[str, ...] | None = None) -> YouTubeSyncResult:
        return self.sync_channel(creator_id=creator_id, channel_id=channel_id, sync_type="video_analytics", cursor=cursor, include_analytics=True, metrics=metrics)

    def sync_thumbnail_metadata(self, *, creator_id: str, channel_id: str, cursor: str | None = None) -> YouTubeSyncResult:
        return self.sync_channel(creator_id=creator_id, channel_id=channel_id, sync_type="thumbnails_metadata", cursor=cursor, include_thumbnails=True)

    def sync_repair(self, *, creator_id: str, channel_id: str) -> YouTubeSyncResult:
        return self.sync_channel(creator_id=creator_id, channel_id=channel_id, sync_type="repair_sync", full_resync=True, include_analytics=True, include_thumbnails=True)

    def resume_sync(self, run_id: str) -> YouTubeSyncResult:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise YouTubeSyncError("La corrida no existe.")
        channel = self.repository.get_channel(run.channel_id) if run.channel_id else None
        if channel is None:
            raise YouTubeSyncError("No hay canal para reanudar.")
        return self.sync_channel(creator_id=run.creator_id, channel_id=channel.id, sync_type=run.sync_type.value, cursor=_json_loads(run.cursor_json, {}).get("page_token") if run.cursor_json else None)

    def export_sync_report(self, run_id: str, format_name: str, *, destination: Path | None = None) -> Path:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise YouTubeSyncError("La corrida no existe.")
        report = YouTubeSyncReport(
            connection_id=run.connection_id,
            channel_id=run.channel_id,
            sync_type=run.sync_type.value,
            status=run.status.value,
            discovered_count=run.discovered_count,
            imported_count=run.imported_count,
            updated_count=run.updated_count,
            unchanged_count=0,
            skipped_count=run.skipped_count,
            linked_count=0,
            unlinked_count=0,
            unavailable_metrics=tuple(),
            warnings=tuple(),
            errors=tuple(),
            quota_estimate=run.quota_cost_estimate,
            duration_seconds=None,
            next_recommended_action=None,
        )
        export_root = destination or self._exports_root
        export_root.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path = export_root / f"{run_id}_youtube_sync.json"
            path.write_text(_json_dumps(report.to_dict()), encoding="utf-8")
            return path
        if format_name == "txt":
            path = export_root / f"{run_id}_youtube_sync.txt"
            path.write_text("\n".join(f"{key}: {value}" for key, value in report.to_dict().items()), encoding="utf-8")
            return path
        if format_name == "csv":
            path = export_root / f"{run_id}_youtube_sync.csv"
            rows = [["field", "value"]]
            for key, value in report.to_dict().items():
                rows.append([key, value])
            with path.open("w", encoding="utf-8", newline="") as handle:
                import csv

                writer = csv.writer(handle)
                writer.writerows(rows)
            return path
        raise YouTubeIntegrationError("Formato de exportacion no soportado.")


def build_youtube_integration_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: YouTubeIntegrationRepository,
    database: SQLiteDatabase,
    analytics_repository: SQLiteAnalyticsRepository | None = None,
    creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
    oauth_client: YouTubeOAuthClient | None = None,
    credential_store: CredentialStore | None = None,
    data_api_client: YouTubeDataApiClient | None = None,
    analytics_api_client: YouTubeAnalyticsApiClient | None = None,
    quota_tracker: QuotaTracker | None = None,
    logger: logging.Logger | None = None,
) -> YouTubeIntegrationService:
    return YouTubeIntegrationService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=oauth_client,
        credential_store=credential_store,
        data_api_client=data_api_client,
        analytics_api_client=analytics_api_client,
        quota_tracker=quota_tracker,
        logger=logger,
    )
