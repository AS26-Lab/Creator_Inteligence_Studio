from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations


def _table_columns(connection: sqlite3.Connection, table: str) -> dict[str, dict[str, object]]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1]: {"notnull": bool(row[3]), "default": row[4]} for row in rows}


class ComponentManagerMigrationTests(unittest.TestCase):
    def test_new_database_reaches_v32_and_seeds_foundation_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "runtime.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                indexes = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}

                self.assertTrue(
                    {
                        "component_catalog",
                        "component_installations",
                        "hardware_profiles",
                        "transcription_profiles",
                        "transcription_runtime_checks",
                        "component_events",
                    }.issubset(tables)
                )
                self.assertIn("uq_component_catalog_component_version", indexes)
                self.assertIn("uq_transcription_profiles_profile_version", indexes)
                self.assertIn("idx_component_events_created_at", indexes)
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 32)
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM component_catalog").fetchone()[0], 0)
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM transcription_profiles").fetchone()[0], 0)

                component_columns = _table_columns(connection, "component_installations")
                self.assertIn("installation_status", component_columns)
                self.assertIn("health_status", component_columns)
                self.assertFalse(component_columns["component_id"]["notnull"] is False)

    def test_v31_database_upgrades_idempotently_to_v32(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "upgrade.db", timeout_seconds=5.0)
            with db.connect() as connection:
                connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
                connection.execute(
                    """
                    CREATE TABLE ai_executions (
                        id TEXT PRIMARY KEY,
                        request_fingerprint TEXT NOT NULL
                    )
                    """
                )
                for version in range(1, 32):
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (version, f"migration_{version}", "2026-08-06T00:00:00Z"),
                    )
                run_migrations(connection)
                first_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
                run_migrations(connection)
                second_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

                self.assertEqual(first_count, second_count)
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 32)


if __name__ == "__main__":
    unittest.main()
