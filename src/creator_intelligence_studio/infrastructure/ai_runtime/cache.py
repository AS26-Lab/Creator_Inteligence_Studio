"""Exact cache for AI execution results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import AICacheEntry, AICacheStatus
from .repository import SQLiteAIRuntimeRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class CacheLookupResult:
    entry: AICacheEntry | None
    hit: bool
    stale: bool


class AICache:
    def __init__(self, repository: SQLiteAIRuntimeRepository) -> None:
        self.repository = repository

    def get(self, cache_key: str) -> CacheLookupResult:
        entry = self.repository.get_cache_entry(cache_key)
        if entry is None:
            return CacheLookupResult(entry=None, hit=False, stale=False)
        if entry.status in {"stale", "invalidated", "expired"}:
            return CacheLookupResult(entry=entry, hit=False, stale=True)
        if entry.expires_at is not None and entry.expires_at <= _utc_now():
            return CacheLookupResult(entry=entry, hit=False, stale=True)
        self.repository.mark_cache_hit(cache_key)
        return CacheLookupResult(entry=entry, hit=True, stale=False)

    def put(self, entry: AICacheEntry) -> AICacheEntry:
        return self.repository.upsert_cache_entry(entry)

    def invalidate(self, cache_key: str) -> None:
        self.repository.invalidate_cache_entry(cache_key)
