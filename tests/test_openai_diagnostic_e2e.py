from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.ai_runtime_test_support import StrictOpenAIContractFake, build_runtime_fixture


class OpenAIDiagnosticE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture(
            model_id="gpt-5.6-luna",
            input_price_per_million=None,
            output_price_per_million=None,
            cached_input_price_per_million=None,
        )
        self.addCleanup(self.fixture.cleanup)

    def test_diagnostic_waits_for_approval_then_completes_with_single_call(self) -> None:
        fake = StrictOpenAIContractFake(
            model_id="gpt-5.6-luna",
            success_payload={
                "id": "resp_diag_success",
                "object": "response",
                "status": "completed",
                "completed_at": 1740855870,
                "error": None,
                "incomplete_details": None,
                "model": "gpt-5.6-luna",
                "output": [
                    {
                        "id": "msg_diag_success",
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {"type": "output_text", "text": " OK. ", "annotations": []},
                        ],
                    }
                ],
                "output_text": " OK. ",
                "reasoning_effort": {"effort": "none"},
                "truncation": "disabled",
                "usage": {
                    "input_tokens": 70,
                    "output_tokens": 64,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                    "total_tokens": 134,
                },
            },
        )

        awaiting = self.fixture.service.diagnostic_run(provider="openai", role="cheap_structured_model")
        self.assertEqual(awaiting.status, "awaiting_approval")
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake):
            completed = self.fixture.service.approve_and_run_diagnostic(awaiting.execution_id, approved_by="tester", approval_reason="manual review")

        self.assertEqual(completed.status, "completed")
        self.assertEqual(fake.calls, 1)
        self.assertEqual(fake.request_summaries[0]["endpoint"], "responses")
        self.assertEqual(fake.request_summaries[0]["fields"]["input"], "redacted:string")
        self.assertEqual(fake.request_summaries[0]["fields"]["max_output_tokens"], "integer")
        self.assertEqual(fake.request_summaries[0]["fields"]["reasoning"], "object")
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)
        self.assertEqual(len(self.fixture.repository.list_usage_records()), 1)
        execution = self.fixture.repository.get_execution_by_uuid(awaiting.execution_id)
        self.assertIsNotNone(execution)
        self.assertEqual(execution.status, "completed")
        self.assertEqual(completed.execution_id, awaiting.execution_id)
        self.assertEqual(completed.usage.input_tokens, 70)
        self.assertEqual(completed.usage.output_tokens, 64)
        self.assertEqual(completed.validation.status, "valid")
        self.assertEqual(completed.result.strip(), "OK.")
        self.assertEqual(completed.latency.attempts, 1)


if __name__ == "__main__":
    unittest.main()
