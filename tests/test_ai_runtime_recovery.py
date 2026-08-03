from __future__ import annotations

import unittest
from uuid import uuid4

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionRecord, AIExecutionRequest
from creator_intelligence_studio.infrastructure.ai_runtime.orchestrator import AIOrchestrator
from creator_intelligence_studio.infrastructure.ai_runtime.policies import AIResultValidator, CostEstimator, CostTracker, PrivacyPolicyEngine
from creator_intelligence_studio.infrastructure.ai_runtime.providers import AIProvider
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


def _request(*, request_id: str = "recovery-request", cache_policy: str = "bypass") -> AIExecutionRequest:
    return AIExecutionRequest(
        request_id=request_id,
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
        budget={"monthly_limit": None},
        cache_policy=cache_policy,
        fallback_policy="none",
        approval_policy="not_required",
        metadata={},
    )


def _store_execution(fixture, *, status: str, request_id: str, execution_uuid: str | None = None, approval_required: bool = False, approved_at: str | None = None):
    execution_uuid = execution_uuid or str(uuid4())
    return fixture.repository.store_execution(
        AIExecutionRecord(
            execution_uuid=execution_uuid,
            creator_id=None,
            project_id=None,
            task_type="provider_diagnostic",
            operation="extract",
            status=status,
            requested_model_role="cheap_structured_model",
            provider="openai",
            model_catalog_id=fixture.model.id,
            template_id=fixture.repository.get_prompt_template("provider_diagnostic").id,
            privacy_class="selected_text_allowed",
            quality_level="standard",
            context_fingerprint=None,
            request_fingerprint=request_id,
            input_summary_json={"request_id": request_id, "task_type": "provider_diagnostic"},
            output_reference=None,
            validation_status="rejected" if status in {"cancelled", "failed"} else None,
            cache_status="active",
            fallback_policy="none",
            approval_required=approval_required,
            approved_at=approved_at,
            started_at="2026-08-03T16:00:00Z",
            completed_at=None,
            latency_ms=None,
            error_category=None,
            error_code=None,
            error_message_safe=None,
            created_at="2026-08-03T16:00:00Z",
            updated_at="2026-08-03T16:00:00Z",
        )
    )


class AIRuntimeRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)

    def _orchestrator(self, provider: AIProvider | None = None) -> AIOrchestrator:
        return AIOrchestrator(
            model_registry=self.fixture.model_registry,
            prompt_registry=self.fixture.prompt_registry,
            credential_store=self.fixture.credential_store,
            repository=self.fixture.repository,
            providers={"openai": provider or FakeProvider("openai")},
            privacy_policy=PrivacyPolicyEngine(),
            cost_estimator=CostEstimator(),
            cost_tracker=CostTracker(),
            result_validator=AIResultValidator(),
        )

    def test_queued_or_running_execution_is_marked_interrupted_on_startup(self) -> None:
        queued = _store_execution(self.fixture, status="queued", request_id="queued-stale")
        running = _store_execution(self.fixture, status="running", request_id="running-stale")

        recovered = self.fixture.service.recover_orphaned_diagnostic_executions()

        self.assertEqual({item["execution_uuid"] for item in recovered}, {queued.execution_uuid, running.execution_uuid})
        queued_record = self.fixture.repository.get_execution_by_uuid(queued.execution_uuid)
        running_record = self.fixture.repository.get_execution_by_uuid(running.execution_uuid)
        self.assertEqual(queued_record.status, "cancelled")
        self.assertEqual(running_record.error_category, "interrupted")
        self.assertEqual(running_record.input_summary_json.get("retry_allowed"), True)

    def test_awaiting_approval_is_preserved_on_startup(self) -> None:
        awaiting = _store_execution(self.fixture, status="awaiting_approval", request_id="awaiting-safe", approval_required=True)

        recovered = self.fixture.service.recover_orphaned_diagnostic_executions()

        self.assertEqual(recovered, [])
        self.assertEqual(self.fixture.repository.get_execution_by_uuid(awaiting.execution_uuid).status, "awaiting_approval")

    def test_cancel_diagnostic_execution_releases_retry_path(self) -> None:
        queued = _store_execution(self.fixture, status="queued", request_id="retry-after-cancel")

        cancelled = self.fixture.service.cancel_diagnostic_execution(
            queued.execution_uuid,
            cancelled_by="usuario",
            cancellation_reason="Cancelada desde Task Center.",
        )
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["error_category"], "cancelled_by_user")

        provider = FakeProvider("openai")
        orchestrator = self._orchestrator(provider)
        result = orchestrator.run(_request(request_id="retry-after-cancel"), provider="openai")

        self.assertEqual(result.status, "completed")
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(self.fixture.repository.list_executions()), 2)

    def test_recovery_does_not_call_provider_automatically(self) -> None:
        _store_execution(self.fixture, status="queued", request_id="no-auto-call")
        provider = FakeProvider("openai")
        self.fixture.service.recover_orphaned_diagnostic_executions()
        self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
