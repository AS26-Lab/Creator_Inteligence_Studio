"""Adaptador para fuentes manuales."""

from __future__ import annotations

from typing import Any

from .source_adapter import MarketSourcePage


class ManualSourceAdapter:
    source_type = "manual"

    def is_available(self) -> bool:
        return True

    def search(self, query: dict[str, Any]) -> MarketSourcePage:
        items = tuple(dict(item) for item in query.get("items", [])) if query.get("items") else ()
        return MarketSourcePage(items=items, next_cursor=None, raw_json=None)

