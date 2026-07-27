"""Normalizacion determinista de señales de audiencia."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.audience_model.audience_types import AudienceSignalType
from creator_intelligence_studio.domain.audience_model.entities import AudienceSignal
from creator_intelligence_studio.shared.dates import utc_now


SIGNAL_KEY_TO_TYPE: dict[str, AudienceSignalType] = {
    "new_viewers": AudienceSignalType.ACQUISITION,
    "returning_viewers": AudienceSignalType.LOYALTY,
    "unique_viewers": AudienceSignalType.CONSUMPTION,
    "views": AudienceSignalType.CONSUMPTION,
    "engaged_views": AudienceSignalType.ENGAGEMENT,
    "watch_time": AudienceSignalType.CONSUMPTION,
    "watch_time_minutes": AudienceSignalType.CONSUMPTION,
    "average_view_duration": AudienceSignalType.CONSUMPTION,
    "average_view_duration_seconds": AudienceSignalType.CONSUMPTION,
    "average_percentage_viewed": AudienceSignalType.CONSUMPTION,
    "completion_rate": AudienceSignalType.CONSUMPTION,
    "likes": AudienceSignalType.ENGAGEMENT,
    "comments": AudienceSignalType.ENGAGEMENT,
    "shares": AudienceSignalType.ENGAGEMENT,
    "saves": AudienceSignalType.ENGAGEMENT,
    "subscribers_gained": AudienceSignalType.CONVERSION,
    "subscribers_lost": AudienceSignalType.CONVERSION,
    "followers_gained": AudienceSignalType.CONVERSION,
    "profile_visits": AudienceSignalType.CONVERSION,
    "traffic_to_longform": AudienceSignalType.CROSS_CONTENT_FLOW,
    "browse_views": AudienceSignalType.TRAFFIC_SOURCE,
    "suggested_views": AudienceSignalType.TRAFFIC_SOURCE,
    "search_views": AudienceSignalType.TRAFFIC_SOURCE,
    "shorts_feed_views": AudienceSignalType.TRAFFIC_SOURCE,
    "external_views": AudienceSignalType.TRAFFIC_SOURCE,
    "direct_views": AudienceSignalType.TRAFFIC_SOURCE,
    "notification_views": AudienceSignalType.TRAFFIC_SOURCE,
    "playlist_views": AudienceSignalType.TRAFFIC_SOURCE,
    "geography_share": AudienceSignalType.GEOGRAPHY,
    "device_share": AudienceSignalType.DEVICE,
    "subscription_status_share": AudienceSignalType.SUBSCRIPTION_STATUS,
    "traffic_source": AudienceSignalType.TRAFFIC_SOURCE,
    "topic": AudienceSignalType.AFFINITY,
    "format": AudienceSignalType.AFFINITY,
    "content_type": AudienceSignalType.AFFINITY,
    "platform": AudienceSignalType.AFFINITY,
    "returning_behavior": AudienceSignalType.RETURNING_BEHAVIOR,
}


def signal_type_for_key(signal_key: str) -> AudienceSignalType:
    return SIGNAL_KEY_TO_TYPE.get(signal_key, AudienceSignalType.DATA_QUALITY)


def build_signal(
    *,
    creator_id: str,
    platform: str,
    signal_key: str,
    numeric_value: float | None = None,
    text_value: str | None = None,
    unit: str | None = None,
    channel_id: str | None = None,
    publication_id: str | None = None,
    remote_video_id: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    observed_at: datetime | None = None,
    source_type: str,
    source_id: str | None,
    dimensions_json: str,
    quality_status: str,
    warning_codes_json: str,
) -> AudienceSignal:
    timestamp = observed_at or utc_now()
    return AudienceSignal(
        id=str(uuid4()),
        creator_id=creator_id,
        platform=platform,
        channel_id=channel_id,
        publication_id=publication_id,
        remote_video_id=remote_video_id,
        signal_type=signal_type_for_key(signal_key),
        signal_key=signal_key,
        numeric_value=numeric_value,
        text_value=text_value,
        unit=unit,
        period_start=period_start,
        period_end=period_end,
        observed_at=timestamp,
        source_type=source_type,
        source_id=source_id,
        dimensions_json=dimensions_json,
        quality_status=quality_status,
        warning_codes_json=warning_codes_json,
        created_at=timestamp,
    )

