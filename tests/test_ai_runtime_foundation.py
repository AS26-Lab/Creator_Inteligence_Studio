from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import shutil
from unittest.mock import patch

from creator_intelligence_studio.infrastructure.ai_runtime.credentials import CredentialStore, InMemoryCredentialBackend
from creator_intelligence_studio.infrastructure.ai_runtime.models import (
    AIBudgetPolicy,
    AIExecutionError,
    AIExecutionRequest,
    AIExecutionUsage,
    AIModelCatalogEntry,
    AIPromptTemplate,
    AIRoleAssignment,
    AIProviderResponse,
)
from creator_intelligence_studio.infrastructure.ai_runtime.orchestrator import AIOrchestrator
from creator_intelligence_studio.infrastructure.ai_runtime.policies import AIResultValidator, BudgetPolicy, CostEstimator, CostTracker, PrivacyPolicyEngine
from creator_intelligence_studio.infrastructure.ai_runtime.providers import AnthropicProvider, OpenAIProvider
from creator_intelligence_studio.infrastructure.ai_runtime.registry import ModelRegistry, PromptRegistry
from creator_intelligence_studio.infrastructure.ai_runtime.repository import SQLiteAIRuntimeRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations


class FakeProvider:
    def __init__(self, provider_name: str, response_text: str, *, error: AIExecutionError | None = None) -> None:
        self.provider_name = provider_name
        self.response_text = response_text
        self.error = error
        self.calls = 0

    def capabilities(self):
        return OpenAIProvider().capabilities() if self.provider_name == "openai" else AnthropicProvider().capabilities()

    def test_credentials(self, api_key: str):
        from creator_intelligence_studio.infrastructure.ai_runtime.models import AIProviderDiagnostic

        return AIProviderDiagnostic(
            provider=self.provider_name,
            configured=True,
            model_id=None,
            status="ok",
            message="ok",
            latency_ms=1,
        )

    def execute(self, request, *, api_key: str, model_id: str, prompt_text: str):
        self.calls += 1
        output = self.response_text
        structured_output = None
        try:
            import json

            structured_output = json.loads(output)
        except Exception:
            structured_output = None
        return AIProviderResponse(
            provider=self.provider_name,
            model_id=model_id,
            model_version="v1",
            output_text=output,
            structured_output=structured_output,
            usage=AIExecutionUsage(
                input_tokens=4,
                output_tokens=6,
                cached_input_tokens=0,
                reasoning_tokens=None,
                provider_reported_cost=None,
                calculated_cost=0.00001,
                currency="USD",
                pricing_version="seed",
                calculation_notes="fake",
            ),
            latency_ms=5,
        )


