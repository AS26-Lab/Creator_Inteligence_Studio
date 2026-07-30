from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.ai_runtime_service import AIRuntimeService
from creator_intelligence_studio.infrastructure.ai_runtime.credentials import CredentialStore, InMemoryCredentialBackend
from creator_intelligence_studio.infrastructure.ai_runtime.models import (
    AIExecutionError,
    AIExecutionRequest,
    AIExecutionUsage,
    AIModelCatalogEntry,
    AIPromptTemplate,
    AIRoleAssignment,
    AIProviderDiagnostic,
    AIProviderResponse,
)
from creator_intelligence_studio.infrastructure.ai_runtime.orchestrator import AIOrchestrator
from creator_intelligence_studio.infrastructure.ai_runtime.registry import ModelRegistry, PromptRegistry
from creator_intelligence_studio.infrastructure.ai_runtime.repository import SQLiteAIRuntimeRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations


class FakeProvider:
    def __init__(
        self,
        provider_name: str,
        response_text: str = '{"status":"ok","logical_role":"cheap_structured_model","short_message":"Provider diagnostic completed successfully."}',
        *,
        error: AIExecutionError | None = None,
        diagnostic_status: str = "ok",
        diagnostic_message: str = "ok",
        usage: AIExecutionUsage | None = None,
        model_version: str = "v1",
        latency_ms: int = 5,
    ) -> None:
        self.provider_name = provider_name
        self.response_text = response_text
        self.error = error
        self.diagnostic_status = diagnostic_status
        self.diagnostic_message = diagnostic_message
        self.usage = usage or AIExecutionUsage(
            input_tokens=4,
            output_tokens=6,
            cached_input_tokens=0,
            reasoning_tokens=None,
            provider_reported_cost=None,
            calculated_cost=0.00001,
            currency="USD",
            pricing_version="seed",
            calculation_notes="fake",
        )
        self.model_version = model_version
        self.latency_ms = latency_ms
        self.calls = 0
        self.last_calls: list[dict[str, object]] = []

    def capabilities(self):
        from creator_intelligence_studio.infrastructure.ai_runtime.providers import AnthropicProvider, OpenAIProvider

        return OpenAIProvider().capabilities() if self.provider_name == "openai" else AnthropicProvider().capabilities()

    def test_credentials(self, api_key: str):
        return AIProviderDiagnostic(
            provider=self.provider_name,
            configured=True,
            model_id=None,
            status=self.diagnostic_status,
            message=self.diagnostic_message,
            latency_ms=1,
        )

    def execute(self, request: AIExecutionRequest, *, api_key: str, model_id: str, prompt_text: str):
        self.calls += 1
        self.last_calls.append(
            {
                "request": request,
                "api_key": api_key,
                "model_id": model_id,
                "prompt_text": prompt_text,
            }
        )
        if self.error is not None:
            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version=self.model_version,
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=self.latency_ms,
                error=self.error,
            )
        structured_output = None
        try:
            import json

            structured_output = json.loads(self.response_text)
        except Exception:
            structured_output = None
        return AIProviderResponse(
            provider=self.provider_name,
            model_id=model_id,
            model_version=self.model_version,
            output_text=self.response_text,
            structured_output=structured_output,
            usage=self.usage,
            latency_ms=self.latency_ms,
        )


@dataclass
class RuntimeFixture:
    temp_dir: tempfile.TemporaryDirectory[str]
    database: SQLiteDatabase
    repository: SQLiteAIRuntimeRepository
    model_registry: ModelRegistry
    prompt_registry: PromptRegistry
    credential_store: CredentialStore
    service: AIRuntimeService
    model: AIModelCatalogEntry
    role: AIRoleAssignment

    def cleanup(self) -> None:
        self.temp_dir.cleanup()


def build_runtime_fixture(
    *,
    provider: str = "openai",
    model_id: str = "diag-model",
    model_status: str = "approved",
    model_version: str = "v1",
    input_price_per_million: float | None = 1.0,
    output_price_per_million: float | None = 1.0,
    cached_input_price_per_million: float | None = 0.1,
) -> RuntimeFixture:
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    database = SQLiteDatabase(root / "runtime.db", timeout_seconds=5.0)
    with database.connect() as connection:
        run_migrations(connection)
    repository = SQLiteAIRuntimeRepository(database)
    model = repository.upsert_model_catalog_entry(
        AIModelCatalogEntry(
            provider=provider,
            model_id=model_id,
            display_name="Diagnostic Model",
            snapshot_or_version=model_version,
            status=model_status,
            capabilities_json={"structured_output": True},
            context_limit=4096,
            supports_structured_output=True,
            supports_image_input=False,
            supports_audio_input=False,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
            cached_input_price_per_million=cached_input_price_per_million,
            pricing_currency="USD",
            pricing_effective_at="2026-07-29T00:00:00Z",
            last_verified_at="2026-07-29T00:00:00Z",
        )
    )
    role = repository.upsert_role_assignment(
        AIRoleAssignment(
            role="cheap_structured_model",
            provider=provider,
            model_catalog_id=model.id,
            quality_level="standard",
            is_default=True,
            is_enabled=True,
        )
    )
    repository.upsert_prompt_template(
        AIPromptTemplate(
            template_key="provider_diagnostic",
            task_type="provider_diagnostic",
            operation="extract",
            version=1,
            status="approved",
            required_capabilities_json={"structured_output": True},
            instruction_layers_json={"layers": ["Return JSON only."]},
            input_schema_json={"type": "object"},
            output_schema_json={"type": "object"},
            validation_profile_json={"required_keys": ["status", "logical_role", "short_message"]},
            change_notes="seed",
            approved_at="2026-07-29T00:00:00Z",
            created_at="2026-07-29T00:00:00Z",
            updated_at="2026-07-29T00:00:00Z",
        )
    )
    credential_store = CredentialStore(InMemoryCredentialBackend())
    credential_store.save(CredentialStore.reference_for_provider("openai"), "sk-openai-test")
    credential_store.save(CredentialStore.reference_for_provider("anthropic"), "sk-anthropic-test")
    service = AIRuntimeService(
        settings=SimpleNamespace(),
        paths=SimpleNamespace(),
        database=database,
        credential_store=credential_store,
        repository=repository,
    )
    return RuntimeFixture(
        temp_dir=temp_dir,
        database=database,
        repository=repository,
        model_registry=ModelRegistry(repository),
        prompt_registry=PromptRegistry(repository),
        credential_store=credential_store,
        service=service,
        model=model,
        role=role,
    )
