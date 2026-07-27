"""Entidades persistidas de la integracion TikTok."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .connection_types import TikTokAccessLevel, TikTokConnectionStatus, TikTokLinkMethod, TikTokRemoteStatus
from .metric_types import TikTokMetricScope, TikTokMetricSourceType, TikTokMetricStatus
from .sync_types import TikTokSyncStatus, TikTokSyncType


@dataclass(frozen=True, slots=True)
class TikTokConnection:
    id: str
    creator_id: str
    status: TikTokConnectionStatus
    open_id: str | None
    union_id: str | None
    account_identifier: str | None
    granted_scopes_json: str
    credential_reference: str
    api_version: str
    access_level: TikTokAccessLevel | None
    connected_at: datetime
    last_verified_at: datetime | None
    disconnected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "status": self.status.value,
            "open_id": self.open_id,
            "union_id": self.union_id,
            "account_identifier": self.account_identifier,
            "granted_scopes_json": self.granted_scopes_json,
            "credential_reference": self.credential_reference,
            "api_version": self.api_version,
            "access_level": None if self.access_level is None else self.access_level.value,
            "connected_at": to_iso_z(self.connected_at),
            "last_verified_at": to_iso_z(self.last_verified_at),
            "disconnected_at": to_iso_z(self.disconnected_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokProfile:
    id: str
    creator_id: str
    connection_id: str
    open_id: str
    union_id: str | None
    display_name: str | None
    username: str | None
    avatar_url: str | None
    bio_description: str | None
    profile_deep_link: str | None
    profile_web_link: str | None
    is_verified: bool | None
    follower_count: int | None
    following_count: int | None
    likes_count: int | None
    video_count: int | None
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
            "open_id": self.open_id,
            "union_id": self.union_id,
            "display_name": self.display_name,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "bio_description": self.bio_description,
            "profile_deep_link": self.profile_deep_link,
            "profile_web_link": self.profile_web_link,
            "is_verified": self.is_verified,
            "follower_count": self.follower_count,
            "following_count": self.following_count,
            "likes_count": self.likes_count,
            "video_count": self.video_count,
            "selected_for_sync": 1 if self.selected_for_sync else 0,
            "last_synced_at": to_iso_z(self.last_synced_at),
            "remote_fingerprint": self.remote_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokRemoteVideo:
    id: str
    creator_id: str
    profile_id: str
    tiktok_video_id: str
    publication_id: str | None
    video_asset_id: str | None
    packaging_asset_id: str | None
    title: str | None
    video_description: str | None
    create_time: datetime
    duration_seconds: int | None
    width: int | None
    height: int | None
    share_url: str | None
    embed_link: str | None
    cover_image_url: str | None
    like_count: int | None
    comment_count: int | None
    share_count: int | None
    view_count: int | None
    remote_fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    remote_status: TikTokRemoteStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_id": self.profile_id,
            "tiktok_video_id": self.tiktok_video_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "packaging_asset_id": self.packaging_asset_id,
            "title": self.title,
            "video_description": self.video_description,
            "create_time": to_iso_z(self.create_time),
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "share_url": self.share_url,
            "embed_link": self.embed_link,
            "cover_image_url": self.cover_image_url,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "view_count": self.view_count,
            "remote_fingerprint": self.remote_fingerprint,
            "first_seen_at": to_iso_z(self.first_seen_at),
            "last_seen_at": to_iso_z(self.last_seen_at),
            "remote_status": self.remote_status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokVideoTextVersion:
    id: str
    remote_video_id: str
    version_number: int
    title_text: str | None
    description_text: str | None
    source_fingerprint: str
    is_current: bool
    observed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_video_id": self.remote_video_id,
            "version_number": self.version_number,
            "title_text": self.title_text,
            "description_text": self.description_text,
            "source_fingerprint": self.source_fingerprint,
            "is_current": 1 if self.is_current else 0,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokCoverVersion:
    id: str
    remote_video_id: str
    version_number: int
    cover_image_url: str | None
    remote_fingerprint: str
    packaging_asset_id: str | None
    is_current: bool
    observed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_video_id": self.remote_video_id,
            "version_number": self.version_number,
            "cover_image_url": self.cover_image_url,
            "remote_fingerprint": self.remote_fingerprint,
            "packaging_asset_id": self.packaging_asset_id,
            "is_current": 1 if self.is_current else 0,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokSyncRun:
    id: str
    creator_id: str
    connection_id: str
    profile_id: str | None
    sync_type: TikTokSyncType
    status: TikTokSyncStatus
    configuration_json: str
    cursor_json: str | None
    discovered_count: int
    imported_count: int
    updated_count: int
    unchanged_count: int
    skipped_count: int
    warning_count: int
    error_count: int
    estimated_usage: str | None
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
            "profile_id": self.profile_id,
            "sync_type": self.sync_type.value,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "cursor_json": self.cursor_json,
            "discovered_count": self.discovered_count,
            "imported_count": self.imported_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "skipped_count": self.skipped_count,
            "warning_count": self.warning_count,
            "error_count": self.error_count,
            "estimated_usage": self.estimated_usage,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokSyncItem:
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
class TikTokMetricImport:
    id: str
    creator_id: str
    profile_id: str
    remote_video_id: str | None
    sync_run_id: str
    metric_scope: TikTokMetricScope
    source_type: TikTokMetricSourceType
    observed_at: datetime
    period_start: str | None
    period_end: str | None
    comparable_window: str | None
    source_fingerprint: str
    status: TikTokMetricStatus
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_id": self.profile_id,
            "remote_video_id": self.remote_video_id,
            "sync_run_id": self.sync_run_id,
            "metric_scope": self.metric_scope.value,
            "source_type": self.source_type.value,
            "observed_at": to_iso_z(self.observed_at),
            "period_start": self.period_start,
            "period_end": self.period_end,
            "comparable_window": self.comparable_window,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokMetricValue:
    id: str
    metric_import_id: str
    metric_key: str
    raw_metric_name: str
    numeric_value: float | None
    text_value: str | None
    unit: str | None
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
class TikTokContentLink:
    id: str
    creator_id: str
    remote_video_id: str
    publication_id: str | None
    video_asset_id: str | None
    packaging_asset_id: str | None
    link_method: TikTokLinkMethod
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
            "packaging_asset_id": self.packaging_asset_id,
            "link_method": self.link_method.value,
            "confidence_level": self.confidence_level,
            "status": self.status,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokRateLimitUsage:
    id: str
    connection_id: str
    operation_key: str
    endpoint: str
    request_count: int
    estimated_usage: str | None
    window_started_at: datetime | None
    response_headers_json: str | None
    usage_date: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "operation_key": self.operation_key,
            "endpoint": self.endpoint,
            "request_count": self.request_count,
            "estimated_usage": self.estimated_usage,
            "window_started_at": to_iso_z(self.window_started_at),
            "response_headers_json": self.response_headers_json,
            "usage_date": self.usage_date,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokSyncSchedule:
    id: str
    creator_id: str
    connection_id: str
    profile_id: str | None
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
            "profile_id": self.profile_id,
            "schedule_type": self.schedule_type,
            "enabled": 1 if self.enabled else 0,
            "interval_hours": self.interval_hours,
            "last_run_at": to_iso_z(self.last_run_at),
            "next_run_at": to_iso_z(self.next_run_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TikTokSyncReport:
    connection_id: str
    profile_id: str | None
    granted_scopes: tuple[str, ...]
    access_level: str | None
    sync_type: str
    period: str | None
    discovered_count: int
    imported_count: int
    updated_count: int
    unchanged_count: int
    skipped_count: int
    linked_count: int
    unlinked_count: int
    profile_metrics: tuple[str, ...]
    video_metrics: tuple[str, ...]
    unavailable_metrics: tuple[str, ...]
    manual_import_recommendation: str | None
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    estimated_usage: str | None
    duration_seconds: float | None
    next_action: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": self.connection_id,
            "profile_id": self.profile_id,
            "granted_scopes": list(self.granted_scopes),
            "access_level": self.access_level,
            "sync_type": self.sync_type,
            "period": self.period,
            "discovered_count": self.discovered_count,
            "imported_count": self.imported_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "skipped_count": self.skipped_count,
            "linked_count": self.linked_count,
            "unlinked_count": self.unlinked_count,
            "profile_metrics": list(self.profile_metrics),
            "video_metrics": list(self.video_metrics),
            "unavailable_metrics": list(self.unavailable_metrics),
            "manual_import_recommendation": self.manual_import_recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "estimated_usage": self.estimated_usage,
            "duration_seconds": self.duration_seconds,
            "next_action": self.next_action,
        }

