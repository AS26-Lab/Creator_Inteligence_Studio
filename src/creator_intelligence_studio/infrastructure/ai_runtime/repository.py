"""SQLite repository for AI runtime data."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Protocol

from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase

from .models import (
    AIBudgetPolicy,
    AICacheEntry,
    AICacheStatus,
    AIExecutionPayload,
    AIExecutionRecord,
    AIExecutionRequest,
    AIExecutionResult,
    AIExecutionUsage,
    AIModelCatalogEntry,
    AIPromptTemplate,
    AIRoleAssignment,
    AIRuntimeSetting,
    AIUsageRecord,
)


_ACTIVE_EXECUTION_STATUSES = {
    "queued",
    "preparing_context",
    "awaiting_approval",
    "running",
    "validating",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: str | None) -> Any:
    import json

    if not value:
        return None
    return json.loads(value)


class AIExecutionRepository(Protocol):
    def upsert_model_catalog_entry(self, entry: AIModelCatalogEntry) -> AIModelCatalogEntry: ...
    def list_model_catalog_entries(self, provider: str | None = None) -> list[AIModelCatalogEntry]: ...
    def get_model_catalog_entry(self, model_catalog_id: str) -> AIModelCatalogEntry | None: ...
    def upsert_role_assignment(self, assignment: AIRoleAssignment) -> AIRoleAssignment: ...
    def list_role_assignments(self, creator_id: str | None = None, provider: str | None = None) -> list[AIRoleAssignment]: ...
    def resolve_role_assignment(self, role: str, creator_id: str | None = None, provider: str | None = None) -> AIRoleAssignment | None: ...
    def upsert_prompt_template(self, template: AIPromptTemplate) -> AIPromptTemplate: ...
    def get_prompt_template(self, template_key: str, version: int | None = None) -> AIPromptTemplate | None: ...
    def list_prompt_templates(self, status: str | None = None) -> list[AIPromptTemplate]: ...
    def upsert_budget_policy(self, policy: AIBudgetPolicy) -> AIBudgetPolicy: ...
    def get_budget_policy(self, creator_id: str | None = None, provider: str | None = None) -> AIBudgetPolicy | None: ...
    def upsert_runtime_setting(self, setting: AIRuntimeSetting) -> AIRuntimeSetting: ...
    def get_runtime_setting(self, scope_type: str, setting_key: str, scope_id: str | None = None) -> AIRuntimeSetting | None: ...
    def store_execution(self, execution: AIExecutionRecord) -> AIExecutionRecord: ...
    def get_execution_by_uuid(self, execution_uuid: str) -> AIExecutionRecord | None: ...
    def list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 100) -> list[AIExecutionRecord]: ...
    def claim_execution_for_resume(
        self,
        execution_uuid: str,
        *,
        approved_at: str,
        approved_by: str | None = None,
        approval_reason: str | None = None,
        approval_summary: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None: ...
    def update_execution_status(
        self,
        execution_uuid: str,
        *,
        status: str,
        expected_statuses: tuple[str, ...] | None = None,
        input_summary_updates: dict[str, Any] | None = None,
        approved_at: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        latency_ms: int | None = None,
        validation_status: str | None = None,
        cache_status: str | None = None,
        output_reference: str | None = None,
        error_category: str | None = None,
        error_code: str | None = None,
        error_message_safe: str | None = None,
        approval_required: bool | None = None,
    ) -> AIExecutionRecord | None: ...
    def persist_provider_result(
        self,
        execution_uuid: str,
        *,
        status: str,
        validation_status: str,
        cache_status: str,
        completed_at: str,
        latency_ms: int | None,
        output_reference: str,
        input_summary_updates: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None: ...
    def persist_execution_failure(
        self,
        execution_uuid: str,
        *,
        status: str,
        completed_at: str,
        latency_ms: int | None,
        error_category: str,
        error_code: str | None,
        error_message_safe: str,
        validation_status: str | None = None,
        input_summary_updates: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None: ...
    def store_payload(self, payload: AIExecutionPayload) -> AIExecutionPayload: ...
    def list_payloads(self, execution_id: str) -> list[AIExecutionPayload]: ...
    def store_usage(self, usage: AIUsageRecord) -> AIUsageRecord: ...
    def list_usage_records(self, execution_id: str | None = None) -> list[AIUsageRecord]: ...
    def upsert_cache_entry(self, entry: AICacheEntry) -> AICacheEntry: ...
    def get_cache_entry(self, cache_key: str) -> AICacheEntry | None: ...
    def invalidate_cache_entry(self, cache_key: str) -> None: ...
    def mark_cache_hit(self, cache_key: str) -> None: ...


class SQLiteAIRuntimeRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.database.connect() as connection:
            connection.execute(sql, params)

    def _query_one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            return connection.execute(sql, params).fetchone()

    def _query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(connection.execute(sql, params).fetchall())

    def upsert_model_catalog_entry(self, entry: AIModelCatalogEntry) -> AIModelCatalogEntry:
        now = entry.updated_at or _utc_now()
        created_at = entry.created_at or now
        record_id = entry.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id, created_at
                FROM ai_model_catalog
                WHERE provider = ? AND model_id = ? AND IFNULL(snapshot_or_version, '') = IFNULL(?, '')
                """,
                (entry.provider, entry.model_id, entry.snapshot_or_version),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_model_catalog (
                        id,
                        provider, model_id, display_name, snapshot_or_version, status,
                        capabilities_json, context_limit, supports_structured_output,
                        supports_image_input, supports_audio_input,
                        input_price_per_million, output_price_per_million, cached_input_price_per_million,
                        pricing_currency, pricing_effective_at, last_verified_at, replacement_model_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        entry.provider,
                        entry.model_id,
                        entry.display_name,
                        entry.snapshot_or_version,
                        entry.status,
                        _json(entry.capabilities_json),
                        entry.context_limit,
                        1 if entry.supports_structured_output else 0,
                        1 if entry.supports_image_input else 0,
                        1 if entry.supports_audio_input else 0,
                        entry.input_price_per_million,
                        entry.output_price_per_million,
                        entry.cached_input_price_per_million,
                        entry.pricing_currency,
                        entry.pricing_effective_at,
                        entry.last_verified_at,
                        entry.replacement_model_id,
                        created_at,
                        now,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_model_catalog WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_model_catalog
                    SET display_name = ?, status = ?, capabilities_json = ?, context_limit = ?,
                        supports_structured_output = ?, supports_image_input = ?, supports_audio_input = ?,
                        input_price_per_million = ?, output_price_per_million = ?, cached_input_price_per_million = ?,
                        pricing_currency = ?, pricing_effective_at = ?, last_verified_at = ?,
                        replacement_model_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        entry.display_name,
                        entry.status,
                        _json(entry.capabilities_json),
                        entry.context_limit,
                        1 if entry.supports_structured_output else 0,
                        1 if entry.supports_image_input else 0,
                        1 if entry.supports_audio_input else 0,
                        entry.input_price_per_million,
                        entry.output_price_per_million,
                        entry.cached_input_price_per_million,
                        entry.pricing_currency,
                        entry.pricing_effective_at,
                        entry.last_verified_at,
                        entry.replacement_model_id,
                        now,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_model_catalog WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_model(row)

    def list_model_catalog_entries(self, provider: str | None = None) -> list[AIModelCatalogEntry]:
        if provider:
            rows = self._query_all("SELECT * FROM ai_model_catalog WHERE provider = ? ORDER BY provider, model_id, snapshot_or_version", (provider,))
        else:
            rows = self._query_all("SELECT * FROM ai_model_catalog ORDER BY provider, model_id, snapshot_or_version")
        return [self._row_to_model(row) for row in rows]

    def get_model_catalog_entry(self, model_catalog_id: str) -> AIModelCatalogEntry | None:
        row = self._query_one("SELECT * FROM ai_model_catalog WHERE id = ?", (model_catalog_id,))
        return self._row_to_model(row) if row else None

    def _row_to_model(self, row: sqlite3.Row | None) -> AIModelCatalogEntry:
        if row is None:
            raise ValueError("row is required")
        return AIModelCatalogEntry(
            id=row["id"],
            provider=row["provider"],
            model_id=row["model_id"],
            display_name=row["display_name"],
            snapshot_or_version=row["snapshot_or_version"],
            status=row["status"],
            capabilities_json=_loads(row["capabilities_json"]) or {},
            context_limit=row["context_limit"],
            supports_structured_output=bool(row["supports_structured_output"]),
            supports_image_input=bool(row["supports_image_input"]),
            supports_audio_input=bool(row["supports_audio_input"]),
            input_price_per_million=row["input_price_per_million"],
            output_price_per_million=row["output_price_per_million"],
            cached_input_price_per_million=row["cached_input_price_per_million"],
            pricing_currency=row["pricing_currency"],
            pricing_effective_at=row["pricing_effective_at"],
            last_verified_at=row["last_verified_at"],
            replacement_model_id=row["replacement_model_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_role_assignment(self, assignment: AIRoleAssignment) -> AIRoleAssignment:
        now = assignment.updated_at or _utc_now()
        created_at = assignment.created_at or now
        record_id = assignment.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM ai_model_role_assignments
                WHERE role = ? AND IFNULL(creator_id, '') = IFNULL(?, '') AND provider = ?
                """,
                (assignment.role, assignment.creator_id, assignment.provider),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_model_role_assignments (
                        id,
                        creator_id, role, provider, model_catalog_id, quality_level,
                        is_default, is_enabled, fallback_policy, approved_benchmark_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        assignment.creator_id,
                        assignment.role,
                        assignment.provider,
                        assignment.model_catalog_id,
                        assignment.quality_level,
                        1 if assignment.is_default else 0,
                        1 if assignment.is_enabled else 0,
                        assignment.fallback_policy,
                        assignment.approved_benchmark_id,
                        created_at,
                        now,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_model_role_assignments WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_model_role_assignments
                    SET model_catalog_id = ?, quality_level = ?, is_default = ?, is_enabled = ?,
                        fallback_policy = ?, approved_benchmark_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        assignment.model_catalog_id,
                        assignment.quality_level,
                        1 if assignment.is_default else 0,
                        1 if assignment.is_enabled else 0,
                        assignment.fallback_policy,
                        assignment.approved_benchmark_id,
                        now,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_model_role_assignments WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_assignment(row)

    def list_role_assignments(self, creator_id: str | None = None, provider: str | None = None) -> list[AIRoleAssignment]:
        clauses = []
        params: list[Any] = []
        if creator_id is not None:
            clauses.append("IFNULL(creator_id, '') = IFNULL(?, '')")
            params.append(creator_id)
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._query_all(f"SELECT * FROM ai_model_role_assignments {where} ORDER BY is_default DESC, role, provider", tuple(params))
        return [self._row_to_assignment(row) for row in rows]

    def resolve_role_assignment(self, role: str, creator_id: str | None = None, provider: str | None = None) -> AIRoleAssignment | None:
        clauses = ["role = ?"]
        params: list[Any] = [role]
        if creator_id is not None:
            clauses.append("IFNULL(creator_id, '') = IFNULL(?, '')")
            params.append(creator_id)
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        where = " AND ".join(clauses)
        row = self._query_one(f"SELECT * FROM ai_model_role_assignments WHERE {where} ORDER BY is_default DESC, updated_at DESC LIMIT 1", tuple(params))
        return self._row_to_assignment(row) if row else None

    def _row_to_assignment(self, row: sqlite3.Row | None) -> AIRoleAssignment:
        if row is None:
            raise ValueError("row is required")
        return AIRoleAssignment(
            id=row["id"],
            creator_id=row["creator_id"],
            role=row["role"],
            provider=row["provider"],
            model_catalog_id=row["model_catalog_id"],
            quality_level=row["quality_level"],
            is_default=bool(row["is_default"]),
            is_enabled=bool(row["is_enabled"]),
            fallback_policy=row["fallback_policy"],
            approved_benchmark_id=row["approved_benchmark_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_prompt_template(self, template: AIPromptTemplate) -> AIPromptTemplate:
        now = template.updated_at or _utc_now()
        created_at = template.created_at or now
        record_id = template.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM ai_prompt_templates WHERE template_key = ? AND version = ?",
                (template.template_key, template.version),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_prompt_templates (
                        id,
                        template_key, task_type, operation, version, status,
                        required_capabilities_json, instruction_layers_json,
                        input_schema_json, output_schema_json, validation_profile_json,
                        benchmark_id, change_notes, approved_at, deprecated_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        template.template_key,
                        template.task_type,
                        template.operation,
                        template.version,
                        template.status,
                        _json(template.required_capabilities_json),
                        _json(template.instruction_layers_json),
                        _json(template.input_schema_json),
                        _json(template.output_schema_json),
                        _json(template.validation_profile_json),
                        template.benchmark_id,
                        template.change_notes,
                        template.approved_at,
                        template.deprecated_at,
                        created_at,
                        now,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_prompt_templates WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_prompt_templates
                    SET task_type = ?, operation = ?, status = ?, required_capabilities_json = ?,
                        instruction_layers_json = ?, input_schema_json = ?, output_schema_json = ?,
                        validation_profile_json = ?, benchmark_id = ?, change_notes = ?,
                        approved_at = ?, deprecated_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        template.task_type,
                        template.operation,
                        template.status,
                        _json(template.required_capabilities_json),
                        _json(template.instruction_layers_json),
                        _json(template.input_schema_json),
                        _json(template.output_schema_json),
                        _json(template.validation_profile_json),
                        template.benchmark_id,
                        template.change_notes,
                        template.approved_at,
                        template.deprecated_at,
                        now,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_prompt_templates WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_template(row)

    def get_prompt_template(self, template_key: str, version: int | None = None) -> AIPromptTemplate | None:
        if version is None:
            row = self._query_one(
                "SELECT * FROM ai_prompt_templates WHERE template_key = ? AND status = 'approved' ORDER BY version DESC LIMIT 1",
                (template_key,),
            )
        else:
            row = self._query_one(
                "SELECT * FROM ai_prompt_templates WHERE template_key = ? AND version = ?",
                (template_key, version),
            )
        return self._row_to_template(row) if row else None

    def list_prompt_templates(self, status: str | None = None) -> list[AIPromptTemplate]:
        if status is None:
            rows = self._query_all("SELECT * FROM ai_prompt_templates ORDER BY template_key, version")
        else:
            rows = self._query_all("SELECT * FROM ai_prompt_templates WHERE status = ? ORDER BY template_key, version", (status,))
        return [self._row_to_template(row) for row in rows]

    def _row_to_template(self, row: sqlite3.Row | None) -> AIPromptTemplate:
        if row is None:
            raise ValueError("row is required")
        return AIPromptTemplate(
            id=row["id"],
            template_key=row["template_key"],
            task_type=row["task_type"],
            operation=row["operation"],
            version=row["version"],
            status=row["status"],
            required_capabilities_json=_loads(row["required_capabilities_json"]) or {},
            instruction_layers_json=_loads(row["instruction_layers_json"]) or {},
            input_schema_json=_loads(row["input_schema_json"]) or {},
            output_schema_json=_loads(row["output_schema_json"]) or {},
            validation_profile_json=_loads(row["validation_profile_json"]) or {},
            benchmark_id=row["benchmark_id"],
            change_notes=row["change_notes"],
            approved_at=row["approved_at"],
            deprecated_at=row["deprecated_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_budget_policy(self, policy: AIBudgetPolicy) -> AIBudgetPolicy:
        now = policy.updated_at or _utc_now()
        created_at = policy.created_at or now
        record_id = policy.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM ai_budget_policies
                WHERE IFNULL(creator_id, '') = IFNULL(?, '') AND IFNULL(provider, '') = IFNULL(?, '')
                ORDER BY effective_from DESC, created_at DESC
                LIMIT 1
                """,
                (policy.creator_id, policy.provider),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_budget_policies (
                        id,
                        creator_id, provider, daily_limit, monthly_limit, per_task_limit,
                        warning_threshold_50, warning_threshold_75, warning_threshold_90,
                        hard_block_enabled, currency, effective_from, effective_until,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        policy.creator_id,
                        policy.provider,
                        policy.daily_limit,
                        policy.monthly_limit,
                        policy.per_task_limit,
                        policy.warning_threshold_50,
                        policy.warning_threshold_75,
                        policy.warning_threshold_90,
                        1 if policy.hard_block_enabled else 0,
                        policy.currency,
                        policy.effective_from,
                        policy.effective_until,
                        created_at,
                        now,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_budget_policies WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_budget_policies
                    SET daily_limit = ?, monthly_limit = ?, per_task_limit = ?, warning_threshold_50 = ?,
                        warning_threshold_75 = ?, warning_threshold_90 = ?, hard_block_enabled = ?, currency = ?,
                        effective_from = ?, effective_until = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        policy.daily_limit,
                        policy.monthly_limit,
                        policy.per_task_limit,
                        policy.warning_threshold_50,
                        policy.warning_threshold_75,
                        policy.warning_threshold_90,
                        1 if policy.hard_block_enabled else 0,
                        policy.currency,
                        policy.effective_from,
                        policy.effective_until,
                        now,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_budget_policies WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_budget(row)

    def get_budget_policy(self, creator_id: str | None = None, provider: str | None = None) -> AIBudgetPolicy | None:
        rows = self._query_all("SELECT * FROM ai_budget_policies ORDER BY effective_from DESC, created_at DESC")
        for row in rows:
            candidate = self._row_to_budget(row)
            if candidate.creator_id == creator_id and candidate.provider == provider:
                return candidate
        for row in rows:
            candidate = self._row_to_budget(row)
            if candidate.creator_id == creator_id and candidate.provider is None:
                return candidate
        for row in rows:
            candidate = self._row_to_budget(row)
            if candidate.creator_id is None and candidate.provider == provider:
                return candidate
        for row in rows:
            candidate = self._row_to_budget(row)
            if candidate.creator_id is None and candidate.provider is None:
                return candidate
        return None

    def _row_to_budget(self, row: sqlite3.Row | None) -> AIBudgetPolicy:
        if row is None:
            raise ValueError("row is required")
        return AIBudgetPolicy(
            id=row["id"],
            creator_id=row["creator_id"],
            provider=row["provider"],
            daily_limit=row["daily_limit"],
            monthly_limit=row["monthly_limit"],
            per_task_limit=row["per_task_limit"],
            warning_threshold_50=row["warning_threshold_50"],
            warning_threshold_75=row["warning_threshold_75"],
            warning_threshold_90=row["warning_threshold_90"],
            hard_block_enabled=bool(row["hard_block_enabled"]),
            currency=row["currency"],
            effective_from=row["effective_from"],
            effective_until=row["effective_until"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert_runtime_setting(self, setting: AIRuntimeSetting) -> AIRuntimeSetting:
        now = setting.updated_at or _utc_now()
        created_at = setting.created_at or now
        record_id = setting.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM ai_runtime_settings
                WHERE scope_type = ? AND IFNULL(scope_id, '') = IFNULL(?, '') AND setting_key = ?
                """,
                (setting.scope_type, setting.scope_id, setting.setting_key),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_runtime_settings (
                        id, scope_type, scope_id, setting_key, setting_value_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        setting.scope_type,
                        setting.scope_id,
                        setting.setting_key,
                        _json(setting.setting_value_json),
                        created_at,
                        now,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_runtime_settings WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_runtime_settings
                    SET setting_value_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (_json(setting.setting_value_json), now, existing["id"]),
                )
                row = connection.execute("SELECT * FROM ai_runtime_settings WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_setting(row)

    def get_runtime_setting(self, scope_type: str, setting_key: str, scope_id: str | None = None) -> AIRuntimeSetting | None:
        row = self._query_one(
            """
            SELECT * FROM ai_runtime_settings
            WHERE scope_type = ? AND IFNULL(scope_id, '') = IFNULL(?, '') AND setting_key = ?
            """,
            (scope_type, scope_id, setting_key),
        )
        return self._row_to_setting(row) if row else None

    def _row_to_setting(self, row: sqlite3.Row | None) -> AIRuntimeSetting:
        if row is None:
            raise ValueError("row is required")
        return AIRuntimeSetting(
            id=row["id"],
            scope_type=row["scope_type"],
            scope_id=row["scope_id"],
            setting_key=row["setting_key"],
            setting_value_json=_loads(row["setting_value_json"]) or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def store_execution(self, execution: AIExecutionRecord) -> AIExecutionRecord:
        now = execution.updated_at or _utc_now()
        created_at = execution.created_at or now
        record_id = execution.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM ai_executions WHERE execution_uuid = ?",
                (execution.execution_uuid,),
            ).fetchone()
            params = (
                execution.execution_uuid,
                execution.creator_id,
                execution.project_id,
                execution.task_type,
                execution.operation,
                execution.status,
                execution.requested_model_role,
                execution.provider,
                execution.model_catalog_id,
                execution.template_id,
                execution.privacy_class,
                execution.quality_level,
                execution.context_fingerprint,
                execution.request_fingerprint,
                _json(execution.input_summary_json),
                execution.output_reference,
                execution.validation_status,
                execution.cache_status,
                execution.fallback_policy,
                1 if execution.approval_required else 0,
                execution.approved_at,
                execution.started_at,
                execution.completed_at,
                execution.latency_ms,
                execution.error_category,
                execution.error_code,
                execution.error_message_safe,
                created_at,
                now,
            )
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_executions (
                        id,
                        execution_uuid, creator_id, project_id, task_type, operation, status,
                        requested_model_role, provider, model_catalog_id, template_id, privacy_class,
                        quality_level, context_fingerprint, request_fingerprint, input_summary_json,
                        output_reference, validation_status, cache_status, fallback_policy,
                        approval_required, approved_at, started_at, completed_at, latency_ms,
                        error_category, error_code, error_message_safe, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (record_id, *params),
                )
                row = connection.execute("SELECT * FROM ai_executions WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_executions
                    SET creator_id = ?, project_id = ?, task_type = ?, operation = ?, status = ?,
                        requested_model_role = ?, provider = ?, model_catalog_id = ?, template_id = ?,
                        privacy_class = ?, quality_level = ?, context_fingerprint = ?, request_fingerprint = ?,
                        input_summary_json = ?, output_reference = ?, validation_status = ?, cache_status = ?,
                        fallback_policy = ?, approval_required = ?, approved_at = ?, started_at = ?,
                        completed_at = ?, latency_ms = ?, error_category = ?, error_code = ?,
                        error_message_safe = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        execution.creator_id,
                        execution.project_id,
                        execution.task_type,
                        execution.operation,
                        execution.status,
                        execution.requested_model_role,
                        execution.provider,
                        execution.model_catalog_id,
                        execution.template_id,
                        execution.privacy_class,
                        execution.quality_level,
                        execution.context_fingerprint,
                        execution.request_fingerprint,
                        _json(execution.input_summary_json),
                        execution.output_reference,
                        execution.validation_status,
                        execution.cache_status,
                        execution.fallback_policy,
                        1 if execution.approval_required else 0,
                        execution.approved_at,
                        execution.started_at,
                        execution.completed_at,
                        execution.latency_ms,
                        execution.error_category,
                        execution.error_code,
                        execution.error_message_safe,
                        now,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_executions WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_execution(row)

    def _update_execution_columns(
        self,
        execution_uuid: str,
        *,
        values: dict[str, Any],
        expected_statuses: tuple[str, ...] | None = None,
    ) -> AIExecutionRecord | None:
        with self.database.connect() as connection:
            current_row = connection.execute("SELECT * FROM ai_executions WHERE execution_uuid = ?", (execution_uuid,)).fetchone()
            if current_row is None:
                return None
            current = self._row_to_execution(current_row)
            if expected_statuses is not None and current.status not in expected_statuses:
                return None
            assignments: list[str] = []
            params: list[Any] = []
            for column, value in values.items():
                assignments.append(f"{column} = ?")
                if column == "input_summary_json" and value is not None:
                    params.append(_json(value))
                else:
                    params.append(value)
            params.append(execution_uuid)
            connection.execute(
                f"UPDATE ai_executions SET {', '.join(assignments)} WHERE execution_uuid = ?",
                tuple(params),
            )
            row = connection.execute("SELECT * FROM ai_executions WHERE execution_uuid = ?", (execution_uuid,)).fetchone()
        return self._row_to_execution(row)

    def claim_execution_for_resume(
        self,
        execution_uuid: str,
        *,
        approved_at: str,
        approved_by: str | None = None,
        approval_reason: str | None = None,
        approval_summary: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None:
        current = self.get_execution_by_uuid(execution_uuid)
        if current is None:
            return None
        summary = current.input_summary_json if isinstance(current.input_summary_json, dict) else {}
        if current.status in {"preparing_context", "running", "validating", "completed", "completed_with_warnings", "failed", "cancelled"}:
            return current
        merged_summary = {
            **summary,
            "approval_state": "approved",
            "approved_at": approved_at,
            "approved_by": approved_by,
            "approval_reason": approval_reason,
            "approval_transition_at": approved_at,
            "approval_summary": approval_summary or summary.get("approval_summary"),
            "resume_claimed_at": approved_at,
            "resume_claimed_by": approved_by,
        }
        return self._update_execution_columns(
            execution_uuid,
            expected_statuses=("awaiting_approval", "approved"),
            values={
                "status": "preparing_context",
                "approved_at": approved_at,
                "updated_at": approved_at,
                "input_summary_json": merged_summary,
            },
        )

    def update_execution_status(
        self,
        execution_uuid: str,
        *,
        status: str,
        expected_statuses: tuple[str, ...] | None = None,
        input_summary_updates: dict[str, Any] | None = None,
        approved_at: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        latency_ms: int | None = None,
        validation_status: str | None = None,
        cache_status: str | None = None,
        output_reference: str | None = None,
        error_category: str | None = None,
        error_code: str | None = None,
        error_message_safe: str | None = None,
        approval_required: bool | None = None,
    ) -> AIExecutionRecord | None:
        current = self.get_execution_by_uuid(execution_uuid)
        if current is None:
            return None
        summary = current.input_summary_json if isinstance(current.input_summary_json, dict) else {}
        merged_summary = {**summary, **(input_summary_updates or {})}
        values: dict[str, Any] = {
            "status": status,
            "updated_at": completed_at or started_at or approved_at or _utc_now(),
            "input_summary_json": merged_summary,
        }
        if approved_at is not None:
            values["approved_at"] = approved_at
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if latency_ms is not None:
            values["latency_ms"] = latency_ms
        if validation_status is not None:
            values["validation_status"] = validation_status
        if cache_status is not None:
            values["cache_status"] = cache_status
        if output_reference is not None:
            values["output_reference"] = output_reference
        if error_category is not None:
            values["error_category"] = error_category
        if error_code is not None:
            values["error_code"] = error_code
        if error_message_safe is not None:
            values["error_message_safe"] = error_message_safe
        if approval_required is not None:
            values["approval_required"] = approval_required
        return self._update_execution_columns(
            execution_uuid,
            expected_statuses=expected_statuses,
            values=values,
        )

    def persist_provider_result(
        self,
        execution_uuid: str,
        *,
        status: str,
        validation_status: str,
        cache_status: str,
        completed_at: str,
        latency_ms: int | None,
        output_reference: str,
        input_summary_updates: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None:
        return self.update_execution_status(
            execution_uuid,
            status=status,
            expected_statuses=("running", "validating", "preparing_context", "approved"),
            input_summary_updates=input_summary_updates,
            completed_at=completed_at,
            latency_ms=latency_ms,
            validation_status=validation_status,
            cache_status=cache_status,
            output_reference=output_reference,
            error_category=None,
            error_code=None,
            error_message_safe=None,
        )

    def persist_execution_failure(
        self,
        execution_uuid: str,
        *,
        status: str,
        completed_at: str,
        latency_ms: int | None,
        error_category: str,
        error_code: str | None,
        error_message_safe: str,
        validation_status: str | None = None,
        input_summary_updates: dict[str, Any] | None = None,
    ) -> AIExecutionRecord | None:
        return self.update_execution_status(
            execution_uuid,
            status=status,
            expected_statuses=("approved", "preparing_context", "running", "validating", "awaiting_approval"),
            input_summary_updates=input_summary_updates,
            completed_at=completed_at,
            latency_ms=latency_ms,
            validation_status=validation_status,
            error_category=error_category,
            error_code=error_code,
            error_message_safe=error_message_safe,
        )

    def get_execution_by_uuid(self, execution_uuid: str) -> AIExecutionRecord | None:
        row = self._query_one("SELECT * FROM ai_executions WHERE execution_uuid = ?", (execution_uuid,))
        return self._row_to_execution(row) if row else None

    def get_execution_by_request_fingerprint(self, request_fingerprint: str) -> AIExecutionRecord | None:
        rows = self._query_all(
            "SELECT * FROM ai_executions WHERE request_fingerprint = ? ORDER BY created_at DESC",
            (request_fingerprint,),
        )
        for row in rows:
            execution = self._row_to_execution(row)
            if execution.status in _ACTIVE_EXECUTION_STATUSES:
                return execution
        return None

    def find_execution_by_request_id(self, request_id: str) -> AIExecutionRecord | None:
        rows = self._query_all("SELECT * FROM ai_executions ORDER BY created_at DESC")
        for row in rows:
            execution = self._row_to_execution(row)
            request_summary = execution.input_summary_json if isinstance(execution.input_summary_json, dict) else {}
            if request_summary.get("request_id") == request_id and execution.status in _ACTIVE_EXECUTION_STATUSES:
                return execution
        return None

    def list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 100) -> list[AIExecutionRecord]:
        clauses = []
        params: list[Any] = []
        if creator_id is not None:
            clauses.append("IFNULL(creator_id, '') = IFNULL(?, '')")
            params.append(creator_id)
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._query_all(f"SELECT * FROM ai_executions {where} ORDER BY created_at DESC LIMIT ?", tuple(params + [limit]))
        return [self._row_to_execution(row) for row in rows]

    def _row_to_execution(self, row: sqlite3.Row | None) -> AIExecutionRecord:
        if row is None:
            raise ValueError("row is required")
        return AIExecutionRecord(
            id=row["id"],
            execution_uuid=row["execution_uuid"],
            creator_id=row["creator_id"],
            project_id=row["project_id"],
            task_type=row["task_type"],
            operation=row["operation"],
            status=row["status"],
            requested_model_role=row["requested_model_role"],
            provider=row["provider"],
            model_catalog_id=row["model_catalog_id"],
            template_id=row["template_id"],
            privacy_class=row["privacy_class"],
            quality_level=row["quality_level"],
            context_fingerprint=row["context_fingerprint"],
            request_fingerprint=row["request_fingerprint"],
            input_summary_json=_loads(row["input_summary_json"]) or {},
            output_reference=row["output_reference"],
            validation_status=row["validation_status"],
            cache_status=row["cache_status"],
            fallback_policy=row["fallback_policy"],
            approval_required=bool(row["approval_required"]),
            approved_at=row["approved_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            latency_ms=row["latency_ms"],
            error_category=row["error_category"],
            error_code=row["error_code"],
            error_message_safe=row["error_message_safe"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def store_payload(self, payload: AIExecutionPayload) -> AIExecutionPayload:
        created_at = payload.created_at or _utc_now()
        record_id = payload.id or str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_execution_payloads (
                    id, execution_id, payload_type, content_json, content_text,
                    content_hash, is_redacted, retention_class, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    payload.execution_id,
                    payload.payload_type,
                    _json(payload.content_json) if payload.content_json is not None else None,
                    payload.content_text,
                    payload.content_hash,
                    1 if payload.is_redacted else 0,
                    payload.retention_class,
                    created_at,
                ),
            )
            row = connection.execute("SELECT * FROM ai_execution_payloads WHERE rowid = last_insert_rowid()").fetchone()
        return self._row_to_payload(row)

    def list_payloads(self, execution_id: str) -> list[AIExecutionPayload]:
        rows = self._query_all("SELECT * FROM ai_execution_payloads WHERE execution_id = ? ORDER BY created_at", (execution_id,))
        return [self._row_to_payload(row) for row in rows]

    def _row_to_payload(self, row: sqlite3.Row | None) -> AIExecutionPayload:
        if row is None:
            raise ValueError("row is required")
        return AIExecutionPayload(
            id=row["id"],
            execution_id=row["execution_id"],
            payload_type=row["payload_type"],
            content_json=_loads(row["content_json"]) or None,
            content_text=row["content_text"],
            content_hash=row["content_hash"],
            is_redacted=bool(row["is_redacted"]),
            retention_class=row["retention_class"],
            created_at=row["created_at"],
        )

    def store_usage(self, usage: AIUsageRecord) -> AIUsageRecord:
        created_at = usage.created_at or _utc_now()
        record_id = usage.id or str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO ai_usage_records (
                    id, execution_id, provider, model_catalog_id, input_tokens, output_tokens,
                    cached_input_tokens, reasoning_tokens, provider_reported_cost,
                    calculated_cost, currency, pricing_version, calculation_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    usage.execution_id,
                    usage.provider,
                    usage.model_catalog_id,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.cached_input_tokens,
                    usage.reasoning_tokens,
                    usage.provider_reported_cost,
                    usage.calculated_cost,
                    usage.currency,
                    usage.pricing_version,
                    usage.calculation_notes,
                    created_at,
                ),
            )
            row = connection.execute("SELECT * FROM ai_usage_records WHERE rowid = last_insert_rowid()").fetchone()
        return self._row_to_usage(row)

    def list_usage_records(self, execution_id: str | None = None) -> list[AIUsageRecord]:
        if execution_id is None:
            rows = self._query_all("SELECT * FROM ai_usage_records ORDER BY created_at DESC")
        else:
            rows = self._query_all("SELECT * FROM ai_usage_records WHERE execution_id = ? ORDER BY created_at DESC", (execution_id,))
        return [self._row_to_usage(row) for row in rows]

    def _row_to_usage(self, row: sqlite3.Row | None) -> AIUsageRecord:
        if row is None:
            raise ValueError("row is required")
        return AIUsageRecord(
            id=row["id"],
            execution_id=row["execution_id"],
            provider=row["provider"],
            model_catalog_id=row["model_catalog_id"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cached_input_tokens=row["cached_input_tokens"],
            reasoning_tokens=row["reasoning_tokens"],
            provider_reported_cost=row["provider_reported_cost"],
            calculated_cost=row["calculated_cost"],
            currency=row["currency"],
            pricing_version=row["pricing_version"],
            calculation_notes=row["calculation_notes"],
            created_at=row["created_at"],
        )

    def upsert_cache_entry(self, entry: AICacheEntry) -> AICacheEntry:
        now = entry.created_at or _utc_now()
        last_accessed = entry.last_accessed_at or now
        record_id = entry.id or str(uuid4())
        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id, hit_count FROM ai_cache_entries WHERE cache_key = ?",
                (entry.cache_key,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO ai_cache_entries (
                        id, cache_key, task_type, operation, provider, model_catalog_id,
                        template_id, request_fingerprint, context_fingerprint,
                        result_reference, status, created_at, expires_at,
                        last_accessed_at, hit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        entry.cache_key,
                        entry.task_type,
                        entry.operation,
                        entry.provider,
                        entry.model_catalog_id,
                        entry.template_id,
                        entry.request_fingerprint,
                        entry.context_fingerprint,
                        entry.result_reference,
                        entry.status,
                        now,
                        entry.expires_at,
                        last_accessed,
                        entry.hit_count,
                    ),
                )
                row = connection.execute("SELECT * FROM ai_cache_entries WHERE rowid = last_insert_rowid()").fetchone()
            else:
                connection.execute(
                    """
                    UPDATE ai_cache_entries
                    SET task_type = ?, operation = ?, provider = ?, model_catalog_id = ?, template_id = ?,
                        request_fingerprint = ?, context_fingerprint = ?, result_reference = ?, status = ?,
                        expires_at = ?, last_accessed_at = ?, hit_count = ?
                    WHERE id = ?
                    """,
                    (
                        entry.task_type,
                        entry.operation,
                        entry.provider,
                        entry.model_catalog_id,
                        entry.template_id,
                        entry.request_fingerprint,
                        entry.context_fingerprint,
                        entry.result_reference,
                        entry.status,
                        entry.expires_at,
                        last_accessed,
                        entry.hit_count,
                        existing["id"],
                    ),
                )
                row = connection.execute("SELECT * FROM ai_cache_entries WHERE id = ?", (existing["id"],)).fetchone()
        return self._row_to_cache(row)

    def get_cache_entry(self, cache_key: str) -> AICacheEntry | None:
        row = self._query_one("SELECT * FROM ai_cache_entries WHERE cache_key = ?", (cache_key,))
        return self._row_to_cache(row) if row else None

    def invalidate_cache_entry(self, cache_key: str) -> None:
        self._execute(
            "UPDATE ai_cache_entries SET status = 'invalidated' WHERE cache_key = ?",
            (cache_key,),
        )

    def mark_cache_hit(self, cache_key: str) -> None:
        self._execute(
            "UPDATE ai_cache_entries SET hit_count = hit_count + 1, last_accessed_at = ? WHERE cache_key = ?",
            (_utc_now(), cache_key),
        )

    def _row_to_cache(self, row: sqlite3.Row | None) -> AICacheEntry:
        if row is None:
            raise ValueError("row is required")
        return AICacheEntry(
            id=row["id"],
            cache_key=row["cache_key"],
            task_type=row["task_type"],
            operation=row["operation"],
            provider=row["provider"],
            model_catalog_id=row["model_catalog_id"],
            template_id=row["template_id"],
            request_fingerprint=row["request_fingerprint"],
            context_fingerprint=row["context_fingerprint"],
            result_reference=row["result_reference"],
            status=row["status"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            last_accessed_at=row["last_accessed_at"],
            hit_count=row["hit_count"],
        )
