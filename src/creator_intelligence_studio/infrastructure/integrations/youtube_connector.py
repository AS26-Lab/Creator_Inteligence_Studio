"""Read-first YouTube provider adapter behind the integration foundation."""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from uuid import uuid4
from hashlib import sha256

from creator_intelligence_studio.domain.integrations import (
    ExternalContentResource,
    INTEGRATION_CONTRACT_VERSION,
    IntegrationAccount,
    IntegrationAccountStatus,
    IntegrationAnalyticsMetric,
    IntegrationAuthType,
    IntegrationCapability,
    IntegrationConnectorDefinition,
    IntegrationErrorCategory,
    IntegrationErrorDetails,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationRateLimitState,
    IntegrationReadRequest,
    IntegrationReadResult,
    IntegrationWriteRequest,
    IntegrationWriteResult,
)
from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES
from creator_intelligence_studio.infrastructure.youtube.analytics_api_client import YouTubeAnalyticsApiClient
from creator_intelligence_studio.infrastructure.youtube.credential_store import (
    CredentialBundle,
    CredentialStore,
    DevelopmentCredentialStore,
    EncryptedLocalCredentialStore,
)
from creator_intelligence_studio.infrastructure.youtube.data_api_client import YouTubeApiPage, YouTubeDataApiClient
from creator_intelligence_studio.infrastructure.youtube.oauth_config import resolve_youtube_oauth_client_id
from creator_intelligence_studio.infrastructure.youtube.oauth_client import (
    DesktopYouTubeOAuthClient,
    OAuthAuthorizationResult,
    OAuthTokenResult,
    YouTubeOAuthClient,
)
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _stable_id(*parts: object) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return sha256(payload.encode("utf-8")).hexdigest()


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback: Any) -> Any:
    if not payload:
        return fallback
    try:
        parsed = json.loads(payload)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _safe_dt(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return from_iso_z(str(value))


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


class _DisabledCredentialStore:
    def save(self, reference: str, bundle: CredentialBundle) -> None:  # noqa: ARG002
        return

    def load(self, reference: str) -> CredentialBundle | None:  # noqa: ARG002
        return None

    def delete(self, reference: str) -> None:  # noqa: ARG002
        return


@dataclass(frozen=True, slots=True)
class YouTubeAuthStartResult:
    authorization: OAuthAuthorizationResult
    scopes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_url": self.authorization.authorization_url,
            "state": self.authorization.state,
            "redirect_uri": self.authorization.redirect_uri,
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True, slots=True)
class YouTubeAuthCompleteResult:
    account: IntegrationAccount
    google_account_identifier: str | None
    granted_scopes: tuple[str, ...]
    channel_profile: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "account": self.account.to_dict(),
            "google_account_identifier": self.google_account_identifier,
            "granted_scopes": list(self.granted_scopes),
            "channel_profile": dict(self.channel_profile),
        }


class _AccountIndexStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._accounts: dict[str, IntegrationAccount] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._accounts = {}
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            self._accounts = {}
            return
        accounts: dict[str, IntegrationAccount] = {}
        if isinstance(payload, list):
            for item in payload:
                account = self._from_dict(item)
                if account is not None:
                    accounts[account.id] = account
        self._accounts = accounts

    def _save(self) -> None:
        payload = [account.to_dict() for account in sorted(self._accounts.values(), key=lambda item: (item.creator_id, item.display_name.casefold(), item.external_account_id))]
        self._path.write_text(_json_dumps(payload), encoding="utf-8")

    def _from_dict(self, payload: object) -> IntegrationAccount | None:
        if not isinstance(payload, dict):
            return None
        try:
            return IntegrationAccount(
                id=str(payload.get("id") or ""),
                creator_id=str(payload.get("creator_id") or ""),
                connector_id=str(payload.get("connector_id") or ""),
                external_account_id=str(payload.get("external_account_id") or ""),
                display_name=str(payload.get("display_name") or ""),
                status=IntegrationAccountStatus(str(payload.get("status") or IntegrationAccountStatus.NOT_LINKED.value)),
                linked_at=_safe_dt(payload.get("linked_at")) or utc_now(),
                last_verified_at=_safe_dt(payload.get("last_verified_at")),
                granted_scopes=tuple(str(item) for item in (payload.get("granted_scopes") or [])),
                granted_capabilities=tuple(IntegrationCapability(str(item)) for item in (payload.get("granted_capabilities") or [])),
                credential_ref=str(payload.get("credential_ref") or "") or None,
                metadata_summary=dict(payload.get("metadata_summary") or {}),
                auth_type=IntegrationAuthType(str(payload.get("auth_type") or IntegrationAuthType.LOCAL_NO_AUTH.value)),
            )
        except Exception:
            return None

    def all_for_creator(self, creator_id: str) -> tuple[IntegrationAccount, ...]:
        return tuple(
            sorted(
                (account for account in self._accounts.values() if account.creator_id == creator_id),
                key=lambda item: (item.display_name.casefold(), item.external_account_id),
            )
        )

    def get(self, account_id: str) -> IntegrationAccount | None:
        return self._accounts.get(account_id)

    def upsert(self, account: IntegrationAccount) -> IntegrationAccount:
        self._accounts[account.id] = account
        self._save()
        return account

    def delete(self, account_id: str) -> None:
        if account_id in self._accounts:
            self._accounts.pop(account_id, None)
            self._save()


