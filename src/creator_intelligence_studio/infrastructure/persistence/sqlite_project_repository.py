"""Repositorio SQLite para proyectos."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime, timezone

from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.domain.projects.repositories import ProjectRepository
from creator_intelligence_studio.domain.errors import ConflictError
from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        description=row["description"],
        project_type=ProjectType(row["project_type"]),
        status=ProjectStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]),
        updated_at=from_iso_z(row["updated_at"]),
    )


class SQLiteProjectRepository(ProjectRepository):
    """Repositorio de proyectos sobre SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def create(self, project: Project) -> Project:
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO projects (id, creator_id, name, description, project_type, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project.id,
                        project.creator_id,
                        project.name,
                        project.description,
                        project.project_type.value,
                        project.status.value,
                        to_iso_z(project.created_at),
                        to_iso_z(project.updated_at),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("No se pudo crear el proyecto. Verifica el creador y el nombre.") from exc
        return project

    def list(self) -> list[Project]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_project(row) for row in rows]

    def list_by_creator(self, creator_id: str) -> list[Project]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects WHERE creator_id = ? ORDER BY created_at ASC",
                (creator_id,),
            ).fetchall()
        return [_row_to_project(row) for row in rows]

    def get_by_id(self, project_id: str) -> Project | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return _row_to_project(row) if row else None

    def archive(self, project_id: str) -> Project | None:
        project = self.get_by_id(project_id)
        if project is None:
            return None
        archived = replace(project, status=ProjectStatus.ARCHIVED, updated_at=datetime.now(timezone.utc))
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                (archived.status.value, to_iso_z(archived.updated_at), project.id),
            )
        return archived
