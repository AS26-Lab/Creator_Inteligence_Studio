"""Entidades persistidas de la integracion Instagram."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .connection_types import (
    InstagramAccessLevel,
    InstagramAppAccessStatus,
    InstagramConnectionStatus,
    InstagramContentType,
    InstagramLinkMethod,
    InstagramMediaType,
    InstagramProfessionalAccountType,
)
from .insight_types import InstagramInsightPeriod, InstagramInsightScope
from .sync_types import InstagramSyncStatus, InstagramSyncType


@dataclass(frozen=True, slots=True)
class InstagramConnection:
    id: str
    creator_id: str
    provider: str
    account_identifier: str | None
    professional_account_type: InstagramProfessionalAccountType | None
    status: InstagramConnectionStatus
    granted_scopes_json: str
    credential_reference: str
    api_version: str
    access_level: InstagramAccessLevel | None
    app_access_status: InstagramAppAccessStatus
    connected_at: datetime
    last_verified_at: datetime | None
    disconnected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "provider": self.provider,
            "account_identifier": self.account_identifier,
            "professional_account_type": None if self.professional_account_type is None else self.professional_account_type.value,
            "status": self.status.value,
            "granted_scopes_json": self.granted_scopes_json,
            "credential_reference": self.credential_reference,
            "api_version": self.api_version,
            "access_level": None if self.access_level is None else self.access_level.value,
            "app_access_status": self.app_access_status.value,
            "connected_at": to_iso_z(self.connected_at),
            "last_verified_at": to_iso_z(self.last_verified_at),
            "disconnected_at": to_iso_z(self.disconnected_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramAccount:
    id: str
    creator_id: str
    connection_id: str
    instagram_user_id: str
    username: str
    name: str | None
    biography: str | None
    website: str | None
    profile_picture_url: str | None
    followers_count: int | None
    follows_count: int | None
    media_count: int | None
    account_type: InstagramProfessionalAccountType
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
            "instagram_user_id": self.instagram_user_id,
            "username": self.username,
            "name": self.name,
            "biography": self.biography,
            "website": self.website,
            "profile_picture_url": self.profile_picture_url,
            "followers_count": self.followers_count,
            "follows_count": self.follows_count,
            "media_count": self.media_count,
            "account_type": self.account_type.value,
            "selected_for_sync": 1 if self.selected_for_sync else 0,
            "last_synced_at": to_iso_z(self.last_synced_at),
            "remote_fingerprint": self.remote_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramRemoteMedia:
    id: str
    creator_id: str
    account_id: str
    instagram_media_id: str
    publication_id: str | None
    video_asset_id: str | None
    packaging_asset_id: str | None
    media_type: InstagramMediaType
    media_product_type: str | None
    content_type: InstagramContentType
    caption: str | None
    permalink: str | None
    media_url: str | None
    thumbnail_url: str | None
    cover_url: str | None
    timestamp: datetime
    shortcode: str | None
    children_count: int | None
    remote_fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    remote_status: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "account_id": self.account_id,
            "instagram_media_id": self.instagram_media_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "packaging_asset_id": self.packaging_asset_id,
            "media_type": self.media_type.value,
            "media_product_type": self.media_product_type,
            "content_type": self.content_type.value,
            "caption": self.caption,
            "permalink": self.permalink,
            "media_url": self.media_url,
            "thumbnail_url": self.thumbnail_url,
            "cover_url": self.cover_url,
            "timestamp": to_iso_z(self.timestamp),
            "shortcode": self.shortcode,
            "children_count": self.children_count,
            "remote_fingerprint": self.remote_fingerprint,
            "first_seen_at": to_iso_z(self.first_seen_at),
            "last_seen_at": to_iso_z(self.last_seen_at),
            "remote_status": self.remote_status,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramCarouselChild:
    id: str
    remote_media_id: str
    instagram_child_id: str
    child_order: int
    media_type: InstagramMediaType
    media_url: str | None
    thumbnail_url: str | None
    remote_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_media_id": self.remote_media_id,
            "instagram_child_id": self.instagram_child_id,
            "child_order": self.child_order,
            "media_type": self.media_type.value,
            "media_url": self.media_url,
            "thumbnail_url": self.thumbnail_url,
            "remote_fingerprint": self.remote_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramCaptionVersion:
    id: str
    remote_media_id: str
    version_number: int
    caption_text: str | None
    source_fingerprint: str
    is_current: bool
    observed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_media_id": self.remote_media_id,
            "version_number": self.version_number,
            "caption_text": self.caption_text,
            "source_fingerprint": self.source_fingerprint,
            "is_current": 1 if self.is_current else 0,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramCoverVersion:
    id: str
    remote_media_id: str
    version_number: int
    cover_url: str | None
    thumbnail_url: str | None
    remote_fingerprint: str
    packaging_asset_id: str | None
    is_current: bool
    observed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "remote_media_id": self.remote_media_id,
            "version_number": self.version_number,
            "cover_url": self.cover_url,
            "thumbnail_url": self.thumbnail_url,
            "remote_fingerprint": self.remote_fingerprint,
            "packaging_asset_id": self.packaging_asset_id,
            "is_current": 1 if self.is_current else 0,
            "observed_at": to_iso_z(self.observed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramSyncRun:
    id: str
    creator_id: str
    connection_id: str
    account_id: str | None
    sync_type: InstagramSyncType
    status: InstagramSyncStatus
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
            "account_id": self.account_id,
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
class InstagramSyncItem:
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
class InstagramInsightImport:
    id: str
    creator_id: str
    account_id: str
    remote_media_id: str | None
    sync_run_id: str
    insight_scope: InstagramInsightScope
    metric_period: InstagramInsightPeriod | None
    date_start: str | None
    date_end: str | None
    comparable_window: str | None
    source_fingerprint: str
    status: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "account_id": self.account_id,
            "remote_media_id": self.remote_media_id,
            "sync_run_id": self.sync_run_id,
            "insight_scope": self.insight_scope.value,
            "metric_period": None if self.metric_period is None else self.metric_period.value,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "comparable_window": self.comparable_window,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramInsightValue:
    id: str
    insight_import_id: str
    metric_key: str
    raw_metric_name: str
    numeric_value: float | None
    text_value: str | None
    unit: str | None
    period: str | None
    dimensions_json: str
    breakdowns_json: str
    quality_status: str
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "insight_import_id": self.insight_import_id,
            "metric_key": self.metric_key,
            "raw_metric_name": self.raw_metric_name,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "period": self.period,
            "dimensions_json": self.dimensions_json,
            "breakdowns_json": self.breakdowns_json,
            "quality_status": self.quality_status,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramContentLink:
    id: str
    creator_id: str
    remote_media_id: str
    publication_id: str | None
    video_asset_id: str | None
    packaging_asset_id: str | None
    link_method: InstagramLinkMethod
    confidence_level: str
    status: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "remote_media_id": self.remote_media_id,
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
class InstagramRateLimitUsage:
    id: str
    connection_id: str
    operation_key: str
    estimated_usage: str | None
    request_count: int
    usage_date: str
    headers_snapshot_json: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "operation_key": self.operation_key,
            "estimated_usage": self.estimated_usage,
            "request_count": self.request_count,
            "usage_date": self.usage_date,
            "headers_snapshot_json": self.headers_snapshot_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramSyncSchedule:
    id: str
    creator_id: str
    connection_id: str
    account_id: str | None
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
            "account_id": self.account_id,
            "schedule_type": self.schedule_type,
            "enabled": 1 if self.enabled else 0,
            "interval_hours": self.interval_hours,
            "last_run_at": to_iso_z(self.last_run_at),
            "next_run_at": to_iso_z(self.next_run_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class InstagramSyncReport:
    connection_id: str
    account_id: str | None
    provider: str
    professional_account_type: str | None
    api_version: str
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
    insights_imported_count: int
    unavailable_metrics: tuple[str, ...]
    partial_periods: tuple[str, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    estimated_usage: str | None
    duration_seconds: float | None
    next_recommended_action: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "connection_id": self.connection_id,
            "account_id": self.account_id,
            "provider": self.provider,
            "professional_account_type": self.professional_account_type,
            "api_version": self.api_version,
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
            "insights_imported_count": self.insights_imported_count,
            "unavailable_metrics": list(self.unavailable_metrics),
            "partial_periods": list(self.partial_periods),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "estimated_usage": self.estimated_usage,
            "duration_seconds": self.duration_seconds,
            "next_recommended_action": self.next_recommended_action,
        }