def _credential_store(root: Path, *, environment: str | None = None) -> CredentialStore:
    try:
        return EncryptedLocalCredentialStore(root)
    except Exception:
        if environment in {"development", "test"}:
            return DevelopmentCredentialStore(root / "development")
        return _DisabledCredentialStore()


def _parse_http_error(exc: HTTPError) -> tuple[IntegrationErrorCategory, str, bool, str | None]:
    status = getattr(exc, "code", None)
    try:
        body = exc.read().decode("utf-8")
        payload = json.loads(body)
    except Exception:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else {}
    if isinstance(error, dict):
        message = str(error.get("message") or exc.reason or "provider error")
        errors = error.get("errors")
        reason = None
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                reason = str(first.get("reason") or "") or None
        if status == 401:
            return IntegrationErrorCategory.AUTHENTICATION_EXPIRED, message, False, reason
        if status == 403:
            if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                return IntegrationErrorCategory.RATE_LIMITED, message, True, reason
            return IntegrationErrorCategory.PERMISSION_DENIED, message, False, reason
        if status == 404:
            return IntegrationErrorCategory.RESOURCE_NOT_FOUND, message, False, reason
        if status == 429:
            return IntegrationErrorCategory.RATE_LIMITED, message, True, reason
        if 500 <= int(status or 0) < 600:
            return IntegrationErrorCategory.PROVIDER_UNAVAILABLE, message, True, reason
        return IntegrationErrorCategory.PROVIDER_ERROR, message, False, reason
    message = str(exc.reason or "provider error")
    if status == 401:
        return IntegrationErrorCategory.AUTHENTICATION_EXPIRED, message, False, None
    if status == 403:
        return IntegrationErrorCategory.PERMISSION_DENIED, message, False, None
    if status == 404:
        return IntegrationErrorCategory.RESOURCE_NOT_FOUND, message, False, None
    if status == 429:
        return IntegrationErrorCategory.RATE_LIMITED, message, True, None
    if 500 <= int(status or 0) < 600:
        return IntegrationErrorCategory.PROVIDER_UNAVAILABLE, message, True, None
    return IntegrationErrorCategory.PROVIDER_ERROR, message, False, None


