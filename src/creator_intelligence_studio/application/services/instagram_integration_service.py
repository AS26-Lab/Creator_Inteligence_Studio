"""Servicio principal de integracion de solo lectura con Instagram."""

from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.analytics.entities import AnalyticsImport, AnalyticsMetricSnapshot, AnalyticsPublication
from creator_intelligence_studio.domain.analytics.services import build_metric_snapshot_dedupe_key, build_publication_dedupe_key
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsContentType, AnalyticsImportStatus, AnalyticsQualityStatus, AnalyticsSourceType
from creator_intelligence_studio.domain.creative_packaging.entities import PackagingAsset, ThumbnailVersion
from creator_intelligence_studio.domain.creative_packaging.value_objects import PackagingAssetStatus, PackagingAssetType
from creator_intelligence_studio.domain.integrations.contracts import (
    IntegrationErrorCategory,
    IntegrationErrorDetails,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationRateLimitState,
)
from creator_intelligence_studio.domain.instagram_integration.connection_types import (
    InstagramAccessLevel,
    InstagramAppAccessStatus,
    InstagramAuthProvider,
    InstagramConnectionStatus,
    InstagramContentType,
    InstagramLinkMethod,
    InstagramMediaType,
    InstagramProfessionalAccountType,
)
from creator_intelligence_studio.domain.instagram_integration.entities import (
    InstagramAccount,
    InstagramCaptionVersion,
    InstagramCarouselChild,
    InstagramConnection,
    InstagramContentLink,
    InstagramCoverVersion,
    InstagramInsightImport,
    InstagramInsightValue,
    InstagramRateLimitUsage,
    InstagramRemoteMedia,
    InstagramSyncItem,
    InstagramSyncReport,
    InstagramSyncRun,
    InstagramSyncSchedule,
)
from creator_intelligence_studio.domain.instagram_integration.errors import (
    InstagramAccountValidationError,
    InstagramAuthorizationError,
    InstagramConnectionError,
    InstagramIntegrationError,
    InstagramSyncError,
)
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod, InstagramInsightScope
from creator_intelligence_studio.domain.instagram_integration.media_types import map_content_type
from creator_intelligence_studio.domain.instagram_integration.repositories import InstagramIntegrationRepository
from creator_intelligence_studio.domain.instagram_integration.sync_types import InstagramSyncStatus, InstagramSyncType
from creator_intelligence_studio.domain.instagram_integration.value_objects import (
    InstagramAuthProviderClient,
    InstagramOAuthAuthorizationResult,
    InstagramOAuthTokenResult,
    build_instagram_credential_reference,
    READ_ONLY_SCOPES,
    build_instagram_fingerprint,
    is_write_scope,
)
from creator_intelligence_studio.domain.instagram_integration.value_objects import InstagramOAuthAuthorizationResult as OAuthAuthorizationResult
from creator_intelligence_studio.domain.instagram_integration.value_objects import InstagramOAuthTokenResult as OAuthTokenResult
from creator_intelligence_studio.domain.instagram_integration.oauth_broker import (
    InstagramOAuthBrokerClient,
    InstagramOAuthBrokerRedeemResult,
    InstagramOAuthBrokerStartResult,
    InstagramOAuthBrokerStatusResult,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.instagram.account_mapper import map_account_payload
from creator_intelligence_studio.infrastructure.instagram.api_client import InstagramApiClient, InstagramApiError
from creator_intelligence_studio.infrastructure.instagram.api_version import DEFAULT_INSTAGRAM_API_VERSION
from creator_intelligence_studio.infrastructure.instagram.credential_store import (
    DevelopmentInstagramCredentialStore,
    EncryptedLocalInstagramCredentialStore,
    InstagramCredentialBundle,
    InstagramCredentialStore,
)
from creator_intelligence_studio.infrastructure.instagram.insights_mapper import map_insight_import, map_insight_value
from creator_intelligence_studio.infrastructure.instagram.media_mapper import map_carousel_child_payload, map_cover_version, map_remote_media_payload
from creator_intelligence_studio.infrastructure.instagram.oauth_client import InstagramLoginOAuthClient
from creator_intelligence_studio.infrastructure.instagram.pagination import InstagramPage
from creator_intelligence_studio.infrastructure.instagram.rate_limit_tracker import InstagramRateLimitTracker
from creator_intelligence_studio.infrastructure.instagram.retry_policy import backoff_delay, is_retryable_status
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.shared.dates import utc_now
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


def _dict_payload(value: object) -> dict[str, object]:
    if hasattr(value, "payload") and isinstance(getattr(value, "payload"), dict):
        return getattr(value, "payload")
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError("No se puede convertir la respuesta remota a diccionario.")


def _page_items(value: object) -> tuple[dict[str, object], ...]:
    payload = _dict_payload(value)
    if "data" in payload and isinstance(payload["data"], list):
        return tuple(item for item in payload["data"] if isinstance(item, dict))
    if "items" in payload and isinstance(payload["items"], list):
        return tuple(item for item in payload["items"] if isinstance(item, dict))
    return tuple()


def _page_cursor(value: object) -> str | None:
    payload = _dict_payload(value)
    paging = payload.get("paging")
    if isinstance(paging, dict):
        cursors = paging.get("cursors")
        if isinstance(cursors, dict):
            after = cursors.get("after")
            if isinstance(after, str) and after:
                return after
    next_cursor = payload.get("next_cursor") or payload.get("next_page_token")
    return next_cursor if isinstance(next_cursor, str) and next_cursor else None


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


def _safe_float(value: object | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _map_content_type_to_analytics(content_type: InstagramContentType) -> AnalyticsContentType:
    return {
        InstagramContentType.INSTAGRAM_REEL: AnalyticsContentType.REEL,
        InstagramContentType.INSTAGRAM_POST: AnalyticsContentType.OTHER,
        InstagramContentType.INSTAGRAM_VIDEO: AnalyticsContentType.LONGFORM_VIDEO,
        InstagramContentType.INSTAGRAM_CAROUSEL: AnalyticsContentType.OTHER,
        InstagramContentType.INSTAGRAM_STORY: AnalyticsContentType.SHORT_VIDEO,
        InstagramContentType.INSTAGRAM_LIVE: AnalyticsContentType.LIVE_REPLAY,
        InstagramContentType.INSTAGRAM_UNKNOWN: AnalyticsContentType.OTHER,
    }[content_type]


def _analytics_platform_for_content_type(content_type: InstagramContentType) -> str:
    return {
        InstagramContentType.INSTAGRAM_REEL: "instagram_reel",
        InstagramContentType.INSTAGRAM_POST: "manual_other",
        InstagramContentType.INSTAGRAM_VIDEO: "instagram_post",
        InstagramContentType.INSTAGRAM_CAROUSEL: "instagram_post",
        InstagramContentType.INSTAGRAM_STORY: "instagram_story",
        InstagramContentType.INSTAGRAM_LIVE: "instagram_live",
        InstagramContentType.INSTAGRAM_UNKNOWN: "manual_other",
    }[content_type]


def _bounded_media_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_MEDIA_PAGE_LIMIT
    try:
        numeric = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_MEDIA_PAGE_LIMIT
    return max(1, min(numeric, MAX_MEDIA_PAGE_LIMIT))


PROFILE_READ_FIELDS: tuple[str, ...] = (
    "id",
    "username",
    "name",
    "biography",
    "website",
    "profile_picture_url",
    "followers_count",
    "follows_count",
    "media_count",
    "account_type",
)

MEDIA_READ_FIELDS: tuple[str, ...] = (
    "id",
    "caption",
    "media_type",
    "media_product_type",
    "media_url",
    "thumbnail_url",
    "permalink",
    "timestamp",
    "shortcode",
    "children_count",
    "children{id,media_type,media_url,thumbnail_url}",
)

DEFAULT_MEDIA_PAGE_LIMIT = 25
MAX_MEDIA_PAGE_LIMIT = 100


@dataclass(frozen=True, slots=True)
class InstagramConnectionResult:
    connection: InstagramConnection
    authorization_url: str | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "connection": self.connection.to_dict(),
            "authorization_url": self.authorization_url,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class InstagramProfileReadResult:
    connection: InstagramConnection
    account: InstagramAccount | None
    health: IntegrationHealth
    success: bool
    error: IntegrationErrorDetails | None = None
    provider_metadata: dict[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "connection": self.connection.to_dict(),
            "account": None if self.account is None else self.account.to_dict(),
            "health": self.health.to_dict(),
            "success": self.success,
            "error": None if self.error is None else self.error.to_dict(),
            "provider_metadata": dict(self.provider_metadata),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class InstagramSyncResult:
    run: InstagramSyncRun
    report: InstagramSyncReport
    accounts: tuple[InstagramAccount, ...]
    media: tuple[InstagramRemoteMedia, ...]
    captions: tuple[InstagramCaptionVersion, ...]
    covers: tuple[InstagramCoverVersion, ...]
    children: tuple[InstagramCarouselChild, ...]
    insight_imports: tuple[InstagramInsightImport, ...]
    insight_values: tuple[InstagramInsightValue, ...]
    links: tuple[InstagramContentLink, ...]
    sync_items: tuple[InstagramSyncItem, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "report": self.report.to_dict(),
            "accounts": [item.to_dict() for item in self.accounts],
            "media": [item.to_dict() for item in self.media],
            "captions": [item.to_dict() for item in self.captions],
            "covers": [item.to_dict() for item in self.covers],
            "children": [item.to_dict() for item in self.children],
            "insight_imports": [item.to_dict() for item in self.insight_imports],
            "insight_values": [item.to_dict() for item in self.insight_values],
            "links": [item.to_dict() for item in self.links],
            "sync_items": [item.to_dict() for item in self.sync_items],
            "warnings": list(self.warnings),
        }


class InstagramIntegrationService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: InstagramIntegrationRepository,
        database: SQLiteDatabase,
        analytics_repository: SQLiteAnalyticsRepository | None = None,
        creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
        oauth_client: InstagramAuthProviderClient | None = None,
        oauth_broker: InstagramOAuthBrokerClient | None = None,
        credential_store: InstagramCredentialStore | None = None,
        api_client: InstagramApiClient | None = None,
        rate_limit_tracker: InstagramRateLimitTracker | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.analytics_repository = analytics_repository
        self.creative_packaging_repository = creative_packaging_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.instagram")
        self.oauth_client = oauth_client or InstagramLoginOAuthClient()
        self.oauth_broker = oauth_broker
        self.credential_store = credential_store or self._build_default_credential_store()
        self.api_client = api_client or InstagramApiClient(api_version=DEFAULT_INSTAGRAM_API_VERSION)
        self.rate_limit_tracker = rate_limit_tracker or InstagramRateLimitTracker()
        self._exports_root = self.paths.data_directory / "instagram" / "exports"
        self._exports_root.mkdir(parents=True, exist_ok=True)

    def _build_default_credential_store(self) -> InstagramCredentialStore:
        credential_root = self.paths.data_directory / "instagram" / "credentials"
        try:
            return EncryptedLocalInstagramCredentialStore(credential_root)
        except Exception as exc:
            if self.settings.environment in {"development", "test"}:
                self.logger.warning("Cayendo a almacenamiento de desarrollo para credenciales de Instagram: %s", exc)
                return DevelopmentInstagramCredentialStore(self.paths.data_directory / "instagram" / "development_credentials")
            raise InstagramAuthorizationError("No se pudo inicializar el almacenamiento seguro de credenciales de Instagram.") from exc

    def _assert_creator_isolation(self, connection: InstagramConnection, creator_id: str) -> None:
        if connection.creator_id != creator_id:
            raise InstagramConnectionError("La conexion no pertenece al creador solicitado.")

    def _ensure_read_only_scopes(self, scopes: tuple[str, ...]) -> None:
        forbidden = [scope for scope in scopes if is_write_scope(scope)]
        if forbidden:
            raise InstagramAuthorizationError(f"Se detectaron scopes de escritura no permitidos: {forbidden}")
        if not set(scopes).issubset(set(READ_ONLY_SCOPES)):
            raise InstagramAuthorizationError("Solo se permiten scopes de lectura aprobados para Instagram.")

    def _credential_bundle(self, connection: InstagramConnection) -> InstagramCredentialBundle | None:
        return self.credential_store.load(connection.credential_reference)

    def _existing_connection_for_account(self, creator_id: str, instagram_user_id: str | None, *, provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN) -> InstagramConnection | None:
        if not instagram_user_id:
            return None
        for connection in self.repository.list_connections(creator_id):
            if connection.provider == provider.value and connection.account_identifier == instagram_user_id:
                return connection
        return None

    def _credential_reference_for(self, creator_id: str, instagram_user_id: str, *, provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN) -> str:
        return build_instagram_credential_reference(creator_id=creator_id, instagram_user_id=instagram_user_id, provider=provider)

    def _load_connection_bundle(self, connection: InstagramConnection) -> InstagramCredentialBundle:
        bundle = self._credential_bundle(connection)
        if bundle is None or not bundle.access_token:
            raise InstagramAuthorizationError("No hay credenciales disponibles para la conexion.")
        return bundle

    def _profile_read_health(
        self,
        *,
        connection: InstagramConnection,
        success: bool,
        error: IntegrationErrorDetails | None = None,
        rate_limit_state: IntegrationRateLimitState | None = None,
    ) -> IntegrationHealth:
        if success:
            return IntegrationHealth(
                connector_id=connection.provider,
                connector_available=True,
                account_authenticated=True,
                permissions_valid=True,
                rate_limit_state=rate_limit_state,
                last_success_at=_now(),
                status=IntegrationHealthStatus.HEALTHY,
                checked_at=_now(),
            )
        status = IntegrationHealthStatus.DEGRADED
        if error is not None and error.category == IntegrationErrorCategory.PROVIDER_UNAVAILABLE:
            status = IntegrationHealthStatus.UNAVAILABLE
        return IntegrationHealth(
            connector_id=connection.provider,
            connector_available=status != IntegrationHealthStatus.UNAVAILABLE,
            account_authenticated=False,
            permissions_valid=False,
            rate_limit_state=rate_limit_state,
            last_error_category=None if error is None else error.category,
            last_error_message=None if error is None else error.message,
            status=status,
            checked_at=_now(),
        )

    def _profile_read_error(
        self,
        *,
        connection: InstagramConnection,
        category: IntegrationErrorCategory,
        message: str,
        provider_code: str | None = None,
        provider_request_id: str | None = None,
        retryable: bool = False,
        safe_detail: str | None = None,
    ) -> InstagramProfileReadResult:
        error = IntegrationErrorDetails(
            category=category,
            message=message,
            provider_code=provider_code,
            provider_request_id=provider_request_id,
            retryable=retryable,
            safe_detail=safe_detail,
        )
        updated_connection = self.repository.upsert_connection(
            self._connection_to_status(connection, status=InstagramConnectionStatus.ERROR)
        )
        return InstagramProfileReadResult(
            connection=updated_connection,
            account=None,
            health=self._profile_read_health(connection=updated_connection, success=False, error=error),
            success=False,
            error=error,
            provider_metadata={},
            warnings=(),
        )

    def _profile_read_error_from_api_error(self, connection: InstagramConnection, error: InstagramApiError) -> InstagramProfileReadResult:
        details = error.details
        http_status = details.http_status
        reason = (details.reason or "").lower()
        message = details.message.strip() or "No se pudo leer el perfil de Instagram."
        code = details.code
        safe_detail = "provider_error"
        category = IntegrationErrorCategory.PROVIDER_ERROR
        retryable = False
        if http_status == 429 or "rate" in reason or "limit" in reason or "rate" in message.lower() or "limit" in message.lower():
            category = IntegrationErrorCategory.RATE_LIMITED
            safe_detail = "rate_limited"
            retryable = True
        elif http_status in {401, 403} and (
            code in {"190", "102", "190.0"}
            or "expired" in reason
            or "invalid" in reason
            or "auth" in reason
            or "auth" in message.lower()
        ):
            category = IntegrationErrorCategory.AUTHENTICATION_EXPIRED
            safe_detail = "authentication_expired"
            retryable = True
        elif http_status == 403 and ("permission" in reason or "permission" in message.lower() or "insufficient" in message.lower()):
            category = IntegrationErrorCategory.PERMISSION_DENIED
            safe_detail = "insufficient_permissions"
            retryable = True
        elif http_status is None:
            category = IntegrationErrorCategory.PROVIDER_UNAVAILABLE
            safe_detail = "network_unavailable"
            retryable = True
        elif http_status >= 500:
            category = IntegrationErrorCategory.PROVIDER_UNAVAILABLE
            safe_detail = "provider_unavailable"
            retryable = True
        elif http_status == 400:
            category = IntegrationErrorCategory.INVALID_REQUEST
            safe_detail = "invalid_request"
        error_details = IntegrationErrorDetails(
            category=category,
            message=message,
            provider_code=code,
            provider_request_id=details.request_path,
            retryable=retryable,
            safe_detail=safe_detail,
        )
        updated_connection = self.repository.upsert_connection(self._connection_to_status(connection, status=InstagramConnectionStatus.ERROR))
        self._record_rate_limit(updated_connection.id, "account_profile", error)
        rate_limit_state = IntegrationRateLimitState(limited=True) if category == IntegrationErrorCategory.RATE_LIMITED else None
        return InstagramProfileReadResult(
            connection=updated_connection,
            account=None,
            health=self._profile_read_health(connection=updated_connection, success=False, error=error_details, rate_limit_state=rate_limit_state),
            success=False,
            error=error_details,
            provider_metadata={
                "http_status": http_status,
                "provider_reason": details.reason,
            },
            warnings=(),
        )

    def _profile_read_success(
        self,
        *,
        connection: InstagramConnection,
        account_payload: dict[str, object],
        bundle: InstagramCredentialBundle,
        response: object | None = None,
    ) -> InstagramProfileReadResult:
        account_identifier = _safe_str(account_payload.get("id")) or connection.account_identifier or bundle.instagram_user_id
        if not account_identifier:
            raise InstagramConnectionError("No se pudo resolver el identificador de cuenta de Instagram.")
        mapped_account = map_account_payload(
            account_payload,
            creator_id=connection.creator_id,
            connection_id=connection.id,
            instagram_user_id=account_identifier,
            api_version=self.api_client.api_version,
        )
        if mapped_account.account_type == InstagramProfessionalAccountType.PERSONAL:
            return self._profile_read_error(
                connection=replace(connection, account_identifier=account_identifier),
                category=IntegrationErrorCategory.UNSUPPORTED_OPERATION,
                message="unsupported_account_type",
                safe_detail="personal_account",
            )
        existing_account = self.repository.get_account_by_instagram_user_id(connection.creator_id, account_identifier)
        if existing_account is not None:
            mapped_account = replace(
                mapped_account,
                id=existing_account.id,
                selected_for_sync=existing_account.selected_for_sync,
                last_synced_at=existing_account.last_synced_at,
                created_at=existing_account.created_at,
            )
        updated_account = self.repository.upsert_account(mapped_account)
        self._record_rate_limit(connection.id, "account_profile", response)
        verified_connection = self.repository.upsert_connection(
            self._connection_to_status(
                replace(connection, account_identifier=account_identifier),
                status=InstagramConnectionStatus.VERIFIED,
                verified=True,
            )
        )
        return InstagramProfileReadResult(
            connection=verified_connection,
            account=updated_account,
            health=self._profile_read_health(connection=verified_connection, success=True),
            success=True,
            error=None,
            provider_metadata={
                "provider_account_id": updated_account.instagram_user_id,
                "username": updated_account.username,
                "account_type": updated_account.account_type.value,
            },
            warnings=(),
        )

    def _read_account_profile_from_connection(self, connection: InstagramConnection) -> InstagramProfileReadResult:
        bundle = self._load_connection_bundle(connection)
        account_identifier = connection.account_identifier or bundle.instagram_user_id
        if not account_identifier:
            return self._profile_read_error(
                connection=connection,
                category=IntegrationErrorCategory.AUTHENTICATION_REQUIRED,
                message="No se pudo resolver el identificador de cuenta de Instagram.",
                safe_detail="account_identifier_missing",
            )
        try:
            response = self.api_client.fetch_account(token=bundle.access_token or "", instagram_user_id=account_identifier, fields=PROFILE_READ_FIELDS)
        except InstagramApiError as exc:
            return self._profile_read_error_from_api_error(connection, exc)
        payload = _dict_payload(response)
        return self._profile_read_success(connection=connection, account_payload=payload, bundle=bundle, response=response)

    def _connection_to_status(self, connection: InstagramConnection, *, status: InstagramConnectionStatus, verified: bool = False, disconnected: bool = False) -> InstagramConnection:
        now = _now()
        return replace(
            connection,
            status=status,
            last_verified_at=now if verified else connection.last_verified_at,
            disconnected_at=now if disconnected else connection.disconnected_at,
            updated_at=now,
        )

    def _build_connection(self, *, creator_id: str, provider: InstagramAuthProvider, granted_scopes: tuple[str, ...], credential_reference: str, api_version: str, access_level: InstagramAccessLevel | None, app_access_status: InstagramAppAccessStatus, account_identifier: str | None = None, professional_account_type: InstagramProfessionalAccountType | None = None, authorization_url: str | None = None) -> InstagramConnectionResult:
        connection = InstagramConnection(
            id=str(uuid4()),
            creator_id=creator_id,
            provider=provider.value,
            account_identifier=account_identifier,
            professional_account_type=professional_account_type,
            status=InstagramConnectionStatus.CONNECTED,
            granted_scopes_json=_json_dumps(list(granted_scopes)),
            credential_reference=credential_reference,
            api_version=api_version,
            access_level=access_level,
            app_access_status=app_access_status,
            connected_at=_now(),
            last_verified_at=None,
            disconnected_at=None,
            created_at=_now(),
            updated_at=_now(),
        )
        persisted = self.repository.upsert_connection(connection)
        return InstagramConnectionResult(connection=persisted, authorization_url=authorization_url, warnings=())

    def connect_account(
        self,
        *,
        creator_id: str,
        client_id: str,
        scopes: tuple[str, ...] = READ_ONLY_SCOPES,
        provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN,
        client_secret: str | None = None,
        authorization_code: str | None = None,
        redirect_uri: str | None = None,
        state: str | None = None,
        account_identifier: str | None = None,
        api_version: str | None = None,
    ) -> InstagramConnectionResult:
        if self.settings.environment == "production" and self.oauth_broker is None:
            raise InstagramAuthorizationError("El broker OAuth de Instagram es obligatorio en produccion.")
        self._ensure_read_only_scopes(scopes)
        auth_result = self.oauth_client.begin_authorization(client_id=client_id, scopes=scopes, redirect_uri=redirect_uri, state=state)
        if authorization_code is None:
            connection = self._build_connection(
                creator_id=creator_id,
                provider=provider,
                granted_scopes=scopes,
                credential_reference=uuid4().hex,
                api_version=api_version or DEFAULT_INSTAGRAM_API_VERSION.configured_version,
                access_level=InstagramAccessLevel.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAccessLevel.STANDARD_ACCESS,
                app_access_status=InstagramAppAccessStatus.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAppAccessStatus.STANDARD_ACCESS,
                account_identifier=account_identifier,
                authorization_url=auth_result.authorization_url,
            )
            return connection
        token_result = self.oauth_client.exchange_code(client_id=client_id, client_secret=client_secret, code=authorization_code, redirect_uri=auth_result.redirect_uri)
        missing = [scope for scope in scopes if scope not in token_result.granted_scopes]
        if missing:
            raise InstagramAuthorizationError(f"Faltan scopes aprobados: {missing}")
        if provider == InstagramAuthProvider.INSTAGRAM_LOGIN and not token_result.instagram_user_id:
            raise InstagramAuthorizationError("No se pudo verificar el identificador de usuario de Instagram.")
        resolved_account_identifier = account_identifier or token_result.instagram_user_id
        existing_connection = self._existing_connection_for_account(creator_id, resolved_account_identifier, provider=provider)
        credential_reference = existing_connection.credential_reference if existing_connection is not None else self._credential_reference_for(creator_id, resolved_account_identifier or uuid4().hex, provider=provider)
        self.credential_store.save(
            credential_reference,
            InstagramCredentialBundle(
                access_token=token_result.access_token,
                refresh_token=token_result.refresh_token,
                token_type=token_result.token_type,
                expires_at=token_result.expires_at,
                granted_scopes=token_result.granted_scopes,
                instagram_user_id=token_result.instagram_user_id,
                provider=provider.value,
            ),
        )
        connection = self._build_connection(
            creator_id=creator_id,
            provider=provider,
            granted_scopes=token_result.granted_scopes,
            credential_reference=credential_reference,
            api_version=api_version or DEFAULT_INSTAGRAM_API_VERSION.configured_version,
            access_level=InstagramAccessLevel.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAccessLevel.STANDARD_ACCESS,
            app_access_status=InstagramAppAccessStatus.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAppAccessStatus.STANDARD_ACCESS,
            account_identifier=resolved_account_identifier,
            authorization_url=auth_result.authorization_url,
        )
        verified = self.verify_connection(connection.connection.id)
        return replace(connection, connection=verified.connection, warnings=verified.warnings)

    def start_oauth_transaction(
        self,
        *,
        creator_id: str,
        client_id: str,
        scopes: tuple[str, ...] = READ_ONLY_SCOPES,
        provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN,
        transaction_proof: str | None = None,
    ) -> InstagramOAuthBrokerStartResult:
        if self.oauth_broker is None:
            raise InstagramAuthorizationError("No hay broker OAuth de Instagram configurado.")
        return self.oauth_broker.start_transaction(
            creator_id=creator_id,
            client_id=client_id,
            scopes=scopes,
            transaction_proof=transaction_proof,
            provider=provider,
        )

    def poll_oauth_transaction(self, *, transaction_id: str, transaction_proof: str) -> InstagramOAuthBrokerStatusResult:
        if self.oauth_broker is None:
            raise InstagramAuthorizationError("No hay broker OAuth de Instagram configurado.")
        return self.oauth_broker.poll_transaction(transaction_id=transaction_id, transaction_proof=transaction_proof)

    def complete_oauth_transaction(
        self,
        *,
        creator_id: str,
        transaction_id: str,
        transaction_proof: str,
        provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN,
        api_version: str | None = None,
        account_identifier: str | None = None,
    ) -> InstagramConnectionResult:
        if self.oauth_broker is None:
            raise InstagramAuthorizationError("No hay broker OAuth de Instagram configurado.")
        redeem_result = self.oauth_broker.redeem_transaction(transaction_id=transaction_id, transaction_proof=transaction_proof)
        if redeem_result.token_result is None:
            raise InstagramAuthorizationError("No hay token recuperable para la transaccion de Instagram.")
        token_result = redeem_result.token_result
        if provider == InstagramAuthProvider.INSTAGRAM_LOGIN and not token_result.instagram_user_id:
            raise InstagramAuthorizationError("No se pudo verificar el identificador de usuario de Instagram.")
        resolved_account_identifier = account_identifier or token_result.instagram_user_id
        if not resolved_account_identifier:
            raise InstagramAuthorizationError("No se pudo resolver el identificador de cuenta de Instagram.")
        existing_connection = self._existing_connection_for_account(creator_id, resolved_account_identifier, provider=provider)
        credential_reference = existing_connection.credential_reference if existing_connection is not None else self._credential_reference_for(creator_id, resolved_account_identifier, provider=provider)
        self.credential_store.save(
            credential_reference,
            InstagramCredentialBundle(
                access_token=token_result.access_token,
                refresh_token=token_result.refresh_token,
                token_type=token_result.token_type,
                expires_at=token_result.expires_at,
                granted_scopes=token_result.granted_scopes,
                instagram_user_id=token_result.instagram_user_id,
                provider=provider.value,
            ),
        )
        connection = self.repository.upsert_connection(
            InstagramConnection(
                id=existing_connection.id if existing_connection is not None else str(uuid4()),
                creator_id=creator_id,
                provider=provider.value,
                account_identifier=resolved_account_identifier,
                professional_account_type=None,
                status=InstagramConnectionStatus.PENDING,
                granted_scopes_json=_json_dumps(list(token_result.granted_scopes)),
                credential_reference=credential_reference,
                api_version=api_version or DEFAULT_INSTAGRAM_API_VERSION.configured_version,
                access_level=InstagramAccessLevel.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAccessLevel.STANDARD_ACCESS,
                app_access_status=InstagramAppAccessStatus.DEVELOPMENT_MODE if self.settings.environment != "production" else InstagramAppAccessStatus.STANDARD_ACCESS,
                connected_at=_now(),
                last_verified_at=None,
                disconnected_at=None,
                created_at=existing_connection.created_at if existing_connection is not None else _now(),
                updated_at=_now(),
            )
        )
        return InstagramConnectionResult(connection=connection, authorization_url=None, warnings=("authorized_pending_profile",))

    def verify_connection(self, connection_id: str) -> InstagramConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        bundle = self._load_connection_bundle(connection)
        token_verification = self.oauth_client.verify_token(bundle.access_token or "", tuple(json.loads(connection.granted_scopes_json)))
        missing = token_verification.get("missing_scopes") or ()
        if missing:
            raise InstagramAuthorizationError(f"Scopes faltantes: {missing}")
        if token_verification.get("instagram_user_id") and not connection.account_identifier:
            connection = replace(connection, account_identifier=str(token_verification.get("instagram_user_id")))
        profile_result = self._read_account_profile_from_connection(connection)
        if not profile_result.success or profile_result.account is None:
            if profile_result.error is not None and profile_result.error.category == IntegrationErrorCategory.UNSUPPORTED_OPERATION:
                raise InstagramAccountValidationError(profile_result.error.message)
            raise InstagramAuthorizationError(profile_result.error.message if profile_result.error is not None else "No se pudo verificar la conexion de Instagram.")
        return InstagramConnectionResult(connection=profile_result.connection, authorization_url=None, warnings=profile_result.warnings)

    def read_account_profile(self, connection_id: str) -> InstagramProfileReadResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        return self._read_account_profile_from_connection(connection)

    def disconnect_connection(self, connection_id: str) -> InstagramConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        updated = self.repository.upsert_connection(self._connection_to_status(connection, status=InstagramConnectionStatus.DISCONNECTED, disconnected=True))
        return InstagramConnectionResult(connection=updated, authorization_url=None, warnings=())

    def revoke_connection(self, connection_id: str) -> InstagramConnectionResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        bundle = self._credential_bundle(connection)
        if bundle and bundle.access_token:
            self.oauth_client.revoke(bundle.access_token)
        self.credential_store.delete(connection.credential_reference)
        updated = self.repository.upsert_connection(self._connection_to_status(connection, status=InstagramConnectionStatus.REVOKED, disconnected=True))
        return InstagramConnectionResult(connection=updated, authorization_url=None, warnings=())

    def list_connections(self, creator_id: str) -> list[InstagramConnection]:
        return self.repository.list_connections(creator_id)

    def show_connection(self, connection_id: str) -> InstagramConnection | None:
        return self.repository.get_connection(connection_id)

    def list_accounts(self, creator_id: str, *, connection_id: str | None = None) -> list[InstagramAccount]:
        return self.repository.list_accounts(creator_id, connection_id=connection_id)

    def select_account(self, account_id: str) -> InstagramAccount:
        account = self.repository.get_account(account_id)
        if account is None:
            raise InstagramConnectionError("La cuenta no existe.")
        updated = replace(account, selected_for_sync=True, updated_at=_now())
        return self.repository.upsert_account(updated)

    def show_account(self, account_id: str) -> InstagramAccount | None:
        return self.repository.get_account(account_id)

    def list_media(self, account_id: str) -> list[InstagramRemoteMedia]:
        account = self.repository.get_account(account_id)
        if account is None:
            raise InstagramConnectionError("La cuenta no existe.")
        return self.repository.list_remote_media(account.creator_id, account_id=account_id)

    def list_caption_versions(self, remote_media_id: str) -> list[InstagramCaptionVersion]:
        return self.repository.list_caption_versions(remote_media_id)

    def list_cover_versions(self, remote_media_id: str) -> list[InstagramCoverVersion]:
        return self.repository.list_cover_versions(remote_media_id)

    def show_media(self, remote_media_id: str) -> InstagramRemoteMedia | None:
        return self.repository.get_remote_media(remote_media_id)

    def list_sync_runs(self, creator_id: str) -> list[InstagramSyncRun]:
        return self.repository.list_sync_runs(creator_id)

    def show_sync_run(self, run_id: str) -> InstagramSyncRun | None:
        return self.repository.get_sync_run(run_id)

    def list_sync_items(self, run_id: str) -> list[InstagramSyncItem]:
        return self.repository.list_sync_items(run_id)

    def list_insight_imports(self, creator_id: str, *, account_id: str | None = None) -> list[InstagramInsightImport]:
        return self.repository.list_insight_imports(creator_id, account_id=account_id)

    def list_insight_values(self, insight_import_id: str) -> list[InstagramInsightValue]:
        return self.repository.list_insight_values(insight_import_id)

    def list_content_links(self, creator_id: str) -> list[InstagramContentLink]:
        return self.repository.list_content_links(creator_id)

    def list_rate_limit_usage(self, connection_id: str) -> list[InstagramRateLimitUsage]:
        return self.repository.list_rate_limit_usage(connection_id)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[InstagramSyncSchedule]:
        return self.repository.list_sync_schedules(creator_id, connection_id=connection_id)

    def _record_rate_limit(self, connection_id: str, operation_key: str, response: object | None = None, request_count: int = 1) -> InstagramRateLimitUsage:
        headers_snapshot = None
        if response is not None and hasattr(response, "headers"):
            headers_snapshot = _json_dumps({str(key).lower(): value for key, value in getattr(response, "headers").items()})
        usage = InstagramRateLimitUsage(
            id=str(uuid4()),
            connection_id=connection_id,
            operation_key=operation_key,
            estimated_usage=None,
            request_count=request_count,
            usage_date=_now().date().isoformat(),
            headers_snapshot_json=headers_snapshot,
            created_at=_now(),
        )
        return self.repository.upsert_rate_limit_usage(usage)

    def _resolve_media_cursor(self, *, account: InstagramAccount, connection: InstagramConnection, cursor: str | None) -> str | None:
        if cursor is not None:
            return cursor
        for run in self.repository.list_sync_runs(account.creator_id):
            if run.connection_id != connection.id or run.account_id != account.id or not run.cursor_json:
                continue
            payload = _json_loads(run.cursor_json, {})
            if isinstance(payload, dict):
                next_cursor = payload.get("cursor")
                if isinstance(next_cursor, str) and next_cursor:
                    return next_cursor
        return None

    def _failed_media_sync_result(
        self,
        *,
        connection: InstagramConnection,
        account: InstagramAccount,
        run: InstagramSyncRun,
        error_message: str,
        error_code: str | None = None,
        warnings: list[str] | None = None,
        sync_type: InstagramSyncType = InstagramSyncType.MEDIA_CATALOG,
    ) -> InstagramSyncResult:
        errors = [error_message]
        finalized = self._finalize_sync_run(
            run,
            discovered=0,
            imported=0,
            updated=0,
            unchanged=0,
            skipped=0,
            warnings=warnings or [],
            errors=errors,
            status=InstagramSyncStatus.FAILED,
        )
        report = InstagramSyncReport(
            connection_id=connection.id,
            account_id=account.id,
            provider=connection.provider,
            professional_account_type=account.account_type.value,
            api_version=connection.api_version,
            granted_scopes=tuple(json.loads(connection.granted_scopes_json)),
            access_level=None if connection.access_level is None else connection.access_level.value,
            sync_type=sync_type.value,
            period=None,
            discovered_count=0,
            imported_count=0,
            updated_count=0,
            unchanged_count=0,
            skipped_count=0,
            linked_count=0,
            unlinked_count=0,
            insights_imported_count=0,
            unavailable_metrics=tuple(),
            partial_periods=tuple(),
            warnings=tuple(sorted(set(warnings or []))),
            errors=tuple(errors),
            estimated_usage=None,
            duration_seconds=None,
            next_recommended_action="review",
        )
        return InstagramSyncResult(
            run=replace(finalized, error_code=error_code or error_message, error_message=error_message),
            report=report,
            accounts=(account,),
            media=tuple(),
            captions=tuple(),
            covers=tuple(),
            children=tuple(),
            insight_imports=tuple(),
            insight_values=tuple(),
            links=tuple(),
            sync_items=tuple(),
            warnings=tuple(sorted(set(warnings or []))),
        )

    def _create_publication_if_needed(self, *, creator_id: str, account_id: str, media: InstagramRemoteMedia) -> AnalyticsPublication | None:
        if self.analytics_repository is None:
            return None
        publication = AnalyticsPublication(
            id=f"instagram:{creator_id}:{media.instagram_media_id}",
            creator_id=creator_id,
            channel_id=account_id,
            video_asset_id=media.video_asset_id,
            external_publication_id=media.instagram_media_id,
            platform=_analytics_platform_for_content_type(media.content_type),
            content_type=_map_content_type_to_analytics(media.content_type),
            title=media.caption or media.shortcode or media.instagram_media_id,
            description=media.caption,
            published_at=media.timestamp,
            duration_seconds=None,
            url=media.permalink,
            thumbnail_path=media.thumbnail_url,
            status="observed",
            source_type=AnalyticsSourceType.MANUAL,
            source_fingerprint=media.remote_fingerprint,
            dedupe_key=build_publication_dedupe_key(
                platform=_analytics_platform_for_content_type(media.content_type),
                external_publication_id=media.instagram_media_id,
                url=media.permalink or "",
                title=media.caption or media.shortcode or media.instagram_media_id,
                published_at=media.timestamp,
                channel_id=account_id,
            ),
            created_at=media.created_at,
            updated_at=media.updated_at,
        )
        return self.analytics_repository.upsert_publication(publication)

    def _ensure_analytics_import(self, *, creator_id: str, channel_id: str, platform: str, source_filename: str, sync_run: InstagramSyncRun) -> AnalyticsImport | None:
        if self.analytics_repository is None:
            return None
        now = _now()
        import_record = AnalyticsImport(
            id=sync_run.id,
            creator_id=creator_id,
            channel_id=channel_id,
            platform=platform,
            source_filename=source_filename,
            source_path=None,
            source_fingerprint=build_instagram_fingerprint({"creator_id": creator_id, "channel_id": channel_id, "platform": platform, "source_filename": source_filename, "sync_run_id": sync_run.id}),
            source_type=AnalyticsSourceType.MANUAL,
            schema_version=self.api_client.api_version.configured_version,
            status=AnalyticsImportStatus.COMPLETED,
            total_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            warning_rows=0,
            duplicate_rows=0,
            source_sheet_name=None,
            timezone_name=None,
            delimiter=None,
            mapping_json="{}",
            report_path=None,
            started_at=sync_run.started_at,
            completed_at=now,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        return self.analytics_repository.upsert_import(import_record)

    def _upsert_metric_snapshot(self, *, publication_id: str, metric_key: str, raw_metric_name: str, numeric_value: float | None, unit: str | None, source_import_id: str, captured_at: datetime, quality_status: AnalyticsQualityStatus = AnalyticsQualityStatus.ACCEPTED, warning_codes_json: str = "[]") -> AnalyticsMetricSnapshot:
        if self.analytics_repository is None:
            raise InstagramIntegrationError("El repositorio de analytics no esta disponible.")
        snapshot = AnalyticsMetricSnapshot(
            id=str(uuid4()),
            publication_id=publication_id,
            snapshot_date=captured_at.date().isoformat(),
            captured_at=captured_at,
            metric_key=metric_key,
            numeric_value=numeric_value,
            text_value=None,
            unit=unit or "",
            source_import_id=source_import_id,
            source_row_number=None,
            is_derived=False,
            quality_status=quality_status,
            warning_codes_json=warning_codes_json,
            created_at=captured_at,
            row_fingerprint=build_instagram_fingerprint({"publication_id": publication_id, "metric_key": metric_key, "numeric_value": numeric_value, "raw_metric_name": raw_metric_name, "captured_at": captured_at.isoformat()}),
            dedupe_key=build_metric_snapshot_dedupe_key(
                {
                    "publication_id": publication_id,
                    "metric_key": metric_key,
                    "snapshot_date": captured_at.date().isoformat(),
                    "source_import_id": source_import_id,
                    "source_row_number": None,
                    "row_fingerprint": build_instagram_fingerprint({"publication_id": publication_id, "metric_key": metric_key, "numeric_value": numeric_value, "raw_metric_name": raw_metric_name, "captured_at": captured_at.isoformat()}),
                }
            ),
        )
        return self.analytics_repository.upsert_metric_snapshot(snapshot)

    def _ensure_packaging_asset(self, *, creator_id: str, media: InstagramRemoteMedia) -> PackagingAsset | None:
        if self.creative_packaging_repository is None:
            return None
        asset = PackagingAsset(
            id=media.packaging_asset_id or media.instagram_media_id,
            creator_id=creator_id,
            publication_id=media.publication_id,
            video_asset_id=media.video_asset_id,
            asset_type=PackagingAssetType.THUMBNAIL,
            platform=_analytics_platform_for_content_type(media.content_type),
            content_type=_map_content_type_to_analytics(media.content_type).value,
            topic=None,
            status=PackagingAssetStatus.ACTIVE,
            created_at=media.created_at,
            updated_at=media.updated_at,
        )
        return self.creative_packaging_repository.upsert_asset(asset)

    def _ensure_thumbnail_version(self, *, creator_id: str, media: InstagramRemoteMedia, packaging_asset_id: str | None) -> ThumbnailVersion | None:
        if self.creative_packaging_repository is None:
            return None
        asset_id = packaging_asset_id or media.packaging_asset_id or media.instagram_media_id
        existing = self.creative_packaging_repository.list_thumbnail_versions(asset_id)
        version = ThumbnailVersion(
            id=str(uuid4()),
            packaging_asset_id=asset_id,
            version_number=(max((item.version_number for item in existing), default=0) + 1),
            image_path=None,
            source_type="instagram_cover",
            width=None,
            height=None,
            file_fingerprint=media.remote_fingerprint,
            concept_id=None,
            is_published=False,
            is_selected=False,
            creator_approval_status="pending",
            creator_feedback=None,
            created_at=media.created_at,
            updated_at=media.updated_at,
        )
        return self.creative_packaging_repository.upsert_thumbnail_version(version)

    def _sync_account_payload(self, *, creator_id: str, connection: InstagramConnection, account_payload: dict[str, object], sync_run: InstagramSyncRun) -> InstagramAccount:
        account = map_account_payload(account_payload, creator_id=creator_id, connection_id=connection.id, instagram_user_id=_safe_str(account_payload.get("id")), api_version=self.api_client.api_version)
        return self.repository.upsert_account(account)

    def _sync_media_items(self, *, creator_id: str, connection: InstagramConnection, account: InstagramAccount, media_items: tuple[dict[str, object], ...], sync_run: InstagramSyncRun, include_children: bool = True, capture_analytics: bool = False, credential_bundle: InstagramCredentialBundle | None = None) -> tuple[list[InstagramRemoteMedia], list[InstagramCaptionVersion], list[InstagramCoverVersion], list[InstagramCarouselChild], list[InstagramSyncItem], list[str], list[str]]:
        remote_media: list[InstagramRemoteMedia] = []
        captions: list[InstagramCaptionVersion] = []
        covers: list[InstagramCoverVersion] = []
        children: list[InstagramCarouselChild] = []
        items: list[InstagramSyncItem] = []
        warnings: list[str] = []
        errors: list[str] = []
        analytics_import = None
        if capture_analytics and self.analytics_repository is not None:
            analytics_import = self._ensure_analytics_import(
                creator_id=creator_id,
                channel_id=account.id,
                platform="instagram",
                source_filename=f"instagram:{sync_run.id}",
                sync_run=sync_run,
            )
        for payload in media_items:
            discovered_media = map_remote_media_payload(payload, creator_id=creator_id, account_id=account.id)
            existing = self.repository.get_remote_media_by_instagram_id(creator_id, discovered_media.instagram_media_id)
            remote_media.append(self.repository.upsert_remote_media(discovered_media))
            items.append(self.repository.upsert_sync_item(InstagramSyncItem(id=str(uuid4()), sync_run_id=sync_run.id, remote_type="media", remote_id=discovered_media.instagram_media_id, local_type="instagram_remote_media", local_id=discovered_media.id, action="upsert", status="completed", warnings_json="[]", error_code=None, error_message=None, created_at=_now())))
            caption_versions = self.repository.list_caption_versions(remote_media[-1].id)
            if existing is None or existing.caption != remote_media[-1].caption:
                captions.append(self.repository.upsert_caption_version(InstagramCaptionVersion(id=str(uuid4()), remote_media_id=remote_media[-1].id, version_number=(max((item.version_number for item in caption_versions), default=0) + 1), caption_text=remote_media[-1].caption, source_fingerprint=build_instagram_fingerprint({"caption": remote_media[-1].caption, "media_id": remote_media[-1].instagram_media_id}), is_current=True, observed_at=_now(), created_at=_now())))
            cover_versions = self.repository.list_cover_versions(remote_media[-1].id)
            if existing is None or existing.cover_url != remote_media[-1].cover_url or existing.thumbnail_url != remote_media[-1].thumbnail_url:
                covers.append(self.repository.upsert_cover_version(map_cover_version(remote_media_id=remote_media[-1].id, cover_url=remote_media[-1].cover_url, thumbnail_url=remote_media[-1].thumbnail_url, packaging_asset_id=remote_media[-1].packaging_asset_id, version_number=(max((item.version_number for item in cover_versions), default=0) + 1))))
            if include_children and remote_media[-1].content_type == InstagramContentType.INSTAGRAM_CAROUSEL:
                child_items = payload.get("children")
                if isinstance(child_items, dict) and isinstance(child_items.get("data"), list):
                    iterable = tuple(item for item in child_items["data"] if isinstance(item, dict))
                elif isinstance(child_items, list):
                    iterable = tuple(item for item in child_items if isinstance(item, dict))
                else:
                    iterable = tuple()
                if not iterable and payload.get("id") and credential_bundle is not None:
                    try:
                        child_response = self.api_client.fetch_children(
                            token=credential_bundle.access_token or "",
                            media_id=discovered_media.instagram_media_id,
                            fields=("id", "media_type", "media_url", "thumbnail_url", "timestamp"),
                        )
                        child_page = _page_items(child_response)
                        if child_page:
                            iterable = child_page
                    except InstagramApiError as exc:
                        errors.append(exc.details.message)
                for idx, child_payload in enumerate(iterable, start=1):
                    child = map_carousel_child_payload(child_payload, remote_media_id=remote_media[-1].id, child_order=idx)
                    children.append(self.repository.upsert_carousel_child(child))
                    items.append(self.repository.upsert_sync_item(InstagramSyncItem(id=str(uuid4()), sync_run_id=sync_run.id, remote_type="carousel_child", remote_id=child.instagram_child_id, local_type="instagram_carousel_child", local_id=child.id, action="upsert", status="completed", warnings_json="[]", error_code=None, error_message=None, created_at=_now())))
            if capture_analytics and self.analytics_repository is not None:
                publication = self._create_publication_if_needed(creator_id=creator_id, account_id=account.id, media=remote_media[-1])
                if publication is not None:
                    metrics = {
                        "views": _safe_float(payload.get("views")),
                        "reach": _safe_float(payload.get("reach")),
                        "shares": _safe_float(payload.get("shares")),
                        "saves": _safe_float(payload.get("saves")),
                        "likes": _safe_float(payload.get("likes")),
                        "comments": _safe_float(payload.get("comments")),
                        "profile_visits": _safe_float(payload.get("profile_visits")),
                        "follows": _safe_float(payload.get("follows")),
                        "completion_rate": _safe_float(payload.get("completion_rate")),
                    }
                    for key, value in metrics.items():
                        if value is not None:
                            self._upsert_metric_snapshot(publication_id=publication.id, metric_key=key, raw_metric_name=key, numeric_value=value, unit="count" if key not in {"completion_rate"} else "ratio", source_import_id=(analytics_import.id if analytics_import is not None else sync_run.id), captured_at=remote_media[-1].timestamp, quality_status=AnalyticsQualityStatus.ACCEPTED)
            if self.creative_packaging_repository is not None:
                asset = self._ensure_packaging_asset(creator_id=creator_id, media=remote_media[-1])
                if asset is not None:
                    self._ensure_thumbnail_version(creator_id=creator_id, media=remote_media[-1], packaging_asset_id=asset.id)
        return remote_media, captions, covers, children, items, warnings, errors

    def _prepare_sync_run(self, *, creator_id: str, connection: InstagramConnection, account_id: str | None, sync_type: InstagramSyncType, configuration: dict[str, object], cursor: str | None = None) -> InstagramSyncRun:
        return self.repository.upsert_sync_run(
            InstagramSyncRun(
                id=str(uuid4()),
                creator_id=creator_id,
                connection_id=connection.id,
                account_id=account_id,
                sync_type=sync_type,
                status=InstagramSyncStatus.AUTHENTICATING,
                configuration_json=_json_dumps(configuration),
                cursor_json=_json_dumps({"cursor": cursor}) if cursor else None,
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

    def _finalize_sync_run(self, run: InstagramSyncRun, *, discovered: int, imported: int, updated: int, unchanged: int, skipped: int, warnings: list[str], errors: list[str], cursor: str | None = None, status: InstagramSyncStatus | None = None, estimated_usage: str | None = None) -> InstagramSyncRun:
        return self.repository.upsert_sync_run(
            replace(
                run,
                status=status or (InstagramSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else InstagramSyncStatus.COMPLETED),
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
                cursor_json=_json_dumps({"cursor": cursor}) if cursor is not None else None,
            )
        )

    def sync_account(self, *, account_id: str, cursor: str | None = None, full_resync: bool = False, limit: int = DEFAULT_MEDIA_PAGE_LIMIT) -> InstagramSyncResult:
        account = self.repository.get_account(account_id)
        if account is None:
            raise InstagramConnectionError("La cuenta no existe.")
        connection = self.repository.get_connection(account.connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, account.creator_id)
        if connection.status in {InstagramConnectionStatus.DISCONNECTED, InstagramConnectionStatus.REVOKED}:
            raise InstagramAuthorizationError("La conexion no esta activa.")
        bundle = self._load_connection_bundle(connection)
        bounded_limit = _bounded_media_limit(limit)
        resolved_cursor = self._resolve_media_cursor(account=account, connection=connection, cursor=cursor)
        run = self._prepare_sync_run(creator_id=account.creator_id, connection=connection, account_id=account.id, sync_type=InstagramSyncType.ACCOUNT_METADATA, configuration={"full_resync": full_resync, "limit": bounded_limit, "cursor": resolved_cursor}, cursor=resolved_cursor)
        warnings: list[str] = []
        errors: list[str] = []
        account_response = self.api_client.fetch_account(token=bundle.access_token or "", instagram_user_id=account.instagram_user_id, fields=("id", "username", "name", "biography", "website", "profile_picture_url", "followers_count", "follows_count", "media_count", "account_type"))
        account_payload = _dict_payload(account_response)
        mapped_account = map_account_payload(
            account_payload,
            creator_id=account.creator_id,
            connection_id=connection.id,
            instagram_user_id=account.instagram_user_id,
            api_version=self.api_client.api_version,
        )
        if mapped_account.account_type == InstagramProfessionalAccountType.PERSONAL:
            raise InstagramAccountValidationError("professional_account_required")
        updated_account = self.repository.upsert_account(mapped_account)
        self._record_rate_limit(connection.id, "account_metadata", account_response)
        media_response = self.api_client.fetch_media(token=bundle.access_token or "", instagram_user_id=account.instagram_user_id, fields=MEDIA_READ_FIELDS, after=resolved_cursor, limit=bounded_limit)
        media_items = _page_items(media_response)
        cursor_value = _page_cursor(media_response)
        remote_media, captions, covers, children, sync_items, media_warnings, media_errors = self._sync_media_items(creator_id=account.creator_id, connection=connection, account=updated_account, media_items=media_items, sync_run=run, include_children=True, credential_bundle=bundle)
        warnings.extend(media_warnings)
        errors.extend(media_errors)
        self._record_rate_limit(connection.id, "media_catalog", media_response)
        run = self._finalize_sync_run(run, discovered=len(media_items), imported=len(remote_media), updated=max(0, len(remote_media) - (0 if full_resync else 0)), unchanged=0, skipped=0, warnings=warnings, errors=errors, cursor=cursor_value, status=InstagramSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else InstagramSyncStatus.COMPLETED)
        report = InstagramSyncReport(connection_id=connection.id, account_id=updated_account.id, provider=connection.provider, professional_account_type=None if updated_account.account_type is None else updated_account.account_type.value, api_version=connection.api_version, granted_scopes=tuple(json.loads(connection.granted_scopes_json)), access_level=None if connection.access_level is None else connection.access_level.value, sync_type=run.sync_type.value, period=None, discovered_count=len(media_items), imported_count=len(remote_media), updated_count=0, unchanged_count=0, skipped_count=0, linked_count=0, unlinked_count=0, insights_imported_count=0, unavailable_metrics=tuple(), partial_periods=tuple(), warnings=tuple(sorted(set(warnings))), errors=tuple(sorted(set(errors))), estimated_usage=None, duration_seconds=None, next_recommended_action="review" if warnings or errors else "incremental_sync")
        return InstagramSyncResult(run=run, report=report, accounts=(updated_account,), media=tuple(remote_media), captions=tuple(captions), covers=tuple(covers), children=tuple(children), insight_imports=tuple(), insight_values=tuple(), links=tuple(), sync_items=tuple(sync_items), warnings=tuple(sorted(set(warnings))))

    def sync_media(self, *, account_id: str, cursor: str | None = None, limit: int = DEFAULT_MEDIA_PAGE_LIMIT) -> InstagramSyncResult:
        account = self.repository.get_account(account_id)
        if account is None:
            raise InstagramConnectionError("La cuenta no existe.")
        connection = self.repository.get_connection(account.connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, account.creator_id)
        if connection.status in {InstagramConnectionStatus.DISCONNECTED, InstagramConnectionStatus.REVOKED}:
            raise InstagramAuthorizationError("La conexion no esta activa.")
        bundle = self._load_connection_bundle(connection)
        bounded_limit = _bounded_media_limit(limit)
        resolved_cursor = self._resolve_media_cursor(account=account, connection=connection, cursor=cursor)
        run = self._prepare_sync_run(
            creator_id=account.creator_id,
            connection=connection,
            account_id=account.id,
            sync_type=InstagramSyncType.MEDIA_CATALOG,
            configuration={"limit": bounded_limit, "cursor": resolved_cursor},
            cursor=resolved_cursor,
        )
        try:
            media_response = self.api_client.fetch_media(
                token=bundle.access_token or "",
                instagram_user_id=account.instagram_user_id,
                fields=MEDIA_READ_FIELDS,
                after=resolved_cursor,
                limit=bounded_limit,
            )
        except InstagramApiError as exc:
            self._record_rate_limit(connection.id, "media_catalog", exc)
            return self._failed_media_sync_result(
                connection=connection,
                account=account,
                run=run,
                error_message=exc.details.message,
                error_code=exc.details.code or exc.details.reason,
                sync_type=InstagramSyncType.MEDIA_CATALOG,
            )
        media_items = _page_items(media_response)
        next_cursor = _page_cursor(media_response)
        remote_media, captions, covers, children, sync_items, media_warnings, media_errors = self._sync_media_items(
            creator_id=account.creator_id,
            connection=connection,
            account=account,
            media_items=media_items,
            sync_run=run,
            include_children=True,
            capture_analytics=False,
            credential_bundle=bundle,
        )
        self._record_rate_limit(connection.id, "media_catalog", media_response)
        run = self._finalize_sync_run(
            run,
            discovered=len(media_items),
            imported=len(remote_media),
            updated=0,
            unchanged=0,
            skipped=0,
            warnings=media_warnings,
            errors=media_errors,
            cursor=next_cursor,
            status=InstagramSyncStatus.COMPLETED_WITH_WARNINGS if media_warnings or media_errors else InstagramSyncStatus.COMPLETED,
        )
        report = InstagramSyncReport(
            connection_id=connection.id,
            account_id=account.id,
            provider=connection.provider,
            professional_account_type=account.account_type.value,
            api_version=connection.api_version,
            granted_scopes=tuple(json.loads(connection.granted_scopes_json)),
            access_level=None if connection.access_level is None else connection.access_level.value,
            sync_type=InstagramSyncType.MEDIA_CATALOG.value,
            period=None,
            discovered_count=len(media_items),
            imported_count=len(remote_media),
            updated_count=0,
            unchanged_count=0,
            skipped_count=0,
            linked_count=0,
            unlinked_count=0,
            insights_imported_count=0,
            unavailable_metrics=tuple(),
            partial_periods=tuple(),
            warnings=tuple(sorted(set(media_warnings))),
            errors=tuple(sorted(set(media_errors))),
            estimated_usage=None,
            duration_seconds=None,
            next_recommended_action="review" if media_warnings or media_errors else "incremental_sync",
        )
        return InstagramSyncResult(
            run=run,
            report=report,
            accounts=(account,),
            media=tuple(remote_media),
            captions=tuple(captions),
            covers=tuple(covers),
            children=tuple(children),
            insight_imports=tuple(),
            insight_values=tuple(),
            links=tuple(),
            sync_items=tuple(sync_items),
            warnings=tuple(sorted(set(media_warnings))),
        )

    def sync_incremental(self, *, account_id: str, cursor: str | None = None) -> InstagramSyncResult:
        return self.sync_account(account_id=account_id, cursor=cursor, full_resync=False)

    def sync_repair(self, *, account_id: str) -> InstagramSyncResult:
        return self.sync_account(account_id=account_id, full_resync=True)

    def sync_insights(self, *, account_id: str, remote_media_id: str | None = None, period: InstagramInsightPeriod = InstagramInsightPeriod.DAYS_28) -> InstagramSyncResult:
        account = self.repository.get_account(account_id)
        if account is None:
            raise InstagramConnectionError("La cuenta no existe.")
        connection = self.repository.get_connection(account.connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        self._assert_creator_isolation(connection, account.creator_id)
        bundle = self._load_connection_bundle(connection)
        sync_type = InstagramSyncType.MEDIA_INSIGHTS if remote_media_id else InstagramSyncType.ACCOUNT_INSIGHTS
        run = self._prepare_sync_run(creator_id=account.creator_id, connection=connection, account_id=account.id, sync_type=sync_type, configuration={"period": period.value, "remote_media_id": remote_media_id})
        warnings: list[str] = []
        errors: list[str] = []
        insight_imports: list[InstagramInsightImport] = []
        insight_values: list[InstagramInsightValue] = []
        if account.account_type == InstagramProfessionalAccountType.PERSONAL:
            raise InstagramAccountValidationError("professional_account_required")
        if remote_media_id:
            response = self.api_client.fetch_media_insights(token=bundle.access_token or "", media_id=remote_media_id, metrics=("reach", "likes", "comments", "shares", "saves", "plays", "watch_time"), period=period)
            self._record_rate_limit(connection.id, "media_insights", response)
            payload = _dict_payload(response)
            remote_media = self.repository.get_remote_media_by_instagram_id(account.creator_id, remote_media_id)
            import_record = self.repository.upsert_insight_import(map_insight_import(creator_id=account.creator_id, account_id=account.id, sync_run_id=run.id, source_payload=payload, insight_scope=InstagramInsightScope.MEDIA, metric_period=period, remote_media_id=remote_media.id if remote_media else None))
            insight_imports.append(import_record)
            raw_items = payload.get("data")
            page_items = tuple(item for item in raw_items if isinstance(item, dict)) if isinstance(raw_items, list) else tuple()
            for item in page_items:
                if not isinstance(item, dict):
                    continue
                metric_name = _safe_str(item.get("name")) or "unknown"
                values = item.get("values")
                if isinstance(values, list) and values:
                    first = values[0] if isinstance(values[0], dict) else {}
                else:
                    first = item
                insight_values.append(self.repository.upsert_insight_value(map_insight_value(insight_import_id=import_record.id, metric_key=metric_name, raw_metric_name=metric_name, raw_value=first if isinstance(first, dict) else {})))
        else:
            response = self.api_client.fetch_account_insights(token=bundle.access_token or "", instagram_user_id=account.instagram_user_id, metrics=("reach", "accounts_engaged", "profile_visits", "follows"), period=period)
            self._record_rate_limit(connection.id, "account_insights", response)
            payload = _dict_payload(response)
            import_record = self.repository.upsert_insight_import(map_insight_import(creator_id=account.creator_id, account_id=account.id, sync_run_id=run.id, source_payload=payload, insight_scope=InstagramInsightScope.ACCOUNT, metric_period=period, remote_media_id=None))
            insight_imports.append(import_record)
            for item in payload.get("data", []) if isinstance(payload.get("data"), list) else []:
                if not isinstance(item, dict):
                    continue
                metric_name = _safe_str(item.get("name")) or "unknown"
                values = item.get("values")
                raw = values[0] if isinstance(values, list) and values and isinstance(values[0], dict) else item
                insight_values.append(self.repository.upsert_insight_value(map_insight_value(insight_import_id=import_record.id, metric_key=metric_name, raw_metric_name=metric_name, raw_value=raw if isinstance(raw, dict) else {})))
        run = self._finalize_sync_run(run, discovered=0, imported=0, updated=0, unchanged=0, skipped=0, warnings=warnings, errors=errors, status=InstagramSyncStatus.COMPLETED_WITH_WARNINGS if warnings or errors else InstagramSyncStatus.COMPLETED)
        report = InstagramSyncReport(connection_id=connection.id, account_id=account.id, provider=connection.provider, professional_account_type=account.account_type.value, api_version=connection.api_version, granted_scopes=tuple(json.loads(connection.granted_scopes_json)), access_level=None if connection.access_level is None else connection.access_level.value, sync_type=sync_type.value, period=period.value, discovered_count=0, imported_count=0, updated_count=0, unchanged_count=0, skipped_count=0, linked_count=0, unlinked_count=0, insights_imported_count=len(insight_imports), unavailable_metrics=tuple(), partial_periods=tuple(), warnings=tuple(sorted(set(warnings))), errors=tuple(sorted(set(errors))), estimated_usage=None, duration_seconds=None, next_recommended_action="review" if warnings or errors else "incremental_sync")
        return InstagramSyncResult(run=run, report=report, accounts=(account,), media=tuple(), captions=tuple(), covers=tuple(), children=tuple(), insight_imports=tuple(insight_imports), insight_values=tuple(insight_values), links=tuple(), sync_items=tuple(self.repository.list_sync_items(run.id)), warnings=tuple(sorted(set(warnings))))

    def sync_incremental_by_connection(self, *, connection_id: str) -> InstagramSyncResult:
        connection = self.repository.get_connection(connection_id)
        if connection is None:
            raise InstagramConnectionError("La conexion no existe.")
        account = next((item for item in self.repository.list_accounts(connection.creator_id, connection_id=connection.id) if item.selected_for_sync), None)
        if account is None:
            raise InstagramConnectionError("No hay cuenta seleccionada para la sincronizacion.")
        latest = self.repository.get_latest_sync_run(connection.creator_id, connection_id=connection.id)
        cursor = _json_loads(latest.cursor_json, {}).get("cursor") if latest and latest.cursor_json else None
        return self.sync_incremental(account_id=account.id, cursor=cursor)

    def resume_sync(self, run_id: str) -> InstagramSyncResult:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise InstagramSyncError("La corrida no existe.")
        if run.account_id is None:
            raise InstagramSyncError("No hay cuenta para reanudar.")
        cursor = _json_loads(run.cursor_json, {}).get("cursor") if run.cursor_json else None
        return self.sync_incremental(account_id=run.account_id, cursor=cursor)

    def link_content(self, *, remote_media_id: str, publication_id: str | None = None, video_asset_id: str | None = None, packaging_asset_id: str | None = None, link_method: InstagramLinkMethod = InstagramLinkMethod.MANUAL, confidence_level: str = "low", status: str = "pending", creator_id: str | None = None) -> InstagramContentLink:
        media = self.repository.get_remote_media(remote_media_id)
        if media is None:
            raise InstagramConnectionError("El medio remoto no existe.")
        if creator_id is None:
            creator_id = media.creator_id
        link = InstagramContentLink(id=str(uuid4()), creator_id=creator_id, remote_media_id=remote_media_id, publication_id=publication_id, video_asset_id=video_asset_id, packaging_asset_id=packaging_asset_id, link_method=link_method, confidence_level=confidence_level, status=status, reviewed_at=_now(), created_at=_now(), updated_at=_now())
        return self.repository.upsert_content_link(link)

    def unlink_content(self, *, remote_media_id: str, creator_id: str | None = None) -> InstagramContentLink:
        media = self.repository.get_remote_media(remote_media_id)
        if media is None:
            raise InstagramConnectionError("El medio remoto no existe.")
        if creator_id is None:
            creator_id = media.creator_id
        existing = next((item for item in self.repository.list_content_links(creator_id) if item.remote_media_id == remote_media_id), None)
        if existing is None:
            raise InstagramConnectionError("No hay vinculo para desvincular.")
        updated = replace(existing, status="unlinked", updated_at=_now())
        return self.repository.upsert_content_link(updated)

    def export_report(self, run_id: str, format_name: str, *, destination: Path | None = None) -> Path:
        run = self.repository.get_sync_run(run_id)
        if run is None:
            raise InstagramSyncError("La corrida no existe.")
        report = InstagramSyncReport(
            connection_id=run.connection_id,
            account_id=run.account_id,
            provider=self.repository.get_connection(run.connection_id).provider if self.repository.get_connection(run.connection_id) else "instagram",
            professional_account_type=self.repository.get_account(run.account_id).account_type.value if run.account_id and self.repository.get_account(run.account_id) else None,
            api_version=self.repository.get_connection(run.connection_id).api_version if self.repository.get_connection(run.connection_id) else DEFAULT_INSTAGRAM_API_VERSION.configured_version,
            granted_scopes=tuple(json.loads(self.repository.get_connection(run.connection_id).granted_scopes_json)) if self.repository.get_connection(run.connection_id) else READ_ONLY_SCOPES,
            access_level=self.repository.get_connection(run.connection_id).access_level.value if self.repository.get_connection(run.connection_id) and self.repository.get_connection(run.connection_id).access_level else None,
            sync_type=run.sync_type.value,
            period=None,
            discovered_count=run.discovered_count,
            imported_count=run.imported_count,
            updated_count=run.updated_count,
            unchanged_count=run.unchanged_count,
            skipped_count=run.skipped_count,
            linked_count=len([item for item in self.repository.list_content_links(self.repository.get_connection(run.connection_id).creator_id if self.repository.get_connection(run.connection_id) else run.creator_id)]),
            unlinked_count=0,
            insights_imported_count=len(self.repository.list_insight_imports(run.creator_id, account_id=run.account_id)) if run.account_id else len(self.repository.list_insight_imports(run.creator_id)),
            unavailable_metrics=tuple(),
            partial_periods=tuple(),
            warnings=tuple(),
            errors=tuple(),
            estimated_usage=run.estimated_usage,
            duration_seconds=None,
            next_recommended_action=None,
        )
        export_root = destination or self._exports_root
        export_root.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path = export_root / f"{run_id}_instagram_sync.json"
            path.write_text(_json_dumps(report.to_dict()), encoding="utf-8")
            return path
        if format_name == "txt":
            path = export_root / f"{run_id}_instagram_sync.txt"
            path.write_text("\n".join(f"{key}: {value}" for key, value in report.to_dict().items()), encoding="utf-8")
            return path
        if format_name == "csv":
            path = export_root / f"{run_id}_instagram_sync.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["field", "value"])
                for key, value in report.to_dict().items():
                    writer.writerow([key, _csv_safe_value(value)])
            return path
        raise InstagramSyncError("Formato de exportacion no soportado.")


def build_instagram_integration_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: InstagramIntegrationRepository,
    database: SQLiteDatabase,
    analytics_repository: SQLiteAnalyticsRepository | None = None,
    creative_packaging_repository: SQLiteCreativePackagingRepository | None = None,
    oauth_client: InstagramAuthProviderClient | None = None,
    oauth_broker: InstagramOAuthBrokerClient | None = None,
    credential_store: InstagramCredentialStore | None = None,
    api_client: InstagramApiClient | None = None,
    rate_limit_tracker: InstagramRateLimitTracker | None = None,
    logger: logging.Logger | None = None,
) -> InstagramIntegrationService:
    return InstagramIntegrationService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=oauth_client,
        oauth_broker=oauth_broker,
        credential_store=credential_store,
        api_client=api_client,
        rate_limit_tracker=rate_limit_tracker,
        logger=logger,
    )
