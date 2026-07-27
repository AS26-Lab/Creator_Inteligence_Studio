"""Cliente HTTP de lectura para Instagram."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from creator_intelligence_studio.domain.instagram_integration.connection_types import InstagramAuthProvider
from creator_intelligence_studio.domain.instagram_integration.errors import InstagramSyncError
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod
from creator_intelligence_studio.infrastructure.instagram.api_version import InstagramApiVersionConfig, DEFAULT_INSTAGRAM_API_VERSION
from creator_intelligence_studio.infrastructure.instagram.pagination import InstagramPage


@dataclass(frozen=True, slots=True)
class InstagramApiResponse:
    payload: dict[str, Any]
    raw_json: str
    headers: dict[str, str]


class InstagramApiClient:
    def __init__(self, *, api_version: InstagramApiVersionConfig | None = None, provider: InstagramAuthProvider = InstagramAuthProvider.INSTAGRAM_LOGIN) -> None:
        self.api_version = api_version or DEFAULT_INSTAGRAM_API_VERSION
        self.provider = provider

    @property
    def base_url(self) -> str:
        return "https://graph.instagram.com" if self.provider == InstagramAuthProvider.INSTAGRAM_LOGIN else "https://graph.facebook.com"

    def _request_json(self, path: str, *, token: str, params: dict[str, object] | None = None) -> InstagramApiResponse:
        query = params or {}
        query.setdefault("access_token", token)
        url = f"{self.base_url}/{self.api_version.configured_version}/{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return InstagramApiResponse(payload=json.loads(raw), raw_json=raw, headers={key.lower(): value for key, value in response.headers.items()})
        except Exception as exc:  # pragma: no cover - network dependent
            raise InstagramSyncError(f"No se pudo consultar Instagram: {exc}") from exc

    def fetch_account(self, *, token: str, instagram_user_id: str, fields: tuple[str, ...]) -> InstagramApiResponse:
        return self._request_json(instagram_user_id, token=token, params={"fields": ",".join(fields)})

    def fetch_media(self, *, token: str, instagram_user_id: str, fields: tuple[str, ...], after: str | None = None, before: str | None = None, limit: int = 25) -> InstagramApiResponse:
        params: dict[str, object] = {"fields": ",".join(fields), "limit": limit}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        return self._request_json(f"{instagram_user_id}/media", token=token, params=params)

    def fetch_children(self, *, token: str, media_id: str, fields: tuple[str, ...]) -> InstagramApiResponse:
        return self._request_json(f"{media_id}/children", token=token, params={"fields": ",".join(fields)})

    def fetch_account_insights(self, *, token: str, instagram_user_id: str, metrics: tuple[str, ...], period: InstagramInsightPeriod) -> InstagramApiResponse:
        return self._request_json(f"{instagram_user_id}/insights", token=token, params={"metric": ",".join(metrics), "period": period.value})

    def fetch_media_insights(self, *, token: str, media_id: str, metrics: tuple[str, ...], period: InstagramInsightPeriod) -> InstagramApiResponse:
        return self._request_json(f"{media_id}/insights", token=token, params={"metric": ",".join(metrics), "period": period.value})

