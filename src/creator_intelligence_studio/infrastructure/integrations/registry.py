"""Registry and discovery for provider-neutral integration connectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from creator_intelligence_studio.domain.integrations import INTEGRATION_CONTRACT_VERSION, IntegrationConnectorDefinition, IntegrationConnectorSummary
from creator_intelligence_studio.shared.dates import utc_now

from .fake_connector import FakeIntegrationConnector
from .local_connector import LocalNoAuthIntegrationConnector


class IntegrationRegistry:
    def __init__(self, connectors: Iterable[object] | None = None) -> None:
        self._connectors: dict[str, object] = {}
        for connector in connectors or ():
            self.register(connector)

    def register(self, connector: object) -> None:
        definition = getattr(connector, "definition", None)
        connector_id = getattr(definition, "connector_id", None)
        if not connector_id:
            raise ValueError("connector must expose a definition with connector_id")
        if connector_id in self._connectors:
            raise ValueError(f"Duplicate connector id: {connector_id}")
        self._connectors[connector_id] = connector

    def get(self, connector_id: str) -> object | None:
        return self._connectors.get(connector_id)

    def list_connectors(self) -> tuple[object, ...]:
        return tuple(self._connectors[key] for key in sorted(self._connectors))

    def list_definitions(self) -> tuple[IntegrationConnectorDefinition, ...]:
        return tuple(getattr(connector, "definition") for connector in self.list_connectors())

    def summary(self) -> dict[str, object]:
        connector_summaries: list[IntegrationConnectorSummary] = []
        for connector in self.list_connectors():
            definition = connector.definition
            health = connector.get_health()
            account_count = len(connector.list_accounts("")) if hasattr(connector, "list_accounts") else 0
            connector_summaries.append(
                IntegrationConnectorSummary(
                    definition=definition,
                    health=health,
                    account_count=account_count,
                )
            )
        return {
            "integration_contract_version": INTEGRATION_CONTRACT_VERSION,
            "registered_connector_count": len(connector_summaries),
            "registered_connector_ids": [summary.definition.connector_id for summary in connector_summaries],
            "connectors": [summary.to_dict() for summary in connector_summaries],
            "generated_at": utc_now().isoformat(),
        }


def build_default_integration_registry() -> IntegrationRegistry:
    return IntegrationRegistry(
        connectors=(
            FakeIntegrationConnector(),
            LocalNoAuthIntegrationConnector(),
        )
    )


def build_default_integration_registry_summary() -> dict[str, object]:
    return build_default_integration_registry().summary()
