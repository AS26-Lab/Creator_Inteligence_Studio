"""Mapeo estatico de capacidades por plataforma."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.platform_integrations.capability_types import (
    CapabilityAvailabilityStatus,
    CapabilityCategory,
)
from creator_intelligence_studio.domain.platform_integrations.entities import PlatformCapabilitySnapshot
from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind
from creator_intelligence_studio.shared.dates import utc_now


_CAPABILITY_MATRIX: dict[PlatformKind, dict[CapabilityCategory, list[tuple[str, CapabilityAvailabilityStatus, str | None, str | None, str | None]]]] = {
    PlatformKind.YOUTUBE: {
        CapabilityCategory.AUTHENTICATION: [
            ("oauth", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "youtube_read_only"),
            ("refresh", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "youtube_read_only"),
            ("revoke", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "youtube_read_only"),
            ("multiple_accounts", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, "native_scope_limited"),
        ],
        CapabilityCategory.CONTENT: [
            ("channel", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("videos", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("shorts", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("covers", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("captions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("descriptions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.METRICS: [
            ("public_counters", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("private_analytics", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("retention", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("watch_time", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("completion", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("traffic_source", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("audience", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
        ],
        CapabilityCategory.SYNC: [
            ("pagination", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("incremental", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("resume", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("repair", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("scheduling", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("rate_limit_awareness", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.WRITE: [
            ("publish", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("edit", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("delete", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
        ],
    },
    PlatformKind.INSTAGRAM: {
        CapabilityCategory.AUTHENTICATION: [
            ("oauth", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "instagram_login"),
            ("refresh", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "instagram_login"),
            ("revoke", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "instagram_login"),
            ("multiple_accounts", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, "access_level_limited"),
        ],
        CapabilityCategory.CONTENT: [
            ("account", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("posts", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("reels", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("carousels", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("stories", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
            ("covers", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("captions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("descriptions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.METRICS: [
            ("public_counters", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("private_analytics", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("retention", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
            ("watch_time", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
            ("completion", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
            ("traffic_source", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
            ("audience", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, None),
        ],
        CapabilityCategory.SYNC: [
            ("pagination", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("incremental", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("resume", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("repair", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("scheduling", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("rate_limit_awareness", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.WRITE: [
            ("publish", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("edit", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("delete", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
        ],
    },
    PlatformKind.TIKTOK: {
        CapabilityCategory.AUTHENTICATION: [
            ("oauth", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "login_kit"),
            ("refresh", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "login_kit"),
            ("revoke", CapabilityAvailabilityStatus.AVAILABLE, "read_only", None, "login_kit"),
            ("multiple_accounts", CapabilityAvailabilityStatus.PARTIALLY_AVAILABLE, None, None, "product_approval_limited"),
        ],
        CapabilityCategory.CONTENT: [
            ("profile", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("videos", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("covers", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("captions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("descriptions", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.METRICS: [
            ("public_counters", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("private_analytics", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
            ("retention", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
            ("watch_time", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
            ("completion", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
            ("traffic_source", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
            ("audience", CapabilityAvailabilityStatus.MANUAL_IMPORT_ONLY, None, None, "display_api_limited"),
        ],
        CapabilityCategory.SYNC: [
            ("pagination", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("incremental", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("resume", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("repair", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("scheduling", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("rate_limit_awareness", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.WRITE: [
            ("publish", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("edit", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("delete", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
        ],
    },
    PlatformKind.MANUAL_OTHER: {
        CapabilityCategory.AUTHENTICATION: [
            ("oauth", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("refresh", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("revoke", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("multiple_accounts", CapabilityAvailabilityStatus.AVAILABLE, None, None, "manual"),
        ],
        CapabilityCategory.CONTENT: [
            ("manual_imports", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.METRICS: [
            ("manual_private_analytics", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("watch_time", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("completion", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
            ("retention", CapabilityAvailabilityStatus.AVAILABLE, None, None, None),
        ],
        CapabilityCategory.SYNC: [
            ("pagination", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("incremental", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("resume", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("repair", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("scheduling", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
            ("rate_limit_awareness", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "manual"),
        ],
        CapabilityCategory.WRITE: [
            ("publish", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("edit", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
            ("delete", CapabilityAvailabilityStatus.UNSUPPORTED, None, None, "intentionally_disabled"),
        ],
    },
}


def build_capability_snapshots(*, creator_id: str, platform_connection_id: str, platform: PlatformKind, source_version: str | None = None) -> list[PlatformCapabilitySnapshot]:
    observed_at = utc_now()
    created_at = observed_at
    snapshots: list[PlatformCapabilitySnapshot] = []
    for category, entries in _CAPABILITY_MATRIX[platform].items():
        for key, status, access_level, permission_required, limitation_code in entries:
            snapshots.append(
                PlatformCapabilitySnapshot(
                    id=str(uuid4()),
                    creator_id=creator_id,
                    platform_connection_id=platform_connection_id,
                    capability_key=f"{category.value}.{key}",
                    availability_status=status,
                    access_level=access_level,
                    permission_required=permission_required,
                    limitation_code=limitation_code,
                    source_version=source_version,
                    observed_at=observed_at,
                    created_at=created_at,
                )
            )
    return snapshots
