"""Domain contract package for provider-neutral integrations."""

from __future__ import annotations

from .contracts import (
    INTEGRATION_CONTRACT_VERSION,
    ExternalContentResource,
    IntegrationAccount,
    IntegrationAccountLinkRequest,
    IntegrationAccountStatus,
    IntegrationAnalyticsMetric,
    IntegrationAuthType,
    IntegrationCapability,
    IntegrationConnectorDefinition,
    IntegrationConnectorSummary,
    IntegrationErrorCategory,
    IntegrationErrorDetails,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationRateLimitState,
    IntegrationReadRequest,
    IntegrationReadResult,
    IntegrationSyncMode,
    IntegrationUserStatus,
    IntegrationWriteRequest,
    IntegrationWriteResult,
)
from .protocols import IntegrationConnector

__all__ = [
    "INTEGRATION_CONTRACT_VERSION",
    "ExternalContentResource",
    "IntegrationAccount",
    "IntegrationAccountLinkRequest",
    "IntegrationAccountStatus",
    "IntegrationAnalyticsMetric",
    "IntegrationAuthType",
    "IntegrationCapability",
    "IntegrationConnector",
    "IntegrationConnectorDefinition",
    "IntegrationConnectorSummary",
    "IntegrationErrorCategory",
    "IntegrationErrorDetails",
    "IntegrationHealth",
    "IntegrationHealthStatus",
    "IntegrationRateLimitState",
    "IntegrationReadRequest",
    "IntegrationReadResult",
    "IntegrationSyncMode",
    "IntegrationUserStatus",
    "IntegrationWriteRequest",
    "IntegrationWriteResult",
]
