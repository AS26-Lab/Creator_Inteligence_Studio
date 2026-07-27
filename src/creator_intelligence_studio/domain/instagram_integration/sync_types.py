"""Tipos de sincronizacion para Instagram."""

from __future__ import annotations

from enum import Enum


class InstagramSyncStatus(str, Enum):
    QUEUED = "queued"
    AUTHENTICATING = "authenticating"
    VERIFYING_ACCOUNT = "verifying_account"
    SYNCING_PROFILE = "syncing_profile"
    SYNCING_MEDIA = "syncing_media"
    SYNCING_CHILDREN = "syncing_children"
    SYNCING_ACCOUNT_INSIGHTS = "syncing_account_insights"
    SYNCING_MEDIA_INSIGHTS = "syncing_media_insights"
    LINKING_CONTENT = "linking_content"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstagramSyncType(str, Enum):
    CONNECTION_VERIFY = "connection_verify"
    ACCOUNT_METADATA = "account_metadata"
    MEDIA_CATALOG = "media_catalog"
    MEDIA_METADATA = "media_metadata"
    CAROUSEL_CHILDREN = "carousel_children"
    ACCOUNT_INSIGHTS = "account_insights"
    MEDIA_INSIGHTS = "media_insights"
    INCREMENTAL_SYNC = "incremental_sync"
    FULL_RESYNC = "full_resync"
    REPAIR_SYNC = "repair_sync"

