"""Repositorio SQLite para creadores."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime, timezone

from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.creators.repositories import CreatorRepository
from creator_intelligence_studio.domain.errors import ConflictError
from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _row_to_creator(row: sqlite3.Row) -> Creator:
    return Creator(
        id=row["id"],
        display_name=row["display_name"],
        slug=row["slug"],
        description=row["description"],
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
        status=CreatorStatus(row["status"]),
    )


class SQLiteCreatorRepository(CreatorRepository):
    """Repositorio de creadores sobre SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def create(self, creator: Creator) -> Creator:
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO creators (id, display_name, slug, description, created_at, updated_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        creator.id,
                        creator.display_name,
                        creator.slug,
                        creator.description,
                        to_iso_z(creator.created_at),
                        to_iso_z(creator.updated_at),
                        creator.status.value,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("Ya existe un creador con ese slug.") from exc
        return creator

    def list(self) -> list[Creator]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creators ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_creator(row) for row in rows]

    def get_by_id(self, creator_id: str) -> Creator | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creators WHERE id = ?",
                (creator_id,),
            ).fetchone()
        return _row_to_creator(row) if row else None

    def get_by_slug(self, slug: str) -> Creator | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creators WHERE slug = ?",
                (slug,),
            ).fetchone()
        return _row_to_creator(row) if row else None

    def archive(self, creator_id: str) -> Creator | None:
        creator = self.get_by_id(creator_id)
        if creator is None:
            return None
        updated_at = datetime.now(timezone.utc)
        archived = replace(
            creator,
            status=CreatorStatus.ARCHIVED,
            updated_at=updated_at,
        )
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE creators SET status = ?, updated_at = ? WHERE id = ?",
                (archived.status.value, to_iso_z(archived.updated_at), creator.id),
            )
        return archived
