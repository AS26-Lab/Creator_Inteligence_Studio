"""Helpers de paginacion para TikTok v2."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TikTokPage:
    items: tuple[dict[str, object], ...]
    cursor: str | None
    has_more: bool
    raw: dict[str, object]


def extract_cursor(payload: dict[str, object]) -> str | None:
    data = payload.get("data")
    if isinstance(data, dict):
        cursor = data.get("cursor")
        if isinstance(cursor, int):
            return str(cursor)
        if isinstance(cursor, str) and cursor:
            return cursor
        search_id = data.get("search_id")
        if isinstance(search_id, str) and search_id:
            return search_id
    cursor = payload.get("cursor")
    if isinstance(cursor, int):
        return str(cursor)
    if isinstance(cursor, str) and cursor:
        return cursor
    return None


def extract_has_more(payload: dict[str, object]) -> bool:
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("has_more"), bool):
        return bool(data["has_more"])
    if isinstance(payload.get("has_more"), bool):
        return bool(payload["has_more"])
    return False


def extract_items(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    data = payload.get("data")
    if isinstance(data, dict):
        videos = data.get("videos")
        if isinstance(videos, list):
            return tuple(item for item in videos if isinstance(item, dict))
        user = data.get("user")
        if isinstance(user, dict):
            return (user,)
    if isinstance(payload.get("items"), list):
        return tuple(item for item in payload["items"] if isinstance(item, dict))
    return tuple()

