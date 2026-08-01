from __future__ import annotations

import time
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
    AIProviderModelSyncReport,
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
        discovered_models: list[dict[str, object]] | None = None,
        discovery_status: str = "ok",
        discovery_message: str = "Model catalog synchronized.",
        execution_delay_ms: int = 0,
        raise_on_execute: Exception | None = None,
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
        self.discovered_models = discovered_models or [
            {
                "model_id": f"{provider_name}-structured-mini",
                "display_name": f"{provider_name.title()} Structured Mini",
                "snapshot_or_version": model_version,
                "status": "testing",
                "capabilities_json": {"structured_output": True},
                "supports_structured_output": True,
                "supports_image_input": provider_name == "openai",
                "supports_audio_input": False,
            }
        ]
        self.discovery_status = discovery_status
        self.discovery_message = discovery_message
        self.execution_delay_ms = execution_delay_ms
        self.raise_on_execute = raise_on_execute
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

    def discover_models(self, api_key: str):
        from creator_intelligence_studio.infrastructure.ai_runtime.models import AIProviderDiscoveredModel

        discovered = tuple(
            AIProviderDiscoveredModel(
                provider=self.provider_name,
                model_id=str(model["model_id"]),
                display_name=str(model["display_name"]),
                snapshot_or_version=str(model.get("snapshot_or_version")) if model.get("snapshot_or_version") is not None else None,
                status=str(model.get("status") or "testing"),
                capabilities_json=dict(model.get("capabilities_json") or {}),
                supports_structured_output=bool(model.get("supports_structured_output", False)),
                supports_image_input=bool(model.get("supports_image_input", False)),
                supports_audio_input=bool(model.get("supports_audio_input", False)),
                input_price_per_million=model.get("input_price_per_million"),
                output_price_per_million=model.get("output_price_per_million"),
                cached_input_price_per_million=model.get("cached_input_price_per_million"),
                pricing_currency=str(model.get("pricing_currency") or "USD"),
                pricing_effective_at=model.get("pricing_effective_at"),
                replacement_model_id=model.get("replacement_model_id"),
                compatibility_notes=tuple(model.get("compatibility_notes") or ()),
            )
            for model in self.discovered_models
        )
        compatible = sum(1 for model in discovered if model.status in {"approved", "testing"})
        return AIProviderModelSyncReport(
            provider=self.provider_name,
            status=self.discovery_status,
            message=self.discovery_message,
            found_count=len(discovered),
            compatible_count=compatible,
            new_count=0,
            updated_count=0,
            unavailable_count=0,
            latency_ms=1,
            checked_at="2026-07-29T00:00:00Z",
            models=discovered,
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
        if self.execution_delay_ms:
            time.sleep(self.execution_delay_ms / 1000.0)
        if self.raise_on_execute is not None:
            raise self.raise_on_execute
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
