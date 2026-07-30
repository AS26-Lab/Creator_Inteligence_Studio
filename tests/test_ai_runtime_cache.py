from __future__ import annotations

import unittest
from dataclasses import replace

from creator_intelligence_studio.infrastructure.ai_runtime.cache import AICache
from creator_intelligence_studio.infrastructure.ai_runtime.models import AICacheEntry, AIExecutionRecord, AIModelCatalogEntry, AIPromptTemplate
from creator_intelligence_studio.infrastructure.ai_runtime.orchestrator import AIOrchestrator
from creator_intelligence_studio.infrastructure.ai_runtime.policies import AIResultValidator, CostEstimator, CostTracker, PrivacyPolicyEngine
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


class AIRuntimeCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_cache_key_changes_with_template_model_context_and_request(self) -> None:
        from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest

        request_object = AIExecutionRequest(
            request_id="req-cache",
            task_type="provider_diagnostic",
            operation="extract",
            creator_id=None,
            project_id=None,
            model_role="cheap_structured_model",
            quality_level="standard",
            privacy_class="selected_text_allowed",
            input_data={"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic request."},
            context_package={"context": "alpha"},
            output_contract={"required": ["status", "logical_role", "short_message"]},
            budget={"provider": "openai"},
            cache_policy="use",
            fallback_policy="none",
            approval_policy="not_required",
            metadata={"variant": "a"},
        )
        orchestrator = AIOrchestrator(
            model_registry=self.fixture.model_registry,
            prompt_registry=self.fixture.prompt_registry,
            credential_store=self.fixture.credential_store,
            repository=self.fixture.repository,
            providers={"openai": FakeProvider("openai")},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )
        cache_key_a = orchestrator._cache_key(
            provider_name="openai",
            model_entry=self.fixture.model,
            template=self.fixture.prompt_registry.get_approved("provider_diagnostic"),
            request=request_object,
            request_fingerprint="request-a",
            context_fingerprint="context-a",
        )
        cache_key_b = orchestrator._cache_key(
            provider_name="openai",
            model_entry=self.fixture.model,
            template=self.fixture.prompt_registry.get_approved("provider_diagnostic"),
            request=request_object,
            request_fingerprint="request-a",
            context_fingerprint="context-b",
        )
        cache_key_c = orchestrator._cache_key(
            provider_name="openai",
            model_entry=self.fixture.model,
            template=self.fixture.prompt_registry.get_approved("provider_diagnostic"),
            request=request_object,
            request_fingerprint="request-b",
            context_fingerprint="context-a",
        )
        alt_template = self.fixture.repository.upsert_prompt_template(
            AIPromptTemplate(
                template_key="provider_diagnostic",
                task_type="provider_diagnostic",
                operation="extract",
                version=2,
                status="approved",
                required_capabilities_json={"structured_output": True},
                instruction_layers_json={"layers": ["Return JSON only."]},
                input_schema_json={"type": "object"},
                output_schema_json={"type": "object"},
                validation_profile_json={"required_keys": ["status", "logical_role", "short_message"]},
                change_notes="version 2",
                approved_at="2026-07-29T00:00:00Z",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        alt_model = self.fixture.repository.upsert_model_catalog_entry(
            AIModelCatalogEntry(
                provider=self.fixture.model.provider,
                model_id=self.fixture.model.model_id,
                display_name=self.fixture.model.display_name,
                snapshot_or_version="v2",
                status=self.fixture.model.status,
                capabilities_json=self.fixture.model.capabilities_json,
                context_limit=self.fixture.model.context_limit,
                supports_structured_output=self.fixture.model.supports_structured_output,
                supports_image_input=self.fixture.model.supports_image_input,
                supports_audio_input=self.fixture.model.supports_audio_input,
                input_price_per_million=self.fixture.model.input_price_per_million,
                output_price_per_million=self.fixture.model.output_price_per_million,
                cached_input_price_per_million=self.fixture.model.cached_input_price_per_million,
                pricing_currency=self.fixture.model.pricing_currency,
                pricing_effective_at=self.fixture.model.pricing_effective_at,
                last_verified_at=self.fixture.model.last_verified_at,
                replacement_model_id=self.fixture.model.replacement_model_id,
                created_at=self.fixture.model.created_at,
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        cache_key_d = orchestrator._cache_key(
            provider_name="openai",
            model_entry=alt_model,
            template=alt_template,
            request=request_object,
            request_fingerprint="request-a",
            context_fingerprint="context-a",
        )
        self.assertNotEqual(cache_key_a, cache_key_b)
        self.assertNotEqual(cache_key_a, cache_key_c)
        self.assertNotEqual(cache_key_a, cache_key_d)

    def test_cache_get_marks_active_hits_and_treats_stale_as_miss(self) -> None:
        cache = AICache(self.fixture.repository)
        execution_uuid = "execution-1"
        self.fixture.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=execution_uuid,
                creator_id=None,
                project_id=None,
                task_type="provider_diagnostic",
                operation="extract",
                status="completed",
                requested_model_role="cheap_structured_model",
                provider="openai",
                model_catalog_id=self.fixture.model.id,
                template_id=self.fixture.repository.get_prompt_template("provider_diagnostic").id,
                privacy_class="selected_text_allowed",
                quality_level="standard",
                context_fingerprint=None,
                request_fingerprint="hash",
                input_summary_json={"request_id": "cache-hit"},
                output_reference=None,
                validation_status="valid",
                cache_status="active",
                fallback_policy="none",
                approval_required=False,
                approved_at="2026-07-29T00:00:00Z",
                started_at="2026-07-29T00:00:00Z",
                completed_at="2026-07-29T00:00:00Z",
                latency_ms=1,
                error_category=None,
                error_code=None,
                error_message_safe=None,
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        entry = AICacheEntry(
            cache_key="ai:openai:model:template:1:v1:hash",
            task_type="provider_diagnostic",
            operation="extract",
            provider="openai",
            model_catalog_id=self.fixture.model.id,
            template_id=self.fixture.repository.get_prompt_template("provider_diagnostic").id,
            request_fingerprint="hash",
            context_fingerprint="context",
            result_reference=execution_uuid,
            status="active",
            created_at="2026-07-29T00:00:00Z",
            expires_at=None,
            last_accessed_at="2026-07-29T00:00:00Z",
            hit_count=0,
        )
        cache.put(entry)
        hit = cache.get(entry.cache_key)
        self.assertTrue(hit.hit)
        self.assertFalse(hit.stale)
        self.assertEqual(self.fixture.repository.get_cache_entry(entry.cache_key).hit_count, 1)

        self.fixture.repository.invalidate_cache_entry(entry.cache_key)
        stale = cache.get(entry.cache_key)
        self.assertFalse(stale.hit)
        self.assertTrue(stale.stale)

    def test_cache_refresh_rewrites_entry(self) -> None:
        orchestrator = AIOrchestrator(
            model_registry=self.fixture.model_registry,
            prompt_registry=self.fixture.prompt_registry,
            credential_store=self.fixture.credential_store,
            repository=self.fixture.repository,
            providers={"openai": FakeProvider("openai")},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )
        request = self._request()
        first = orchestrator.run(request, provider="openai")
        cached = self.fixture.repository.get_cache_entry(first.cache.cache_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.result_reference, first.execution_id)
        refresh = orchestrator.run(replace(request, request_id="refresh", cache_policy="refresh"), provider="openai")
        refreshed = self.fixture.repository.get_cache_entry(refresh.cache.cache_key)
        self.assertEqual(refreshed.result_reference, refresh.execution_id)

    def _request(self):
        from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRequest

        return AIExecutionRequest(
            request_id="cache-request",
            task_type="provider_diagnostic",
            operation="extract",
            creator_id=None,
            project_id=None,
            model_role="cheap_structured_model",
            quality_level="standard",
            privacy_class="selected_text_allowed",
            input_data={"status": "ok", "logical_role": "cheap_structured_model", "short_message": "Provider diagnostic completed successfully."},
            context_package={},
            output_contract={"required": ["status", "logical_role", "short_message"]},
            budget={},
            cache_policy="use",
            fallback_policy="none",
            approval_policy="not_required",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
