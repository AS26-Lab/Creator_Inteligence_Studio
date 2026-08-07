from __future__ import annotations

import unittest
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from creator_intelligence_studio.domain.components.entities import (
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.views.local_components_view import LocalComponentsView
from tests.ai_runtime_test_support import build_runtime_fixture
from tests.test_ai_runtime_gui import DesktopWorkspaceFacade, _patch_main_window_views


def _installation(component_id: str, status: ComponentInstallationStatus, *, version: str | None = "1.0") -> ComponentInstallation:
    return ComponentInstallation(
        component_id=component_id,
        installation_status=status,
        installed_version=version,
        revision="1",
        install_type=ComponentInstallKind.MANAGED,
        location_path=f"C:/managed/{component_id}",
        location_reference="managed_root",
        detected_at=None,
        verified_at=None,
        health_status=RuntimeCheckStatus.READY if status == ComponentInstallationStatus.READY else RuntimeCheckStatus.NOT_CHECKED,
        source="test",
        managed=True,
        metadata={},
    )


class FakeLocalWorkspace:
    def __init__(self, *, report, installations, matrix) -> None:
        self.ui_state = SimpleNamespace(
            transcription_profile="balanced",
            preferred_transcription_device="auto",
            local_components_show_advanced_details=False,
        )
        self._report = report
        self._installations = tuple(installations)
        self._matrix = dict(matrix)
        self.profile_updates: list[tuple[str | None, str | None]] = []
        self.advanced_updates: list[bool] = []
        self.benchmark_calls: list[dict[str, object]] = []
        self.onboarding_updates: list[dict[str, object]] = []

    def transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return self._report

    def component_manager_status(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(installations=self._installations)

    def transcription_execution_plan(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(selected_profile_id=self._report.selected_profile.profile_id)

    def transcription_capability_matrix(self, *, preferred_device: str = "auto"):
        return dict(self._matrix)

    def background_tasks(self):
        return []

    def set_transcription_preferences(self, *, device: str | None = None, profile: str | None = None):
        self.profile_updates.append((device, profile))

    def set_local_components_advanced_details_visible(self, visible: bool) -> None:
        self.advanced_updates.append(visible)

    def run_transcription_benchmark(self, **kwargs):
        self.benchmark_calls.append(dict(kwargs))
        return SimpleNamespace()

    def set_onboarding_state(self, **changes):
        self.onboarding_updates.append(dict(changes))


class LocalComponentsGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.qt_app = QApplication.instance()

    def tearDown(self) -> None:
        if self.qt_app is None:
            return
        for widget in list(self.qt_app.topLevelWidgets()):
            close = getattr(widget, "close", None)
            if callable(close):
                close()
        self.qt_app.processEvents()

    def _wait_until(self, predicate, timeout_ms: int = 3000) -> bool:
        deadline = timeout_ms // 25
        for _ in range(max(1, deadline)):
            self.qt_app.processEvents()
            if predicate():
                return True
            QTest.qWait(25)
        self.qt_app.processEvents()
        return predicate()

    def test_navigation_exposes_local_components_page(self) -> None:
        fixture = build_runtime_fixture()
        self.addCleanup(fixture.cleanup)
        workspace = DesktopWorkspaceFacade(fixture.service)
        stack, inspector_patch = _patch_main_window_views()
        with stack, inspector_patch:
            window = MainWindow(workspace)
            self.addCleanup(window.close)
            labels = [window.sidebar.item(i).text() for i in range(window.sidebar.count())]
            self.assertIn("Componentes locales", labels)
            row = labels.index("Componentes locales")
            item_rect = window.sidebar.visualItemRect(window.sidebar.item(row))
            QTest.mouseClick(window.sidebar.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, item_rect.center())
            self.qt_app.processEvents()
            self.assertIs(window.stack.currentWidget(), window.local_components_view)

    def test_local_components_view_renders_ready_state_and_primary_action(self) -> None:
        report = SimpleNamespace(
            readiness="ready",
            can_transcribe_now=True,
            primary_message="Tu computadora esta lista para transcribir.",
            secondary_message="Todo listo.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
            selected_device="gpu",
            compute_type="int8",
            ffmpeg_status=SimpleNamespace(value="ready"),
            ffprobe_status=SimpleNamespace(value="ready"),
            runtime_status=SimpleNamespace(value="ready"),
            model_status=SimpleNamespace(value="ready"),
            gpu_status=SimpleNamespace(name="DETECTED"),
            benchmark_status=SimpleNamespace(name="READY", value="ready"),
            benchmark_age_seconds=10.0,
            technical_summary="summary",
            blockers=(),
            structured_suggested_actions=(
                SimpleNamespace(
                    action_id="choose_balanced",
                    action_type="choose_profile",
                    description="Usar este perfil",
                    available_now=True,
                    blocking=False,
                    target_component=None,
                    target_profile="balanced",
                    reason=None,
                ),
            ),
        )
        installations = [
            _installation("ffmpeg", ComponentInstallationStatus.READY),
            _installation("ffprobe", ComponentInstallationStatus.READY),
            _installation("transcription-runtime.faster-whisper", ComponentInstallationStatus.READY),
            _installation("transcription-model.small", ComponentInstallationStatus.READY),
        ]
        workspace = FakeLocalWorkspace(report=report, installations=installations, matrix={"balanced": report})
        opened = {"transcription": 0}
        view = LocalComponentsView(workspace, open_transcription_callback=lambda: opened.__setitem__("transcription", opened["transcription"] + 1))
        self.addCleanup(view.close)

        view.refresh()
        self.assertTrue(self._wait_until(lambda: view._status is not None))
        self.assertEqual(view.summary_label.text(), "Tu computadora esta lista para transcribir.")
        self.assertEqual(view.primary_action_button.text(), "Comenzar a transcribir")
        self.assertFalse(view.advanced_container.isVisible())
        QTest.mouseClick(view.profile_change_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertTrue(workspace.profile_updates)
        QTest.mouseClick(view.primary_action_button, Qt.MouseButton.LeftButton)
        self.qt_app.processEvents()
        self.assertEqual(opened["transcription"], 1)

    def test_unavailable_action_is_disabled_and_explained(self) -> None:
        report = SimpleNamespace(
            readiness="degraded",
            can_transcribe_now=True,
            primary_message="Listo con advertencias.",
            secondary_message="GPU no comprobada.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id=None,
            selected_device="cpu",
            compute_type="int8",
            ffmpeg_status=SimpleNamespace(value="ready"),
            ffprobe_status=SimpleNamespace(value="ready"),
            runtime_status=SimpleNamespace(value="ready"),
            model_status=SimpleNamespace(value="ready"),
            gpu_status=SimpleNamespace(name="REPORTED_NOT_TESTED"),
            benchmark_status=None,
            benchmark_age_seconds=None,
            technical_summary=None,
            blockers=(),
            structured_suggested_actions=(
                SimpleNamespace(
                    action_id="install_component",
                    action_type="install_component",
                    description="Instalar",
                    available_now=False,
                    blocking=True,
                    target_component="transcription-model.small",
                    target_profile="balanced",
                    reason="source_not_approved",
                ),
            ),
        )
        workspace = FakeLocalWorkspace(report=report, installations=[], matrix={"balanced": report})
        view = LocalComponentsView(workspace)
        self.addCleanup(view.close)

        view.refresh()
        self.assertTrue(self._wait_until(lambda: view._status is not None))
        self.assertIn("source_not_approved", view._action_buttons["install_component"].toolTip())
        self.assertFalse(view._action_buttons["install_component"].isEnabled())


if __name__ == "__main__":
    unittest.main()
