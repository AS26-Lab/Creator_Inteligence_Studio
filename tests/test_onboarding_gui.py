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
from creator_intelligence_studio.presentation.desktop.views.onboarding_view import OnboardingView


def _installation(component_id: str, status: ComponentInstallationStatus) -> ComponentInstallation:
    return ComponentInstallation(
        component_id=component_id,
        installation_status=status,
        installed_version="1.0",
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


class FakeWorkspace:
    def __init__(self, *, report) -> None:
        self.ui_state = SimpleNamespace(
            transcription_profile="balanced",
            preferred_transcription_device="auto",
            local_components_show_advanced_details=False,
        )
        self._report = report
        self.onboarding_updates: list[dict[str, object]] = []

    def transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return self._report

    def component_manager_status(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(installations=(
            _installation("ffmpeg", ComponentInstallationStatus.READY),
            _installation("ffprobe", ComponentInstallationStatus.READY),
        ))

    def transcription_execution_plan(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(selected_profile_id=self._report.selected_profile.profile_id)

    def transcription_capability_matrix(self, *, preferred_device: str = "auto"):
        return {"balanced": self._report}

    def background_tasks(self):
        return []

    def set_onboarding_state(self, **changes):
        self.onboarding_updates.append(dict(changes))


class OnboardingGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        qt_app = QApplication.instance()
        if qt_app is None:
            return
        for widget in list(qt_app.topLevelWidgets()):
            close = getattr(widget, "close", None)
            if callable(close):
                close()
        qt_app.processEvents()

    def test_onboarding_shell_updates_state_on_skip_and_complete(self) -> None:
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
            structured_suggested_actions=(),
        )
        workspace = FakeWorkspace(report=report)
        opened = {"components": 0, "transcription": 0}
        view = OnboardingView(
            workspace,
            open_local_components_callback=lambda: opened.__setitem__("components", opened["components"] + 1),
            open_transcription_callback=lambda: opened.__setitem__("transcription", opened["transcription"] + 1),
        )
        self.addCleanup(view.close)

        self.assertEqual(view.page_stack.count(), 5)
        self.assertEqual(view.start_button.text(), "Comenzar")
        self.assertIn("Recomendamos el perfil", view._page_messages[2].text())

        QTest.mouseClick(view.skip_button, Qt.MouseButton.LeftButton)
        self.assertTrue(workspace.onboarding_updates)
        self.assertEqual(workspace.onboarding_updates[-1]["skipped"], True)
        self.assertEqual(opened["components"], 1)

        view.refresh()
        view.page_stack.setCurrentIndex(view.page_stack.count() - 1)
        view._sync_buttons()
        QTest.mouseClick(view.complete_button, Qt.MouseButton.LeftButton)
        self.assertEqual(opened["transcription"], 1)

    def test_limited_mode_shows_alternative_action(self) -> None:
        report = SimpleNamespace(
            readiness="missing_components",
            can_transcribe_now=False,
            primary_message="Faltan componentes.",
            secondary_message="Aun puedes revisar la configuracion.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id=None,
            selected_device="cpu",
            compute_type=None,
            ffmpeg_status=SimpleNamespace(value="missing"),
            ffprobe_status=SimpleNamespace(value="missing"),
            runtime_status=SimpleNamespace(value="missing"),
            model_status=SimpleNamespace(value="missing"),
            gpu_status=SimpleNamespace(name="NOT_DETECTED"),
            benchmark_status=None,
            benchmark_age_seconds=None,
            technical_summary=None,
            blockers=("missing",),
            structured_suggested_actions=(),
        )
        workspace = FakeWorkspace(report=report)
        opened = {"components": 0, "transcription": 0}
        view = OnboardingView(
            workspace,
            open_local_components_callback=lambda: opened.__setitem__("components", opened["components"] + 1),
            open_transcription_callback=lambda: opened.__setitem__("transcription", opened["transcription"] + 1),
        )
        self.addCleanup(view.close)

        self.assertEqual(view.start_button.text(), "Continuar en modo limitado")
        QTest.mouseClick(view.start_button, Qt.MouseButton.LeftButton)
        self.assertEqual(opened["components"], 1)
        self.assertEqual(workspace.onboarding_updates[-1]["last_status"], "limited")


if __name__ == "__main__":
    unittest.main()
