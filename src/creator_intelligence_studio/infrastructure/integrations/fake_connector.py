"""Deterministic fake integration connector for offline validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.integrations import (
    ExternalContentResource,
    INTEGRATION_CONTRACT_VERSION,
    IntegrationAccount,
    IntegrationAccountLinkRequest,
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
from creator_intelligence_studio.shared.dates import utc_now


def _stable_id(*parts: object) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return sha256(payload.encode("utf-8")).hexdigest()


def _error(
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


class FakeIntegrationConnector:
    """In-memory connector used for offline smoke tests and architecture validation."""

    def __init__(
        self,
        *,
        connector_id: str = "fake.connector",
        provider: str = "fake",
        display_name: str = "Fake Integration Connector",
        version: str = "fake-1",
    ) -> None:
        self._definition = IntegrationConnectorDefinition(
            connector_id=connector_id,
            provider=provider,
            display_name=display_name,
            version=version,
            authentication_type=IntegrationAuthType.OAUTH2,
            read_capabilities=(
                IntegrationCapability.ACCOUNT_PROFILE_READ,
                IntegrationCapability.CONTENT_LIST_READ,
                IntegrationCapability.CONTENT_METADATA_READ,
                IntegrationCapability.ANALYTICS_READ,
                IntegrationCapability.COMMENTS_READ,
            ),
            write_capabilities=(
                IntegrationCapability.CONTENT_UPLOAD,
                IntegrationCapability.CONTENT_PUBLISH,
                IntegrationCapability.CONTENT_SCHEDULE,
                IntegrationCapability.CONTENT_UPDATE,
                IntegrationCapability.CONTENT_DELETE,
            ),
        )
        self._accounts_by_id: dict[str, IntegrationAccount] = {}
        self._accounts_by_creator: dict[str, list[str]] = {}
        self._write_results_by_idempotency_key: dict[str, IntegrationWriteResult] = {}
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
        account = self._accounts_by_id.get(account_id)
        if account is None:
            return
        self._accounts_by_id[account_id] = replace(account, status=status)

    def _account_ids_for_creator(self, creator_id: str) -> tuple[str, ...]:
        return tuple(self._accounts_by_creator.get(creator_id, ()))

    def list_accounts(self, creator_id: str) -> tuple[IntegrationAccount, ...]:
        account_ids = self._accounts_by_creator.get(creator_id, ())
        accounts = [self._accounts_by_id[account_id] for account_id in account_ids if account_id in self._accounts_by_id]
        return tuple(sorted(accounts, key=lambda item: (item.display_name.casefold(), item.external_account_id)))

    def link_account(self, request: IntegrationAccountLinkRequest) -> IntegrationAccount:
        if request.creator_id is None or not str(request.creator_id).strip():
            raise ValueError("creator_id is required.")
        account_id = _stable_id(self.definition.connector_id, request.creator_id, request.external_account_id)
        linked_at = request.linked_at or utc_now()
        account = IntegrationAccount(
            id=account_id,
            creator_id=request.creator_id,
            connector_id=self.definition.connector_id,
            external_account_id=request.external_account_id,
            display_name=request.display_name,
            status=IntegrationAccountStatus.CONNECTED,
            linked_at=linked_at,
            last_verified_at=linked_at,
            granted_scopes=request.granted_scopes,
            granted_capabilities=request.granted_capabilities,
            credential_ref=request.credential_ref or f"integration.fake.{account_id}",
            metadata_summary=dict(request.metadata_summary),
            auth_type=request.auth_type,
        )
        self._accounts_by_id[account.id] = account
        self._accounts_by_creator.setdefault(request.creator_id, [])
        if account.id not in self._accounts_by_creator[request.creator_id]:
            self._accounts_by_creator[request.creator_id].append(account.id)
        return account

    def unlink_account(self, *, creator_id: str, account_id: str) -> bool:
        account = self._accounts_by_id.get(account_id)
        if account is None or account.creator_id != creator_id:
            return False
        self._accounts_by_id.pop(account_id, None)
        creator_accounts = self._accounts_by_creator.get(creator_id, [])
        if account_id in creator_accounts:
            creator_accounts.remove(account_id)
        self._write_results_by_idempotency_key = {
            key: value for key, value in self._write_results_by_idempotency_key.items() if value.account_id != account_id
        }
        return True

    def get_account(self, account_id: str) -> IntegrationAccount | None:
        return self._accounts_by_id.get(account_id)

    def get_health(self, *, creator_id: str | None = None, account_id: str | None = None) -> IntegrationHealth:
        account = self._accounts_by_id.get(account_id) if account_id is not None else None
        rate_limit = self._rate_limits.get(account_id) if account_id is not None else None
        connector_available = self._available
        account_authenticated = account is not None and account.status == IntegrationAccountStatus.CONNECTED
        permissions_valid = account is not None and bool(account.granted_capabilities)
        if account is None and creator_id is not None:
            account_authenticated = bool(self._accounts_by_creator.get(creator_id))
            permissions_valid = account_authenticated
        if not connector_available:
            status = IntegrationHealthStatus.UNAVAILABLE
        elif account is None:
            status = IntegrationHealthStatus.UNKNOWN
        elif account.status in {IntegrationAccountStatus.EXPIRED, IntegrationAccountStatus.REVOKED, IntegrationAccountStatus.PERMISSION_MISSING}:
            status = IntegrationHealthStatus.DEGRADED
        elif rate_limit is not None and rate_limit.limited:
            status = IntegrationHealthStatus.DEGRADED
        elif account_authenticated and permissions_valid:
            status = IntegrationHealthStatus.HEALTHY
        else:
            status = IntegrationHealthStatus.UNKNOWN
        last_error_category = None
        last_error_message = None
        if account is not None:
            if account.status == IntegrationAccountStatus.EXPIRED:
                last_error_category = IntegrationErrorCategory.AUTHENTICATION_EXPIRED
                last_error_message = "account credentials expired"
            elif account.status == IntegrationAccountStatus.REVOKED:
                last_error_category = IntegrationErrorCategory.AUTHENTICATION_REQUIRED
                last_error_message = "account revoked"
            elif account.status == IntegrationAccountStatus.PERMISSION_MISSING:
                last_error_category = IntegrationErrorCategory.PERMISSION_DENIED
                last_error_message = "account permissions missing"
        return IntegrationHealth(
            connector_id=self.definition.connector_id,
            connector_available=connector_available,
            account_authenticated=account_authenticated,
            permissions_valid=permissions_valid,
            rate_limit_state=rate_limit,
            last_success_at=account.last_verified_at if account is not None else None,
            last_error_category=last_error_category,
            last_error_message=last_error_message,
            status=status,
            checked_at=utc_now(),
        )

    def _ensure_account(self, request: IntegrationReadRequest | IntegrationWriteRequest) -> tuple[IntegrationAccount | None, IntegrationErrorDetails | None]:
        account = self.get_account(request.account_id)
        if account is None:
            return None, _error(IntegrationErrorCategory.RESOURCE_NOT_FOUND, "account not found", safe_detail="account_missing")
        if account.creator_id != request.creator_id:
            return None, _error(IntegrationErrorCategory.PERMISSION_DENIED, "creator does not own the account", safe_detail="owner_mismatch")
        return account, None

    def _build_content_resources(self, account: IntegrationAccount, request: IntegrationReadRequest) -> tuple[ExternalContentResource, ...]:
        page_token = str(request.parameters.get("page_token") or request.parameters.get("cursor") or "")
        base = [
            ExternalContentResource(
                connector_id=self.definition.connector_id,
                external_id=_stable_id(account.id, request.capability.value, "item-1"),
                account_id=account.id,
                resource_type="content",
                title=f"{account.display_name} content 1",
                description="Deterministic fake content item.",
                published_at=utc_now(),
                url=f"https://fake.local/{account.external_account_id}/content/1",
                public_reference=f"fake:{account.external_account_id}:1",
                status="published",
                provider_metadata={"page": 1, "capability": request.capability.value},
            ),
            ExternalContentResource(
                connector_id=self.definition.connector_id,
                external_id=_stable_id(account.id, request.capability.value, "item-2"),
                account_id=account.id,
                resource_type="content",
                title=f"{account.display_name} content 2",
                description="Deterministic fake content item.",
                published_at=utc_now(),
                url=f"https://fake.local/{account.external_account_id}/content/2",
                public_reference=f"fake:{account.external_account_id}:2",
                status="published",
                provider_metadata={"page": 1, "capability": request.capability.value},
            ),
        ]
        if page_token == "page-2":
            return tuple(
                replace(item, provider_metadata={**item.provider_metadata, "page": 2})
                for item in base[:1]
            )
        return tuple(base)

    def _build_analytics(self, account: IntegrationAccount, request: IntegrationReadRequest) -> tuple[IntegrationAnalyticsMetric, ...]:
        now = utc_now()
        base_value = float(len(account.display_name) + len(request.capability.value))
        return (
            IntegrationAnalyticsMetric(
                connector_id=self.definition.connector_id,
                account_id=account.id,
                external_resource_id=None,
                metric_name="views",
                value=round(base_value * 11.0, 2),
                unit="count",
                metric_period_start=now,
                metric_period_end=now,
                retrieved_at=now,
                availability="available",
                provider_metadata={"source": "fake"},
            ),
            IntegrationAnalyticsMetric(
                connector_id=self.definition.connector_id,
                account_id=account.id,
                external_resource_id=None,
                metric_name="likes",
                value=None,
                unit="count",
                metric_period_start=now,
                metric_period_end=now,
                retrieved_at=now,
                availability="missing",
                provider_metadata={"source": "fake", "reason": "not_reported"},
            ),
            IntegrationAnalyticsMetric(
                connector_id=self.definition.connector_id,
                account_id=account.id,
                external_resource_id=None,
                metric_name="comments",
                value=round(base_value * 2.0, 2),
                unit="count",
                metric_period_start=now,
                metric_period_end=now,
                retrieved_at=now,
                availability="available",
                provider_metadata={"source": "fake"},
            ),
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
                error=_error(IntegrationErrorCategory.PROVIDER_UNAVAILABLE, "connector unavailable", provider_request_id=provider_request_id, retryable=True),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=self._rate_limits.get(request.account_id),
                timestamp=utc_now(),
            )
        account, error = self._ensure_account(request)
        if error is not None or account is None:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=error,
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=self._rate_limits.get(request.account_id),
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
                error=_error(IntegrationErrorCategory.AUTHENTICATION_EXPIRED, "account credentials expired", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=self._rate_limits.get(request.account_id),
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
                error=_error(IntegrationErrorCategory.AUTHENTICATION_REQUIRED, "account revoked", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=self._rate_limits.get(request.account_id),
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
                error=_error(IntegrationErrorCategory.PERMISSION_DENIED, "permissions missing", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=self._rate_limits.get(request.account_id),
                timestamp=utc_now(),
            )
        rate_limit = self._rate_limits.get(request.account_id)
        if rate_limit is not None and rate_limit.limited:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=_error(IntegrationErrorCategory.RATE_LIMITED, "rate limited", provider_request_id=provider_request_id, retryable=True, safe_detail="retry_after_available" if rate_limit.retry_after_seconds else "rate_limited"),
                provider_request_id=provider_request_id,
                rate_limit_state=rate_limit,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                timestamp=utc_now(),
            )
        if request.capability not in self.definition.read_capabilities:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=_error(IntegrationErrorCategory.UNSUPPORTED_OPERATION, "unsupported read capability", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
                rate_limit_state=rate_limit,
                timestamp=utc_now(),
            )
        resources: tuple[ExternalContentResource, ...] = ()
        analytics: tuple[IntegrationAnalyticsMetric, ...] = ()
        next_page_token = None
        if request.capability == IntegrationCapability.ACCOUNT_PROFILE_READ:
            resources = (
                ExternalContentResource(
                    connector_id=self.definition.connector_id,
                    external_id=account.external_account_id,
                    account_id=account.id,
                    resource_type="account_profile",
                    title=account.display_name,
                    description="Fake account profile.",
                    published_at=account.linked_at,
                    url=f"https://fake.local/accounts/{account.external_account_id}",
                    public_reference=f"fake:{account.external_account_id}",
                    status=account.status.value,
                    provider_metadata={"connector_id": self.definition.connector_id},
                ),
            )
        elif request.capability in {IntegrationCapability.CONTENT_LIST_READ, IntegrationCapability.CONTENT_METADATA_READ, IntegrationCapability.COMMENTS_READ}:
            resources = self._build_content_resources(account, request)
            next_page_token = "page-2" if request.parameters.get("page_token") is None else None
        elif request.capability == IntegrationCapability.ANALYTICS_READ:
            analytics = self._build_analytics(account, request)
        provider_metadata = {
            "capability": request.capability.value,
            "connector_version": self.definition.version,
            "contract_version": INTEGRATION_CONTRACT_VERSION,
        }
        return IntegrationReadResult(
            request_id=request.request_id,
            creator_id=request.creator_id,
            connector_id=self.definition.connector_id,
            account_id=request.account_id,
            capability=request.capability,
            success=True,
            resources=resources,
            analytics=analytics,
            next_page_token=next_page_token,
            rate_limit_state=rate_limit,
            health=self.get_health(creator_id=request.creator_id, account_id=request.account_id),
            provider_request_id=provider_request_id,
            provider_metadata=provider_metadata,
            timestamp=utc_now(),
        )

    def write(self, request: IntegrationWriteRequest) -> IntegrationWriteResult:
        provider_request_id = _stable_id(self.definition.connector_id, request.request_id, request.account_id, request.capability.value, request.idempotency_key or "")
        account, error = self._ensure_account(request)
        if error is not None or account is None:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="failed",
                error=error,
                provider_request_id=provider_request_id,
                timestamp=utc_now(),
            )
        if not request.approved_by_user:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="approval_required",
                error=_error(IntegrationErrorCategory.CONFLICT, "user approval required", provider_request_id=provider_request_id, retryable=False, safe_detail="approved_by_user_required"),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if not request.idempotency_key:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="invalid_request",
                error=_error(IntegrationErrorCategory.INVALID_REQUEST, "idempotency key is required", provider_request_id=provider_request_id, retryable=False, safe_detail="idempotency_key_missing"),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if not self._available:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="provider_unavailable",
                error=_error(IntegrationErrorCategory.PROVIDER_UNAVAILABLE, "connector unavailable", provider_request_id=provider_request_id, retryable=True),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.EXPIRED:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="authentication_expired",
                error=_error(IntegrationErrorCategory.AUTHENTICATION_EXPIRED, "account credentials expired", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.REVOKED:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="authentication_required",
                error=_error(IntegrationErrorCategory.AUTHENTICATION_REQUIRED, "account revoked", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if account.status == IntegrationAccountStatus.PERMISSION_MISSING:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="permission_denied",
                error=_error(IntegrationErrorCategory.PERMISSION_DENIED, "permissions missing", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        if request.capability not in self.definition.write_capabilities:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=self.definition.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="unsupported_operation",
                error=_error(IntegrationErrorCategory.UNSUPPORTED_OPERATION, "unsupported write capability", provider_request_id=provider_request_id, retryable=False),
                provider_request_id=provider_request_id,
                approval_reference=request.approval_reference,
                timestamp=utc_now(),
            )
        existing = self._write_results_by_idempotency_key.get(request.idempotency_key)
        if existing is not None:
            return existing
        payload = dict(request.payload)
        resource = ExternalContentResource(
            connector_id=self.definition.connector_id,
            external_id=_stable_id(account.id, request.capability.value, request.idempotency_key),
            account_id=account.id,
            resource_type="content_publish_result" if request.capability == IntegrationCapability.CONTENT_PUBLISH else "content_write_result",
            title=str(payload.get("title") or payload.get("caption") or f"Fake {request.capability.value}"),
            description=str(payload.get("description") or payload.get("body") or "Fake write result"),
            published_at=utc_now(),
            url=f"https://fake.local/{account.external_account_id}/{request.idempotency_key}",
            public_reference=f"fake-write:{request.idempotency_key}",
            status="completed",
            provider_metadata={"capability": request.capability.value, "idempotency_key": request.idempotency_key},
        )
        result = IntegrationWriteResult(
            request_id=request.request_id,
            creator_id=request.creator_id,
            connector_id=self.definition.connector_id,
            account_id=request.account_id,
            capability=request.capability,
            success=True,
            status="completed",
            resource=resource,
            idempotency_key=request.idempotency_key,
            approval_reference=request.approval_reference,
            provider_request_id=provider_request_id,
            provider_metadata={"connector_version": self.definition.version, "contract_version": INTEGRATION_CONTRACT_VERSION},
            timestamp=utc_now(),
        )
        self._write_results_by_idempotency_key[request.idempotency_key] = result
        self._accounts_by_id[account.id] = replace(account, last_verified_at=utc_now())
        return result
