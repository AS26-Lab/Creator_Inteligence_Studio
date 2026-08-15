"""A minimal no-auth local connector used to prove registry multi-connector support."""

from __future__ import annotations

from creator_intelligence_studio.domain.integrations import (
    ExternalContentResource,
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
    IntegrationReadRequest,
    IntegrationReadResult,
    IntegrationWriteRequest,
    IntegrationWriteResult,
)
from creator_intelligence_studio.shared.dates import utc_now


class LocalNoAuthIntegrationConnector:
    def __init__(self, *, connector_id: str = "local.connector") -> None:
        self._definition = IntegrationConnectorDefinition(
            connector_id=connector_id,
            provider="local",
            display_name="Local No-Auth Connector",
            version="local-1",
            authentication_type=IntegrationAuthType.LOCAL_NO_AUTH,
            read_capabilities=(),
            write_capabilities=(),
        )

    @property
    def definition(self) -> IntegrationConnectorDefinition:
        return self._definition

    def list_accounts(self, creator_id: str) -> tuple[IntegrationAccount, ...]:
        return ()

    def link_account(self, request: IntegrationAccountLinkRequest) -> IntegrationAccount:
        raise ValueError("local connector does not support linking accounts")

    def unlink_account(self, *, creator_id: str, account_id: str) -> bool:
        return False

    def get_account(self, account_id: str) -> IntegrationAccount | None:
        return None

    def get_health(self, *, creator_id: str | None = None, account_id: str | None = None) -> IntegrationHealth:
        return IntegrationHealth(
            connector_id=self.definition.connector_id,
            connector_available=True,
            account_authenticated=False,
            permissions_valid=False,
            status=IntegrationHealthStatus.HEALTHY,
            checked_at=utc_now(),
        )

    def read(self, request: IntegrationReadRequest) -> IntegrationReadResult:
        return IntegrationReadResult(
            request_id=request.request_id,
            creator_id=request.creator_id,
            connector_id=self.definition.connector_id,
            account_id=request.account_id,
            capability=request.capability,
            success=False,
            error=IntegrationErrorDetails(
                category=IntegrationErrorCategory.UNSUPPORTED_OPERATION,
                message="local connector does not expose read operations",
                retryable=False,
                safe_detail="local_no_auth",
            ),
            provider_metadata={"connector_version": self.definition.version},
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
            error=IntegrationErrorDetails(
                category=IntegrationErrorCategory.UNSUPPORTED_OPERATION,
                message="local connector does not expose write operations",
                retryable=False,
                safe_detail="local_no_auth",
            ),
            provider_metadata={"connector_version": self.definition.version},
            timestamp=utc_now(),
        )
