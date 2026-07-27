"""Paginacion cursor-based para Instagram."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class InstagramPage:
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None = None
    previous_cursor: str | None = None
    raw_json: str | None = None

