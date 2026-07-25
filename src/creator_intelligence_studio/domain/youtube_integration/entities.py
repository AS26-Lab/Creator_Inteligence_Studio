"""Entidades persistidas de la integracion YouTube."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .connection_types import YouTubeConnectionStatus, YouTubeLinkMethod, YouTubeRemoteContentType
from .sync_types import YouTubeSyncStatus, YouTubeSyncType


@dataclass(frozen=True, slots=True)
class YouTubeConnection:
    id: str
    creator_id: str
    google_account_identifier: str | None
    status: YouTubeConnectionStatus
    granted_scopes_json: str
    credential_reference: str
    connected_at: datetime
    last_verified_at: datetime | None
    disconnected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "google_account_identifier": self.google_account_identifier,
            "status": self.status.value,
            "granted_scopes_json": self.granted_scopes_json,
            "credential_reference": self.credential_reference,
            "connected_at": to_iso_z(self.connected_at),
            "last_verified_at": to_iso_z(self.last_verified_at),
            "disconnected_at": to_iso_z(self.disconnected_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeChannel:
    id: str
    creator_id: str
    connection_id: str
    youtube_channel_id: str
    title: str
    description: str | None
    custom_url: str | None
    country: str | None
    published_at: datetime | None
    thumbnail_url: str | None
    subscriber_count: int | None
    video_count: int | None
    view_count: int | None
    hidden_subscriber_count: bool
    selected_for_sync: bool
    last_synced_at: datetime | None
    remote_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "connection_id": self.connection_id,
            "youtube_channel_id": self.youtube_channel_id,
            "title": self.title,
            "description": self.description,
            "custom_url": self.custom_url,
            "country": self.country,
            "published_at": to_iso_z(self.published_at),
            "thumbnail_url": self.thumbnail_url,
            "subscriber_count": self.subscriber_count,
            "video_count": self.video_count,
            "view_count": self.view_count,
            "hidden_subscriber_count": 1 if self.hidden_subscriber_count else 0,
            "selected_for_sync": 1 if self.selected_for_sync else 0,
            "last_synced_at": to_iso_z(self.last_synced_at),
            "remote_fingerprint": self.remote_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeRemoteVideo:
    id: str
    creator_id: str
    channel_id: str
    youtube_video_id: str
    publication_id: str | None
    video_asset_id: str | None
    content_type: YouTubeRemoteContentType
    title: str
    description: str | None
    published_at: datetime
    duration_seconds: float | None
    privacy_status: str | None
    live_broadcast_content: str | None
    default_language: str | None
    default_audio_language: str | None
    category_id: str | None
    tags_json: str
    thumbnail_metadata_json: str
    remote_fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "channel_id": self.channel_id,
            "youtube_video_id": self.youtube_video_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "content_type": self.content_type.value,
            "title": self.title,
            "description": self.description,
            "published_at": to_iso_z(self.published_at),
            "duration_seconds": self.duration_seconds,
            "privacy_status": self.privacy_status,
            "live_broadcast_content": self.live_broadcast_content,
            "default_language": self.default_language,
            "default_audio_language": self.default_audio_language,
            "category_id": self.category_id,
            "tags_json": self.tags_json,
            "thumbnail_metadata_json": self.thumbnail_metadata_json,
            "remote_fingerprint": self.remote_fingerprint,
            "first_seen_at": to_iso_z(self.first_seen_at),
            "last_seen_at": to_iso_z(self.last_seen_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeVideoThumbnail:
    id: str
    remote_video_id: str
    thumbnail_type: str
    remote_url: str
    width: int | None
    height: int | None
    local_cache_path: str | None
    remote_fingerprint: str
    imported_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_video_id": self.remote_video_id,
            "thumbnail_type": self.thumbnail_type,
            "remote_url": self.remote_url,
            "width": self.width,
            "height": self.height,
            "local_cache_path": self.local_cache_path,
            "remote_fingerprint": self.remote_fingerprint,
            "imported_at": to_iso_z(self.imported_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeSyncRun:
    id: str
    creator_id: str
    connection_id: str
    channel_id: str | None
    sync_type: YouTubeSyncType
    status: YouTubeSyncStatus
    configuration_json: str
    cursor_json: str | None
    discovered_count: int
    imported_count: int
    updated_count: int
    skipped_count: int
    warning_count: int
    error_count: int
    quota_cost_estimate: float | None
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "connection_id": self.connection_id,
            "channel_id": self.channel_id,
            "sync_type": self.sync_type.value,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "cursor_json": self.cursor_json,
            "discovered_count": self.discovered_count,
            "imported_count": self.imported_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "quota_cost_estimate": self.quota_cost_estimate,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeSyncItem:
    id: str
    sync_run_id: str
    remote_type: str
    remote_id: str
    local_type: str | None
    local_id: str | None
    action: str
    status: str
    warnings_json: str
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "sync_run_id": self.sync_run_id,
            "remote_type": self.remote_type,
            "remote_id": self.remote_id,
            "local_type": self.local_type,
            "local_id": self.local_id,
            "action": self.action,
            "status": self.status,
            "warnings_json": self.warnings_json,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeMetricImport:
    id: str
    creator_id: str
    channel_id: str
    remote_video_id: str | None
    sync_run_id: str
    metric_scope: str
    date_start: str
    date_end: str
    comparable_window: str | None
    source_fingerprint: str
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "channel_id": self.channel_id,
            "remote_video_id": self.remote_video_id,
            "sync_run_id": self.sync_run_id,
            "metric_scope": self.metric_scope,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "comparable_window": self.comparable_window,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeMetricValue:
    id: str
    metric_import_id: str
    metric_key: str
    raw_metric_name: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    dimensions_json: str
    quality_status: str
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "metric_import_id": self.metric_import_id,
            "metric_key": self.metric_key,
            "raw_metric_name": self.raw_metric_name,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "dimensions_json": self.dimensions_json,
            "quality_status": self.quality_status,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeContentLink:
    id: str
    creator_id: str
    remote_video_id: str
    publication_id: str | None
    video_asset_id: str | None
    link_method: YouTubeLinkMethod
    confidence_level: str
    status: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "remote_video_id": self.remote_video_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "link_method": self.link_method.value,
            "confidence_level": self.confidence_level,
            "status": self.status,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeQuotaUsage:
    id: str
    connection_id: str
    operation_key: str
    estimated_cost: float
    request_count: int
    usage_date: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "operation_key": self.operation_key,
            "estimated_cost": self.estimated_cost,
            "request_count": self.request_count,
            "usage_date": self.usage_date,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeSyncSchedule:
    id: str
    creator_id: str
    connection_id: str
    channel_id: str | None
    schedule_type: str
    enabled: bool
    interval_hours: int | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "connection_id": self.connection_id,
            "channel_id": self.channel_id,
            "schedule_type": self.schedule_type,
            "enabled": 1 if self.enabled else 0,
            "interval_hours": self.interval_hours,
            "last_run_at": to_iso_z(self.last_run_at),
            "next_run_at": to_iso_z(self.next_run_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class YouTubeSyncReport:
    connection_id: str
    channel_id: str | None
    sync_type: str
    status: str
    discovered_count: int
    imported_count: int
    updated_count: int
    unchanged_count: int
    skipped_count: int
    linked_count: int
    unlinked_count: int
    unavailable_metrics: tuple[str, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    quota_estimate: float | None
    duration_seconds: float | None
    next_recommended_action: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": self.connection_id,
            "channel_id": self.channel_id,
            "sync_type": self.sync_type,
            "status": self.status,
            "discovered_count": self.discovered_count,
            "imported_count": self.imported_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "skipped_count": self.skipped_count,
            "linked_count": self.linked_count,
            "unlinked_count": self.unlinked_count,
            "unavailable_metrics": list(self.unavailable_metrics),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "quota_estimate": self.quota_estimate,
            "duration_seconds": self.duration_seconds,
            "next_recommended_action": self.next_recommended_action,
        }

