"""Cliente para TikTok Display API."""

from __future__ import annotations

import json
import urllib.parse
from typing import Callable


class TikTokDisplayApiClient:
    def __init__(
        self,
        *,
        api_version: str = "v2",
        base_url: str = "https://open.tiktokapis.com",
        request_sender: Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]] | None = None,
    ) -> None:
        self.api_version = api_version
        self.base_url = base_url.rstrip("/")
        self._request_sender = request_sender

    def _request(self, method: str, path: str, *, token: str, fields: tuple[str, ...], body: dict[str, object] | None = None) -> dict[str, object]:
        url = f"{self.base_url}{path}"
        if fields:
            url += f"?{urllib.parse.urlencode({'fields': ','.join(fields)})}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = json.dumps(body or {}, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        if self._request_sender is not None:
            status_code, response_headers, response_body = self._request_sender(method, url, headers, payload)
            del status_code, response_headers
            return json.loads(response_body.decode("utf-8"))
        from urllib import request as urllib_request

        req = urllib_request.Request(url, data=payload, headers=headers, method=method)
        with urllib_request.urlopen(req, timeout=30) as response:  # pragma: no cover - network path
            return json.loads(response.read().decode("utf-8"))

    def get_user_info(self, *, token: str, fields: tuple[str, ...]) -> dict[str, object]:
        return self._request("GET", "/v2/user/info/", token=token, fields=fields)

    def list_videos(self, *, token: str, cursor: int | None = None, max_count: int | None = None, fields: tuple[str, ...]) -> dict[str, object]:
        body: dict[str, object] = {}
        if cursor is not None:
            body["cursor"] = cursor
        if max_count is not None:
            body["max_count"] = max_count
        return self._request("POST", "/v2/video/list/", token=token, fields=fields, body=body)

    def query_videos(self, *, token: str, video_ids: tuple[str, ...], fields: tuple[str, ...]) -> dict[str, object]:
        return self._request(
            "POST",
            "/v2/video/query/",
            token=token,
            fields=fields,
            body={"filters": {"video_ids": list(video_ids)}},
        )

