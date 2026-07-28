"""Adaptador oficial de YouTube Data API para investigacion publica."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request, error

from creator_intelligence_studio.domain.market_intelligence.errors import MarketResearchError, MarketPermissionError
from creator_intelligence_studio.infrastructure.market_sources.retry_policy import is_retryable_status
from creator_intelligence_studio.infrastructure.market_sources.source_adapter import MarketSourcePage


@dataclass(frozen=True, slots=True)
class YouTubePublicRequest:
    endpoint: str
    params: dict[str, Any]


class YouTubePublicAdapter:
    source_type = "youtube_public"

    def __init__(self, *, api_key: str | None = None, base_url: str = "https://www.googleapis.com/youtube/v3") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _request_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise MarketPermissionError("Se requiere API key oficial de YouTube para investigacion publica.")
        query = dict(params)
        query["key"] = self.api_key
        url = f"{self.base_url}/{endpoint}?{parse.urlencode(query, doseq=True)}"
        try:
            with request.urlopen(url, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if is_retryable_status(exc.code):
                raise MarketResearchError(f"YouTube public research temporarily unavailable ({exc.code}).") from exc
            raise MarketResearchError(f"YouTube public research error ({exc.code}). {body[:200]}") from exc
        except Exception as exc:  # pragma: no cover - red no usada en tests
            raise MarketResearchError("No se pudo consultar YouTube Data API publica.") from exc

    def search(self, query: dict[str, Any]) -> MarketSourcePage:
        payload = self._request_json("search", query)
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def search_videos(self, *, query_text: str | None = None, channel_id: str | None = None, region: str | None = None, language: str | None = None, published_after: str | None = None, published_before: str | None = None, max_results: int = 25, page_token: str | None = None) -> MarketSourcePage:
        params: dict[str, Any] = {"part": "snippet", "type": "video", "maxResults": max_results}
        if query_text:
            params["q"] = query_text
        if channel_id:
            params["channelId"] = channel_id
        if region:
            params["regionCode"] = region
        if language:
            params["relevanceLanguage"] = language
        if published_after:
            params["publishedAfter"] = published_after
        if published_before:
            params["publishedBefore"] = published_before
        if page_token:
            params["pageToken"] = page_token
        return self.search(params)

    def list_videos(self, *, ids: tuple[str, ...], max_results: int = 50) -> MarketSourcePage:
        payload = self._request_json("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(ids), "maxResults": max_results})
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def list_channels(self, *, ids: tuple[str, ...]) -> MarketSourcePage:
        payload = self._request_json("channels", {"part": "snippet,contentDetails,statistics", "id": ",".join(ids)})
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def list_playlists(self, *, channel_id: str | None = None, ids: tuple[str, ...] | None = None) -> MarketSourcePage:
        params: dict[str, Any] = {"part": "snippet,contentDetails", "maxResults": 50}
        if channel_id:
            params["channelId"] = channel_id
        if ids:
            params["id"] = ",".join(ids)
        payload = self._request_json("playlists", params)
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def list_playlist_items(self, *, playlist_id: str, page_token: str | None = None, max_results: int = 50) -> MarketSourcePage:
        params: dict[str, Any] = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": max_results}
        if page_token:
            params["pageToken"] = page_token
        payload = self._request_json("playlistItems", params)
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def list_video_categories(self, *, region_code: str) -> MarketSourcePage:
        payload = self._request_json("videoCategories", {"part": "snippet", "regionCode": region_code})
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

    def most_popular(self, *, region_code: str, video_category_id: str | None = None, max_results: int = 25) -> MarketSourcePage:
        params: dict[str, Any] = {"part": "snippet,contentDetails,statistics", "chart": "mostPopular", "regionCode": region_code, "maxResults": max_results}
        if video_category_id:
            params["videoCategoryId"] = video_category_id
        payload = self._request_json("videos", params)
        return MarketSourcePage(items=tuple(payload.get("items", ())), next_cursor=payload.get("nextPageToken"), raw_json=json.dumps(payload, ensure_ascii=False))

