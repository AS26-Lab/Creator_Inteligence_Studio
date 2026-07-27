"""Comandos de aplicacion para la integracion TikTok de solo lectura."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokLinkMethod


@dataclass(frozen=True, slots=True)
class ListTikTokConnectionsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ConnectTikTokCommand:
    creator_id: str
    client_id: str
    client_secret: str | None = None
    authorization_code: str | None = None
    redirect_uri: str | None = None
    scopes_json: str | None = None
    account_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class ShowTikTokConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class VerifyTikTokConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class DisconnectTikTokConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class RevokeTikTokConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ListTikTokProfilesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class SelectTikTokProfileCommand:
    profile_id: str


@dataclass(frozen=True, slots=True)
class ShowTikTokProfileCommand:
    profile_id: str


@dataclass(frozen=True, slots=True)
class SyncTikTokProfileCommand:
    profile_id: str
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class SyncTikTokVideosCommand:
    profile_id: str
    cursor: str | None = None
    max_count: int = 20


@dataclass(frozen=True, slots=True)
class SyncTikTokIncrementalCommand:
    profile_id: str
    cursor: str | None = None
    max_count: int = 20


@dataclass(frozen=True, slots=True)
class SyncTikTokResumeCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class SyncTikTokRepairCommand:
    profile_id: str


@dataclass(frozen=True, slots=True)
class SyncTikTokHistoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowTikTokSyncRunCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListTikTokVideosCommand:
    profile_id: str


@dataclass(frozen=True, slots=True)
class ShowTikTokVideoCommand:
    remote_video_id: str


@dataclass(frozen=True, slots=True)
class RefreshTikTokVideoCommand:
    remote_video_id: str


@dataclass(frozen=True, slots=True)
class LinkTikTokContentCommand:
    remote_video_id: str
    publication_id: str | None = None
    video_asset_id: str | None = None
    packaging_asset_id: str | None = None
    link_method: TikTokLinkMethod = TikTokLinkMethod.MANUAL
    confidence_level: str = "low"
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class UnlinkTikTokContentCommand:
    remote_video_id: str


@dataclass(frozen=True, slots=True)
class TikTokRateLimitCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ExportTikTokSyncReportCommand:
    run_id: str
    format: str
    output: Path | None = None

