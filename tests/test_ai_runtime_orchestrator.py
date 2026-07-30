from __future__ import annotations

import json
import unittest
from dataclasses import replace
from uuid import uuid4

from creator_intelligence_studio.infrastructure.ai_runtime.credentials import CredentialStore, InMemoryCredentialBackend
from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionError, AIExecutionRecord, AIExecutionRequest, AIExecutionUsage, AIBudgetPolicy, AIRuntimeSetting, build_request_fingerprint
from creator_intelligence_studio.infrastructure.ai_runtime.orchestrator import AIOrchestrator
from creator_intelligence_studio.infrastructure.ai_runtime.policies import AIResultValidator, BudgetPolicy, CostEstimator, CostTracker, PrivacyPolicyEngine
from creator_intelligence_studio.infrastructure.ai_runtime.repository import SQLiteAIRuntimeRepository
from creator_intelligence_studio.infrastructure.ai_runtime.registry import ModelRegistry, PromptRegistry
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


def _request(
    *,
    request_id: str = "req-001",
    cache_policy: str = "use",
    privacy_class: str = "selected_text_allowed",
    model_role: str | None = "cheap_structured_model",
    creator_id: str | None = None,
    context_package: dict[str, object] | None = None,
    input_data: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id=request_id,
        task_type="provider_diagnostic",
        operation="extract",
        creator_id=creator_id,
        project_id=None,
        model_role=model_role,
        quality_level="standard",
        privacy_class=privacy_class,
        input_data=input_data
        or {"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic completed successfully."},
        context_package=context_package or {},
        output_contract={"required": ["status", "logical_role", "short_message"]},
        budget={"monthly_limit": None},
        cache_policy=cache_policy,
        fallback_policy="none",
        approval_policy="not_required",
        metadata=metadata or {},
    )


class SequenceProvider:
    def __init__(self, provider_name: str, responses: list[AIExecutionError | str]) -> None:
        self.provider_name = provider_name
        self.responses = list(responses)
        self.calls = 0

    def capabilities(self):
        return FakeProvider(self.provider_name).capabilities()

    def test_credentials(self, api_key: str):
        return FakeProvider(self.provider_name).test_credentials(api_key)

    def execute(self, request, *, api_key: str, model_id: str, prompt_text: str):
        self.calls += 1
        item = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(item, AIExecutionError):
            from creator_intelligence_studio.infrastructure.ai_runtime.models import AIProviderResponse

            return AIProviderResponse(
                provider=self.provider_name,
                model_id=model_id,
                model_version="v1",
                output_text="",
                structured_output=None,
                usage=AIExecutionUsage(),
                latency_ms=5,
                error=item,
            )
        return FakeProvider(self.provider_name, item).execute(request, api_key=api_key, model_id=model_id, prompt_text=prompt_text)


class AIRuntimeOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)

    def _orchestrator(self, providers: dict[str, object] | None = None) -> AIOrchestrator:
        return AIOrchestrator(
            model_registry=self.fixture.model_registry,
            prompt_registry=self.fixture.prompt_registry,
            credential_store=self.fixture.credential_store,
            repository=self.fixture.repository,
            providers=providers or {"openai": FakeProvider("openai"), "anthropic": FakeProvider("anthropic")},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )

    def _request(self, **kwargs) -> AIExecutionRequest:
        return _request(**kwargs)

    def test_valid_request_runs_and_persists_execution(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})

        result = orchestrator.run(self._request(), provider="openai")

        self.assertEqual(result.status, "completed")
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)
        self.assertEqual(len(self.fixture.repository.list_usage_records()), 1)
        self.assertIn("request_fingerprint", result.provenance)
        self.assertIn("context_fingerprint", result.provenance)

    def test_duplicate_request_id_while_active_blocks_without_provider_call(self) -> None:
        request = self._request(request_id="dup-active")
        self.fixture.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=str(uuid4()),
                creator_id=None,
                project_id=None,
                task_type=request.task_type,
                operation=request.operation,
                status="running",
                requested_model_role=request.model_role,
                provider="openai",
                model_catalog_id=self.fixture.model.id,
                template_id=self.fixture.repository.get_prompt_template("provider_diagnostic").id,
                privacy_class=request.privacy_class,
                quality_level=request.quality_level,
                context_fingerprint=None,
                request_fingerprint="active-fingerprint",
                input_summary_json={"request_id": request.request_id, "task_type": request.task_type},
                output_reference=None,
                validation_status=None,
                cache_status="active",
                fallback_policy=request.fallback_policy,
                approval_required=False,
                approved_at=None,
                started_at="2026-07-29T00:00:00Z",
                completed_at=None,
                latency_ms=None,
                error_category=None,
                error_code=None,
                error_message_safe=None,
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})

        result = orchestrator.run(request, provider="openai")

        self.assertEqual(result.status, "queued")
        self.assertEqual(result.error.category, "internal_error")
        self.assertEqual(provider.calls, 0)
        self.assertEqual(len(self.fixture.repository.list_executions()), 2)

    def test_duplicate_request_fingerprint_while_active_blocks_without_provider_call(self) -> None:
        request = self._request(request_id="dup-fingerprint")
        request_hash = build_request_fingerprint(request.to_dict())
        fingerprint = self.fixture.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=str(uuid4()),
                creator_id=None,
                project_id=None,
                task_type=request.task_type,
                operation=request.operation,
                status="running",
                requested_model_role=request.model_role,
                provider="openai",
                model_catalog_id=self.fixture.model.id,
                template_id=self.fixture.repository.get_prompt_template("provider_diagnostic").id,
                privacy_class=request.privacy_class,
                quality_level=request.quality_level,
                context_fingerprint=None,
                request_fingerprint=request_hash,
                input_summary_json={"request_id": "different", "task_type": request.task_type},
                output_reference=None,
                validation_status=None,
                cache_status="active",
                fallback_policy=request.fallback_policy,
                approval_required=False,
                approved_at=None,
                started_at="2026-07-29T00:00:00Z",
                completed_at=None,
                latency_ms=None,
                error_category=None,
                error_code=None,
                error_message_safe=None,
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})

        result = orchestrator.run(request, provider="openai")

        self.assertEqual(result.status, "queued")
        self.assertEqual(result.error.category, "internal_error")
        self.assertEqual(provider.calls, 0)
        self.assertIsNotNone(fingerprint)
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)

    def test_cache_hit_bypass_and_refresh(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        request = self._request()

        first = orchestrator.run(request, provider="openai")
        second = orchestrator.run(request, provider="openai")
        bypass = orchestrator.run(self._request(request_id="bypass", cache_policy="bypass"), provider="openai")
        refresh = orchestrator.run(self._request(request_id="refresh", cache_policy="refresh"), provider="openai")

        self.assertEqual(first.status, "completed")
        self.assertEqual(second.cache.cache_status, "exact_hit")
        self.assertEqual(bypass.status, "completed")
        self.assertEqual(refresh.status, "completed")
        self.assertEqual(provider.calls, 3)
        self.assertEqual(len(self.fixture.repository.list_usage_records()), 3)

    def test_cache_invalidation_forces_reexecution(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(), provider="openai")
        cache_entry = self.fixture.repository.get_cache_entry(result.cache.cache_key)
        self.assertIsNotNone(cache_entry)
        self.fixture.repository.invalidate_cache_entry(result.cache.cache_key)

        rerun = orchestrator.run(self._request(request_id="rerun"), provider="openai")
        self.assertEqual(rerun.status, "completed")
        self.assertEqual(provider.calls, 2)

    def test_privacy_blocks_before_provider_and_persists_safe_reason(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})

        result = orchestrator.run(self._request(privacy_class="local_only"), provider="openai")

        self.assertEqual(result.status, "blocked_by_privacy")
        self.assertEqual(provider.calls, 0)
        execution = self.fixture.repository.get_execution_by_uuid(result.execution_id)
        self.assertIsNotNone(execution)
        self.assertNotIn("short_message", json.dumps(execution.input_summary_json))
        self.assertEqual(self.fixture.repository.list_payloads(result.execution_id), [])

        blocked = orchestrator.run(self._request(request_id="blocked-external", privacy_class="blocked_external"), provider="openai")
        self.assertEqual(blocked.status, "blocked_by_privacy")
        self.assertEqual(provider.calls, 0)

    def test_selected_text_allowed_is_redacted_in_storage(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})

        result = orchestrator.run(self._request(privacy_class="selected_text_allowed"), provider="openai")

        payloads = self.fixture.repository.list_payloads(result.execution_id)
        self.assertTrue(any(payload.is_redacted for payload in payloads if payload.payload_type != "validation_report"))
        self.assertNotIn("Provider diagnostic completed successfully.", json.dumps(self.fixture.repository.get_execution_by_uuid(result.execution_id).input_summary_json))
        self.assertEqual(provider.calls, 1)

    def test_budget_monthly_and_per_task_limits(self) -> None:
        self.fixture.repository.upsert_budget_policy(
            AIBudgetPolicy(
                monthly_limit=0.00001,
                per_task_limit=0.00001,
                hard_block_enabled=True,
                currency="USD",
                effective_from="2026-07-29T00:00:00Z",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(request_id="budget-hard"), provider="openai")
        self.assertEqual(result.status, "blocked_by_budget")
        self.assertEqual(provider.calls, 0)

        self.fixture.repository.upsert_budget_policy(
            AIBudgetPolicy(
                monthly_limit=0.00001,
                per_task_limit=0.00001,
                hard_block_enabled=False,
                currency="USD",
                effective_from="2026-07-29T00:00:00Z",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(request_id="budget-soft"), provider="openai")
        self.assertEqual(result.status, "awaiting_approval")
        self.assertEqual(result.error.category, "budget_block")
        self.assertEqual(provider.calls, 0)

    def test_budget_unknown_pricing_requires_approval_not_zero_cost(self) -> None:
        fixture = build_runtime_fixture(input_price_per_million=None, output_price_per_million=None, cached_input_price_per_million=None)
        self.addCleanup(fixture.cleanup)
        fixture.repository.upsert_budget_policy(
            AIBudgetPolicy(
                monthly_limit=1.0,
                per_task_limit=1.0,
                hard_block_enabled=True,
                currency="USD",
                effective_from="2026-07-29T00:00:00Z",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = AIOrchestrator(
            model_registry=fixture.model_registry,
            prompt_registry=fixture.prompt_registry,
            credential_store=fixture.credential_store,
            repository=fixture.repository,
            providers={"openai": provider},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )
        result = orchestrator.run(_request(request_id="budget-unknown"), provider="openai")
        self.assertEqual(result.status, "awaiting_approval")
        self.assertIsNone(result.cost.estimated_min_cost)
        self.assertIsNone(result.cost.estimated_max_cost)
        self.assertEqual(provider.calls, 0)

    def test_provider_disabled_and_role_mismatch_block_before_call(self) -> None:
        self.fixture.repository.upsert_runtime_setting(
            AIRuntimeSetting(
                scope_type="application",
                setting_key="provider_enabled",
                setting_value_json={"openai": False, "anthropic": True},
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(request_id="provider-disabled"), provider="openai")
        self.assertEqual(result.status, "blocked_by_provider")
        self.assertEqual(provider.calls, 0)

        orchestrator = self._orchestrator({"anthropic": FakeProvider("anthropic")})
        mismatch = orchestrator.run(self._request(request_id="role-mismatch"), provider="anthropic")
        self.assertEqual(mismatch.status, "blocked_by_model")

    def test_deprecated_and_unavailable_models_are_not_selected(self) -> None:
        self.fixture.repository.upsert_model_catalog_entry(
            replace(self.fixture.model, status="deprecated", updated_at="2026-07-29T00:00:00Z")
        )
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(request_id="deprecated-model"), provider="openai")
        self.assertEqual(result.status, "blocked_by_model")
        self.assertEqual(provider.calls, 0)

        self.fixture.repository.upsert_model_catalog_entry(
            replace(self.fixture.model, status="unavailable", updated_at="2026-07-29T00:00:00Z")
        )
        result = orchestrator.run(self._request(request_id="unavailable-model"), provider="openai")
        self.assertEqual(result.status, "blocked_by_model")
        self.assertEqual(provider.calls, 0)

    def test_retries_are_capped_and_non_retryable_errors_do_not_retry(self) -> None:
        timeout_error = AIExecutionError(category="timeout", safe_message="timeout", retryable=True)
        retry_provider = SequenceProvider("openai", [timeout_error, timeout_error, '{"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"}'])
        orchestrator = self._orchestrator({"openai": retry_provider})
        result = orchestrator.run(self._request(request_id="retry-timeout"), provider="openai")
        self.assertEqual(retry_provider.calls, 3)
        self.assertEqual(result.status, "completed")

        billing_error = AIExecutionError(category="billing_error", safe_message="billing", retryable=False)
        billing_provider = SequenceProvider("openai", [billing_error])
        orchestrator = self._orchestrator({"openai": billing_provider})
        result = orchestrator.run(self._request(request_id="billing"), provider="openai")
        self.assertEqual(billing_provider.calls, 1)
        self.assertEqual(result.status, "failed")

        auth_error = AIExecutionError(category="authentication_error", safe_message="auth", retryable=False)
        auth_provider = SequenceProvider("openai", [auth_error])
        orchestrator = self._orchestrator({"openai": auth_provider})
        result = orchestrator.run(self._request(request_id="auth"), provider="openai")
        self.assertEqual(auth_provider.calls, 1)
        self.assertEqual(result.status, "failed")

        invalid_error = AIExecutionError(category="invalid_request", safe_message="invalid", retryable=False)
        invalid_provider = SequenceProvider("openai", [invalid_error])
        orchestrator = self._orchestrator({"openai": invalid_provider})
        result = orchestrator.run(self._request(request_id="invalid"), provider="openai")
        self.assertEqual(invalid_provider.calls, 1)
        self.assertEqual(result.status, "failed")

    def test_validation_repair_is_applied_once(self) -> None:
        provider = FakeProvider(
            "openai",
            'prefix {"status":"ok","logical_role":"cheap_structured_model","short_message":"ok"} suffix',
        )
        orchestrator = self._orchestrator({"openai": provider})
        result = orchestrator.run(self._request(request_id="repair"), provider="openai")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.validation.status, "valid")
        self.assertEqual(provider.calls, 1)

    def test_no_cross_provider_fallback(self) -> None:
        failing_openai = SequenceProvider("openai", [AIExecutionError(category="model_unavailable", safe_message="missing", retryable=False)])
        anthropic = FakeProvider("anthropic")
        orchestrator = self._orchestrator({"openai": failing_openai, "anthropic": anthropic})
        result = orchestrator.run(self._request(request_id="no-fallback"), provider="openai")
        self.assertEqual(result.status, "failed")
        self.assertEqual(failing_openai.calls, 1)
        self.assertEqual(anthropic.calls, 0)

    def test_cost_is_not_charged_again_on_cache_hit(self) -> None:
        provider = FakeProvider("openai")
        orchestrator = self._orchestrator({"openai": provider})
        first = orchestrator.run(self._request(request_id="cost-1"), provider="openai")
        second = orchestrator.run(self._request(request_id="cost-1"), provider="openai")
        self.assertGreater(first.cost.calculated_cost, 0)
        self.assertEqual(second.cost.calculated_cost, 0.0)
        self.assertEqual(len(self.fixture.repository.list_usage_records()), 1)
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
