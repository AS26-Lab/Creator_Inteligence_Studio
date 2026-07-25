"""Tipos cerrados de sincronizacion de YouTube."""

from __future__ import annotations

from enum import Enum


class YouTubeSyncStatus(str, Enum):
    QUEUED = "queued"
    AUTHENTICATING = "authenticating"
    LISTING_CHANNELS = "listing_channels"
    SYNCING_CONTENT = "syncing_content"
    SYNCING_METADATA = "syncing_metadata"
    SYNCING_ANALYTICS = "syncing_analytics"
    LINKING_CONTENT = "linking_content"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class YouTubeSyncType(str, Enum):
    CONNECTION_VERIFY = "connection_verify"
    CHANNEL_METADATA = "channel_metadata"
    CONTENT_CATALOG = "content_catalog"
    VIDEO_METADATA = "video_metadata"
    THUMBNAILS_METADATA = "thumbnails_metadata"
    CHANNEL_ANALYTICS = "channel_analytics"
    VIDEO_ANALYTICS = "video_analytics"
    INCREMENTAL_SYNC = "incremental_sync"
    FULL_RESYNC = "full_resync"
    REPAIR_SYNC = "repair_sync"

