from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest

from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


def _workspace(service) -> WorkspaceViewModel:
    workspace = WorkspaceViewModel.__new__(WorkspaceViewModel)
    workspace.ai_runtime_service = service
    workspace.register_background_task = lambda **kwargs: SimpleNamespace(task_id="task-1", **kwargs)
    workspace.complete_background_task = lambda task_id, message=None: SimpleNamespace(task_id=task_id, message=message)
    workspace.fail_background_task = lambda task_id, error: SimpleNamespace(task_id=task_id, error=error)
    workspace.paths = SimpleNamespace(database_path=Path("runtime.db"), free_space_bytes=lambda: 1024 * 1024)
    workspace.diagnostic = SimpleNamespace(
        application_name="CIS",
        application_version="v31",
        os_name="Windows",
        os_version="11",
        os_architecture="x64",
        cpu_reported="CPU",
        logical_processors=8,
        python_version="3.11",
        python_executable="python.exe",
        git_version="git",
        nvidia_smi_available=False,
        nvidia_driver_version=None,
        cuda_version_reported=None,
        cuda_driver_detected=False,
        state=SimpleNamespace(cuda_runtime_not_verified=True, ready_for_basic_mode=True),
        gpu_devices=[],
        preferred_compute_backend="CPU",
    )
    workspace.media_tools = lambda: SimpleNamespace(
        ffmpeg=SimpleNamespace(version="1.0", available=True),
        ffprobe=SimpleNamespace(version="1.0", available=True),
    )
    workspace.selected_creator = lambda: None
    workspace.selected_project = lambda: None
    workspace.activity_log = []
    workspace.background_tasks = lambda: []
    return workspace


class AIRuntimeGUITests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai")
        self.fixture.service.providers["anthropic"] = FakeProvider("anthropic")
        self.workspace = _workspace(self.fixture.service)

    def test_workspace_wrappers_save_replace_delete_and_history(self) -> None:
        self.workspace.ai_runtime_store_provider_credential("openai", "sk-new")
        status = self.workspace.ai_runtime_provider_status()
        self.assertEqual(status["openai"]["configured"], True)
        self.assertNotEqual(status["openai"]["masked_key"], "sk-new")

        self.workspace.ai_runtime_store_provider_credential("openai", "sk-replaced")
        status = self.workspace.ai_runtime_provider_status()
        self.assertNotEqual(status["openai"]["masked_key"], "sk-replaced")

        self.workspace.ai_runtime_delete_provider_credential("openai")
        status = self.workspace.ai_runtime_provider_status()
        self.assertEqual(status["openai"]["configured"], False)

        self.workspace.ai_runtime_assign_role(role="evaluation_model", provider="openai", model_id=self.fixture.model.model_id, is_default=False)
        self.workspace.ai_runtime_set_monthly_budget(25.0, "USD")
        self.workspace.ai_runtime_set_per_task_budget(5.0, "USD")
        budget = self.workspace.ai_runtime_get_budget_policy()
        self.assertEqual(budget["monthly_limit"], 25.0)
        self.assertEqual(budget["per_task_limit"], 5.0)

        executions = self.workspace.ai_runtime_list_executions()
        self.assertEqual(executions, [])

    def test_workspace_diagnostic_and_history_are_connected(self) -> None:
        result = self.workspace.run_ai_runtime_diagnostic(provider="openai")
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.workspace.ai_runtime_service.provider_status()["openai"]["configured"], True)
        self.assertTrue(self.workspace.ai_runtime_list_executions())
        execution = self.workspace.ai_runtime_get_execution(result.execution_id)
        self.assertIsNotNone(execution)
        self.assertEqual(execution["execution_uuid"], result.execution_id)

    def test_system_items_show_runtime_state_without_leaking_secret(self) -> None:
        items = self.workspace.system_items()
        labels = {item.label for item in items}
        self.assertIn("AI runtime", labels)
        self.assertIn("OpenAI", labels)
        self.assertIn("Anthropic", labels)
        self.assertIn("Credenciales IA", labels)
        self.assertNotIn("sk-openai-test", " ".join(item.value for item in items))


if __name__ == "__main__":
    unittest.main()
