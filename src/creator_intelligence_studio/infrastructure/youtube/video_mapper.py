"""Mapeos de payloads remotos de videos de YouTube."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from creator_intelligence_studio.domain.youtube_integration.connection_types import YouTubeRemoteContentType
from creator_intelligence_studio.domain.youtube_integration.entities import YouTubeRemoteVideo, YouTubeVideoThumbnail
from creator_intelligence_studio.domain.youtube_integration.services import build_youtube_fingerprint, classify_remote_content_type


def _parse_dt(value: object | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)


def _duration_seconds(payload: dict[str, object]) -> float | None:
    value = payload.get("duration_seconds")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    content = payload.get("contentDetails")
    if isinstance(content, dict):
        duration = content.get("duration")
        if isinstance(duration, str) and duration.startswith("PT"):
            total = 0.0
            number = ""
            for char in duration[2:]:
                if char.isdigit() or char == ".":
                    number += char
                    continue
                if char == "H":
                    total += float(number or 0) * 3600
                elif char == "M":
                    total += float(number or 0) * 60
                elif char == "S":
                    total += float(number or 0)
                number = ""
            return total
    return None


def map_remote_video(
    payload: dict[str, object],
    *,
    creator_id: str,
    channel_id: str,
    publication_id: str | None = None,
    video_asset_id: str | None = None,
) -> YouTubeRemoteVideo:
    snippet = payload.get("snippet") if isinstance(payload.get("snippet"), dict) else {}
    content_details = payload.get("contentDetails") if isinstance(payload.get("contentDetails"), dict) else {}
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    topic = payload.get("topicDetails") if isinstance(payload.get("topicDetails"), dict) else {}
    duration = _duration_seconds(payload)
    content_type_hint = None
    if isinstance(snippet, dict):
        content_type_hint = snippet.get("contentType") or snippet.get("liveBroadcastContent")
    remote_type, confidence, warnings = classify_remote_content_type(
        content_type_hint=str(content_type_hint) if content_type_hint is not None else None,
        duration_seconds=duration,
        has_shorts_dimension=bool(payload.get("isShort") or (isinstance(snippet, dict) and snippet.get("categoryId") == "SHORTS")),
    )
    if remote_type == YouTubeRemoteContentType.UNKNOWN and duration is not None and duration <= 60:
        warnings = (*warnings, "probable_short")
    fingerprint = build_youtube_fingerprint({
        "youtube_video_id": payload.get("id"),
        "title": snippet.get("title") if isinstance(snippet, dict) else None,
        "description": snippet.get("description") if isinstance(snippet, dict) else None,
        "publishedAt": snippet.get("publishedAt") if isinstance(snippet, dict) else None,
        "duration_seconds": duration,
        "privacyStatus": status.get("privacyStatus") if isinstance(status, dict) else None,
        "liveBroadcastContent": snippet.get("liveBroadcastContent") if isinstance(snippet, dict) else None,
    })
    thumbnails = snippet.get("thumbnails") if isinstance(snippet, dict) else {}
    thumbnail_metadata = {}
    if isinstance(thumbnails, dict):
        for name, thumb in thumbnails.items():
            if isinstance(thumb, dict):
                thumbnail_metadata[name] = {
                    "url": thumb.get("url"),
                    "width": thumb.get("width"),
                    "height": thumb.get("height"),
                }
    return YouTubeRemoteVideo(
        id=str(payload.get("id") or ""),
        creator_id=creator_id,
        channel_id=channel_id,
        youtube_video_id=str(payload.get("id") or ""),
        publication_id=publication_id,
        video_asset_id=video_asset_id,
        content_type=remote_type,
        title=str(snippet.get("title") or ""),
        description=str(snippet.get("description")) if snippet.get("description") is not None else None,
        published_at=_parse_dt(snippet.get("publishedAt")),
        duration_seconds=duration,
        privacy_status=str(status.get("privacyStatus")) if status.get("privacyStatus") is not None else None,
        live_broadcast_content=str(snippet.get("liveBroadcastContent")) if snippet.get("liveBroadcastContent") is not None else None,
        default_language=str(snippet.get("defaultLanguage")) if snippet.get("defaultLanguage") is not None else None,
        default_audio_language=str(snippet.get("defaultAudioLanguage")) if snippet.get("defaultAudioLanguage") is not None else None,
        category_id=str(snippet.get("categoryId")) if snippet.get("categoryId") is not None else None,
        tags_json=json.dumps(snippet.get("tags") if isinstance(snippet.get("tags"), list) else [], ensure_ascii=False),
        thumbnail_metadata_json=json.dumps({
            "thumbnails": thumbnail_metadata,
            "warnings": list(warnings),
            "confidence": confidence,
            "topic_details": topic,
        }, ensure_ascii=False),
        remote_fingerprint=fingerprint,
        first_seen_at=_parse_dt(payload.get("first_seen_at") or snippet.get("publishedAt")),
        last_seen_at=_parse_dt(payload.get("last_seen_at") or snippet.get("publishedAt")),
        created_at=_parse_dt(payload.get("created_at") or snippet.get("publishedAt")),
        updated_at=_parse_dt(payload.get("updated_at") or snippet.get("publishedAt")),
    )


def map_video_thumbnails(remote_video_id: str, payload: dict[str, object], *, imported_at: datetime, local_cache_path: str | None = None) -> tuple[YouTubeVideoThumbnail, ...]:
    snippet = payload.get("snippet") if isinstance(payload.get("snippet"), dict) else {}
    thumbnails = snippet.get("thumbnails") if isinstance(snippet, dict) else {}
    items: list[YouTubeVideoThumbnail] = []
    if isinstance(thumbnails, dict):
        for thumb_type, thumb in thumbnails.items():
            if not isinstance(thumb, dict):
                continue
            items.append(
                YouTubeVideoThumbnail(
                    id=build_youtube_fingerprint({
                        "remote_video_id": remote_video_id,
                        "thumbnail_type": thumb_type,
                        "url": thumb.get("url"),
                        "width": thumb.get("width"),
                        "height": thumb.get("height"),
                    }),
                    remote_video_id=remote_video_id,
                    thumbnail_type=thumb_type,
                    remote_url=str(thumb.get("url") or ""),
                    width=int(thumb["width"]) if isinstance(thumb.get("width"), int) else None,
                    height=int(thumb["height"]) if isinstance(thumb.get("height"), int) else None,
                    local_cache_path=local_cache_path,
                    remote_fingerprint=build_youtube_fingerprint(thumb),
                    imported_at=imported_at,
                    created_at=imported_at,
                )
            )
    return tuple(items)

