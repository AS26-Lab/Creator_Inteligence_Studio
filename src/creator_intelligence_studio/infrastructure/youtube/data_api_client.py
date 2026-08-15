"""Cliente local/inyectable para YouTube Data API v3."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YouTubeApiPage:
    items: tuple[dict[str, object], ...]
    next_page_token: str | None
    prev_page_token: str | None
    raw_json: str


class YouTubeDataApiClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, *, access_token: str | None = None, opener=urllib.request.urlopen) -> None:
        self.access_token = access_token
        self._opener = opener

    def _request_json(self, endpoint: str, params: dict[str, object]) -> dict[str, object]:
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None and value != ""})
        url = f"{self.BASE_URL}/{endpoint}?{query}"
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        request = urllib.request.Request(url, headers=headers)
        with self._opener(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:
        data = self._request_json("channels", {"part": part, "mine": "true" if mine else None, "pageToken": page_token, "maxResults": max_results})
        return YouTubeApiPage(tuple(data.get("items", ())), data.get("nextPageToken"), data.get("prevPageToken"), json.dumps(data, ensure_ascii=False))

    def list_videos(self, *, channel_id: str | None = None, ids: tuple[str, ...] | None = None, page_token: str | None = None, max_results: int = 50, part: str = "snippet,contentDetails,statistics,status,topicDetails") -> YouTubeApiPage:
        params: dict[str, object] = {"part": part, "pageToken": page_token, "maxResults": max_results}
        if channel_id:
            params["channelId"] = channel_id
        if ids:
            params["id"] = ",".join(ids)
        data = self._request_json("videos", params)
        return YouTubeApiPage(tuple(data.get("items", ())), data.get("nextPageToken"), data.get("prevPageToken"), json.dumps(data, ensure_ascii=False))

    def list_video_thumbnails(self, *, video_id: str, page_token: str | None = None) -> YouTubeApiPage:
        data = self._request_json("videos", {"part": "snippet", "id": video_id, "pageToken": page_token, "maxResults": 1})
        return YouTubeApiPage(tuple(data.get("items", ())), data.get("nextPageToken"), data.get("prevPageToken"), json.dumps(data, ensure_ascii=False))

    def list_playlist_items(self, *, playlist_id: str, page_token: str | None = None, max_results: int = 50, part: str = "snippet,contentDetails,status") -> YouTubeApiPage:
        data = self._request_json("playlistItems", {"part": part, "playlistId": playlist_id, "pageToken": page_token, "maxResults": max_results})
        return YouTubeApiPage(tuple(data.get("items", ())), data.get("nextPageToken"), data.get("prevPageToken"), json.dumps(data, ensure_ascii=False))
