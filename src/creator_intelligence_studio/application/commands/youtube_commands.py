"""Comandos de aplicacion para la integracion YouTube de solo lectura."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ListYouTubeConnectionsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ConnectYouTubeCommand:
    creator_id: str
    client_id: str
    client_secret: str | None = None
    authorization_code: str | None = None
    redirect_uri: str | None = None
    scopes_json: str | None = None
    google_account_identifier: str | None = None


@dataclass(frozen=True, slots=True)
class ShowYouTubeConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class VerifyYouTubeConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class DisconnectYouTubeConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class RevokeYouTubeConnectionCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ListYouTubeChannelsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class SelectYouTubeChannelCommand:
    channel_id: str


@dataclass(frozen=True, slots=True)
class ShowYouTubeChannelCommand:
    channel_id: str


@dataclass(frozen=True, slots=True)
class SyncYouTubeChannelCommand:
    channel_id: str
    sync_type: str = "incremental_sync"
    cursor: str | None = None
    full_resync: bool = False
    include_analytics: bool = True
    include_thumbnails: bool = False
    metrics_json: str | None = None


@dataclass(frozen=True, slots=True)
class ResumeYouTubeSyncCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class SyncYouTubeHistoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowYouTubeSyncRunCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListYouTubeVideosCommand:
    channel_id: str


@dataclass(frozen=True, slots=True)
class ShowYouTubeVideoCommand:
    remote_video_id: str


@dataclass(frozen=True, slots=True)
class LinkYouTubeContentCommand:
    remote_video_id: str
    publication_id: str | None = None
    video_asset_id: str | None = None
    link_method: str = "manual"
    confidence_level: str = "low"
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class UnlinkYouTubeContentCommand:
    remote_video_id: str


@dataclass(frozen=True, slots=True)
class YouTubeQuotaCommand:
    connection_id: str


@dataclass(frozen=True, slots=True)
class ExportYouTubeSyncReportCommand:
    run_id: str
    format: str
    output: Path | None = None
