"""Protocols for provider-neutral integrations."""

from __future__ import annotations

from typing import Protocol

from .contracts import (
    IntegrationAccount,
    IntegrationAccountLinkRequest,
    IntegrationConnectorDefinition,
    IntegrationHealth,
    IntegrationReadRequest,
    IntegrationReadResult,
    IntegrationWriteRequest,
    IntegrationWriteResult,
)


class IntegrationConnector(Protocol):
    @property
    def definition(self) -> IntegrationConnectorDefinition: ...

    def list_accounts(self, creator_id: str) -> tuple[IntegrationAccount, ...]: ...

    def link_account(self, request: IntegrationAccountLinkRequest) -> IntegrationAccount: ...

    def unlink_account(self, *, creator_id: str, account_id: str) -> bool: ...

    def get_account(self, account_id: str) -> IntegrationAccount | None: ...

    def get_health(self, *, creator_id: str | None = None, account_id: str | None = None) -> IntegrationHealth: ...

    def read(self, request: IntegrationReadRequest) -> IntegrationReadResult: ...

    def write(self, request: IntegrationWriteRequest) -> IntegrationWriteResult: ...
