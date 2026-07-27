"""Comandos de aplicacion para la integracion de Instagram."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider, InstagramLinkMethod
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod
from creator_intelligence_studio.domain.instagram_integration.sync_types import InstagramSyncType


@dataclass(frozen=True, slots=True)
class ListInstagramConnectionsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ConnectInstagramCommand:
    creator_id: str
    client_id: str
    client_secret: str | None = None
    authorization_code: str | None = None
    redirect_uri: str | None = None
    scopes_json: str | None = None
    provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN
    account_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class ShowInstagramConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class VerifyInstagramConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class DisconnectInstagramConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class RevokeInstagramConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ListInstagramAccountsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class SelectInstagramAccountCommand:
    account_id: str


@dataclass(frozen=True, slots=True)
class ShowInstagramAccountCommand:
    account_id: str


@dataclass(frozen=True, slots=True)
class SyncInstagramAccountCommand:
    account_id: str
    cursor: str | None = None
    full_resync: bool = False


@dataclass(frozen=True, slots=True)
class SyncInstagramMediaCommand:
    account_id: str
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class SyncInstagramInsightsCommand:
    account_id: str
    remote_media_id: str | None = None
    period: InstagramInsightPeriod = InstagramInsightPeriod.DAYS_28


@dataclass(frozen=True, slots=True)
class SyncInstagramIncrementalCommand:
    account_id: str
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ResumeInstagramSyncCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class SyncInstagramRepairCommand:
    account_id: str


@dataclass(frozen=True, slots=True)
class SyncInstagramHistoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowInstagramSyncRunCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListInstagramMediaCommand:
    account_id: str


@dataclass(frozen=True, slots=True)
class ShowInstagramMediaCommand:
    remote_media_id: str


@dataclass(frozen=True, slots=True)
class LinkInstagramContentCommand:
    remote_media_id: str
    publication_id: str | None = None
    video_asset_id: str | None = None
    packaging_asset_id: str | None = None
    link_method: InstagramLinkMethod = InstagramLinkMethod.MANUAL
    confidence_level: str = "low"
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class UnlinkInstagramContentCommand:
    remote_media_id: str


@dataclass(frozen=True, slots=True)
class InstagramRateLimitCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ExportInstagramSyncReportCommand:
    run_id: str
    format: str
    output: Path | None = None