def _normalize_page_items(items: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    return tuple(item for item in items if isinstance(item, dict))


class YouTubeIntegrationConnector:
    def __init__(
        self,
        *,
        connector_id: str = "youtube.connector",
        data_root: Path | None = None,
        credential_root: Path | None = None,
        environment: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        oauth_client: YouTubeOAuthClient | None = None,
        data_api_client: YouTubeDataApiClient | None = None,
        analytics_api_client: YouTubeAnalyticsApiClient | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._definition = IntegrationConnectorDefinition(
            connector_id=connector_id,
            provider="youtube",
            display_name="YouTube Read-First Connector",
            version="youtube-read-1",
            authentication_type=IntegrationAuthType.OAUTH2,
            read_capabilities=(
                IntegrationCapability.ACCOUNT_PROFILE_READ,
                IntegrationCapability.CONTENT_LIST_READ,
                IntegrationCapability.CONTENT_METADATA_READ,
                IntegrationCapability.ANALYTICS_READ,
            ),
            write_capabilities=(),
        )
        self._logger = logger or logging.getLogger("creator_intelligence_studio.integrations.youtube")
        self._data_root = data_root or Path(tempfile.gettempdir()) / "creator_intelligence_studio" / "integrations" / "youtube"
        self._data_root.mkdir(parents=True, exist_ok=True)
        self._credential_store = _credential_store(credential_root or (self._data_root / "credentials"), environment=environment)
        self._account_index = _AccountIndexStore(self._data_root / "accounts.json")
        self._oauth_client = oauth_client or DesktopYouTubeOAuthClient()
        self._data_api_factory = data_api_client or YouTubeDataApiClient()
        self._analytics_api_factory = analytics_api_client or YouTubeAnalyticsApiClient()
        self._client_id = client_id
        self._client_secret = client_secret
        self._required_scopes = READ_ONLY_SCOPES
        self._available = True
        self._rate_limits: dict[str, IntegrationRateLimitState] = {}

    @property
    def definition(self) -> IntegrationConnectorDefinition:
        return self._definition

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_rate_limit(self, account_id: str, rate_limit_state: IntegrationRateLimitState | None) -> None:
        if rate_limit_state is None:
            self._rate_limits.pop(account_id, None)
            return
        self._rate_limits[account_id] = rate_limit_state

    def set_account_status(self, account_id: str, status: IntegrationAccountStatus) -> None:
        account = self.get_account(account_id)
        if account is None:
            return
        self._account_index.upsert(replace(account, status=status))

    def _error(
        self,
        category: IntegrationErrorCategory,
        message: str,
        *,
        provider_code: str | None = None,
        provider_request_id: str | None = None,
        retryable: bool = False,
        safe_detail: str | None = None,
    ) -> IntegrationErrorDetails:
        return IntegrationErrorDetails(
            category=category,
            message=message,
            provider_code=provider_code,
            provider_request_id=provider_request_id,
            retryable=retryable,
            safe_detail=safe_detail,
        )

    def _credential_bundle(self, account: IntegrationAccount) -> CredentialBundle | None:
        if not account.credential_ref:
            return None
        return self._credential_store.load(account.credential_ref)

    def _resolved_client_id(self, explicit_client_id: str | None = None) -> str:
        resolved = resolve_youtube_oauth_client_id(configured_client_id=explicit_client_id or self._client_id)
        if not resolved:
            raise ValueError("YouTube OAuth client_id is not configured.")
        return resolved

    def _refresh_if_needed(self, account: IntegrationAccount) -> CredentialBundle | None:
        bundle = self._credential_bundle(account)
        if bundle is None:
            return None
        if not bundle.expires_at or not bundle.refresh_token:
            return bundle
        try:
            expires_at = datetime.fromisoformat(bundle.expires_at)
        except ValueError:
            return bundle
        if expires_at > utc_now():
            return bundle
        try:
            refreshed = self._oauth_client.refresh_token(
                client_id=self._resolved_client_id(),
                client_secret=self._client_secret,
                refresh_token=bundle.refresh_token,
            )
        except Exception as exc:
            self._logger.debug("YouTube token refresh failed for %s: %s", account.id, exc)
            updated = replace(account, status=IntegrationAccountStatus.EXPIRED, last_verified_at=utc_now())
            self._account_index.upsert(updated)
            return None
        refreshed_bundle = CredentialBundle(
            access_token=refreshed.access_token,
            refresh_token=refreshed.refresh_token,
            token_type=refreshed.token_type,
            expires_at=(utc_now() + timedelta(seconds=refreshed.expires_in or 3600)).isoformat(),
            granted_scopes=refreshed.granted_scopes,
            google_account_identifier=bundle.google_account_identifier,
        )
        self._credential_store.save(account.credential_ref, refreshed_bundle)
        updated = replace(account, status=IntegrationAccountStatus.CONNECTED, last_verified_at=utc_now())
        self._account_index.upsert(updated)
        return refreshed_bundle

    def list_accounts(self, creator_id: str) -> tuple[IntegrationAccount, ...]:
        return self._account_index.all_for_creator(creator_id)

    def get_account(self, account_id: str) -> IntegrationAccount | None:
        return self._account_index.get(account_id)

    def get_health(self, *, creator_id: str | None = None, account_id: str | None = None) -> IntegrationHealth:
        account = self.get_account(account_id) if account_id is not None else None
        if account is None and creator_id is not None:
            has_account = bool(self.list_accounts(creator_id))
            return IntegrationHealth(
                connector_id=self.definition.connector_id,
                connector_available=self._available,
                account_authenticated=has_account,
                permissions_valid=has_account,
                status=IntegrationHealthStatus.UNKNOWN if self._available else IntegrationHealthStatus.UNAVAILABLE,
                checked_at=utc_now(),
            )
        if not self._available:
            return IntegrationHealth(
                connector_id=self.definition.connector_id,
                connector_available=False,
                account_authenticated=False,
                permissions_valid=False,
                last_error_category=IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                last_error_message="connector unavailable",
                status=IntegrationHealthStatus.UNAVAILABLE,
                checked_at=utc_now(),
            )
        if account is None:
            return IntegrationHealth(
                connector_id=self.definition.connector_id,
                connector_available=True,
                account_authenticated=False,
                permissions_valid=False,
                status=IntegrationHealthStatus.UNKNOWN,
                checked_at=utc_now(),
            )
        bundle = self._credential_bundle(account)
        rate_limit = self._rate_limits.get(account.id)
        if account.status in {IntegrationAccountStatus.EXPIRED, IntegrationAccountStatus.REVOKED, IntegrationAccountStatus.PERMISSION_MISSING}:
            status = IntegrationHealthStatus.DEGRADED
        elif rate_limit is not None and rate_limit.limited:
            status = IntegrationHealthStatus.DEGRADED
        elif bundle is None:
            status = IntegrationHealthStatus.UNKNOWN
        else:
            status = IntegrationHealthStatus.HEALTHY
        last_error_category = None
        last_error_message = None
        if account.status == IntegrationAccountStatus.EXPIRED:
            last_error_category = IntegrationErrorCategory.AUTHENTICATION_EXPIRED
            last_error_message = "account credentials expired"
        elif account.status == IntegrationAccountStatus.REVOKED:
            last_error_category = IntegrationErrorCategory.AUTHENTICATION_REQUIRED
            last_error_message = "account revoked"
        elif account.status == IntegrationAccountStatus.PERMISSION_MISSING:
            last_error_category = IntegrationErrorCategory.PERMISSION_DENIED
            last_error_message = "permissions missing"
        return IntegrationHealth(
            connector_id=self.definition.connector_id,
            connector_available=True,
            account_authenticated=bundle is not None and account.status == IntegrationAccountStatus.CONNECTED,
            permissions_valid=bundle is not None and set(bundle.granted_scopes).issuperset(self._required_scopes),
            rate_limit_state=rate_limit,
            last_success_at=account.last_verified_at,
            last_error_category=last_error_category,
            last_error_message=last_error_message,
            status=status,
            checked_at=utc_now(),
        )

    def begin_authorization(
        self,
        *,
        creator_id: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        scopes: tuple[str, ...] | None = None,
    ) -> YouTubeAuthStartResult:
        requested_scopes = tuple(scopes or self._required_scopes)
        if not set(requested_scopes).issubset(set(self._required_scopes)):
            raise ValueError("YouTube read-first connector only requests read-only scopes.")
        auth = self._oauth_client.begin_authorization(
            client_id=self._resolved_client_id(client_id),
            scopes=requested_scopes,
            redirect_uri=redirect_uri,
        )
        return YouTubeAuthStartResult(authorization=auth, scopes=requested_scopes)

    def complete_authorization(
        self,
        *,
        creator_id: str,
        authorization_code: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        code_verifier: str | None = None,
        display_name: str | None = None,
    ) -> YouTubeAuthCompleteResult:
        token_result = self._oauth_client.exchange_code(
            client_id=self._resolved_client_id(client_id),
            client_secret=client_secret or self._client_secret,
            code=authorization_code,
            redirect_uri=redirect_uri or "http://localhost/callback",
            code_verifier=code_verifier,
        )
        if not set(token_result.granted_scopes).issubset(set(self._required_scopes)):
            raise ValueError("YouTube read-first connector only accepts read-only scopes.")
        verified = self._oauth_client.verify_token(token_result.access_token, self._required_scopes)
        google_account_identifier = str(verified.get("google_account_identifier") or token_result.google_account_identifier or "")
        credential_ref = f"youtube_{creator_id}_{uuid4().hex}"
        expires_at = None
        if token_result.expires_in is not None:
            expires_at = (utc_now() + timedelta(seconds=token_result.expires_in)).isoformat()
        self._credential_store.save(
            credential_ref,
            CredentialBundle(
                access_token=token_result.access_token,
                refresh_token=token_result.refresh_token,
                token_type=token_result.token_type,
                expires_at=expires_at,
                granted_scopes=token_result.granted_scopes,
                google_account_identifier=google_account_identifier,
            ),
        )
        profile = self._fetch_account_profile(
            access_token=token_result.access_token,
            creator_id=creator_id,
            credential_ref=credential_ref,
            display_name=display_name,
        )
        account = IntegrationAccount(
            id=profile["account_id"],
            creator_id=creator_id,
            connector_id=self.definition.connector_id,
            external_account_id=profile["channel_id"],
            display_name=profile["display_name"],
            status=IntegrationAccountStatus.CONNECTED,
            linked_at=utc_now(),
            last_verified_at=utc_now(),
            granted_scopes=token_result.granted_scopes,
            granted_capabilities=self.definition.read_capabilities,
            credential_ref=credential_ref,
            metadata_summary=profile,
            auth_type=IntegrationAuthType.OAUTH2,
        )
        self._account_index.upsert(account)
        return YouTubeAuthCompleteResult(
            account=account,
            google_account_identifier=google_account_identifier or None,
            granted_scopes=token_result.granted_scopes,
            channel_profile=profile,
        )

    def disconnect_account(self, *, creator_id: str, account_id: str) -> bool:
        account = self.get_account(account_id)
        if account is None or account.creator_id != creator_id:
            return False
        if account.credential_ref:
            self._credential_store.delete(account.credential_ref)
        self._account_index.delete(account_id)
        return True

    def link_account(self, request):  # pragma: no cover - generic link should not be used for YouTube
        raise ValueError("Use the YouTube OAuth flow instead of generic manual linking.")

    def _load_data_client(self, access_token: str) -> YouTubeDataApiClient:
        client = self._data_api_factory
        if hasattr(client, "access_token"):
            client.access_token = access_token
        return client

    def _load_analytics_client(self, access_token: str) -> YouTubeAnalyticsApiClient:
        client = self._analytics_api_factory
        if hasattr(client, "access_token"):
            client.access_token = access_token
        return client

    def _fetch_account_profile(self, *, access_token: str, creator_id: str, credential_ref: str, display_name: str | None = None) -> dict[str, object]:
        data_client = self._load_data_client(access_token)
        page = data_client.list_channels(mine=True, part="snippet,contentDetails,statistics,brandingSettings")
        if not page.items:
            raise ValueError("YouTube did not return a channel profile for the authenticated user.")
        channel = page.items[0]
        snippet = channel.get("snippet") if isinstance(channel.get("snippet"), dict) else {}
        content_details = channel.get("contentDetails") if isinstance(channel.get("contentDetails"), dict) else {}
        related = content_details.get("relatedPlaylists") if isinstance(content_details.get("relatedPlaylists"), dict) else {}
        statistics = channel.get("statistics") if isinstance(channel.get("statistics"), dict) else {}
        thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
        default_thumb = thumbnails.get("default") if isinstance(thumbnails.get("default"), dict) else {}
        channel_id = str(channel.get("id") or "")
        title = str(display_name or snippet.get("title") or channel_id or "YouTube Channel")
        uploads_playlist_id = str(related.get("uploads") or "")
        custom_url = None
        branding = channel.get("brandingSettings") if isinstance(channel.get("brandingSettings"), dict) else {}
        if isinstance(branding.get("channel"), dict):
            custom_url = branding.get("channel", {}).get("customUrl")
        return {
            "account_id": _stable_id(creator_id, self.definition.connector_id, channel_id or credential_ref),
            "channel_id": channel_id,
            "display_name": title,
            "public_reference": f"https://www.youtube.com/channel/{channel_id}" if channel_id else None,
            "custom_url": custom_url,
            "description": snippet.get("description"),
            "thumbnail_url": default_thumb.get("url"),
            "uploads_playlist_id": uploads_playlist_id,
            "subscriber_count": _safe_int(statistics.get("subscriberCount")),
            "video_count": _safe_int(statistics.get("videoCount")),
            "view_count": _safe_int(statistics.get("viewCount")),
            "country": snippet.get("country"),
            "published_at": snippet.get("publishedAt"),
            "creator_id": creator_id,
            "credential_ref": credential_ref,
        }

    def _account_profile_resource(self, account: IntegrationAccount) -> ExternalContentResource:
        return ExternalContentResource(
            connector_id=self.definition.connector_id,
            external_id=account.external_account_id,
            account_id=account.id,
            resource_type="account_profile",
            title=account.display_name,
            description=account.metadata_summary.get("description") if isinstance(account.metadata_summary, dict) else None,
            published_at=_safe_dt(account.metadata_summary.get("published_at")) if isinstance(account.metadata_summary, dict) else None,
            url=account.metadata_summary.get("public_reference") if isinstance(account.metadata_summary, dict) else None,
            public_reference=account.metadata_summary.get("custom_url") if isinstance(account.metadata_summary, dict) else None,
            status=account.status.value,
            provider_metadata=dict(account.metadata_summary),
        )

    def _ensure_channel_profile(self, account: IntegrationAccount, *, access_token: str) -> IntegrationAccount:
        profile = self._fetch_account_profile(access_token=access_token, creator_id=account.creator_id, credential_ref=account.credential_ref or "", display_name=account.display_name)
        updated = replace(account, metadata_summary=profile, last_verified_at=utc_now(), status=IntegrationAccountStatus.CONNECTED)
        return self._account_index.upsert(updated)

    def _build_content_list(self, account: IntegrationAccount, *, access_token: str, page_token: str | None = None, max_results: int = 50) -> tuple[ExternalContentResource, str | None]:
        uploads_playlist_id = str(account.metadata_summary.get("uploads_playlist_id") or "") if isinstance(account.metadata_summary, dict) else ""
        if not uploads_playlist_id:
            refreshed = self._ensure_channel_profile(account, access_token=access_token)
            uploads_playlist_id = str(refreshed.metadata_summary.get("uploads_playlist_id") or "") if isinstance(refreshed.metadata_summary, dict) else ""
            account = refreshed
        if not uploads_playlist_id:
            raise ValueError("YouTube uploads playlist is unavailable for this channel.")
        data_client = self._load_data_client(access_token)
        page = data_client.list_playlist_items(playlist_id=uploads_playlist_id, page_token=page_token, max_results=max_results, part="snippet,contentDetails,status")
        resources: list[ExternalContentResource] = []
        for item in _normalize_page_items(page.items):
            snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
            content_details = item.get("contentDetails") if isinstance(item.get("contentDetails"), dict) else {}
            resource_id = snippet.get("resourceId") if isinstance(snippet.get("resourceId"), dict) else {}
            video_id = str(resource_id.get("videoId") or content_details.get("videoId") or item.get("id") or "")
            thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
            default_thumb = thumbnails.get("default") if isinstance(thumbnails.get("default"), dict) else {}
            resources.append(
                ExternalContentResource(
                    connector_id=self.definition.connector_id,
                    external_id=video_id,
                    account_id=account.id,
                    resource_type="video",
                    title=str(snippet.get("title") or ""),
                    description=str(snippet.get("description")) if snippet.get("description") is not None else None,
                    published_at=_safe_dt(snippet.get("publishedAt")),
                    url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                    public_reference=default_thumb.get("url"),
                    status=str(item.get("status", {}).get("privacyStatus")) if isinstance(item.get("status"), dict) and item.get("status", {}).get("privacyStatus") is not None else None,
                    provider_metadata={
                        "playlist_item_id": item.get("id"),
                        "playlist_id": uploads_playlist_id,
                        "video_id": video_id,
                        "video_published_at": content_details.get("videoPublishedAt"),
                        "thumbnails": thumbnails,
                        "snippet": {
                            "channelTitle": snippet.get("channelTitle"),
                            "title": snippet.get("title"),
                            "description": snippet.get("description"),
                            "publishedAt": snippet.get("publishedAt"),
                            "resourceId": resource_id,
                        },
                    },
                )
            )
        return tuple(resources), page.next_page_token

    def _build_video_metadata(self, account: IntegrationAccount, *, access_token: str, video_ids: tuple[str, ...]) -> tuple[ExternalContentResource, ...]:
        data_client = self._load_data_client(access_token)
        page = data_client.list_videos(ids=video_ids, part="snippet,contentDetails,status,statistics")
        resources: list[ExternalContentResource] = []
        for item in _normalize_page_items(page.items):
            snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
            content_details = item.get("contentDetails") if isinstance(item.get("contentDetails"), dict) else {}
            status = item.get("status") if isinstance(item.get("status"), dict) else {}
            statistics = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
            thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
            default_thumb = thumbnails.get("default") if isinstance(thumbnails.get("default"), dict) else {}
            video_id = str(item.get("id") or "")
            resources.append(
                ExternalContentResource(
                    connector_id=self.definition.connector_id,
                    external_id=video_id,
                    account_id=account.id,
                    resource_type="video_metadata",
                    title=str(snippet.get("title") or ""),
                    description=str(snippet.get("description")) if snippet.get("description") is not None else None,
                    published_at=_safe_dt(snippet.get("publishedAt")),
                    url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                    public_reference=default_thumb.get("url"),
                    status=str(status.get("privacyStatus")) if status.get("privacyStatus") is not None else None,
                    provider_metadata={
                        "video_id": video_id,
                        "content_details": content_details,
                        "status": status,
                        "statistics": statistics,
                        "snippet": snippet,
                    },
                )
            )
        return tuple(resources)

    def _parse_analytics_rows(
        self,
        *,
        account: IntegrationAccount,
        raw_json: str,
        requested_metrics: tuple[str, ...],
        start_date: str,
        end_date: str,
    ) -> tuple[IntegrationAnalyticsMetric, ...]:
        payload = _json_loads(raw_json, {})
        headers = payload.get("columnHeaders") if isinstance(payload, dict) else []
        rows = payload.get("rows") if isinstance(payload, dict) else []
        if not isinstance(headers, list):
            headers = []
        if not isinstance(rows, list):
            rows = []
        dimension_names = [str(header.get("name")) for header in headers if isinstance(header, dict) and header.get("columnType") == "DIMENSION"]
        metric_names = [str(header.get("name")) for header in headers if isinstance(header, dict) and header.get("columnType") == "METRIC"]
        metrics: list[IntegrationAnalyticsMetric] = []
        metric_by_name = {name: None for name in requested_metrics}
        for row in rows:
            if not isinstance(row, list):
                continue
            row_map: dict[str, object] = {}
            for index, value in enumerate(row):
                if index < len(headers) and isinstance(headers[index], dict):
                    row_map[str(headers[index].get("name"))] = value
            resource_id = None
            if "video" in row_map:
                resource_id = str(row_map.get("video") or "")
            for metric_name in metric_names:
                value = row_map.get(metric_name)
                if metric_name not in metric_by_name:
                    continue
                metric_by_name[metric_name] = True
                metrics.append(
                    IntegrationAnalyticsMetric(
                        connector_id=self.definition.connector_id,
                        account_id=account.id,
                        external_resource_id=resource_id,
                        metric_name=metric_name,
                        value=_safe_float(value),
                        unit="count" if metric_name not in {"averageViewDuration", "averageViewPercentage"} else ("seconds" if metric_name == "averageViewDuration" else "percent"),
                        metric_period_start=_safe_dt(start_date),
                        metric_period_end=_safe_dt(end_date),
                        retrieved_at=utc_now(),
                        availability="available" if value is not None else "missing",
                        provider_metadata={"dimension_names": dimension_names, "raw_row": row_map},
                    )
                )
        for metric_name in requested_metrics:
            if metric_by_name.get(metric_name):
                continue
            metrics.append(
                IntegrationAnalyticsMetric(
                    connector_id=self.definition.connector_id,
                    account_id=account.id,
                    external_resource_id=None,
                    metric_name=metric_name,
                    value=None,
                    unit="count",
                    metric_period_start=_safe_dt(start_date),
                    metric_period_end=_safe_dt(end_date),
                    retrieved_at=utc_now(),
                    availability="missing",
                    provider_metadata={"dimension_names": dimension_names, "reason": "not_reported"},
                )
            )
        return tuple(metrics)

    def _analytics_query(
        self,
        *,
        access_token: str,
        account: IntegrationAccount,
        parameters: dict[str, object],
    ) -> tuple[IntegrationAnalyticsMetric, ...]:
        analytics_client = self._load_analytics_client(access_token)
        start_date = str(parameters.get("start_date") or parameters.get("startDate") or "")
        end_date = str(parameters.get("end_date") or parameters.get("endDate") or "")
        if not start_date:
            start_date = (utc_now().date() - timedelta(days=28)).isoformat()
        if not end_date:
            end_date = utc_now().date().isoformat()
        metrics = parameters.get("metrics")
        if isinstance(metrics, str):
            requested_metrics = tuple(metric.strip() for metric in metrics.split(",") if metric.strip())
        elif isinstance(metrics, list):
            requested_metrics = tuple(str(metric) for metric in metrics if str(metric).strip())
        else:
            requested_metrics = (
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "averageViewPercentage",
                "likes",
                "comments",
                "subscribersGained",
                "subscribersLost",
            )
        dimensions = parameters.get("dimensions")
        if isinstance(dimensions, list):
            dimensions = ",".join(str(item) for item in dimensions if str(item).strip())
        filters = parameters.get("filters")
        if isinstance(filters, dict):
            parts: list[str] = []
            for key, value in filters.items():
                if value is None:
                    continue
                if isinstance(value, list):
                    parts.append(f"{key}=={','.join(str(item) for item in value)}")
                else:
                    parts.append(f"{key}=={value}")
            filters = ";".join(parts)
        if filters is None and parameters.get("video_id"):
            filters = f"video=={parameters['video_id']}"
        page = analytics_client.query(
            ids="channel==MINE",
            metrics=",".join(requested_metrics),
            dimensions=str(dimensions) if dimensions else None,
            filters=str(filters) if filters else None,
            start_date=start_date,
            end_date=end_date,
            max_results=int(parameters.get("max_results") or parameters.get("maxResults") or 200),
            sort=str(parameters.get("sort")) if parameters.get("sort") else None,
        )
        return self._parse_analytics_rows(
            account=account,
            raw_json=page.raw_json,
            requested_metrics=requested_metrics,
            start_date=start_date,
            end_date=end_date,
        )

    def read(self, request: IntegrationReadRequest) -> IntegrationReadResult:
        provider_request_id = _stable_id(self.definition.connector_id, request.request_id, request.account_id, request.capability.value)
        if not self._available:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.PROVIDER_UNAVAILABLE, "connector unavailable", provider_request_id=provider_request_id, retryable=True),
                provider_request_id=provider_request_id,
                timestamp=utc_now(),
            )
        account = self.get_account(request.account_id)
        if account is None:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.RESOURCE_NOT_FOUND, "account not found", provider_request_id=provider_request_id, safe_detail="account_missing"),
                provider_request_id=provider_request_id,
                timestamp=utc_now(),
            )
        if account.creator_id != request.creator_id:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.PERMISSION_DENIED, "creator does not own the account", provider_request_id=provider_request_id, safe_detail="owner_mismatch"),
                provider_request_id=provider_request_id,
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.EXPIRED:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.AUTHENTICATION_EXPIRED, "account credentials expired", provider_request_id=provider_request_id),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.REVOKED:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.AUTHENTICATION_REQUIRED, "account revoked", provider_request_id=provider_request_id),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.PERMISSION_MISSING:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.PERMISSION_DENIED, "permissions missing", provider_request_id=provider_request_id),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        rate_limit = self._rate_limits.get(account.id)
        if rate_limit is not None and rate_limit.limited:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(
                    IntegrationErrorCategory.RATE_LIMITED,
                    "rate limit exceeded",
                    provider_request_id=provider_request_id,
                    retryable=True,
                    safe_detail="rate_limited",
                ),
                provider_request_id=provider_request_id,
                rate_limit_state=rate_limit,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        bundle = self._refresh_if_needed(account)
        if bundle is None or not bundle.access_token:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.AUTHENTICATION_REQUIRED, "authentication required", provider_request_id=provider_request_id, safe_detail="credential_unavailable"),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        try:
            if request.capability == IntegrationCapability.ACCOUNT_PROFILE_READ:
                profile = self._fetch_account_profile(
                    access_token=bundle.access_token,
                    creator_id=request.creator_id,
                    credential_ref=account.credential_ref or "",
                    display_name=account.display_name,
                )
                updated = replace(account, metadata_summary=profile, last_verified_at=utc_now(), status=IntegrationAccountStatus.CONNECTED)
                self._account_index.upsert(updated)
                resource = self._account_profile_resource(updated)
                return IntegrationReadResult(
                    request_id=request.request_id,
                    creator_id=request.creator_id,
                    connector_id=self.definition.connector_id,
                    account_id=request.account_id,
                    capability=request.capability,
                    success=True,
                    resources=(resource,),
                    health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                    provider_request_id=provider_request_id,
                    provider_metadata={"contract_version": INTEGRATION_CONTRACT_VERSION, "scope": "account_profile"},
                    timestamp=utc_now(),
                )
            if request.capability == IntegrationCapability.CONTENT_LIST_READ:
                resources, next_page_token = self._build_content_list(
                    account,
                    access_token=bundle.access_token,
                    page_token=str(request.parameters.get("page_token") or request.parameters.get("pageToken") or "") or None,
                    max_results=int(request.parameters.get("max_results") or request.parameters.get("maxResults") or 50),
                )
                return IntegrationReadResult(
                    request_id=request.request_id,
                    creator_id=request.creator_id,
                    connector_id=self.definition.connector_id,
                    account_id=request.account_id,
                    capability=request.capability,
                    success=True,
                    resources=resources,
                    next_page_token=next_page_token,
                    health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                    provider_request_id=provider_request_id,
                    provider_metadata={"contract_version": INTEGRATION_CONTRACT_VERSION, "scope": "content_list"},
                    timestamp=utc_now(),
                )
            if request.capability == IntegrationCapability.CONTENT_METADATA_READ:
                raw_ids = request.parameters.get("video_ids") or request.parameters.get("videoIds") or request.parameters.get("video_id") or request.parameters.get("videoId")
                if raw_ids is None:
                    return IntegrationReadResult(
                        request_id=request.request_id,
                        creator_id=request.creator_id,
                        connector_id=self.definition.connector_id,
                        account_id=request.account_id,
                        capability=request.capability,
                        success=False,
                        error=self._error(IntegrationErrorCategory.INVALID_REQUEST, "video_ids are required", provider_request_id=provider_request_id, safe_detail="video_ids_missing"),
                        provider_request_id=provider_request_id,
                        timestamp=utc_now(),
                    )
                if isinstance(raw_ids, list):
                    video_ids = tuple(str(item) for item in raw_ids if str(item).strip())
                else:
                    video_ids = tuple(str(raw_ids).split(","))
                    video_ids = tuple(item.strip() for item in video_ids if item.strip())
                resources = self._build_video_metadata(account, access_token=bundle.access_token, video_ids=video_ids)
                return IntegrationReadResult(
                    request_id=request.request_id,
                    creator_id=request.creator_id,
                    connector_id=self.definition.connector_id,
                    account_id=request.account_id,
                    capability=request.capability,
                    success=True,
                    resources=resources,
                    health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                    provider_request_id=provider_request_id,
                    provider_metadata={"contract_version": INTEGRATION_CONTRACT_VERSION, "scope": "content_metadata"},
                    timestamp=utc_now(),
                )
            if request.capability == IntegrationCapability.ANALYTICS_READ:
                analytics = self._analytics_query(access_token=bundle.access_token, account=account, parameters=request.parameters)
                return IntegrationReadResult(
                    request_id=request.request_id,
                    creator_id=request.creator_id,
                    connector_id=self.definition.connector_id,
                    account_id=request.account_id,
                    capability=request.capability,
                    success=True,
                    analytics=analytics,
                    health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                    provider_request_id=provider_request_id,
                    provider_metadata={"contract_version": INTEGRATION_CONTRACT_VERSION, "scope": "analytics"},
                    timestamp=utc_now(),
                )
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.UNSUPPORTED_OPERATION, "unsupported read capability", provider_request_id=provider_request_id),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        except HTTPError as exc:
            category, message, retryable, reason = _parse_http_error(exc)
            if category == IntegrationErrorCategory.AUTHENTICATION_EXPIRED and bundle.refresh_token:
                refreshed = self._refresh_if_needed(account)
                if refreshed is not None:
                    return self.read(request)
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(category, message, provider_code=reason, provider_request_id=provider_request_id, retryable=retryable),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        except URLError as exc:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.NETWORK_UNAVAILABLE, str(getattr(exc, "reason", exc)), provider_request_id=provider_request_id, retryable=True),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        except Exception as exc:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=self._error(IntegrationErrorCategory.PROVIDER_ERROR, "youtube request failed", provider_request_id=provider_request_id, safe_detail=str(exc)[:120]),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )

    def write(self, request: IntegrationWriteRequest) -> IntegrationWriteResult:
        return IntegrationWriteResult(
            request_id=request.request_id,
            creator_id=request.creator_id,
            connector_id=self.definition.connector_id,
            account_id=request.account_id,
            capability=request.capability,
            success=False,
            status="unsupported_operation",
            error=self._error(IntegrationErrorCategory.UNSUPPORTED_OPERATION, "YouTube connector is read-only", retryable=False),
            timestamp=utc_now(),
        )


def build_default_youtube_connector(
    *,
    data_root: Path | None = None,
    environment: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> YouTubeIntegrationConnector:
    return YouTubeIntegrationConnector(data_root=data_root, environment=environment, client_id=client_id, client_secret=client_secret)
