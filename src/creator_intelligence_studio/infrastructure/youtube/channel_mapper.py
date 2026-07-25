"""Mapeos de respuesta de canal de YouTube."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from creator_intelligence_studio.domain.youtube_integration.connection_types import YouTubeConnectionStatus
from creator_intelligence_studio.domain.youtube_integration.entities import YouTubeChannel
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def map_channel_payload(*, creator_id: str, connection_id: str, payload: dict[str, object], remote_fingerprint: str) -> YouTubeChannel:
    snippet = payload.get("snippet") if isinstance(payload.get("snippet"), dict) else {}
    statistics = payload.get("statistics") if isinstance(payload.get("statistics"), dict) else {}
    branding = payload.get("brandingSettings") if isinstance(payload.get("brandingSettings"), dict) else {}
    thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
    default_thumb = thumbnails.get("default") if isinstance(thumbnails.get("default"), dict) else {}
    return YouTubeChannel(
        id=str(uuid4()),
        creator_id=creator_id,
        connection_id=connection_id,
        youtube_channel_id=str(payload.get("id") or ""),
        title=str(snippet.get("title") or ""),
        description=snippet.get("description"),
        custom_url=branding.get("channel", {}).get("customUrl") if isinstance(branding.get("channel"), dict) else None,
        country=snippet.get("country"),
        published_at=from_iso_z(snippet.get("publishedAt")) or utc_now(),
        thumbnail_url=default_thumb.get("url"),
        subscriber_count=_int_or_none(statistics.get("subscriberCount")),
        video_count=_int_or_none(statistics.get("videoCount")),
        view_count=_int_or_none(statistics.get("viewCount")),
        hidden_subscriber_count=bool(statistics.get("hiddenSubscriberCount", False)),
        selected_for_sync=True,
        last_synced_at=utc_now(),
        remote_fingerprint=remote_fingerprint,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def _int_or_none(value: object) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None

