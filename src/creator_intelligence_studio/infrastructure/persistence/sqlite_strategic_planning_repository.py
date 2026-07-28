"""Repositorio SQLite para Strategic Planning."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.strategic_planning.repositories import StrategicPlanningRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


_ALLOWED_TABLES = {
    "planning_context_snapshots",
    "strategic_plans",
    "strategic_objectives",
    "strategic_objective_metrics",
    "strategy_themes",
    "content_pillars",
    "strategic_initiatives",
    "campaigns",
    "content_series",
    "planning_cycles",
    "roadmap_items",
    "roadmap_item_dependencies",
    "roadmap_item_milestones",
    "roadmap_item_metrics",
    "roadmap_item_risks",
    "planning_backlog_items",
    "capacity_profiles",
    "capacity_allocations",
    "resource_constraints",
    "planning_conflicts",
    "planning_scenarios",
    "planning_reviews",
    "planning_snapshots",
    "planning_reports",
    "planning_content_links",
}


def _ensure_table_name(table: str) -> str:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Tabla estrategica no permitida: {table}")
    return table


def _row_to_dict(row) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class SQLiteStrategicPlanningRepository(StrategicPlanningRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_record(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        conflict_columns: tuple[str, ...] = ("id",),
    ) -> dict[str, Any]:
        table = _ensure_table_name(table)
        columns = list(payload.keys())
        placeholders = [f":{column}" for column in columns]
        update_columns = [column for column in columns if column not in conflict_columns]
        conflict_clause = ", ".join(conflict_columns)
        update_clause = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
        if update_clause:
            sql = (
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) "
                f"ON CONFLICT({conflict_clause}) DO UPDATE SET {update_clause}"
            )
        else:
            sql = (
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) "
                f"ON CONFLICT({conflict_clause}) DO NOTHING"
            )
        with self._database.connect() as connection:
            connection.execute(sql, payload)
            if "id" in payload:
                row = connection.execute(f"SELECT * FROM {table} WHERE id = ?", (payload["id"],)).fetchone()
            else:
                where_clause = " AND ".join(f"{column} = ?" for column in conflict_columns)
                row = connection.execute(
                    f"SELECT * FROM {table} WHERE {where_clause}",
                    tuple(payload[column] for column in conflict_columns),
                ).fetchone()
        return _row_to_dict(row) or dict(payload)

    def fetch_record(
        self,
        table: str,
        *,
        where: str,
        params: tuple[Any, ...],
    ) -> dict[str, Any] | None:
        table = _ensure_table_name(table)
        with self._database.connect() as connection:
            row = connection.execute(f"SELECT * FROM {table} WHERE {where} LIMIT 1", params).fetchone()
        return _row_to_dict(row)

    def fetch_records(
        self,
        table: str,
        *,
        where: str = "",
        params: tuple[Any, ...] = (),
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        table = _ensure_table_name(table)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with self._database.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_record(self, table: str, *, where: str, params: tuple[Any, ...]) -> int:
        table = _ensure_table_name(table)
        with self._database.connect() as connection:
            cursor = connection.execute(f"DELETE FROM {table} WHERE {where}", params)
        return int(cursor.rowcount or 0)
