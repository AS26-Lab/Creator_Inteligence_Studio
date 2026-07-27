"""Mapeo de disponibilidad de datos por plataforma."""

from __future__ import annotations

from uuid import uuid4

from creator_intelligence_studio.domain.platform_integrations.data_availability_types import (
    DataAvailabilitySourceType,
    DataAvailabilityStatus,
    DataCategory,
)
from creator_intelligence_studio.domain.platform_integrations.entities import PlatformDataAvailability
from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind
from creator_intelligence_studio.shared.dates import utc_now


_AVAILABILITY_MATRIX: dict[PlatformKind, list[tuple[DataCategory, str, DataAvailabilityStatus, DataAvailabilitySourceType, bool, bool, str | None, str | None, list[str]]]] = {
    PlatformKind.YOUTUBE: [
        (DataCategory.PROFILE, "channel_metadata", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "periodic", None, []),
        (DataCategory.CONTENT, "video_metadata", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "event", None, []),
        (DataCategory.PUBLIC_METRICS, "views", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "cumulative", "cumulative", []),
        (DataCategory.PRIVATE_ANALYTICS, "watch_time", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, True, "periodic", None, []),
        (DataCategory.PRIVATE_ANALYTICS, "traffic_source", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, True, "periodic", None, []),
    ],
    PlatformKind.INSTAGRAM: [
        (DataCategory.PROFILE, "professional_account", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "periodic", None, []),
        (DataCategory.CONTENT, "media_metadata", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "event", None, []),
        (DataCategory.PUBLIC_METRICS, "reach", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, True, "cumulative", None, []),
        (DataCategory.PRIVATE_ANALYTICS, "watch_time", DataAvailabilityStatus.PARTIALLY_AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, True, "periodic", None, ["app_review_required"]),
        (DataCategory.AUDIENCE, "demographics", DataAvailabilityStatus.PARTIALLY_AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, True, "periodic", None, ["aggregated_only"]),
    ],
    PlatformKind.TIKTOK: [
        (DataCategory.PROFILE, "profile_metadata", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "periodic", None, []),
        (DataCategory.CONTENT, "public_videos", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "event", None, []),
        (DataCategory.PUBLIC_METRICS, "public_counters", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.AUTOMATIC, True, False, "cumulative", "cumulative", []),
        (DataCategory.PRIVATE_ANALYTICS, "watch_time", DataAvailabilityStatus.MANUAL_IMPORT_ONLY, DataAvailabilitySourceType.MANUAL_IMPORT, False, True, "periodic", None, ["display_api_limited"]),
        (DataCategory.AUDIENCE, "demographics", DataAvailabilityStatus.MANUAL_IMPORT_ONLY, DataAvailabilitySourceType.MANUAL_IMPORT, False, True, "periodic", None, ["display_api_limited"]),
    ],
    PlatformKind.MANUAL_OTHER: [
        (DataCategory.PRIVATE_ANALYTICS, "manual_private_analytics", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.MANUAL_IMPORT, False, True, "periodic", None, []),
        (DataCategory.PUBLIC_METRICS, "manual_public_metrics", DataAvailabilityStatus.AVAILABLE, DataAvailabilitySourceType.MANUAL_IMPORT, False, True, "periodic", None, []),
    ],
}


def build_data_availability_records(*, creator_id: str, platform_connection_id: str, platform: PlatformKind) -> list[PlatformDataAvailability]:
    observed_at = utc_now()
    records: list[PlatformDataAvailability] = []
    for data_category, data_key, status, source_type, automatic_available, manual_import_available, period_semantics, cumulative_semantics, limitations in _AVAILABILITY_MATRIX[platform]:
        records.append(
            PlatformDataAvailability(
                id=str(uuid4()),
                creator_id=creator_id,
                platform_connection_id=platform_connection_id,
                data_category=data_category,
                data_key=data_key,
                availability_status=status,
                source_type=source_type,
                automatic_available=automatic_available,
                manual_import_available=manual_import_available,
                period_semantics=period_semantics,
                cumulative_semantics=cumulative_semantics,
                limitations_json=str(limitations),
                observed_at=observed_at,
                created_at=observed_at,
                updated_at=observed_at,
            )
        )
    return records
