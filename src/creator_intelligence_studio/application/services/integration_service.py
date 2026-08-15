"""Provider-neutral integration service boundary."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.domain.integrations import (
    INTEGRATION_CONTRACT_VERSION,
    ExternalContentResource,
    IntegrationAccount,
    IntegrationAccountLinkRequest,
    IntegrationAccountStatus,
    IntegrationCapability,
    IntegrationConnectorDefinition,
    IntegrationConnectorSummary,
    IntegrationErrorCategory,
    IntegrationErrorDetails,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationReadRequest,
    IntegrationReadResult,
    IntegrationWriteRequest,
    IntegrationWriteResult,
)
from creator_intelligence_studio.infrastructure.integrations import IntegrationRegistry, build_default_integration_registry
from creator_intelligence_studio.shared.dates import utc_now


@dataclass(frozen=True, slots=True)
class IntegrationServiceSummary:
    integration_contract_version: str
    registered_connector_count: int
    registered_connector_ids: tuple[str, ...]
    connector_summaries: tuple[IntegrationConnectorSummary, ...]
    generated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "integration_contract_version": self.integration_contract_version,
            "registered_connector_count": self.registered_connector_count,
            "registered_connector_ids": list(self.registered_connector_ids),
            "connector_summaries": [summary.to_dict() for summary in self.connector_summaries],
            "generated_at": self.generated_at.isoformat(),
        }


class IntegrationService:
    """Application boundary for offline-safe integration operations."""

    def __init__(
        self,
        *,
        registry: IntegrationRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.registry = registry or build_default_integration_registry()
        self.logger = logger or logging.getLogger("creator_intelligence_studio.integrations")

    def list_connectors(self) -> tuple[IntegrationConnectorDefinition, ...]:
        return self.registry.list_definitions()

    def list_accounts(self, creator_id: str) -> tuple[IntegrationAccount, ...]:
        accounts: list[IntegrationAccount] = []
        for connector in self.registry.list_connectors():
            accounts.extend(connector.list_accounts(creator_id))
        return tuple(sorted(accounts, key=lambda item: (item.connector_id, item.display_name.casefold(), item.external_account_id)))

    def get_account(self, *, creator_id: str, account_id: str) -> IntegrationAccount | None:
        account = self._get_account_any(account_id)
        if account is None or account.creator_id != creator_id:
            return None
        return account

    def _get_account_any(self, account_id: str) -> IntegrationAccount | None:
        for connector in self.registry.list_connectors():
            account = connector.get_account(account_id)
            if account is not None:
                return account
        return None

    def list_capabilities(self, connector_id: str) -> tuple[IntegrationCapability, ...]:
        connector = self.registry.get(connector_id)
        if connector is None:
            return ()
        definition = connector.definition
        return definition.capabilities

    def get_health(self, *, creator_id: str | None = None, account_id: str | None = None) -> IntegrationHealth:
        if account_id is not None:
            account = self._get_account_any(account_id)
            if account is None:
                return IntegrationHealth(
                    connector_id="unknown",
                    connector_available=False,
                    account_authenticated=False,
                    permissions_valid=False,
                    last_error_category=IntegrationErrorCategory.RESOURCE_NOT_FOUND,
                    last_error_message="account not found",
                    status=IntegrationHealthStatus.UNKNOWN,
                    checked_at=utc_now(),
                )
            if creator_id is not None and account.creator_id != creator_id:
                return IntegrationHealth(
                    connector_id=account.connector_id,
                    connector_available=True,
                    account_authenticated=False,
                    permissions_valid=False,
                    last_error_category=IntegrationErrorCategory.PERMISSION_DENIED,
                    last_error_message="creator does not own the account",
                    status=IntegrationHealthStatus.UNKNOWN,
                    checked_at=utc_now(),
                )
            connector = self.registry.get(account.connector_id)
            if connector is None:
                return IntegrationHealth(
                    connector_id=account.connector_id,
                    connector_available=False,
                    account_authenticated=False,
                    permissions_valid=False,
                    last_error_category=IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                    last_error_message="connector not registered",
                    status=IntegrationHealthStatus.UNAVAILABLE,
                    checked_at=utc_now(),
                )
            return connector.get_health(creator_id=creator_id or account.creator_id, account_id=account.id)

        connector_health: list[IntegrationHealth] = []
        for connector in self.registry.list_connectors():
            connector_health.append(connector.get_health(creator_id=creator_id, account_id=None))
        if not connector_health:
            return IntegrationHealth(
                connector_id="none",
                connector_available=False,
                account_authenticated=False,
                permissions_valid=False,
                status=IntegrationHealthStatus.UNKNOWN,
                checked_at=utc_now(),
            )
        if any(health.status == IntegrationHealthStatus.UNAVAILABLE for health in connector_health):
            return IntegrationHealth(
                connector_id=connector_health[0].connector_id,
                connector_available=False,
                account_authenticated=any(health.account_authenticated for health in connector_health),
                permissions_valid=any(health.permissions_valid for health in connector_health),
                rate_limit_state=next((health.rate_limit_state for health in connector_health if health.rate_limit_state and health.rate_limit_state.limited), None),
                last_success_at=max((health.last_success_at for health in connector_health if health.last_success_at is not None), default=None),
                last_error_category=IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                last_error_message="one or more connectors unavailable",
                status=IntegrationHealthStatus.DEGRADED,
                checked_at=utc_now(),
            )
        return IntegrationHealth(
            connector_id=connector_health[0].connector_id,
            connector_available=True,
            account_authenticated=any(health.account_authenticated for health in connector_health),
            permissions_valid=any(health.permissions_valid for health in connector_health),
            rate_limit_state=next((health.rate_limit_state for health in connector_health if health.rate_limit_state and health.rate_limit_state.limited), None),
            last_success_at=max((health.last_success_at for health in connector_health if health.last_success_at is not None), default=None),
            status=IntegrationHealthStatus.HEALTHY if all(health.status == IntegrationHealthStatus.HEALTHY for health in connector_health) else IntegrationHealthStatus.DEGRADED,
            checked_at=utc_now(),
        )

    def link_account(self, request: IntegrationAccountLinkRequest) -> IntegrationAccount:
        connector = self.registry.get(request.connector_id)
        if connector is None:
            raise ValueError(f"Unknown connector id: {request.connector_id}")
        return connector.link_account(request)

    def unlink_account(self, *, creator_id: str, account_id: str) -> bool:
        account = self._get_account_any(account_id)
        if account is None or account.creator_id != creator_id:
            return False
        connector = self.registry.get(account.connector_id)
        if connector is None:
            return False
        return connector.unlink_account(creator_id=creator_id, account_id=account_id)

    def read(self, request: IntegrationReadRequest) -> IntegrationReadResult:
        connector = self.registry.get(request.connector_id)
        if connector is None:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=request.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=IntegrationErrorDetails(
                    category=IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                    message="connector not registered",
                    retryable=False,
                    safe_detail="connector_missing",
                ),
                timestamp=utc_now(),
            )
        try:
            return connector.read(request)
        except Exception:
            return IntegrationReadResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=request.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                error=IntegrationErrorDetails(
                    category=IntegrationErrorCategory.PROVIDER_ERROR,
                    message="connector read failed",
                    retryable=False,
                    safe_detail="connector_exception",
                ),
                timestamp=utc_now(),
            )

    def write(self, request: IntegrationWriteRequest) -> IntegrationWriteResult:
        connector = self.registry.get(request.connector_id)
        if connector is None:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=request.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="provider_unavailable",
                error=IntegrationErrorDetails(
                    category=IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                    message="connector not registered",
                    retryable=False,
                    safe_detail="connector_missing",
                ),
                timestamp=utc_now(),
            )
        try:
            return connector.write(request)
        except Exception:
            return IntegrationWriteResult(
                request_id=request.request_id,
                creator_id=request.creator_id,
                connector_id=request.connector_id,
                account_id=request.account_id,
                capability=request.capability,
                success=False,
                status="provider_error",
                error=IntegrationErrorDetails(
                    category=IntegrationErrorCategory.PROVIDER_ERROR,
                    message="connector write failed",
                    retryable=False,
                    safe_detail="connector_exception",
                ),
                timestamp=utc_now(),
            )

    def summary(self) -> IntegrationServiceSummary:
        connectors = self.registry.list_connectors()
        connector_summaries: list[IntegrationConnectorSummary] = []
        for connector in connectors:
            try:
                health = connector.get_health()
                account_count = len(connector.list_accounts(""))
            except Exception:
                health = IntegrationHealth(
                    connector_id=connector.definition.connector_id,
                    connector_available=False,
                    account_authenticated=False,
                    permissions_valid=False,
                    last_error_category=IntegrationErrorCategory.PROVIDER_ERROR,
                    last_error_message="connector summary unavailable",
                    status=IntegrationHealthStatus.UNKNOWN,
                    checked_at=utc_now(),
                )
                account_count = 0
            connector_summaries.append(
                IntegrationConnectorSummary(
                    definition=connector.definition,
                    health=health,
                    account_count=account_count,
                )
            )
        return IntegrationServiceSummary(
            integration_contract_version=INTEGRATION_CONTRACT_VERSION,
            registered_connector_count=len(connector_summaries),
            registered_connector_ids=tuple(summary.definition.connector_id for summary in connector_summaries),
            connector_summaries=tuple(connector_summaries),
            generated_at=utc_now(),
        )

    def diagnostics(self) -> dict[str, object]:
        summary = self.summary()
        return summary.to_dict()


def build_integration_service(
    *,
    registry: IntegrationRegistry | None = None,
    logger: logging.Logger | None = None,
) -> IntegrationService:
    return IntegrationService(registry=registry, logger=logger)
