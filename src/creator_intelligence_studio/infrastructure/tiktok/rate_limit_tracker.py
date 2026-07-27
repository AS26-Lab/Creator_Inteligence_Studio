"""Seguimiento local de rate limits para TikTok."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TikTokRateLimitSnapshot:
    operation_key: str
    endpoint: str
    request_count: int
    estimated_usage: str | None
    window_started_at: datetime | None
    response_headers_json: str | None
    usage_date: str


class TikTokRateLimitTracker:
    def __init__(self) -> None:
        self._history: list[TikTokRateLimitSnapshot] = []

    def record(
        self,
        *,
        operation_key: str,
        endpoint: str,
        request_count: int = 1,
        estimated_usage: str | None = None,
        response_headers: dict[str, str] | None = None,
        window_started_at: datetime | None = None,
    ) -> TikTokRateLimitSnapshot:
        now = _utc_now()
        snapshot = TikTokRateLimitSnapshot(
            operation_key=operation_key,
            endpoint=endpoint,
            request_count=request_count,
            estimated_usage=estimated_usage,
            window_started_at=window_started_at,
            response_headers_json=json.dumps(response_headers or {}, ensure_ascii=False, sort_keys=True),
            usage_date=now.date().isoformat(),
        )
        self._history.append(snapshot)
        return snapshot

    def list(self) -> tuple[TikTokRateLimitSnapshot, ...]:
        return tuple(self._history)

    def current_window_start(self) -> datetime:
        now = _utc_now()
        return now - timedelta(minutes=1)

