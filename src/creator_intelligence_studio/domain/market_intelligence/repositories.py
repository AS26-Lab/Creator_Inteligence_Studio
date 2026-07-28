"""Contratos de persistencia para inteligencia de mercado."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, Any


class MarketIntelligenceRepository(Protocol):
    """Persistencia local para entidades de mercado."""

    def upsert_record(self, table: str, record: dict[str, Any], *, conflict_columns: Sequence[str] | None = None) -> dict[str, Any]: ...

    def fetch_record(self, table: str, *, where: str, params: Sequence[Any]) -> dict[str, Any] | None: ...

    def fetch_records(self, table: str, *, where: str = "", params: Sequence[Any] = (), order_by: str | None = None) -> list[dict[str, Any]]: ...

    def delete_records(self, table: str, *, where: str, params: Sequence[Any]) -> int: ...

