"""Contratos de persistencia para Content Briefs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ContentBriefRepository(ABC):
    @abstractmethod
    def upsert_record(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        conflict_columns: tuple[str, ...] = ("id",),
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_record(self, table: str, *, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def fetch_records(
        self,
        table: str,
        *,
        where: str = "",
        params: tuple[Any, ...] = (),
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete_record(self, table: str, *, where: str, params: tuple[Any, ...]) -> int:
        raise NotImplementedError

