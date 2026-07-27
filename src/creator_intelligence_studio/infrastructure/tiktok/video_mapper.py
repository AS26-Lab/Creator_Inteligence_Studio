"""Mapeos de videos TikTok."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokRemoteStatus
from creator_intelligence_studio.domain.tiktok_integration.entities import TikTokCoverVersion, TikTokRemoteVideo, TikTokVideoTextVersion
from creator_intelligence_studio.domain.tiktok_integration.value_objects import build_tiktok_fingerprint
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _safe_int(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _safe_str(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def map_remote_video_payload(
    payload: dict[str, object],
    *,
    creator_id: str,
    profile_id: str,
    publication_id: str | None = None,
    video_asset_id: str | None = None,
    packaging_asset_id: str | None = None,
) -> TikTokRemoteVideo:
    remote_id = _safe_str(payload.get("id")) or str(uuid4())
    create_time = payload.get("create_time")
    if isinstance(create_time, (int, float)):
        create_dt = datetime.fromtimestamp(float(create_time), tz=timezone.utc)
    else:
        create_dt = from_iso_z(_safe_str(create_time)) or utc_now()
    fingerprint = build_tiktok_fingerprint(
        {
            "id": remote_id,
            "title": payload.get("title"),
            "video_description": payload.get("video_description"),
            "share_url": payload.get("share_url"),
            "embed_link": payload.get("embed_link"),
            "cover_image_url": payload.get("cover_image_url"),
            "like_count": payload.get("like_count"),
            "comment_count": payload.get("comment_count"),
            "share_count": payload.get("share_count"),
            "view_count": payload.get("view_count"),
            "duration": payload.get("duration"),
            "height": payload.get("height"),
            "width": payload.get("width"),
        }
    )
    return TikTokRemoteVideo(
        id=str(uuid4()),
        creator_id=creator_id,
        profile_id=profile_id,
        tiktok_video_id=remote_id,
        publication_id=publication_id,
        video_asset_id=video_asset_id,
        packaging_asset_id=packaging_asset_id,
        title=_safe_str(payload.get("title")),
        video_description=_safe_str(payload.get("video_description")),
        create_time=create_dt,
        duration_seconds=_safe_int(payload.get("duration")),
        width=_safe_int(payload.get("width")),
        height=_safe_int(payload.get("height")),
        share_url=_safe_str(payload.get("share_url")),
        embed_link=_safe_str(payload.get("embed_link")),
        cover_image_url=_safe_str(payload.get("cover_image_url")),
        like_count=_safe_int(payload.get("like_count")),
        comment_count=_safe_int(payload.get("comment_count")),
        share_count=_safe_int(payload.get("share_count")),
        view_count=_safe_int(payload.get("view_count")),
        remote_fingerprint=fingerprint,
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        remote_status=TikTokRemoteStatus.PUBLIC,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def map_text_version(remote_video_id: str, payload: dict[str, object], *, version_number: int, is_current: bool) -> TikTokVideoTextVersion:
    return TikTokVideoTextVersion(
        id=str(uuid4()),
        remote_video_id=remote_video_id,
        version_number=version_number,
        title_text=_safe_str(payload.get("title")),
        description_text=_safe_str(payload.get("video_description")),
        source_fingerprint=build_tiktok_fingerprint({"title": payload.get("title"), "video_description": payload.get("video_description"), "id": remote_video_id}),
        is_current=is_current,
        observed_at=utc_now(),
        created_at=utc_now(),
    )


def map_cover_version(remote_video_id: str, payload: dict[str, object], *, version_number: int, packaging_asset_id: str | None = None, is_current: bool = True) -> TikTokCoverVersion:
    return TikTokCoverVersion(
        id=str(uuid4()),
        remote_video_id=remote_video_id,
        version_number=version_number,
        cover_image_url=_safe_str(payload.get("cover_image_url")),
        remote_fingerprint=build_tiktok_fingerprint({"cover_image_url": payload.get("cover_image_url"), "id": remote_video_id}),
        packaging_asset_id=packaging_asset_id,
        is_current=is_current,
        observed_at=utc_now(),
        created_at=utc_now(),
    )
