"""Repositorio SQLite para Market and Trend Intelligence Foundation."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.repositories import MarketIntelligenceRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _json_default(value: object) -> object:
    if hasattr(value, "value"):
        return getattr(value, "value")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


class SQLiteMarketIntelligenceRepository(MarketIntelligenceRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: Sequence[Any]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, tuple(params)).fetchone()

    def _fetch_all(self, query: str, params: Sequence[Any]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, tuple(params)).fetchall()

    def upsert_record(self, table: str, record: dict[str, Any], *, conflict_columns: Sequence[str] | None = None) -> dict[str, Any]:
        payload = dict(record)
        columns = list(payload.keys())
        placeholders = ", ".join([f":{column}" for column in columns])
        column_list = ", ".join(columns)
        conflict_clause = ""
        if conflict_columns:
            updates = ", ".join([f"{column}=excluded.{column}" for column in columns if column not in conflict_columns])
            conflict_clause = f" ON CONFLICT({', '.join(conflict_columns)}) DO UPDATE SET {updates}" if updates else f" ON CONFLICT({', '.join(conflict_columns)}) DO NOTHING"
        query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders}){conflict_clause}"
        with self._database.connect() as connection:
            connection.execute(query, payload)
        return self.fetch_record(table, where="id = ?", params=(payload["id"],)) or payload

    def fetch_record(self, table: str, *, where: str, params: Sequence[Any]) -> dict[str, Any] | None:
        row = self._fetch_one(f"SELECT * FROM {table} WHERE {where} LIMIT 1", params)
        return dict(row) if row is not None else None

    def fetch_records(self, table: str, *, where: str = "", params: Sequence[Any] = (), order_by: str | None = None) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        rows = self._fetch_all(sql, params)
        return [dict(row) for row in rows]

    def delete_records(self, table: str, *, where: str, params: Sequence[Any]) -> int:
        with self._database.connect() as connection:
            cursor = connection.execute(f"DELETE FROM {table} WHERE {where}", tuple(params))
            return int(cursor.rowcount or 0)

