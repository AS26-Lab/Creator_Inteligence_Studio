"""Tipos de sincronizacion para TikTok."""

from __future__ import annotations

from enum import Enum


class TikTokSyncStatus(str, Enum):
    QUEUED = "queued"
    AUTHENTICATING = "authenticating"
    VERIFYING_PROFILE = "verifying_profile"
    SYNCING_PROFILE = "syncing_profile"
    SYNCING_VIDEOS = "syncing_videos"
    REFRESHING_VIDEOS = "refreshing_videos"
    IMPORTING_METRICS = "importing_metrics"
    LINKING_CONTENT = "linking_content"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TikTokSyncType(str, Enum):
    CONNECTION_VERIFY = "connection_verify"
    PROFILE_METADATA = "profile_metadata"
    PROFILE_STATS = "profile_stats"
    VIDEO_CATALOG = "video_catalog"
    VIDEO_METADATA = "video_metadata"
    PUBLIC_METRICS = "public_metrics"
    INCREMENTAL_SYNC = "incremental_sync"
    FULL_RESYNC = "full_resync"
    REPAIR_SYNC = "repair_sync"
    COVER_REFRESH = "cover_refresh"

