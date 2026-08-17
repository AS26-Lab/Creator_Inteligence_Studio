"""Mapeador de respuestas de medios Instagram."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramContentType, InstagramMediaType
from creator_intelligence_studio.domain.instagram_integration.entities import InstagramCarouselChild, InstagramCoverVersion, InstagramRemoteMedia
from creator_intelligence_studio.domain.instagram_integration.media_types import map_content_type
from creator_intelligence_studio.infrastructure.instagram.value_objects import build_instagram_fingerprint


def _safe_str(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _preserve_text(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _safe_int(value: Any | None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _parse_media_type(value: Any | None) -> InstagramMediaType:
    normalized = _safe_str(value)
    if normalized is None:
        return InstagramMediaType.UNKNOWN
    mapping = {
        "image": InstagramMediaType.IMAGE,
        "video": InstagramMediaType.VIDEO,
        "carousel_album": InstagramMediaType.CAROUSEL_ALBUM,
        "reels": InstagramMediaType.REELS,
        "story": InstagramMediaType.STORIES,
        "stories": InstagramMediaType.STORIES,
        "live": InstagramMediaType.LIVE,
    }
    return mapping.get(normalized.lower(), InstagramMediaType.UNKNOWN)


def map_remote_media_payload(
    payload: dict[str, Any],
    *,
    creator_id: str,
    account_id: str,
    publication_id: str | None = None,
    video_asset_id: str | None = None,
    packaging_asset_id: str | None = None,
) -> InstagramRemoteMedia:
    now = datetime.now(timezone.utc)
    media_type = _parse_media_type(payload.get("media_type"))
    media_product_type = _safe_str(payload.get("media_product_type"))
    content_type = map_content_type(media_type, media_product_type)
    timestamp_raw = _safe_str(payload.get("timestamp")) or now.isoformat()
    try:
        timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
    except ValueError:
        timestamp = now
    fingerprint = build_instagram_fingerprint(
        {
            "instagram_media_id": _safe_str(payload.get("id")),
            "media_type": media_type.value,
            "media_product_type": media_product_type,
            "caption": _safe_str(payload.get("caption")),
            "permalink": _safe_str(payload.get("permalink")),
            "media_url": _safe_str(payload.get("media_url")),
            "thumbnail_url": _safe_str(payload.get("thumbnail_url")),
            "cover_url": _safe_str(payload.get("cover_url")),
            "timestamp": timestamp.isoformat(),
            "shortcode": _safe_str(payload.get("shortcode")),
            "children_count": _safe_int(payload.get("children_count")),
        }
    )
    return InstagramRemoteMedia(
        id=str(uuid4()),
        creator_id=creator_id,
        account_id=account_id,
        instagram_media_id=_safe_str(payload.get("id")) or "",
        publication_id=publication_id,
        video_asset_id=video_asset_id,
        packaging_asset_id=packaging_asset_id,
        media_type=media_type,
        media_product_type=media_product_type,
        content_type=content_type,
        caption=_preserve_text(payload.get("caption")),
        permalink=_safe_str(payload.get("permalink")),
        media_url=_safe_str(payload.get("media_url")),
        thumbnail_url=_safe_str(payload.get("thumbnail_url")),
        cover_url=_safe_str(payload.get("cover_url") or payload.get("thumbnail_url")),
        timestamp=timestamp,
        shortcode=_safe_str(payload.get("shortcode")),
        children_count=_safe_int(payload.get("children_count")),
        remote_fingerprint=fingerprint,
        first_seen_at=now,
        last_seen_at=now,
        remote_status=_safe_str(payload.get("remote_status")) or "active",
        created_at=now,
        updated_at=now,
    )


def map_carousel_child_payload(payload: dict[str, Any], *, remote_media_id: str, child_order: int) -> InstagramCarouselChild:
    now = datetime.now(timezone.utc)
    media_type = _parse_media_type(payload.get("media_type"))
    fingerprint = build_instagram_fingerprint(
        {
            "instagram_child_id": _safe_str(payload.get("id")),
            "media_type": media_type.value,
            "media_url": _safe_str(payload.get("media_url")),
            "thumbnail_url": _safe_str(payload.get("thumbnail_url")),
            "child_order": child_order,
        }
    )
    return InstagramCarouselChild(
        id=str(uuid4()),
        remote_media_id=remote_media_id,
        instagram_child_id=_safe_str(payload.get("id")) or "",
        child_order=child_order,
        media_type=media_type,
        media_url=_safe_str(payload.get("media_url")),
        thumbnail_url=_safe_str(payload.get("thumbnail_url")),
        remote_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
    )


def map_cover_version(
    *,
    remote_media_id: str,
    cover_url: str | None,
    thumbnail_url: str | None,
    packaging_asset_id: str | None = None,
    version_number: int = 1,
) -> InstagramCoverVersion:
    now = datetime.now(timezone.utc)
    fingerprint = build_instagram_fingerprint(
        {
            "remote_media_id": remote_media_id,
            "cover_url": cover_url,
            "thumbnail_url": thumbnail_url,
            "packaging_asset_id": packaging_asset_id,
            "version_number": version_number,
        }
    )
    return InstagramCoverVersion(
        id=str(uuid4()),
        remote_media_id=remote_media_id,
        version_number=version_number,
        cover_url=cover_url,
        thumbnail_url=thumbnail_url,
        remote_fingerprint=fingerprint,
        packaging_asset_id=packaging_asset_id,
        is_current=True,
        observed_at=now,
        created_at=now,
    )
