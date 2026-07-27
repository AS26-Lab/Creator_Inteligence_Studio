"""Mapeador de respuestas de cuenta Instagram."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramProfessionalAccountType
from creator_intelligence_studio.domain.instagram_integration.entities import InstagramAccount
from creator_intelligence_studio.infrastructure.instagram.api_version import InstagramApiVersionConfig
from creator_intelligence_studio.infrastructure.instagram.value_objects import build_instagram_fingerprint


def _safe_str(value: Any | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_int(value: Any | None) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def map_account_payload(
    payload: dict[str, Any],
    *,
    creator_id: str,
    connection_id: str,
    instagram_user_id: str | None = None,
    api_version: InstagramApiVersionConfig | None = None,
) -> InstagramAccount:
    user_id = instagram_user_id or _safe_str(payload.get("id")) or ""
    now = datetime.now(timezone.utc)
    raw_type = _safe_str(payload.get("account_type")) or _safe_str(payload.get("professional_account_type")) or "unknown"
    account_type = {
        "business": InstagramProfessionalAccountType.BUSINESS,
        "creator": InstagramProfessionalAccountType.CREATOR,
        "personal": InstagramProfessionalAccountType.PERSONAL,
    }.get(raw_type.lower(), InstagramProfessionalAccountType.UNKNOWN)
    fingerprint = build_instagram_fingerprint(
        {
            "provider": "instagram",
            "api_version": None if api_version is None else api_version.configured_version,
            "id": user_id,
            "username": _safe_str(payload.get("username")),
            "name": _safe_str(payload.get("name")),
            "biography": _safe_str(payload.get("biography")),
            "website": _safe_str(payload.get("website")),
            "profile_picture_url": _safe_str(payload.get("profile_picture_url") or payload.get("profile_pic_url")),
            "followers_count": _safe_int(payload.get("followers_count") or payload.get("follower_count")),
            "follows_count": _safe_int(payload.get("follows_count")),
            "media_count": _safe_int(payload.get("media_count")),
            "account_type": account_type.value,
        }
    )
    return InstagramAccount(
        id=str(uuid4()),
        creator_id=creator_id,
        connection_id=connection_id,
        instagram_user_id=user_id,
        username=_safe_str(payload.get("username")) or user_id,
        name=_safe_str(payload.get("name")),
        biography=_safe_str(payload.get("biography")),
        website=_safe_str(payload.get("website")),
        profile_picture_url=_safe_str(payload.get("profile_picture_url") or payload.get("profile_pic") or payload.get("profile_pic_url")),
        followers_count=_safe_int(payload.get("followers_count") or payload.get("follower_count")),
        follows_count=_safe_int(payload.get("follows_count") or payload.get("follows_count")),
        media_count=_safe_int(payload.get("media_count")),
        account_type=account_type,
        selected_for_sync=bool(payload.get("selected_for_sync", False)),
        last_synced_at=None,
        remote_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
    )

