from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from creator_intelligence_studio.application.services.transcription_capability_resolver import TranscriptionCapabilityResolver
from creator_intelligence_studio.domain.hardware.entities import GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import SQLiteComponentManagerRepository
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths


def _table_columns(connection: sqlite3.Connection, table: str) -> dict[str, dict[str, object]]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1]: {"notnull": bool(row[3]), "default": row[4]} for row in rows}


def _paths(temp_dir: str) -> ProjectPaths:
    settings = AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="runtime.db",
        database_timeout_seconds=5.0,
        audio_cache_version="v1",
    )
    root = Path(temp_dir)
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    return paths


def _create_legacy_v32_schema(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
    for version in range(1, 33):
        connection.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
            (version, f"migration_{version}", "2026-08-06T00:00:00Z"),
        )
    connection.execute(
        """
        CREATE TABLE component_catalog (
            id TEXT PRIMARY KEY,
            component_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('ffmpeg', 'transcription_runtime', 'transcription_model', 'optional_support')),
            version TEXT,
            revision TEXT,
            platform TEXT,
            architecture TEXT,
            source_type TEXT NOT NULL,
            source_identifier TEXT,
            allowed_domains_json TEXT NOT NULL DEFAULT '[]',
            expected_download_bytes INTEGER,
            expected_installed_bytes INTEGER,
            temporary_space_bytes INTEGER,
            sha256 TEXT,
            license_name TEXT,
            license_url TEXT,
            attribution TEXT,
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            capabilities_enabled_json TEXT NOT NULL DEFAULT '[]',
            minimum_requirements_json TEXT NOT NULL DEFAULT '{}',
            recommended_requirements_json TEXT NOT NULL DEFAULT '{}',
            install_strategy TEXT,
            health_check TEXT,
            rollback_supported INTEGER NOT NULL DEFAULT 0,
            catalog_version INTEGER NOT NULL,
            reviewed_at TEXT,
            status TEXT NOT NULL CHECK (status IN ('verified', 'pending_verification', 'legacy', 'unsupported', 'unknown')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE UNIQUE INDEX uq_component_catalog_component_version ON component_catalog(component_id, catalog_version)")
    connection.execute("CREATE TABLE component_installations (id TEXT PRIMARY KEY, component_id TEXT NOT NULL UNIQUE, updated_at TEXT)")
    connection.execute("CREATE TABLE transcription_profiles (id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL)")
    connection.execute("CREATE TABLE transcription_runtime_checks (id TEXT PRIMARY KEY, component_id TEXT, checked_at TEXT, metadata_json TEXT NOT NULL DEFAULT '{}')")
    connection.execute("CREATE TABLE ai_executions (id TEXT PRIMARY KEY, request_fingerprint TEXT NOT NULL)")


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
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 36)
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM component_catalog").fetchone()[0], 0)
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM transcription_profiles").fetchone()[0], 0)

                component_columns = _table_columns(connection, "component_installations")
                self.assertIn("installation_status", component_columns)
                self.assertIn("health_status", component_columns)
                self.assertFalse(component_columns["component_id"]["notnull"] is False)

                catalog_columns = _table_columns(connection, "component_catalog")
                self.assertIn("source_provider", catalog_columns)
                self.assertIn("expected_sha256", catalog_columns)
                self.assertIn("verified_at", catalog_columns)

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
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 36)

    def test_legacy_v32_database_without_product_columns_still_bootstraps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "legacy.db", timeout_seconds=5.0)
            with db.connect() as connection:
                _create_legacy_v32_schema(connection)
                run_migrations(connection)
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 36)
                catalog_columns = _table_columns(connection, "component_catalog")
                self.assertIn("source_provider", catalog_columns)
                self.assertIn("source_url", catalog_columns)
                self.assertIn("release_tag", catalog_columns)
                self.assertIn("asset_name", catalog_columns)
                self.assertIn("expected_sha256", catalog_columns)
                self.assertIn("verified_at", catalog_columns)
                self.assertGreater(connection.execute("SELECT COUNT(*) FROM component_catalog").fetchone()[0], 0)

            paths = _paths(temp_dir)
            repository = SQLiteComponentManagerRepository(db)
            catalog = repository.get_catalog()
            ffmpeg = catalog.get_entry("ffmpeg")
            self.assertIsNotNone(ffmpeg)
            self.assertEqual(ffmpeg.source_provider, "btbn")
            self.assertEqual(ffmpeg.upstream_project, "ffmpeg")
            self.assertEqual(ffmpeg.license_variant, "lgpl")
            self.assertEqual(ffmpeg.release_tag, "autobuild-2026-07-31-14-10")
            self.assertEqual(ffmpeg.asset_name, "ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip")
            self.assertEqual(ffmpeg.expected_sha256, "089e4169e93b2b3f3acbfced3c0704d24276a225641bdda04d796d28b07a2a38")

            resolver = TranscriptionCapabilityResolver(
                repository=repository,
                paths=paths,
                model_manager=TranscriptionModelManager(paths.models_directory),
            )
            hardware = HardwareProfile(
                generated_at=datetime.now(tz=timezone.utc),
                platform="Windows",
                architecture="AMD64",
                cpu_logical_count=8,
                cpu_summary="AMD64",
                ram_total_bytes=16 * 1024 * 1024 * 1024,
                ram_available_bytes=8 * 1024 * 1024 * 1024,
                gpu=GpuSummary(
                    vendor=None,
                    name=None,
                    driver_version=None,
                    vram_total_bytes=None,
                    cuda_visible=False,
                    status=HardwareCapabilityState.NOT_DETECTED,
                ),
                driver_summary=None,
                cuda_reported=None,
                ctranslate2_cuda_status=HardwareCapabilityState.NOT_DETECTED,
                disk_volumes=(),
                detection_source="test",
                status=HardwareCapabilityState.NOT_DETECTED,
                warnings=(),
                errors=(),
            )
            report = resolver.resolve(requested_profile="balanced", preferred_device="auto", hardware_profile=hardware)
            action_types = {action.action_type for action in report.structured_suggested_actions}
            self.assertIn("download_product_source", action_types)
            self.assertIn("ffmpeg", report.missing_component_ids)
            self.assertEqual(report.structured_suggested_actions[0].target_component, "ffmpeg")


if __name__ == "__main__":
    unittest.main()
