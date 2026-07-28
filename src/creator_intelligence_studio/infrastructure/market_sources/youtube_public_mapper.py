"""Mapeo de respuestas publicas de YouTube."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.market_intelligence.value_objects import json_dumps, normalize_text, normalize_url


def map_search_item(item: dict[str, Any]) -> dict[str, Any]:
    snippet = dict(item.get("snippet") or {})
    return {
        "external_entity_type": item.get("id", {}).get("kind", "video"),
        "external_entity_id": item.get("id", {}).get("videoId") or item.get("id", {}).get("channelId") or item.get("id", {}).get("playlistId"),
        "title": normalize_text(snippet.get("title")) or None,
        "description": normalize_text(snippet.get("description")) or None,
        "published_at": snippet.get("publishedAt"),
        "thumbnail_url": normalize_url(((snippet.get("thumbnails") or {}).get("high") or (snippet.get("thumbnails") or {}).get("default") or {}).get("url")),
        "raw_json": json_dumps(item),
    }


def map_video_item(item: dict[str, Any]) -> dict[str, Any]:
    snippet = dict(item.get("snippet") or {})
    stats = dict(item.get("statistics") or {})
    content = dict(item.get("contentDetails") or {})
    return {
        "external_entity_type": "video",
        "external_entity_id": item.get("id"),
        "title": normalize_text(snippet.get("title")) or None,
        "description": normalize_text(snippet.get("description")) or None,
        "published_at": snippet.get("publishedAt"),
        "duration": content.get("duration"),
        "thumbnail_url": normalize_url(((snippet.get("thumbnails") or {}).get("high") or (snippet.get("thumbnails") or {}).get("default") or {}).get("url")),
        "public_metrics": {
            "view_count": stats.get("viewCount"),
            "like_count": stats.get("likeCount"),
            "comment_count": stats.get("commentCount"),
            "favorite_count": stats.get("favoriteCount"),
        },
        "raw_json": json_dumps(item),
    }

