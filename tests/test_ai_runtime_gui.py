from __future__ import annotations

import inspect
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget, QMessageBox
from PySide6.QtTest import QTest

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIModelCatalogEntry
from creator_intelligence_studio.presentation.desktop import main_window as main_window_module
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.views.ai_runtime_overview_view import (
    AIRuntimeOverviewView,
    ProviderCredentialDialog,
)
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture


class DummyView(QWidget):
    def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - simple test double
        super().__init__()
        self._title = self.__class__.__name__

    def refresh(self) -> None:
        pass


class DummyInspector(QWidget):
    def set_compact_mode(self, *_args, **_kwargs) -> None:
        pass


class DesktopWorkspaceFacade:
    def __init__(self, service) -> None:
        self.ai_runtime_service = service
        self.selected_creator_id = None
        self.selected_project_id = None
        self.ui_state = SimpleNamespace(last_page="home")
        self.activity_log: list[str] = []
        self._tasks: list[SimpleNamespace] = []
        self.diagnostic = SimpleNamespace(
            application_name="Creator Intelligence Studio",
            application_version="0.1.0",
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
        self.paths = SimpleNamespace(
            database_path=Path("runtime.db"),
            free_space_bytes=lambda: 1024 * 1024,
        )

    def creators(self) -> list[object]:
        return []

    def projects_for_selected_creator(self) -> list[object]:
        return []

    def selected_creator(self):
        return None

    def selected_project(self):
        return None

    def media_tools(self):
        return SimpleNamespace(
            ffmpeg=SimpleNamespace(version="1.0", available=True),
            ffprobe=SimpleNamespace(version="1.0", available=True),
        )

    def refresh(self) -> None:
        pass

    def select_creator(self, creator_id: str) -> None:
        self.selected_creator_id = creator_id

    def select_project(self, project_id: str) -> None:
        self.selected_project_id = project_id

    def set_last_page(self, key: str) -> None:
        self.ui_state.last_page = key

    def register_background_task(self, **kwargs):
        task = SimpleNamespace(task_id=f"task-{len(self._tasks) + 1}", **kwargs)
        self._tasks.append(task)
        return task

    def complete_background_task(self, task_id: str, message: str | None = None):
        for task in self._tasks:
            if task.task_id == task_id:
                task.status = "completed"
                task.message = message
                return task
        return SimpleNamespace(task_id=task_id, status="completed", message=message)

    def fail_background_task(self, task_id: str, error: str):
        for task in self._tasks:
            if task.task_id == task_id:
                task.status = "failed"
                task.error = error
                return task
        return SimpleNamespace(task_id=task_id, status="failed", error=error)

    def background_tasks(self) -> list[SimpleNamespace]:
        return list(self._tasks)

    def ai_runtime_provider_status(self):
        return self.ai_runtime_service.provider_status()

    def ai_runtime_store_provider_credential(self, provider: str, api_key: str):
        return self.ai_runtime_service.store_provider_credential(provider, api_key)

    def ai_runtime_delete_provider_credential(self, provider: str):
        return self.ai_runtime_service.delete_provider_credential(provider)

    def ai_runtime_test_provider(self, provider: str):
        return self.ai_runtime_service.test_provider(provider)

    def ai_runtime_list_models(self, provider: str | None = None):
        return self.ai_runtime_service.list_models(provider)

    def ai_runtime_list_assignable_models(self, provider: str, role: str):
        return self.ai_runtime_service.list_assignable_models(provider, role)

    def ai_runtime_refresh_provider_models(self, provider: str):
        return self.ai_runtime_service.refresh_provider_models(provider)

    def ai_runtime_assign_role(self, **kwargs):
        return self.ai_runtime_service.assign_role(**kwargs)

    def ai_runtime_get_budget_policy(self, creator_id: str | None = None, provider: str | None = None):
        return self.ai_runtime_service.get_budget_policy(creator_id=creator_id, provider=provider)

    def ai_runtime_get_runtime_setting(self, setting_key: str, scope_id: str | None = None):
        return self.ai_runtime_service.get_runtime_setting(setting_key, scope_id)

    def ai_runtime_set_runtime_setting(self, setting_key: str, value: dict[str, object], scope_id: str | None = None):
        return self.ai_runtime_service.set_runtime_setting(setting_key, value, scope_id)

    def ai_runtime_update_budget_policy(self, **kwargs):
        return self.ai_runtime_service.update_budget_policy(**kwargs)

    def ai_runtime_list_executions(self, creator_id: str | None = None, provider: str | None = None, limit: int = 50):
        return self.ai_runtime_service.list_executions(creator_id=creator_id, provider=provider, limit=limit)

    def ai_runtime_get_execution(self, execution_uuid: str):
        return self.ai_runtime_service.get_execution(execution_uuid)

    def ai_runtime_list_usage_records(self, execution_id: str | None = None):
        return self.ai_runtime_service.list_usage_records(execution_id)

    def ai_runtime_list_payloads(self, execution_id: str):
        return self.ai_runtime_service.list_payloads(execution_id)

    def ai_runtime_budget_snapshot(self, creator_id: str | None = None, provider: str | None = None):
        return self.ai_runtime_service.budget_snapshot(creator_id=creator_id, provider=provider)

    def run_ai_runtime_diagnostic(self, *, provider: str | None = None, role: str | None = None, cache_policy: str = "use"):
        task = self.register_background_task(
            title="AI Provider Diagnostics",
            status="running",
            stage_name="diagnostic",
            video_title=provider or role or "provider_diagnostic",
            action_id="provider_diagnostic",
            progress_percent=5.0,
            message="Ejecutando diagnostico de proveedor de IA",
            cancellable=True,
            payload={"kind": "ai_runtime_diagnostic", "provider": provider, "role": role, "cache_policy": cache_policy},
        )
        try:
            result = self.ai_runtime_service.diagnostic_run(provider=provider, role=role, cache_policy=cache_policy)
        except Exception as exc:  # pragma: no cover - defensive for the test harness
            self.fail_background_task(task.task_id, f"Diagnostico de IA fallido: {exc}")
            raise
        self.complete_background_task(task.task_id, "Diagnostico de IA completado")
        return result


def _patch_main_window_views():
    stack = patch.multiple(
        main_window_module,
        **{
            name: DummyView
            for name, value in vars(main_window_module).items()
            if inspect.isclass(value)
            and issubclass(value, QWidget)
            and getattr(value, "__module__", "").startswith("creator_intelligence_studio.presentation.desktop")
            and name != "AIRuntimeOverviewView"
            and name != "InspectorPanel"
        },
    )
    inspector_patch = patch.object(main_window_module, "InspectorPanel", DummyInspector)
    return stack, inspector_patch


class AIRuntimeGUIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai")
        self.fixture.service.providers["anthropic"] = FakeProvider("anthropic")
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        self.qt_app = QApplication.instance()

    def test_real_window_exposes_ai_runtime_navigation_and_tabs(self) -> None:
        stack, inspector_patch = _patch_main_window_views()
        with stack, inspector_patch:
            window = MainWindow(self.workspace)
            window.show()
            labels = [window.sidebar.item(i).text() for i in range(window.sidebar.count())]
            self.assertIn("AI Runtime", labels)
            row = labels.index("AI Runtime")
            item_rect = window.sidebar.visualItemRect(window.sidebar.item(row))
            QTest.mouseClick(
                window.sidebar.viewport(),
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                item_rect.center(),
            )
            self.qt_app.processEvents()
            self.assertIs(window.stack.currentWidget(), window.ai_runtime_view)
            tab_labels = [window.ai_runtime_view.tabs.tabText(i) for i in range(window.ai_runtime_view.tabs.count())]
            self.assertEqual(
                tab_labels,
                [
                    "Proveedores",
                    "Modelos y roles",
                    "Presupuesto y consumo",
                    "Diagnostico",
                    "Historial",
                ],
            )
            self.assertTrue(window.sidebar.isVisible())
            self.assertEqual(window.status_label.text(), "AI Runtime")
            window.close()

    def test_provider_cards_configure_test_and_delete(self) -> None:
        view = AIRuntimeOverviewView(self.workspace)
        provider_card = view.providers_tab.cards["openai"]

        QTest.mouseClick(provider_card.configure_button, Qt.MouseButton.LeftButton)
        dialog = QApplication.activeModalWidget()
        self.assertIsInstance(dialog, ProviderCredentialDialog)
        dialog.toggle_button.click()
        self.assertEqual(dialog.secret_edit.echoMode(), QLineEdit.EchoMode.Normal)
        dialog.secret_edit.setText("sk-new-openai")
        QTest.mouseClick(dialog.save_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()

        status = self.workspace.ai_runtime_provider_status()["openai"]
        self.assertTrue(status["configured"])
        self.assertNotEqual(status["masked_key"], "sk-new-openai")

        with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            QTest.mouseClick(provider_card.test_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        status = self.workspace.ai_runtime_provider_status()["openai"]
        self.assertEqual(status["last_check"]["status"], "ok")
        self.assertEqual(status["last_model_sync"]["status"], "ok")
        self.assertGreaterEqual(status["last_model_sync"]["found_count"], 1)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            QTest.mouseClick(provider_card.delete_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        status = self.workspace.ai_runtime_provider_status()["openai"]
        self.assertFalse(status["configured"])

    def test_provider_links_open_official_urls(self) -> None:
        view = AIRuntimeOverviewView(self.workspace)
        with patch("creator_intelligence_studio.presentation.desktop.views.ai_runtime_overview_view.QDesktopServices.openUrl") as open_url:
            QTest.mouseClick(view.providers_tab.cards["anthropic"].keys_button, Qt.MouseButton.LeftButton)
            open_url.assert_called_once()
            url = open_url.call_args.args[0].toString()
            self.assertIn("anthropic", url)

    def test_roles_view_refresh_catalog_populates_selector_and_persists_assignment(self) -> None:
        self.fixture = build_runtime_fixture(model_status="deprecated")
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai")
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.roles_tab.provider_combo.setCurrentIndex(view.roles_tab.provider_combo.findData("openai"))
        view.roles_tab.role_combo.setCurrentIndex(view.roles_tab.role_combo.findData("cheap_structured_model"))
        view.roles_tab.refresh()
        self.assertEqual(view.roles_tab.model_combo.count(), 0)
        self.assertIn("No hay modelos sincronizados", view.roles_tab.model_hint_label.text())

        with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            QTest.mouseClick(view.providers_tab.cards["openai"].sync_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()

        view.roles_tab.refresh()
        self.assertGreater(view.roles_tab.model_combo.count(), 0)
        combo_texts = [view.roles_tab.model_combo.itemText(i) for i in range(view.roles_tab.model_combo.count())]
        self.assertTrue(any("openai-structured-mini" in text for text in combo_texts))
        view.roles_tab.enabled_checkbox.setChecked(True)
        self.assertTrue(view.roles_tab.save_button.isEnabled())

        with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            QTest.mouseClick(view.roles_tab.save_button, Qt.MouseButton.LeftButton)
        assignment = self.fixture.service.model_registry.resolve_role("cheap_structured_model", creator_id=None, provider="openai")
        self.assertIsNotNone(assignment)
        view.diagnostics_tab.refresh()
        self.assertIn("openai-structured-mini", view.diagnostics_tab.model_line.text())

    def test_budget_view_loads_edits_and_reflects_limits(self) -> None:
        self.workspace.run_ai_runtime_diagnostic(provider="openai", role="cheap_structured_model")
        view = AIRuntimeOverviewView(self.workspace)
        snapshot = self.workspace.ai_runtime_budget_snapshot()
        self.assertGreater(snapshot["monthly_cost"], 0.0)

        view.budget_tab.currency_edit.setCurrentText("USD")
        view.budget_tab.monthly_limit_edit.setText("25")
        view.budget_tab.per_task_limit_edit.setText("5")
        view.budget_tab.hard_block_checkbox.setChecked(False)
        view.budget_tab.approval_threshold_edit.setValue(75.0)
        view.budget_tab.fallback_checkbox.setChecked(False)
        with patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            QTest.mouseClick(view.budget_tab.save_button, Qt.MouseButton.LeftButton)
        policy = self.workspace.ai_runtime_get_budget_policy()
        self.assertEqual(policy["monthly_limit"], 25.0)
        self.assertEqual(policy["per_task_limit"], 5.0)
        self.assertFalse(policy["hard_block_enabled"])
        runtime_setting = self.workspace.ai_runtime_get_runtime_setting("cross_provider_fallback_enabled")
        self.assertFalse(runtime_setting["enabled"])

    def test_diagnostics_view_handles_missing_key_and_cache_hit(self) -> None:
        self.fixture.repository.upsert_model_catalog_entry(
            AIModelCatalogEntry(
                provider="anthropic",
                model_id="diag-model-anthropic",
                display_name="Anthropic Diagnostic Model",
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
        self.fixture.service.assign_role(
            role="cheap_structured_model",
            provider="anthropic",
            model_id="diag-model-anthropic",
            display_name="Anthropic Diagnostic Model",
            is_default=True,
            status="approved",
            capabilities_json={"structured_output": True},
            snapshot_or_version="v1",
        )
        self.workspace.ai_runtime_delete_provider_credential("anthropic")
        view = AIRuntimeOverviewView(self.workspace)
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("anthropic"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertIn("No hay una credencial configurada", view.diagnostics_tab.message_label.text())
        self.assertEqual(view.diagnostics_tab.status_label.text(), "blocked_by_credentials")

        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        self.workspace.ai_runtime_store_provider_credential("openai", "sk-openai-test")
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertEqual(view.diagnostics_tab.status_label.text(), "completed")
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertIn("exact_hit", view.diagnostics_tab.cache_label.text())

    def test_history_view_loads_detail_without_secrets(self) -> None:
        self.workspace.run_ai_runtime_diagnostic(provider="openai", role="cheap_structured_model")
        view = AIRuntimeOverviewView(self.workspace)
        self.assertGreater(view.history_tab.table.rowCount(), 0)
        view.history_tab.table.selectRow(0)
        self.qt_app.processEvents()
        detail = view.history_tab.detail.toPlainText()
        self.assertNotIn("Authorization", detail)
        self.assertNotIn("sk-openai-test", detail)


if __name__ == "__main__":
    unittest.main()
