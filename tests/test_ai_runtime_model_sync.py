from __future__ import annotations

import unittest
from uuid import uuid4

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRecord, AIModelCatalogEntry
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


class AIRuntimeModelSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_refresh_provider_models_populates_catalog_updates_existing_and_marks_missing_unavailable(self) -> None:
        self.fixture.repository.upsert_model_catalog_entry(
            AIModelCatalogEntry(
                provider="openai",
                model_id="orphan-model",
                display_name="Orphan Model",
                snapshot_or_version="v1",
                status="approved",
                capabilities_json={"structured_output": True},
                context_limit=4096,
                supports_structured_output=True,
                input_price_per_million=1.0,
                output_price_per_million=1.0,
                pricing_currency="USD",
                created_at="2026-07-29T00:00:00Z",
                updated_at="2026-07-29T00:00:00Z",
            )
        )
        execution = self.fixture.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=str(uuid4()),
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
                request_fingerprint="request-hash-sync",
                input_summary_json={"request_id": "req-sync", "task_type": "provider_diagnostic", "metadata_keys": []},
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
        self.fixture.service.providers["openai"] = FakeProvider(
            "openai",
            discovered_models=[
                {
                    "model_id": "gpt-4.1-mini",
                    "display_name": "GPT-4.1 mini",
                    "snapshot_or_version": "2026-07",
                    "status": "testing",
                    "capabilities_json": {"structured_output": True, "image_input": True},
                    "supports_structured_output": True,
                    "supports_image_input": True,
                    "supports_audio_input": False,
                },
                {
                    "model_id": self.fixture.model.model_id,
                    "display_name": "Diagnostic Model",
                    "snapshot_or_version": self.fixture.model.snapshot_or_version,
                    "status": "testing",
                    "capabilities_json": {"structured_output": True},
                    "supports_structured_output": True,
                },
                {
                    "model_id": "text-embedding-3-small",
                    "display_name": "Embedding Small",
                    "status": "unavailable",
                    "capabilities_json": {"structured_output": False},
                },
            ],
        )

        report = self.fixture.service.refresh_provider_models("openai")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["found_count"], 3)
        self.assertEqual(report["compatible_count"], 2)
        self.assertEqual(report["new_count"], 2)
        self.assertEqual(report["updated_count"], 1)
        self.assertEqual(report["unavailable_count"], 1)

        models = {model.model_id: model for model in self.fixture.repository.list_model_catalog_entries("openai")}
        self.assertIn("gpt-4.1-mini", models)
        self.assertEqual(models["gpt-4.1-mini"].status, "testing")
        self.assertEqual(models["orphan-model"].status, "unavailable")
        self.assertIsNotNone(models[self.fixture.model.model_id].last_verified_at)
        executions = self.fixture.repository.list_executions()
        self.assertTrue(any(item.execution_uuid == execution.execution_uuid for item in executions))

        provider_status = self.fixture.service.provider_status()["openai"]
        self.assertEqual(provider_status["last_model_sync"]["status"], "ok")
        self.assertGreaterEqual(provider_status["last_model_sync"]["compatible_count"], 2)

    def test_refresh_provider_models_reports_missing_credentials_safely(self) -> None:
        self.fixture.service.delete_provider_credential("openai")
        report = self.fixture.service.refresh_provider_models("openai")
        self.assertEqual(report["status"], "blocked")
        self.assertIn("credencial", report["message"].lower())


if __name__ == "__main__":
    unittest.main()
