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

from creator_intelligence_studio.infrastructure.ai_runtime.models import AIExecutionError, AIModelCatalogEntry
from creator_intelligence_studio.presentation.desktop import main_window as main_window_module
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.views.ai_runtime_overview_view import (
    AIRuntimeOverviewView,
    ProviderCredentialDialog,
)
from tests.ai_runtime_test_support import FakeProvider, build_runtime_fixture
from tests.test_ai_runtime_model_selection import build_role_catalog


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
        self._ai_runtime_roles_mode = "recommended"
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

    def ai_runtime_list_model_selection(
        self,
        provider: str,
        role: str,
        *,
        query: str | None = None,
        mode: str = "compatible",
        show_non_recommended: bool = False,
        show_all_models: bool = False,
        show_snapshots_and_previews: bool = False,
        selected_model_id: str | None = None,
    ):
        return self.ai_runtime_service.list_model_selection(
            provider,
            role,
            query=query,
            mode=mode,
            show_non_recommended=show_non_recommended,
            show_all_models=show_all_models,
            show_snapshots_and_previews=show_snapshots_and_previews,
            selected_model_id=selected_model_id,
        )

    def ai_runtime_guided_configuration_summary(self, provider: str, *, profile_key: str = "equilibrado"):
        return self.ai_runtime_service.guided_configuration_summary(provider, profile_key=profile_key, creator_id=self.selected_creator_id)

    def ai_runtime_apply_recommended_configuration(self, provider: str, *, profile_key: str = "equilibrado", replace_existing: bool = True):
        return self.ai_runtime_service.apply_recommended_configuration(
            provider,
            profile_key=profile_key,
            creator_id=self.selected_creator_id,
            replace_existing=replace_existing,
        )

    def ai_runtime_roles_mode(self) -> str:
        return self._ai_runtime_roles_mode

    def set_ai_runtime_roles_mode(self, mode: str) -> None:
        self._ai_runtime_roles_mode = "advanced" if str(mode).strip().lower() == "advanced" else "recommended"

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

    def _wait_until(self, predicate, timeout_ms: int = 10000) -> bool:
        deadline = timeout_ms // 25
        for _ in range(max(1, deadline)):
            self.qt_app.processEvents()
            if predicate():
                return True
            QTest.qWait(25)
        self.qt_app.processEvents()
        return predicate()

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

    def test_guided_configuration_mode_applies_recommendation(self) -> None:
        self.fixture = build_runtime_fixture(provider="anthropic")
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai", discovered_models=build_role_catalog())
        self.fixture.service.refresh_provider_models("openai")
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        self.assertTrue(view.roles_tab.table.isHidden())
        self.assertFalse(view.roles_tab.guided_panel.isHidden())
        self.assertGreater(view.roles_tab.guided_roles_table.rowCount(), 0)
        self.assertIn("Equilibrado", view.roles_tab.guided_summary_label.text())
        self.assertTrue(
            any(
                view.roles_tab.guided_roles_table.item(row, 3) is not None
                and "No requerido en la fase actual" in view.roles_tab.guided_roles_table.item(row, 3).text()
                for row in range(view.roles_tab.guided_roles_table.rowCount())
            )
        )

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), patch.object(QMessageBox, "information", return_value=QMessageBox.StandardButton.Ok):
            QTest.mouseClick(view.roles_tab.apply_recommended_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()

        resolved = self.fixture.service.model_registry.resolve_role("cheap_structured_model", creator_id=None, provider="openai")
        self.assertIsNotNone(resolved)
        _, model = resolved
        self.assertNotEqual(model.model_id, "gpt-3.5-turbo")
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))
        view.diagnostics_tab.refresh()
        self.assertNotIn("Falta configurar", view.diagnostics_tab.model_line.text())

    def test_roles_view_mode_switch_is_persistent_and_reversible(self) -> None:
        self.fixture = build_runtime_fixture(provider="anthropic")
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai", discovered_models=build_role_catalog())
        self.fixture.service.refresh_provider_models("openai")
        assignable = self.fixture.service.list_assignable_models("openai", "cheap_structured_model")
        self.assertGreater(len(assignable), 0)
        base_model = assignable[0]
        self.fixture.service.assign_role(
            role="cheap_structured_model",
            provider="openai",
            model_id=str(base_model["model_id"]),
            display_name=str(base_model.get("display_name") or base_model["model_id"]),
            creator_id=None,
            is_default=True,
            is_enabled=True,
            fallback_policy="none",
            quality_level="standard",
            status=str(base_model.get("status") or "approved"),
            capabilities_json=dict(base_model.get("capabilities_json") or {}),
            snapshot_or_version=base_model.get("snapshot_or_version"),
        )
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.show()
        self.qt_app.processEvents()

        self.assertEqual(view.roles_tab.mode_combo.currentData(), "recommended")
        self.assertFalse(view.roles_tab.mode_combo.isHidden())
        self.assertTrue(view.roles_tab.guided_panel.isVisible() or not view.roles_tab.guided_panel.isHidden())

        QTest.mouseClick(view.roles_tab.open_advanced_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertEqual(view.roles_tab.mode_combo.currentData(), "advanced")
        self.assertFalse(view.roles_tab.mode_combo.isHidden())
        self.assertFalse(view.roles_tab.back_to_recommended_button.isHidden())
        self.assertTrue(view.roles_tab.editor_frame.isVisible() or not view.roles_tab.editor_frame.isHidden())

        current_assignment = self.fixture.service.repository.resolve_role_assignment("cheap_structured_model", creator_id=None, provider="openai")
        self.assertIsNotNone(current_assignment)
        before_model_catalog_id = current_assignment.model_catalog_id if current_assignment is not None else None
        self.assertIsNotNone(before_model_catalog_id)

        self.assertGreaterEqual(view.roles_tab.model_combo.count(), 1)
        alternate_index = -1
        for index in range(view.roles_tab.model_combo.count()):
            data = view.roles_tab.model_combo.itemData(index)
            if isinstance(data, dict) and str(data.get("model_id")) != str(before_model_catalog_id):
                alternate_index = index
                break
        self.assertGreaterEqual(alternate_index, 0)
        view.roles_tab.model_combo.setCurrentIndex(alternate_index)
        self.qt_app.processEvents()

        view.tabs.setCurrentWidget(view.budget_tab)
        view.tabs.setCurrentWidget(view.roles_tab)
        self.qt_app.processEvents()
        self.assertEqual(view.roles_tab.mode_combo.currentData(), "advanced")
        self.assertEqual(view.roles_tab.findChildren(type(view.roles_tab.back_to_recommended_button)).count(view.roles_tab.back_to_recommended_button), 1)

        QTest.mouseClick(view.roles_tab.back_to_recommended_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertEqual(view.roles_tab.mode_combo.currentData(), "recommended")
        self.assertTrue(view.roles_tab.guided_panel.isVisible() or not view.roles_tab.guided_panel.isHidden())
        self.assertFalse(view.roles_tab.editor_frame.isVisible() and not view.roles_tab.editor_frame.isHidden())

        after_assignment = self.fixture.service.repository.resolve_role_assignment("cheap_structured_model", creator_id=None, provider="openai")
        self.assertIsNotNone(after_assignment)
        self.assertEqual(after_assignment.model_catalog_id, before_model_catalog_id)

    def test_roles_view_refresh_catalog_populates_selector_and_persists_assignment(self) -> None:
        self.fixture = build_runtime_fixture(model_status="deprecated")
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider(
            "openai",
            discovered_models=[
                {
                    "model_id": "openai-structured-mini",
                    "display_name": "OpenAI Structured Mini",
                    "snapshot_or_version": None,
                    "status": "approved",
                    "capabilities_json": {"structured_output": True, "image_input": True},
                    "supports_structured_output": True,
                    "supports_image_input": True,
                    "supports_audio_input": False,
                }
            ],
        )
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.roles_tab.mode_combo.setCurrentIndex(view.roles_tab.mode_combo.findData("advanced"))
        view.roles_tab._apply_mode_visibility()
        view.roles_tab.provider_combo.setCurrentIndex(view.roles_tab.provider_combo.findData("openai"))
        view.roles_tab.role_combo.setCurrentIndex(view.roles_tab.role_combo.findData("cheap_structured_model"))
        view.roles_tab.refresh()
        self.assertGreaterEqual(view.roles_tab.model_combo.count(), 1)
        self.assertIn("modelos", view.roles_tab.model_hint_label.text().lower())

        self.workspace.ai_runtime_refresh_provider_models("openai")
        view.roles_tab.show_non_recommended_checkbox.setChecked(True)
        view.roles_tab.refresh()
        self.assertGreaterEqual(view.roles_tab.model_combo.currentIndex(), 0)
        view.roles_tab.search_edit.setText("openai-structured-mini")
        view.roles_tab.refresh()
        self.assertGreaterEqual(view.roles_tab.model_combo.count(), 1)
        selected_index = -1
        for i in range(view.roles_tab.model_combo.count()):
            data = view.roles_tab.model_combo.itemData(i)
            if isinstance(data, dict) and data.get("model_id") == "openai-structured-mini":
                selected_index = i
                break
        self.assertGreaterEqual(selected_index, 0)
        view.roles_tab.model_combo.setCurrentIndex(selected_index)
        view.roles_tab.enabled_checkbox.setChecked(True)
        self.assertTrue(view.roles_tab.save_button.isEnabled())
        selected_model = view.roles_tab.model_combo.currentData()
        self.assertIsInstance(selected_model, dict)
        self.assertEqual(str(selected_model.get("model_id")), "openai-structured-mini")
        self.assertEqual(str(selected_model.get("status")), "approved")

    def test_roles_view_filters_large_catalog_and_all_mode_reveals_full_set(self) -> None:
        self.fixture = build_runtime_fixture()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.service.providers["openai"] = FakeProvider("openai", discovered_models=build_role_catalog())
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        self.fixture.service.refresh_provider_models("openai")
        view = AIRuntimeOverviewView(self.workspace)
        view.roles_tab.mode_combo.setCurrentIndex(view.roles_tab.mode_combo.findData("advanced"))
        view.roles_tab._apply_mode_visibility()
        view.roles_tab.provider_combo.setCurrentIndex(view.roles_tab.provider_combo.findData("openai"))
        view.roles_tab.role_combo.setCurrentIndex(view.roles_tab.role_combo.findData("cheap_structured_model"))
        view.roles_tab.refresh()
        self.assertLessEqual(view.roles_tab.model_combo.count(), 13)
        self.assertGreaterEqual(view.roles_tab.model_combo.currentIndex(), 0)
        self.assertIn("Recomendados:", view.roles_tab.counts_label.text())
        self.assertIn("Compatibles:", view.roles_tab.counts_label.text())
        self.assertIn("Desconocidos:", view.roles_tab.counts_label.text())
        self.assertIn("Catalogo:", view.roles_tab.counts_label.text())

        view.roles_tab.show_all_checkbox.setChecked(True)
        view.roles_tab.show_snapshots_checkbox.setChecked(True)
        view.roles_tab.show_non_recommended_checkbox.setChecked(True)
        view.roles_tab.refresh()
        self.assertGreaterEqual(view.roles_tab.model_combo.count(), 100)
        first_item = view.roles_tab.model_combo.itemText(0)
        self.assertNotIn("GPT-3.5 Turbo", first_item)

        view.roles_tab.search_edit.setText("gpt-4.1-mini")
        view.roles_tab.refresh()
        self.assertGreaterEqual(view.roles_tab.model_combo.count(), 1)
        selected_index = -1
        for i in range(view.roles_tab.model_combo.count()):
            data = view.roles_tab.model_combo.itemData(i)
            if isinstance(data, dict) and data.get("model_id") == "gpt-4.1-mini":
                selected_index = i
                break
        self.assertGreaterEqual(selected_index, 0)
        view.roles_tab.model_combo.setCurrentIndex(selected_index)
        selected_model = view.roles_tab.model_combo.currentData()
        self.assertIsInstance(selected_model, dict)
        self.assertEqual(str(selected_model.get("model_id")), "gpt-4.1-mini")

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
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertIn(view.diagnostics_tab.status_label.text(), {"blocked_by_credentials", "failed"})
        self.assertIn("No hay una credencial configurada", view.diagnostics_tab.message_label.text())

        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        self.workspace.ai_runtime_store_provider_credential("openai", "sk-openai-test")
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertIn(view.diagnostics_tab.status_label.text(), {"completed", "completed_with_warnings"})
        self.assertEqual(view.diagnostics_tab.run_button.isEnabled(), True)
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertIn(view.diagnostics_tab.status_label.text(), {"completed", "completed_with_warnings"})
        self.assertIn("exact_hit", view.diagnostics_tab.cache_label.text())

    def test_diagnostics_view_runs_in_background_shows_running_and_records_history(self) -> None:
        self.fixture.service.providers["openai"] = FakeProvider("openai", execution_delay_ms=150)
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))

        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        self.assertFalse(view.diagnostics_tab.run_button.isEnabled())
        self.assertIn("Preparando diagnóstico", view.diagnostics_tab.message_label.text())
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertIn(view.diagnostics_tab.status_label.text(), {"completed", "completed_with_warnings"})
        self.assertTrue(view.diagnostics_tab.run_button.isEnabled())
        self.assertEqual(self.fixture.service.providers["openai"].calls, 1)
        self.assertNotEqual(view.diagnostics_tab.execution_label.text(), "-")
        self.assertGreater(view.history_tab.table.rowCount(), 0)
        self.assertIn("Diagnóstico completado", view.diagnostics_tab.message_label.text())

    def test_diagnostics_view_handles_exception_and_reenables_button(self) -> None:
        self.fixture.service.providers["openai"] = FakeProvider(
            "openai",
            raise_on_execute=RuntimeError("boom"),
            execution_delay_ms=100,
        )
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))

        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        self.assertFalse(view.diagnostics_tab.run_button.isEnabled())
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertEqual(view.diagnostics_tab.status_label.text(), "failed")
        self.assertTrue(view.diagnostics_tab.run_button.isEnabled())
        self.assertIn("No se pudo completar el diagnóstico", view.diagnostics_tab.message_label.text())
        self.assertTrue(any(task.status == "failed" for task in self.workspace.background_tasks()))

    def test_diagnostics_view_records_failed_execution_from_provider_error(self) -> None:
        self.fixture.service.providers["openai"] = FakeProvider(
            "openai",
            error=AIExecutionError(
                category="rate_limit_error",
                safe_message="Provider request was rate limited.",
                retryable=True,
                suggested_action="Retry the request later.",
                technical_reference="HTTP 429",
            ),
            execution_delay_ms=100,
        )
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))

        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertEqual(view.diagnostics_tab.status_label.text(), "failed")
        self.assertTrue(view.diagnostics_tab.run_button.isEnabled())
        self.assertIn("No se pudo completar", view.diagnostics_tab.message_label.text())
        self.assertGreater(view.history_tab.table.rowCount(), 0)
        self.assertEqual(view.history_tab.table.item(0, 5).text(), "failed")

    def test_diagnostics_view_blocks_double_clicks_while_running(self) -> None:
        self.fixture.service.providers["openai"] = FakeProvider("openai", execution_delay_ms=200)
        self.workspace = DesktopWorkspaceFacade(self.fixture.service)
        view = AIRuntimeOverviewView(self.workspace)
        view.diagnostics_tab.provider_combo.setCurrentIndex(view.diagnostics_tab.provider_combo.findData("openai"))
        view.diagnostics_tab.role_combo.setCurrentIndex(view.diagnostics_tab.role_combo.findData("cheap_structured_model"))

        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        QTest.mouseClick(view.diagnostics_tab.run_button, Qt.MouseButton.LeftButton)
        thread = view.diagnostics_tab._diagnostic_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.qt_app.processEvents()
        self.assertIn(view.diagnostics_tab.status_label.text(), {"completed", "completed_with_warnings"})
        self.assertEqual(self.fixture.service.providers["openai"].calls, 1)

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
