"""Application service for AI runtime orchestration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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
        for provider in self.list_providers():
            credential = self.credential_store.load(CredentialStore.reference_for_provider(provider))
            result[provider] = {
                "configured": bool(credential),
                "masked_key": self.credential_store.mask(credential),
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
            return AIProviderDiagnostic(
                provider=provider,
                configured=False,
                model_id=None,
                status="blocked",
                message="Provider credential is missing.",
            )
        client = self.providers.get(provider)
        if client is None:
            return AIProviderDiagnostic(
                provider=provider,
                configured=True,
                model_id=None,
                status="blocked",
                message="Provider adapter is unavailable.",
            )
        return client.test_credentials(key)

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
    ) -> dict[str, object]:
        assignment = self.model_registry.assign_role(
            role=role,
            provider=provider,
            model_id=model_id,
            creator_id=creator_id,
            display_name=display_name,
            is_default=is_default,
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

    def diagnostic_run(
        self,
        *,
        provider: str | None = None,
        role: str | None = None,
        cache_policy: str = "use",
    ) -> AIExecutionResult:
        return self.orchestrator.run_diagnostic(provider=provider, role=role, cache_policy=cache_policy)

    def list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        return [execution.to_dict() for execution in self.repository.list_executions(creator_id=creator_id, provider=provider, limit=limit)]

    def get_execution(self, execution_uuid: str) -> dict[str, object] | None:
        execution = self.repository.get_execution_by_uuid(execution_uuid)
        return execution.to_dict() if execution else None

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
