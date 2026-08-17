"""Registry and discovery for provider-neutral integration connectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from creator_intelligence_studio.domain.integrations import INTEGRATION_CONTRACT_VERSION, IntegrationConnectorDefinition, IntegrationConnectorSummary
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.youtube.oauth_config import (
    resolve_youtube_oauth_client_id,
    resolve_youtube_oauth_app_config,
)
from creator_intelligence_studio.shared.dates import utc_now

from .fake_connector import FakeIntegrationConnector
from .local_connector import LocalNoAuthIntegrationConnector
from .youtube_connector import build_default_youtube_connector


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


def build_default_integration_registry(
    *,
    settings: AppSettings | None = None,
    paths: object | None = None,
    database: SQLiteDatabase | None = None,
) -> IntegrationRegistry:
    data_root: Path | None = None
    environment = getattr(settings, "environment", None)
    if paths is not None:
        data_root = getattr(paths, "data_directory", None)
    elif settings is not None:
        try:
            from creator_intelligence_studio.shared.paths import ProjectPaths

            if hasattr(settings, "application_name"):
                project_root = Path.cwd()
                data_root = ProjectPaths.from_settings(project_root, settings).data_directory
        except Exception:
            data_root = None
    project_root = getattr(paths, "project_root", None) if paths is not None else None
    config_path = (project_root / "config" / "default.json") if project_root is not None else None
    resolved_client_id = resolve_youtube_oauth_client_id(configured_client_id=getattr(settings, "youtube_oauth_client_id", None))
    if not resolved_client_id:
        resolved_client_id, _ = resolve_youtube_oauth_app_config(config_path)
    _, resolved_client_secret = resolve_youtube_oauth_app_config(config_path)
    if not resolved_client_secret:
        configured_secret = getattr(settings, "youtube_oauth_client_secret", None)
        resolved_client_secret = configured_secret.strip() if isinstance(configured_secret, str) and configured_secret.strip() else None
    return IntegrationRegistry(
        connectors=(
            FakeIntegrationConnector(),
            LocalNoAuthIntegrationConnector(),
            build_default_youtube_connector(
                data_root=(data_root / "integrations" / "youtube") if data_root is not None else None,
                environment=environment,
                client_id=resolved_client_id,
                client_secret=resolved_client_secret,
            ),
        )
    )


def build_default_integration_registry_summary(
    *,
    settings: AppSettings | None = None,
    paths: object | None = None,
    database: SQLiteDatabase | None = None,
) -> dict[str, object]:
    return build_default_integration_registry(settings=settings, paths=paths, database=database).summary()
