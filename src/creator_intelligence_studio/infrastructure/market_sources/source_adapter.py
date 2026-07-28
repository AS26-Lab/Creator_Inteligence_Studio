"""Contrato de adaptadores de fuentes de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True, slots=True)
class MarketSourcePage:
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None = None
    raw_json: str | None = None


class MarketSourceAdapter(Protocol):
    source_type: str

    def is_available(self) -> bool: ...

    def search(self, query: dict[str, Any]) -> MarketSourcePage: ...

