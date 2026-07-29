"""Repositorio SQLite para Production Preparation."""

from __future__ import annotations

from typing import Any

from creator_intelligence_studio.domain.production_preparation.repositories import ProductionPreparationRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


_ALLOWED_TABLES = {
    "production_context_snapshots",
    "script_outline_requests",
    "script_outlines",
    "outline_sections",
    "outline_beats",
    "outline_segments",
    "outline_talking_point_links",
    "outline_claim_links",
    "outline_proof_requirements",
    "production_scene_plans",
    "production_shot_items",
    "production_shot_groups",
    "production_shot_group_items",
    "production_recording_blocks",
    "production_recording_block_items",
    "production_visual_cues",
    "production_audio_cues",
    "production_on_screen_text",
    "production_broll_requirements",
    "production_graphic_requirements",
    "production_screen_recordings",
    "production_participant_requirements",
    "production_location_requirements",
    "production_prop_requirements",
    "production_wardrobe_requirements",
    "production_equipment_requirements",
    "production_continuity_rules",
    "production_platform_variants",
    "production_reusable_segments",
    "production_dependencies",
    "production_milestones",
    "production_checklists",
    "production_checklist_items",
    "production_approval_gates",
    "production_risks",
    "production_reviews",
    "production_snapshots",
    "production_reports",
}


def _ensure_table_name(table: str) -> str:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Tabla de production preparation no permitida: {table}")
    return table


class SQLiteProductionPreparationRepository(ProductionPreparationRepository):
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
        return dict(row) if row is not None else dict(payload)

    def fetch_record(self, table: str, *, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        table = _ensure_table_name(table)
        with self._database.connect() as connection:
            row = connection.execute(f"SELECT * FROM {table} WHERE {where} LIMIT 1", params).fetchone()
        return dict(row) if row is not None else None

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

