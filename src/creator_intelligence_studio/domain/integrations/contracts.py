"""Canonical provider-neutral integration contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

INTEGRATION_CONTRACT_VERSION = "integration-contract-v1"


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class IntegrationAuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    TOKEN = "token"
    LOCAL_NO_AUTH = "local_no_auth"


class IntegrationAccountStatus(str, Enum):
    NOT_LINKED = "not_linked"
    LINKING = "linking"
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PERMISSION_MISSING = "permission_missing"
    ERROR = "error"


class IntegrationHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class IntegrationErrorCategory(str, Enum):
    AUTHENTICATION_REQUIRED = "authentication_required"
    AUTHENTICATION_EXPIRED = "authentication_expired"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    NETWORK_UNAVAILABLE = "network_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_REQUEST = "invalid_request"
    RESOURCE_NOT_FOUND = "resource_not_found"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    CONFLICT = "conflict"
    PROVIDER_ERROR = "provider_error"


class IntegrationCapability(str, Enum):
    ACCOUNT_PROFILE_READ = "account_profile_read"
    CONTENT_LIST_READ = "content_list_read"
    CONTENT_METADATA_READ = "content_metadata_read"
    ANALYTICS_READ = "analytics_read"
    COMMENTS_READ = "comments_read"
    CONTENT_UPLOAD = "content_upload"
    CONTENT_PUBLISH = "content_publish"
    CONTENT_SCHEDULE = "content_schedule"
    CONTENT_UPDATE = "content_update"
    CONTENT_DELETE = "content_delete"


class IntegrationSyncMode(str, Enum):
    MANUAL_REFRESH = "manual_refresh"
    ON_DEMAND_READ = "on_demand_read"
    BACKGROUND_SYNC = "background_sync"


@dataclass(frozen=True, slots=True)
class IntegrationErrorDetails:
    category: IntegrationErrorCategory
    message: str
    provider_code: str | None = None
    provider_request_id: str | None = None
    retryable: bool = False
    safe_detail: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category.value,
            "message": self.message,
            "provider_code": self.provider_code,
            "provider_request_id": self.provider_request_id,
            "retryable": self.retryable,
            "safe_detail": self.safe_detail,
        }


@dataclass(frozen=True, slots=True)
class IntegrationRateLimitState:
    remaining: int | None = None
    retry_after_seconds: float | None = None
    reset_at: datetime | None = None
    provider_window: str | None = None
    limited: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "remaining": self.remaining,
            "retry_after_seconds": self.retry_after_seconds,
            "reset_at": _to_iso(self.reset_at),
            "provider_window": self.provider_window,
            "limited": self.limited,
        }


@dataclass(frozen=True, slots=True)
class IntegrationConnectorDefinition:
    connector_id: str
    provider: str
    display_name: str
    version: str
    authentication_type: IntegrationAuthType
    read_capabilities: tuple[IntegrationCapability, ...] = ()
    write_capabilities: tuple[IntegrationCapability, ...] = ()
    contract_version: str = INTEGRATION_CONTRACT_VERSION

    @property
    def capabilities(self) -> tuple[IntegrationCapability, ...]:
        return tuple(dict.fromkeys((*self.read_capabilities, *self.write_capabilities)))

    @property
    def supported_operations(self) -> tuple[str, ...]:
        operations: list[str] = ["read"] if self.read_capabilities else []
        if self.write_capabilities:
            operations.append("write")
        return tuple(operations)

    def to_dict(self) -> dict[str, object]:
        return {
            "connector_id": self.connector_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "version": self.version,
            "authentication_type": self.authentication_type.value,
            "read_capabilities": [capability.value for capability in self.read_capabilities],
            "write_capabilities": [capability.value for capability in self.write_capabilities],
            "capabilities": [capability.value for capability in self.capabilities],
            "supported_operations": list(self.supported_operations),
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class IntegrationAccount:
    id: str
    creator_id: str
    connector_id: str
    external_account_id: str
    display_name: str
    status: IntegrationAccountStatus
    linked_at: datetime
    last_verified_at: datetime | None = None
    granted_scopes: tuple[str, ...] = ()
    granted_capabilities: tuple[IntegrationCapability, ...] = ()
    credential_ref: str | None = None
    metadata_summary: dict[str, object] = field(default_factory=dict)
    auth_type: IntegrationAuthType = IntegrationAuthType.LOCAL_NO_AUTH

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "external_account_id": self.external_account_id,
            "display_name": self.display_name,
            "status": self.status.value,
            "linked_at": _to_iso(self.linked_at),
            "last_verified_at": _to_iso(self.last_verified_at),
            "granted_scopes": list(self.granted_scopes),
            "granted_capabilities": [capability.value for capability in self.granted_capabilities],
            "credential_ref": self.credential_ref,
            "metadata_summary": dict(self.metadata_summary),
            "auth_type": self.auth_type.value,
        }


@dataclass(frozen=True, slots=True)
class IntegrationHealth:
    connector_id: str
    connector_available: bool
    account_authenticated: bool
    permissions_valid: bool
    rate_limit_state: IntegrationRateLimitState | None = None
    last_success_at: datetime | None = None
    last_error_category: IntegrationErrorCategory | None = None
    last_error_message: str | None = None
    status: IntegrationHealthStatus = IntegrationHealthStatus.UNKNOWN
    checked_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "connector_id": self.connector_id,
            "connector_available": self.connector_available,
            "account_authenticated": self.account_authenticated,
            "permissions_valid": self.permissions_valid,
            "rate_limit_state": None if self.rate_limit_state is None else self.rate_limit_state.to_dict(),
            "last_success_at": _to_iso(self.last_success_at),
            "last_error_category": None if self.last_error_category is None else self.last_error_category.value,
            "last_error_message": self.last_error_message,
            "status": self.status.value,
            "checked_at": _to_iso(self.checked_at),
        }


@dataclass(frozen=True, slots=True)
class IntegrationConnectorSummary:
    definition: IntegrationConnectorDefinition
    health: IntegrationHealth
    account_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "definition": self.definition.to_dict(),
            "health": self.health.to_dict(),
            "account_count": self.account_count,
        }


@dataclass(frozen=True, slots=True)
class ExternalContentResource:
    connector_id: str
    external_id: str
    account_id: str
    resource_type: str
    title: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    url: str | None = None
    public_reference: str | None = None
    status: str | None = None
    provider_metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "connector_id": self.connector_id,
            "external_id": self.external_id,
            "account_id": self.account_id,
            "resource_type": self.resource_type,
            "title": self.title,
            "description": self.description,
            "published_at": _to_iso(self.published_at),
            "url": self.url,
            "public_reference": self.public_reference,
            "status": self.status,
            "provider_metadata": dict(self.provider_metadata),
        }


@dataclass(frozen=True, slots=True)
class IntegrationAnalyticsMetric:
    connector_id: str
    account_id: str
    external_resource_id: str | None
    metric_name: str
    value: float | int | None
    unit: str | None = None
    metric_period_start: datetime | None = None
    metric_period_end: datetime | None = None
    retrieved_at: datetime | None = None
    availability: str | None = None
    provider_metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "connector_id": self.connector_id,
            "account_id": self.account_id,
            "external_resource_id": self.external_resource_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "metric_period_start": _to_iso(self.metric_period_start),
            "metric_period_end": _to_iso(self.metric_period_end),
            "retrieved_at": _to_iso(self.retrieved_at),
            "availability": self.availability,
            "provider_metadata": dict(self.provider_metadata),
        }


@dataclass(frozen=True, slots=True)
class IntegrationAccountLinkRequest:
    creator_id: str
    connector_id: str
    external_account_id: str
    display_name: str
    credential_ref: str | None = None
    granted_scopes: tuple[str, ...] = ()
    granted_capabilities: tuple[IntegrationCapability, ...] = ()
    auth_type: IntegrationAuthType = IntegrationAuthType.LOCAL_NO_AUTH
    metadata_summary: dict[str, object] = field(default_factory=dict)
    linked_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "external_account_id": self.external_account_id,
            "display_name": self.display_name,
            "credential_ref": self.credential_ref,
            "granted_scopes": list(self.granted_scopes),
            "granted_capabilities": [capability.value for capability in self.granted_capabilities],
            "auth_type": self.auth_type.value,
            "metadata_summary": dict(self.metadata_summary),
            "linked_at": _to_iso(self.linked_at),
        }


@dataclass(frozen=True, slots=True)
class IntegrationReadRequest:
    request_id: str
    creator_id: str
    connector_id: str
    account_id: str
    capability: IntegrationCapability
    parameters: dict[str, object] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    timestamp: datetime | None = None
    sync_mode: IntegrationSyncMode = IntegrationSyncMode.ON_DEMAND_READ

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "account_id": self.account_id,
            "capability": self.capability.value,
            "parameters": dict(self.parameters),
            "timeout_seconds": self.timeout_seconds,
            "timestamp": _to_iso(self.timestamp),
            "sync_mode": self.sync_mode.value,
        }


@dataclass(frozen=True, slots=True)
class IntegrationReadResult:
    request_id: str
    creator_id: str
    connector_id: str
    account_id: str
    capability: IntegrationCapability
    success: bool
    error: IntegrationErrorDetails | None = None
    resources: tuple[ExternalContentResource, ...] = ()
    analytics: tuple[IntegrationAnalyticsMetric, ...] = ()
    next_page_token: str | None = None
    rate_limit_state: IntegrationRateLimitState | None = None
    health: IntegrationHealth | None = None
    provider_request_id: str | None = None
    provider_metadata: dict[str, object] = field(default_factory=dict)
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "account_id": self.account_id,
            "capability": self.capability.value,
            "success": self.success,
            "error": None if self.error is None else self.error.to_dict(),
            "resources": [item.to_dict() for item in self.resources],
            "analytics": [item.to_dict() for item in self.analytics],
            "next_page_token": self.next_page_token,
            "rate_limit_state": None if self.rate_limit_state is None else self.rate_limit_state.to_dict(),
            "health": None if self.health is None else self.health.to_dict(),
            "provider_request_id": self.provider_request_id,
            "provider_metadata": dict(self.provider_metadata),
            "timestamp": _to_iso(self.timestamp),
        }


@dataclass(frozen=True, slots=True)
class IntegrationWriteRequest:
    request_id: str
    creator_id: str
    connector_id: str
    account_id: str
    capability: IntegrationCapability
    payload: dict[str, object] = field(default_factory=dict)
    approved_by_user: bool = False
    approval_reference: str | None = None
    idempotency_key: str | None = None
    timeout_seconds: float = 30.0
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "account_id": self.account_id,
            "capability": self.capability.value,
            "payload": dict(self.payload),
            "approved_by_user": self.approved_by_user,
            "approval_reference": self.approval_reference,
            "idempotency_key": self.idempotency_key,
            "timeout_seconds": self.timeout_seconds,
            "timestamp": _to_iso(self.timestamp),
        }


@dataclass(frozen=True, slots=True)
class IntegrationWriteResult:
    request_id: str
    creator_id: str
    connector_id: str
    account_id: str
    capability: IntegrationCapability
    success: bool
    status: str
    error: IntegrationErrorDetails | None = None
    resource: ExternalContentResource | None = None
    idempotency_key: str | None = None
    approval_reference: str | None = None
    provider_request_id: str | None = None
    provider_metadata: dict[str, object] = field(default_factory=dict)
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "creator_id": self.creator_id,
            "connector_id": self.connector_id,
            "account_id": self.account_id,
            "capability": self.capability.value,
            "success": self.success,
            "status": self.status,
            "error": None if self.error is None else self.error.to_dict(),
            "resource": None if self.resource is None else self.resource.to_dict(),
            "idempotency_key": self.idempotency_key,
            "approval_reference": self.approval_reference,
            "provider_request_id": self.provider_request_id,
            "provider_metadata": dict(self.provider_metadata),
            "timestamp": _to_iso(self.timestamp),
        }
