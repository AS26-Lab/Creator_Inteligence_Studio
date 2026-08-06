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
        fake = StrictOpenAIContractFake(model_id="gpt-5.6-luna")

        awaiting = self.fixture.service.diagnostic_run(provider="openai", role="cheap_structured_model")
        self.assertEqual(awaiting.status, "awaiting_approval")
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)

        with patch("creator_intelligence_studio.infrastructure.ai_runtime.providers.urlopen", side_effect=fake):
            completed = self.fixture.service.approve_and_run_diagnostic(awaiting.execution_id, approved_by="tester", approval_reason="manual review")

        self.assertEqual(completed.status, "completed")
        self.assertEqual(fake.calls, 1)
        self.assertEqual(len(self.fixture.repository.list_executions()), 1)
        self.assertEqual(len(self.fixture.repository.list_usage_records()), 1)
        execution = self.fixture.repository.get_execution_by_uuid(awaiting.execution_id)
        self.assertIsNotNone(execution)
        self.assertEqual(execution.status, "completed")
        self.assertEqual(completed.execution_id, awaiting.execution_id)
        self.assertGreater(completed.usage.input_tokens, 0)
        self.assertGreater(completed.usage.output_tokens, 0)


if __name__ == "__main__":
    unittest.main()
