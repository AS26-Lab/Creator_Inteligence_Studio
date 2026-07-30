from __future__ import annotations

import argparse
import io
import json
import unittest
from types import SimpleNamespace

from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.ai_runtime_cli import handle_ai_command
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


class AIRuntimeCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai")
        self.fixture.service.providers["anthropic"] = FakeProvider("anthropic")

    def _invoke(self, argv: list[str]):
        parser = build_parser()
        args = parser.parse_args(argv)
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = handle_ai_command(args, service=self.fixture.service, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_ai_providers_list_status_and_test(self) -> None:
        code, stdout, stderr = self._invoke(["ai", "providers", "list", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout), ["openai", "anthropic"])
        self.assertEqual(stderr, "")

        code, stdout, _ = self._invoke(["ai", "providers", "status", "--json"])
        status = json.loads(stdout)
        self.assertIn("openai", status)
        self.assertIn("masked_key", status["openai"])
        self.assertNotIn("sk-openai-test", stdout)

        code, stdout, _ = self._invoke(["ai", "providers", "test", "--provider", "openai", "--json"])
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "ok")

    def test_ai_models_roles_and_budget_commands(self) -> None:
        code, stdout, _ = self._invoke(["ai", "models", "list", "--json"])
        models = json.loads(stdout)
        self.assertTrue(models)

        code, stdout, _ = self._invoke(["ai", "roles", "list", "--json"])
        roles = json.loads(stdout)
        self.assertTrue(roles)

        code, stdout, _ = self._invoke(["ai", "roles", "assign", "--role", "evaluation_model", "--provider", "openai", "--model", self.fixture.model.model_id, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["role"], "evaluation_model")

        code, stdout, _ = self._invoke(["ai", "budget", "show", "--json"])
        budget = json.loads(stdout)
        self.assertIn("hard_block_enabled", budget)
        self.assertTrue(budget["hard_block_enabled"])

        code, stdout, _ = self._invoke(["ai", "budget", "set-monthly", "--amount", "12.5", "--currency", "USD", "--json"])
        self.assertEqual(json.loads(stdout)["monthly_limit"], 12.5)

        code, stdout, _ = self._invoke(["ai", "budget", "set-per-task", "--amount", "1.5", "--currency", "USD", "--json"])
        self.assertEqual(json.loads(stdout)["per_task_limit"], 1.5)

    def test_ai_diagnostic_executions_and_json_output(self) -> None:
        code, stdout, _ = self._invoke(["ai", "diagnostic", "run", "--provider", "openai", "--json"])
        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "completed")
        self.assertIn("execution_id", result)

        code, stdout, _ = self._invoke(["ai", "executions", "list", "--json"])
        executions = json.loads(stdout)
        self.assertTrue(executions)

        code, stdout, _ = self._invoke(["ai", "executions", "show", result["execution_id"], "--json"])
        execution = json.loads(stdout)
        self.assertEqual(execution["execution_uuid"], result["execution_id"])

    def test_ai_commands_reject_api_key_arguments(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["ai", "providers", "test", "--provider", "openai", "--api-key", "sk-real"])

    def test_ai_command_returns_nonzero_on_missing_service(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["ai", "providers", "list", "--json"])
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = handle_ai_command(args, service=None, stdout=stdout, stderr=stderr)
        self.assertEqual(code, 1)
        self.assertIn("no esta disponible", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
