"""Acceso a SQLite para Creator Intelligence Studio."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import ProjectPaths


class DatabaseError(RuntimeError):
    """Error de infraestructura de base de datos."""


@dataclass(frozen=True, slots=True)
class SQLiteDatabase:
    """Configura el acceso a la base SQLite local."""

    database_path: Path
    timeout_seconds: float

    def ensure_parent_directory(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Abre una conexion con foreign keys habilitadas."""

        self.ensure_parent_directory()
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=self.timeout_seconds,
            )
        except sqlite3.Error as exc:  # pragma: no cover - muy raro
            raise DatabaseError(
                f"No se pudo abrir la base de datos local: {self.database_path}"
            ) from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def build_database(settings: AppSettings, paths: ProjectPaths) -> SQLiteDatabase:
    """Construye el acceso a la base de datos local."""

    return SQLiteDatabase(
        database_path=paths.database_path,
        timeout_seconds=settings.database_timeout_seconds,
    )
