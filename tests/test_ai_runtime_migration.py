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


class AIRuntimeMigrationTests(unittest.TestCase):
    def test_new_database_migrates_to_v31_with_expected_tables_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "runtime.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                indexes = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}

                self.assertTrue({"ai_model_catalog", "ai_model_role_assignments", "ai_prompt_templates", "ai_executions", "ai_execution_payloads", "ai_usage_records", "ai_budget_policies", "ai_cache_entries", "ai_runtime_settings"}.issubset(tables))
                self.assertIn("uq_ai_model_catalog_provider_model_snapshot", indexes)
                self.assertIn("uq_ai_model_role_assignments_scope_role_provider", indexes)
                self.assertIn("uq_ai_prompt_templates_key_version", indexes)
                self.assertIn("idx_ai_executions_request_fingerprint", indexes)
                self.assertIn("idx_ai_cache_entries_status", indexes)

                execution_columns = _table_columns(connection, "ai_executions")
                self.assertIn("input_summary_json", execution_columns)
                self.assertNotIn("api_key", execution_columns)
                self.assertFalse(execution_columns["creator_id"]["notnull"])
                self.assertFalse(execution_columns["project_id"]["notnull"])
                self.assertEqual(execution_columns["request_fingerprint"]["notnull"], True)

                role_columns = _table_columns(connection, "ai_model_role_assignments")
                self.assertFalse(role_columns["creator_id"]["notnull"])

                fk_rows = connection.execute("PRAGMA foreign_key_list(ai_executions)").fetchall()
                fk_targets = {(row[2], row[3], row[4]) for row in fk_rows}
                self.assertIn(("creators", "creator_id", "id"), fk_targets)

                self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 31").fetchone()[0], 1)

    def test_v31_repair_replaces_unique_request_fingerprint_index_without_losing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "repair.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)
                connection.execute("DROP INDEX IF EXISTS idx_ai_executions_request_fingerprint")
                connection.execute("DROP INDEX IF EXISTS uq_ai_executions_request_fingerprint")
                connection.execute("CREATE UNIQUE INDEX uq_ai_executions_request_fingerprint ON ai_executions(request_fingerprint)")
                model_id = "repair-model"
                template_id = "provider-diagnostic-template"
                connection.execute(
                    """
                    INSERT INTO ai_model_catalog (
                        id, provider, model_id, display_name, snapshot_or_version, status,
                        capabilities_json, context_limit, supports_structured_output,
                        supports_image_input, supports_audio_input,
                        input_price_per_million, output_price_per_million, cached_input_price_per_million,
                        pricing_currency, pricing_effective_at, last_verified_at, replacement_model_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model_id,
                        "openai",
                        "repair-model",
                        "Repair Model",
                        "v1",
                        "approved",
                        "{}",
                        4096,
                        1,
                        0,
                        0,
                        1.0,
                        1.0,
                        0.1,
                        "USD",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        None,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO ai_prompt_templates (
                        id, template_key, task_type, operation, version, status,
                        required_capabilities_json, instruction_layers_json, input_schema_json,
                        output_schema_json, validation_profile_json, benchmark_id, change_notes,
                        approved_at, deprecated_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        template_id,
                        "provider_diagnostic",
                        "provider_diagnostic",
                        "extract",
                        1,
                        "approved",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        "{}",
                        None,
                        "repair test",
                        "2026-07-29T00:00:00Z",
                        None,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO ai_executions (
                        id, execution_uuid, creator_id, project_id, task_type, operation, status,
                        requested_model_role, provider, model_catalog_id, template_id, privacy_class,
                        quality_level, context_fingerprint, request_fingerprint, input_summary_json,
                        output_reference, validation_status, cache_status, fallback_policy,
                        approval_required, approved_at, started_at, completed_at, latency_ms,
                        error_category, error_code, error_message_safe, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "execution-a",
                        "execution-a",
                        None,
                        None,
                        "provider_diagnostic",
                        "extract",
                        "completed",
                        "cheap_structured_model",
                        "openai",
                        model_id,
                        template_id,
                        "selected_text_allowed",
                        "standard",
                        None,
                        "fingerprint-x",
                        "{\"request_id\": \"request-a\", \"task_type\": \"provider_diagnostic\"}",
                        None,
                        "valid",
                        "active",
                        "none",
                        0,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        1,
                        None,
                        None,
                        None,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                before_rows = connection.execute("SELECT COUNT(*) FROM ai_executions").fetchone()[0]
                run_migrations(connection)
                indexes = {row[1]: bool(row[2]) for row in connection.execute("PRAGMA index_list(ai_executions)").fetchall()}
                self.assertIn("idx_ai_executions_request_fingerprint", indexes)
                self.assertFalse(indexes["idx_ai_executions_request_fingerprint"])
                self.assertNotIn("uq_ai_executions_request_fingerprint", indexes)
                connection.execute(
                    """
                    INSERT INTO ai_executions (
                        id, execution_uuid, creator_id, project_id, task_type, operation, status,
                        requested_model_role, provider, model_catalog_id, template_id, privacy_class,
                        quality_level, context_fingerprint, request_fingerprint, input_summary_json,
                        output_reference, validation_status, cache_status, fallback_policy,
                        approval_required, approved_at, started_at, completed_at, latency_ms,
                        error_category, error_code, error_message_safe, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "execution-b",
                        "execution-b",
                        None,
                        None,
                        "provider_diagnostic",
                        "extract",
                        "completed",
                        "cheap_structured_model",
                        "openai",
                        model_id,
                        template_id,
                        "selected_text_allowed",
                        "standard",
                        None,
                        "fingerprint-x",
                        "{\"request_id\": \"request-b\", \"task_type\": \"provider_diagnostic\"}",
                        None,
                        "valid",
                        "active",
                        "none",
                        0,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        1,
                        None,
                        None,
                        None,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                after_rows = connection.execute("SELECT COUNT(*) FROM ai_executions").fetchone()[0]
                self.assertEqual(before_rows + 1, after_rows)

    def test_v30_database_upgrades_idempotently_to_v32(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "upgrade.db", timeout_seconds=5.0)
            with db.connect() as connection:
                connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
                for version in range(1, 31):
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (version, f"migration_{version}", "2026-07-29T00:00:00Z"),
                    )
                run_migrations(connection)
                first_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
                run_migrations(connection)
                second_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

                self.assertEqual(first_count, second_count)
                self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 33)

    def test_model_history_survives_deprecation_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "history.db", timeout_seconds=5.0)
            with db.connect() as connection:
                run_migrations(connection)
                connection.execute(
                    """
                    INSERT INTO ai_model_catalog (
                        id, provider, model_id, display_name, snapshot_or_version, status,
                        capabilities_json, context_limit, supports_structured_output,
                        supports_image_input, supports_audio_input,
                        input_price_per_million, output_price_per_million, cached_input_price_per_million,
                        pricing_currency, pricing_effective_at, last_verified_at, replacement_model_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "model-old",
                        "openai",
                        "gpt-old",
                        "Old Model",
                        "v1",
                        "approved",
                        "{}",
                        4096,
                        1,
                        0,
                        0,
                        1.0,
                        1.0,
                        0.1,
                        "USD",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        None,
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO ai_model_catalog (
                        id, provider, model_id, display_name, snapshot_or_version, status,
                        capabilities_json, context_limit, supports_structured_output,
                        supports_image_input, supports_audio_input,
                        input_price_per_million, output_price_per_million, cached_input_price_per_million,
                        pricing_currency, pricing_effective_at, last_verified_at, replacement_model_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "model-new",
                        "openai",
                        "gpt-new",
                        "New Model",
                        "v2",
                        "testing",
                        "{}",
                        4096,
                        1,
                        0,
                        0,
                        1.0,
                        1.0,
                        0.1,
                        "USD",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                        "model-old",
                        "2026-07-29T00:00:00Z",
                        "2026-07-29T00:00:00Z",
                    ),
                )
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM ai_model_catalog").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT replacement_model_id FROM ai_model_catalog WHERE id = 'model-new'").fetchone()[0], "model-old")


if __name__ == "__main__":
    unittest.main()
