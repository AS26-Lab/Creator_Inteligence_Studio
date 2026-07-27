"""Seguimiento local de rate limits de Instagram."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class InstagramRateLimitEstimate:
    operation_key: str
    estimated_usage: str | None
    request_count: int
    headers_snapshot_json: str | None = None


class InstagramRateLimitTracker:
    def __init__(self) -> None:
        self._usage: dict[tuple[str, str], int] = {}

    def record(self, connection_id: str, operation_key: str, request_count: int, *, estimated_usage: str | None = None, headers_snapshot_json: str | None = None) -> InstagramRateLimitEstimate:
        key = (connection_id, operation_key)
        self._usage[key] = self._usage.get(key, 0) + request_count
        return InstagramRateLimitEstimate(operation_key=operation_key, estimated_usage=estimated_usage, request_count=self._usage[key], headers_snapshot_json=headers_snapshot_json)

