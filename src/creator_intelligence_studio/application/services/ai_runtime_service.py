"""Application service for AI runtime orchestration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from creator_intelligence_studio.infrastructure.ai_runtime import (
    AIBudgetPolicy,
    AICache,
    AIExecutionRequest,
    AIExecutionResult,
    AIModelCatalogEntry,
    AIProviderDiagnostic,
    AIPromptTemplate,
    AIRoleAssignment,
    AIRuntimeSetting,
    AnthropicProvider,
    BudgetPolicy,
    CredentialStore,
    CostEstimator,
    CostTracker,
    ModelRegistry,
    OpenAIProvider,
    PrivacyPolicyEngine,
    PromptRegistry,
    SQLiteAIRuntimeRepository,
    AIOrchestrator,
    AIResultValidator,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class AIRuntimeStatus:
    ai_runtime_available: bool
    openai_configured: bool
    anthropic_configured: bool
    model_roles_configured: bool
    budget_policy_configured: bool
    credential_store_available: bool


class AIRuntimeService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        database: SQLiteDatabase,
        credential_store: CredentialStore,
        repository: SQLiteAIRuntimeRepository,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.database = database
        self.credential_store = credential_store
        self.repository = repository
        self.model_registry = ModelRegistry(repository)
        self.prompt_registry = PromptRegistry(repository)
        self.cache = AICache(repository)
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
        }
        self.orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers=self.providers,
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
            cache=self.cache,
        )
        self._seed_runtime()

    def _seed_runtime(self) -> None:
        existing = self.prompt_registry.get_approved("provider_diagnostic")
        if existing is None:
            self.prompt_registry.ensure_template(
                AIPromptTemplate(
                    template_key="provider_diagnostic",
                    task_type="provider_diagnostic",
                    operation="extract",
                    version=1,
                    status="approved",
                    required_capabilities_json={"structured_output": True},
                    instruction_layers_json={
                        "layers": [
                            "Return only JSON.",
                            "Keep the response minimal.",
                            "Do not reference creator data.",
                        ]
                    },
                    input_schema_json={
                        "type": "object",
                        "properties": {
                            "short_message": {"type": "string"},
                        },
                    },
                    output_schema_json={
                        "type": "object",
                        "required": ["status", "logical_role", "short_message"],
                        "properties": {
                            "status": {"const": "ok"},
                            "logical_role": {"type": "string"},
                            "short_message": {"type": "string"},
                        },
                    },
                    validation_profile_json={
                        "required_keys": ["status", "logical_role", "short_message"]
                    },
                    change_notes="Initial diagnostic template.",
                    approved_at=self._now(),
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            )
        default_budget = self.repository.get_budget_policy(None, None)
        if default_budget is None:
            self.repository.upsert_budget_policy(
                AIBudgetPolicy(
                    monthly_limit=None,
                    per_task_limit=None,
                    hard_block_enabled=True,
                    currency="USD",
                    effective_from=self._now(),
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            )
        self._ensure_runtime_flags()

    def _ensure_runtime_flags(self) -> None:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="provider_enabled",
                setting_value_json={"openai": True, "anthropic": True},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="env_credentials_enabled",
                setting_value_json={"enabled": os.environ.get("CIS_ENABLE_ENV_CREDENTIALS") == "1"},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="cross_provider_fallback_enabled",
                setting_value_json={"enabled": True},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="cost_approval_threshold",
                setting_value_json={"value": 0.90},
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def _runtime_setting_value(self, setting_key: str, scope_id: str | None = None) -> dict[str, Any] | None:
        setting = self.repository.get_runtime_setting("application" if scope_id is None else "provider", setting_key, scope_id)
        if setting is None:
            return None
        return setting.setting_value_json

    def get_runtime_setting(self, setting_key: str, scope_id: str | None = None) -> dict[str, Any] | None:
        return self._runtime_setting_value(setting_key, scope_id)

    def set_runtime_setting(self, setting_key: str, value: dict[str, Any], scope_id: str | None = None) -> dict[str, Any]:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application" if scope_id is None else "provider",
                scope_id=scope_id,
                setting_key=setting_key,
                setting_value_json=value,
                created_at=self._now(),
                updated_at=self._now(),
            )
        )
        return value

    def _runtime_flag(self, setting_key: str, *, scope_id: str | None = None, default: bool = False) -> bool:
        value = self._runtime_setting_value(setting_key, scope_id)
        if isinstance(value, dict):
            if scope_id is None:
                enabled = value.get("enabled")
                if enabled is None:
                    return default
                return bool(enabled)
            enabled = value.get("value")
            if enabled is None:
                enabled = value.get("enabled")
            if enabled is None:
                return default
            return bool(enabled)
        return default

    def _runtime_number(self, setting_key: str, *, scope_id: str | None = None, default: float | None = None) -> float | None:
        value = self._runtime_setting_value(setting_key, scope_id)
        if isinstance(value, dict):
            raw = value.get("value")
            if raw is None:
                raw = value.get("threshold")
            if raw is None:
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default
        return default

    def _record_provider_check(self, provider: str, diagnostic: AIProviderDiagnostic) -> None:
        self.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="provider",
                scope_id=provider,
                setting_key="last_check",
                setting_value_json={
                    "provider": provider,
                    "status": diagnostic.status,
                    "message": diagnostic.message,
                    "configured": diagnostic.configured,
                    "model_id": diagnostic.model_id,
                    "latency_ms": diagnostic.latency_ms,
                    "usage": diagnostic.usage,
                    "cost": diagnostic.cost,
                    "error": diagnostic.error,
                    "checked_at": self._now(),
                },
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def status(self) -> AIRuntimeStatus:
        return AIRuntimeStatus(
            ai_runtime_available=True,
            openai_configured=bool(self.credential_store.load(CredentialStore.reference_for_provider("openai"))),
            anthropic_configured=bool(self.credential_store.load(CredentialStore.reference_for_provider("anthropic"))),
            model_roles_configured=bool(self.model_registry.list_roles()),
            budget_policy_configured=self.repository.get_budget_policy(None, None) is not None,
            credential_store_available=self.credential_store.is_available(),
        )

    def list_providers(self) -> list[str]:
        return ["openai", "anthropic"]

    def provider_status(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        provider_enabled = self._runtime_setting_value("provider_enabled") or {}
        for provider in self.list_providers():
            credential = self.credential_store.load(CredentialStore.reference_for_provider(provider))
            last_check = self._runtime_setting_value("last_check", provider) or {}
            result[provider] = {
                "configured": bool(credential),
                "masked_key": self.credential_store.mask(credential),
                "enabled": bool(provider_enabled.get(provider, True)) if isinstance(provider_enabled, dict) else True,
                "last_check": last_check,
                "models": [entry.to_dict() for entry in self.model_registry.list_models(provider)],
                "roles": [assignment.to_dict() for assignment in self.model_registry.list_roles(provider=provider)],
            }
        return result

    def store_provider_credential(self, provider: str, api_key: str) -> None:
        self.credential_store.save(CredentialStore.reference_for_provider(provider), api_key)

    def delete_provider_credential(self, provider: str) -> None:
        self.credential_store.delete(CredentialStore.reference_for_provider(provider))

    def test_provider(self, provider: str) -> AIProviderDiagnostic:
        key = self.credential_store.load(CredentialStore.reference_for_provider(provider))
        if not key:
            diagnostic = AIProviderDiagnostic(
                provider=provider,
                configured=False,
                model_id=None,
                status="blocked",
                message="Provider credential is missing.",
            )
            self._record_provider_check(provider, diagnostic)
            return diagnostic
        client = self.providers.get(provider)
        if client is None:
            diagnostic = AIProviderDiagnostic(
                provider=provider,
                configured=True,
                model_id=None,
                status="blocked",
                message="Provider adapter is unavailable.",
            )
            self._record_provider_check(provider, diagnostic)
            return diagnostic
        diagnostic = client.test_credentials(key)
        self._record_provider_check(provider, diagnostic)
        return diagnostic

    def list_models(self, provider: str | None = None) -> list[dict[str, object]]:
        return [entry.to_dict() for entry in self.model_registry.list_models(provider)]

    def verify_models(self, provider: str) -> list[dict[str, object]]:
        diagnostic = self.test_provider(provider)
        if diagnostic.status != "ok":
            return [diagnostic.to_dict()]
        rows: list[dict[str, object]] = []
        for entry in self.model_registry.list_models(provider):
            updated = self.repository.upsert_model_catalog_entry(
                AIModelCatalogEntry(
                    id=entry.id,
                    provider=entry.provider,
                    model_id=entry.model_id,
                    display_name=entry.display_name,
                    snapshot_or_version=entry.snapshot_or_version,
                    status="approved",
                    capabilities_json=entry.capabilities_json,
                    context_limit=entry.context_limit,
                    supports_structured_output=entry.supports_structured_output,
                    supports_image_input=entry.supports_image_input,
                    supports_audio_input=entry.supports_audio_input,
                    input_price_per_million=entry.input_price_per_million,
                    output_price_per_million=entry.output_price_per_million,
                    cached_input_price_per_million=entry.cached_input_price_per_million,
                    pricing_currency=entry.pricing_currency,
                    pricing_effective_at=entry.pricing_effective_at,
                    last_verified_at=self._now(),
                    replacement_model_id=entry.replacement_model_id,
                    created_at=entry.created_at,
                    updated_at=self._now(),
                )
            )
            rows.append(updated.to_dict())
        return rows

    def list_roles(self, creator_id: str | None = None) -> list[dict[str, object]]:
        return [assignment.to_dict() for assignment in self.model_registry.list_roles(creator_id=creator_id)]

    def assign_role(
        self,
        *,
        role: str,
        provider: str,
        model_id: str,
        creator_id: str | None = None,
        display_name: str | None = None,
        is_default: bool = False,
        is_enabled: bool = True,
        fallback_policy: str = "none",
        quality_level: str = "standard",
        status: str = "testing",
        capabilities_json: dict[str, object] | None = None,
        snapshot_or_version: str | None = None,
    ) -> dict[str, object]:
        assignment = self.model_registry.assign_role(
            role=role,
            provider=provider,
            model_id=model_id,
            creator_id=creator_id,
            display_name=display_name,
            is_default=is_default,
            is_enabled=is_enabled,
            fallback_policy=fallback_policy,
            quality_level=quality_level,
            status=status,
            capabilities_json=capabilities_json,
            snapshot_or_version=snapshot_or_version,
        )
        return assignment.to_dict()

    def get_budget_policy(self, creator_id: str | None = None, provider: str | None = None) -> dict[str, object] | None:
        policy = self.repository.get_budget_policy(creator_id, provider)
        return policy.to_dict() if policy else None

    def set_monthly_budget(self, amount: float, currency: str, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=amount,
                per_task_limit=current.per_task_limit,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=current.warning_threshold_90,
                hard_block_enabled=current.hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def set_per_task_budget(self, amount: float, currency: str, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=current.monthly_limit,
                per_task_limit=amount,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=current.warning_threshold_90,
                hard_block_enabled=current.hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def update_budget_policy(
        self,
        *,
        creator_id: str | None = None,
        provider: str | None = None,
        monthly_limit: float | None = None,
        per_task_limit: float | None = None,
        hard_block_enabled: bool = True,
        currency: str = "USD",
        approval_threshold: float | None = None,
    ) -> dict[str, object]:
        current = self.repository.get_budget_policy(creator_id, provider) or AIBudgetPolicy(creator_id=creator_id, provider=provider, created_at=self._now(), updated_at=self._now())
        updated = self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                id=current.id,
                creator_id=creator_id,
                provider=provider,
                daily_limit=current.daily_limit,
                monthly_limit=monthly_limit,
                per_task_limit=per_task_limit,
                warning_threshold_50=current.warning_threshold_50,
                warning_threshold_75=current.warning_threshold_75,
                warning_threshold_90=approval_threshold if approval_threshold is not None else current.warning_threshold_90,
                hard_block_enabled=hard_block_enabled,
                currency=currency,
                effective_from=current.effective_from or self._now(),
                effective_until=current.effective_until,
                created_at=current.created_at or self._now(),
                updated_at=self._now(),
            )
        )
        return updated.to_dict()

    def budget_snapshot(self, creator_id: str | None = None, provider: str | None = None) -> dict[str, object]:
        policy = self.get_budget_policy(creator_id, provider)
        provider_enabled = self._runtime_setting_value("provider_enabled") or {}
        cross_provider = self._runtime_setting_value("cross_provider_fallback_enabled") or {}
        approval_threshold = self._runtime_setting_value("cost_approval_threshold") or {}
        executions = self.repository.list_executions(creator_id=creator_id, provider=provider, limit=1000)
        usage_records = self.repository.list_usage_records()
        monthly_cost = 0.0
        provider_costs: dict[str, float] = {}
        calls = 0
        billing_errors = 0
        warnings: list[str] = []
        for execution in executions:
            calls += 1
            if execution.error_category == "billing_error":
                billing_errors += 1
            try:
                created_at = execution.created_at
                if created_at is None:
                    continue
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created.year == now.year and created.month == now.month:
                    for record in usage_records:
                        if record.execution_id == execution.execution_uuid:
                            monthly_cost += record.calculated_cost
                            provider_costs[record.provider] = provider_costs.get(record.provider, 0.0) + record.calculated_cost
            except Exception:
                continue
        if policy is not None and policy.get("monthly_limit") is not None and monthly_cost > float(policy["monthly_limit"]):
            warnings.append("Monthly consumption exceeds the configured limit.")
        if any(entry.get("input_price_per_million") is None or entry.get("output_price_per_million") is None for entry in self.list_models()):
            warnings.append("Precio pendiente de verificar para uno o mas modelos.")
        return {
            "policy": policy,
            "monthly_cost": round(monthly_cost, 8),
            "provider_costs": {provider_name: round(value, 8) for provider_name, value in provider_costs.items()},
            "calls": calls,
            "billing_errors": billing_errors,
            "provider_enabled": provider_enabled,
            "cross_provider_fallback_enabled": bool(cross_provider.get("enabled", True)) if isinstance(cross_provider, dict) else True,
            "approval_threshold": float(approval_threshold.get("value")) if isinstance(approval_threshold, dict) and approval_threshold.get("value") is not None else (policy.get("warning_threshold_90") if policy else None),
            "warnings": tuple(warnings),
            "usage_records": [record.to_dict() for record in usage_records],
        }

    def diagnostic_run(
        self,
        *,
        provider: str | None = None,
        role: str | None = None,
        cache_policy: str = "use",
    ) -> AIExecutionResult:
        request_id = f"provider_diagnostic:{provider or 'any'}:{role or 'cheap_structured_model'}:{cache_policy}"
        return self.orchestrator.run_diagnostic(provider=provider, role=role, request_id=request_id, cache_policy=cache_policy)

    def list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        return [execution.to_dict() for execution in self.repository.list_executions(creator_id=creator_id, provider=provider, limit=limit)]

    def get_execution(self, execution_uuid: str) -> dict[str, object] | None:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        return execution.to_dict() if execution else None

    def list_usage_records(self, execution_id: str | None = None) -> list[dict[str, object]]:
        return [record.to_dict() for record in self.repository.list_usage_records(execution_id)]

    def list_payloads(self, execution_id: str) -> list[dict[str, object]]:
        return [payload.to_dict() for payload in self.repository.list_payloads(execution_id)]

    def diagnostics_snapshot(self) -> dict[str, object]:
        status = self.status()
        return {
            "ai_runtime_available": status.ai_runtime_available,
            "openai_configured": status.openai_configured,
            "anthropic_configured": status.anthropic_configured,
            "model_roles_configured": status.model_roles_configured,
            "budget_policy_configured": status.budget_policy_configured,
            "credential_store_available": status.credential_store_available,
        }


def build_ai_runtime_service(*, settings: AppSettings, paths: ProjectPaths, database: SQLiteDatabase, credential_store: CredentialStore | None = None) -> AIRuntimeService:
    repository = SQLiteAIRuntimeRepository(database)
    credential_store = credential_store or CredentialStore.build_default()
    return AIRuntimeService(
        settings=settings,
        paths=paths,
        database=database,
        credential_store=credential_store,
        repository=repository,
    )