class AIRuntimeFoundationTests(unittest.TestCase):
    _template_dir: tempfile.TemporaryDirectory[str] | None = None
    _template_db_path: Path | None = None
    _template_model_id: str | None = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._template_dir = tempfile.TemporaryDirectory()
        template_root = Path(cls._template_dir.name)
        database = SQLiteDatabase(template_root / "template.db", timeout_seconds=5.0)
        with database.connect() as connection:
            run_migrations(connection)
        repository = SQLiteAIRuntimeRepository(database)
        model = repository.upsert_model_catalog_entry(
            AIModelCatalogEntry(
                provider="openai",
                model_id="diag-model",
                display_name="Diagnostic Model",
                snapshot_or_version="v1",
                status="approved",
                capabilities_json={"structured_output": True},
                context_limit=4096,
                supports_structured_output=True,
                supports_image_input=False,
                supports_audio_input=False,
                input_price_per_million=1.0,
                output_price_per_million=1.0,
                cached_input_price_per_million=0.1,
                pricing_currency="USD",
                pricing_effective_at="2026-07-29T00:00:00Z",
                last_verified_at="2026-07-29T00:00:00Z",
            )
        )
        repository.upsert_role_assignment(
            AIRoleAssignment(
                role="cheap_structured_model",
                provider="openai",
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
        cls._template_db_path = database.database_path
        cls._template_model_id = model.id

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._template_dir is not None:
            cls._template_dir.cleanup()

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        shutil.copyfile(self.__class__._template_db_path, self.root / "runtime.db")
        self.database = SQLiteDatabase(self.root / "runtime.db", timeout_seconds=5.0)
        self.repository = SQLiteAIRuntimeRepository(self.database)
        self.model_registry = ModelRegistry(self.repository)
        self.prompt_registry = PromptRegistry(self.repository)
        self.model = self.repository.get_model_catalog_entry(self.__class__._template_model_id)
        self.credential_store = CredentialStore(InMemoryCredentialBackend())
        self.credential_store.save(CredentialStore.reference_for_provider("openai"), "sk-openai-test")
        self.credential_store.save(CredentialStore.reference_for_provider("anthropic"), "sk-anthropic-test")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_request(self, *, cache_policy: str = "use", privacy_class: str = "selected_text_allowed") -> AIExecutionRequest:
        return AIExecutionRequest(
            request_id="req-001",
            task_type="provider_diagnostic",
            operation="extract",
            creator_id=None,
            project_id=None,
            model_role="cheap_structured_model",
            quality_level="standard",
            privacy_class=privacy_class,
            input_data={"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic completed successfully."},
            context_package={},
            output_contract={"required": ["status", "logical_role", "short_message"]},
            budget={"monthly_limit": None},
            cache_policy=cache_policy,
            fallback_policy="none",
            approval_policy="not_required",
            metadata={},
        )

    def test_credential_store_round_trip(self) -> None:
        store = CredentialStore(InMemoryCredentialBackend())
        reference = CredentialStore.reference_for_provider("openai")
        store.save(reference, "sk-test")
        self.assertEqual(store.load(reference), "sk-test")
        self.assertEqual(store.mask("sk-test"), "••••••••test")
        store.delete(reference)
        self.assertIsNone(store.load(reference))

    def test_openai_provider_normalizes_success_and_auth_error(self) -> None:
        provider = OpenAIProvider()
        success_payload = {"data": [{"id": "model-a"}]}
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers._http_json", return_value=(200, success_payload, 12)):
            diagnostic = provider.test_credentials("sk-test")
        self.assertEqual(diagnostic.status, "ok")
        self.assertEqual(diagnostic.usage["models"], 1)

        error_payload = {"error": {"message": "invalid api key", "type": "invalid_api_key"}}
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers._http_json", return_value=(401, error_payload, 8)):
            diagnostic = provider.test_credentials("sk-test")
        self.assertEqual(diagnostic.status, "failed")
        self.assertEqual(diagnostic.error["category"], "authentication_error")

    def test_anthropic_provider_normalizes_success_and_rate_limit(self) -> None:
        provider = AnthropicProvider()
        success_payload = {"data": [{"id": "model-b"}]}
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers._http_json", return_value=(200, success_payload, 11)):
            diagnostic = provider.test_credentials("sk-test")
        self.assertEqual(diagnostic.status, "ok")

        error_payload = {"error": {"message": "rate limited", "type": "rate_limit"}}
        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers._http_json", return_value=(429, error_payload, 7)):
            diagnostic = provider.test_credentials("sk-test")
        self.assertEqual(diagnostic.status, "failed")
        self.assertEqual(diagnostic.error["category"], "rate_limit_error")

    def test_orchestrator_completes_and_caches_diagnostic(self) -> None:
        fake_provider = FakeProvider(
            "openai",
            '{"status":"ok","logical_role":"cheap_structured_model","short_message":"Provider diagnostic completed successfully."}',
        )
        orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers={"openai": fake_provider},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )

        request = self._build_request()
        first = orchestrator.run(request, provider="openai")
        second = orchestrator.run(request, provider="openai")

        self.assertEqual(first.status, "completed")
        self.assertEqual(second.cache.cache_status, "exact_hit")
        self.assertEqual(fake_provider.calls, 1)
        self.assertEqual(len(self.repository.list_executions()), 1)
        self.assertEqual(len(self.repository.list_usage_records()), 1)

    def test_orchestrator_blocks_privacy_without_calling_provider(self) -> None:
        fake_provider = FakeProvider("openai", "{}")
        orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers={"openai": fake_provider},
        )

        result = orchestrator.run(self._build_request(privacy_class="blocked_external"), provider="openai")
        self.assertEqual(result.status, "blocked_by_privacy")
        self.assertEqual(fake_provider.calls, 0)

    def test_orchestrator_blocks_budget_without_calling_provider(self) -> None:
        self.repository.upsert_budget_policy(
            AIBudgetPolicy(
                monthly_limit=None,
                per_task_limit=0.00001,
                hard_block_enabled=True,
                currency="USD",
                effective_from="2026-07-29T00:00:00Z",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        fake_provider = FakeProvider("openai", "{}")
        orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers={"openai": fake_provider},
        )

        result = orchestrator.run(self._build_request(), provider="openai")
        self.assertEqual(result.status, "blocked_by_budget")
        self.assertEqual(fake_provider.calls, 0)

    def test_orchestrator_handles_malformed_response(self) -> None:
        fake_provider = FakeProvider("openai", "not json")
        orchestrator = AIOrchestrator(
            model_registry=self.model_registry,
            prompt_registry=self.prompt_registry,
            credential_store=self.credential_store,
            repository=self.repository,
            providers={"openai": fake_provider},
        )

        result = orchestrator.run(self._build_request(), provider="openai")
        self.assertEqual(result.status, "completed_with_warnings")
        self.assertEqual(result.validation.status, "rejected")

    def test_migration_v31_from_existing_v30_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "upgrade.db", timeout_seconds=5.0)
            with db.connect() as connection:
                connection.execute(
                    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
                )
                for version in range(1, 31):
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (version, f"migration_{version}", "2026-07-29T00:00:00Z"),
                    )
                run_migrations(connection)
                tables = {
                    row["name"]
                    for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                }
                applied = [row["version"] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]

        self.assertIn("ai_executions", tables)
        self.assertIn(31, applied)


if __name__ == "__main__":
    unittest.main()
