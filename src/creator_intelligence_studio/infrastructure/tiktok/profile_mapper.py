"""Mapeos de perfiles TikTok."""

from __future__ import annotations

from uuid import uuid4

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokAccessLevel, TikTokConnectionStatus
from creator_intelligence_studio.domain.tiktok_integration.entities import TikTokProfile
from creator_intelligence_studio.domain.tiktok_integration.value_objects import build_tiktok_fingerprint
from creator_intelligence_studio.shared.dates import utc_now


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


def map_profile_payload(
    payload: dict[str, object],
    *,
    creator_id: str,
    connection_id: str,
    open_id: str,
    api_version: str,
    selected_for_sync: bool = True,
) -> TikTokProfile:
    fingerprint_source = {
        key: payload.get(key)
        for key in (
            "open_id",
            "union_id",
            "avatar_url",
            "avatar_url_100",
            "avatar_large_url",
            "display_name",
            "bio_description",
            "profile_deep_link",
            "profile_web_link",
            "is_verified",
            "username",
            "follower_count",
            "following_count",
            "likes_count",
            "video_count",
        )
    }
    return TikTokProfile(
        id=str(uuid4()),
        creator_id=creator_id,
        connection_id=connection_id,
        open_id=str(payload.get("open_id") or open_id),
        union_id=_safe_str(payload.get("union_id")),
        display_name=_safe_str(payload.get("display_name")),
        username=_safe_str(payload.get("username")),
        avatar_url=_safe_str(payload.get("avatar_url") or payload.get("avatar_url_100") or payload.get("avatar_large_url")),
        bio_description=_safe_str(payload.get("bio_description")),
        profile_deep_link=_safe_str(payload.get("profile_deep_link")),
        profile_web_link=_safe_str(payload.get("profile_web_link")),
        is_verified=payload.get("is_verified") if isinstance(payload.get("is_verified"), bool) else None,
        follower_count=_safe_int(payload.get("follower_count")),
        following_count=_safe_int(payload.get("following_count")),
        likes_count=_safe_int(payload.get("likes_count")),
        video_count=_safe_int(payload.get("video_count")),
        selected_for_sync=selected_for_sync,
        last_synced_at=utc_now(),
        remote_fingerprint=build_tiktok_fingerprint(fingerprint_source | {"api_version": api_version}),
        created_at=utc_now(),
        updated_at=utc_now(),
    )

