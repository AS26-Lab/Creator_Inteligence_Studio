from __future__ import annotations

import unittest
from uuid import uuid4

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRecord
from tests.ai_runtime_test_support import build_runtime_fixture


class AIRuntimeRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)

    def test_assign_role_preserves_existing_model_status(self) -> None:
        model = self.fixture.repository.get_model_catalog_entry(self.fixture.model.id)
        self.assertEqual(model.status, "approved")

        self.fixture.model_registry.assign_role(
            role="evaluation_model",
            provider="openai",
            model_id=self.fixture.model.model_id,
            creator_id=None,
            is_default=False,
        )

        model_after = self.fixture.repository.get_model_catalog_entry(self.fixture.model.id)
        self.assertEqual(model_after.status, "approved")

    def test_find_execution_by_request_id_uses_safe_summary(self) -> None:
        execution = self.fixture.repository.store_execution(
            AIExecutionRecord(
                execution_uuid=str(uuid4()),
                creator_id=None,
                project_id=None,
                task_type="provider_diagnostic",
                operation="extract",
                status="running",
                requested_model_role="cheap_structured_model",
                provider="openai",
                model_catalog_id=self.fixture.model.id,
                template_id=self.fixture.repository.get_prompt_template("provider_diagnostic").id,
                privacy_class="selected_text_allowed",
                quality_level="standard",
                context_fingerprint=None,
                request_fingerprint="request-hash",
                input_summary_json={"request_id": "req-lookup", "task_type": "provider_diagnostic", "metadata_keys": []},
                output_reference=None,
                validation_status=None,
                cache_status="active",
                fallback_policy="none",
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

        found = self.fixture.repository.find_execution_by_request_id("req-lookup")
        self.assertIsNotNone(found)
        self.assertEqual(found.execution_uuid, execution.execution_uuid)

    def test_list_executions_round_trips_records(self) -> None:
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
                request_fingerprint="request-hash-2",
                input_summary_json={"request_id": "req-list", "task_type": "provider_diagnostic", "metadata_keys": []},
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
        executions = self.fixture.repository.list_executions()
        self.assertTrue(any(item.execution_uuid == execution.execution_uuid for item in executions))


if __name__ == "__main__":
    unittest.main()
