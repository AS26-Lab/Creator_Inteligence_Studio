"""Tipos para medios de Instagram."""

from __future__ import annotations

from enum import Enum

from .connection_types import InstagramContentType, InstagramMediaType


class InstagramRemoteMediaStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED_REMOTE_MEDIA = "expired_remote_media"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


def map_content_type(media_type: InstagramMediaType, media_product_type: str | None) -> InstagramContentType:
    if media_product_type:
        normalized = media_product_type.strip().lower()
        if normalized == "reels":
            return InstagramContentType.INSTAGRAM_REEL
        if normalized == "feed":
            if media_type == InstagramMediaType.VIDEO:
                return InstagramContentType.INSTAGRAM_VIDEO
            if media_type == InstagramMediaType.CAROUSEL_ALBUM:
                return InstagramContentType.INSTAGRAM_CAROUSEL
            return InstagramContentType.INSTAGRAM_POST
        if normalized == "story":
            return InstagramContentType.INSTAGRAM_STORY
        if normalized == "live":
            return InstagramContentType.INSTAGRAM_LIVE
    if media_type == InstagramMediaType.REELS:
        return InstagramContentType.INSTAGRAM_REEL
    if media_type == InstagramMediaType.CAROUSEL_ALBUM:
        return InstagramContentType.INSTAGRAM_CAROUSEL
    if media_type == InstagramMediaType.VIDEO:
        return InstagramContentType.INSTAGRAM_VIDEO
    if media_type == InstagramMediaType.IMAGE:
        return InstagramContentType.INSTAGRAM_POST
    if media_type == InstagramMediaType.STORIES:
        return InstagramContentType.INSTAGRAM_STORY
    if media_type == InstagramMediaType.LIVE:
        return InstagramContentType.INSTAGRAM_LIVE
    return InstagramContentType.INSTAGRAM_UNKNOWN

