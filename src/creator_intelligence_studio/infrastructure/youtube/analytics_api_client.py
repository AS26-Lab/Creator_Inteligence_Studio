"""Cliente local/inyectable para YouTube Analytics API."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YouTubeAnalyticsPage:
    rows: tuple[dict[str, object], ...]
    raw_json: str


class YouTubeAnalyticsApiClient:
    BASE_URL = "https://youtubeanalytics.googleapis.com/v2"

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

    def query(self, *, ids: str, metrics: str, dimensions: str | None = None, filters: str | None = None, start_date: str | None = None, end_date: str | None = None, max_results: int = 200, sort: str | None = None) -> YouTubeAnalyticsPage:
        data = self._request_json(
            "reports",
            {
                "ids": ids,
                "metrics": metrics,
                "dimensions": dimensions,
                "filters": filters,
                "startDate": start_date,
                "endDate": end_date,
                "maxResults": max_results,
                "sort": sort,
            },
        )
        rows = tuple(data.get("rows", ()))
        return YouTubeAnalyticsPage(rows=tuple({"row": row} for row in rows), raw_json=json.dumps(data, ensure_ascii=False))

