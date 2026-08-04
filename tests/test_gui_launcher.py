from __future__ import annotations

import io
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.presentation.desktop import app as desktop_app
from creator_intelligence_studio.presentation.desktop import main_window as main_window_module
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from tests.test_ai_runtime_gui import DesktopWorkspaceFacade, _patch_main_window_views
from tests.ai_runtime_test_support import build_runtime_fixture


class GUILauncherTests(unittest.TestCase):
    def test_run_gui_batch_clears_test_variables(self) -> None:
        content = Path("scripts/run_gui.bat").read_text(encoding="utf-8")
        self.assertIn('set "QT_QPA_PLATFORM="', content)
        self.assertIn('set "CIS_GUI_AUTO_EXIT_MS="', content)
        self.assertIn('set "CIS_GUI_TEST_MODE="', content)
        self.assertIn('set "CIS_RUN_GUI_TESTS="', content)

    def test_launch_gui_ignores_inherited_offscreen_and_auto_exit_without_test_mode(self) -> None:
        created: dict[str, object] = {}

        class FakeApp:
            def __init__(self, argv):
                created["argv"] = list(argv)
                created["app"] = self
                self.exec_calls = 0
                self.quit_calls = 0
                self.application_name = None

            def setApplicationName(self, name):
                self.application_name = name

            def platformName(self):
                return "windows"

            def exec(self):
                self.exec_calls += 1
                return 0

            def quit(self):
                self.quit_calls += 1

        class FakeWindow:
            def __init__(self, workspace):
                created["workspace"] = workspace
                self.show_calls = 0
                self.raise_calls = 0
                self.activate_calls = 0

            def show(self):
                self.show_calls += 1

            def raise_(self):
                self.raise_calls += 1

            def activateWindow(self):
                self.activate_calls += 1

        context = SimpleNamespace(
            settings=SimpleNamespace(application_name="Creator Intelligence Studio"),
            service=MagicMock(),
            media_service=MagicMock(),
            audio_service=MagicMock(),
            transcription_service=MagicMock(),
            acoustic_service=MagicMock(),
            visual_service=MagicMock(),
            multimodal_service=None,
            clip_service=None,
            ai_runtime_service=None,
            render_service=None,
            subtitle_service=None,
            analytics_service=None,
            analytics_lab_service=None,
            experiment_service=None,
            recommendation_service=None,
            planning_service=None,
            brief_service=None,
            production_service=None,
            creator_memory_service=None,
            creator_language_service=None,
            creative_packaging_service=None,
            youtube_service=None,
            instagram_service=None,
            tiktok_service=None,
            personalization_service=None,
            model_service=None,
            evaluation_service=None,
            diagnostic=SimpleNamespace(),
            paths=SimpleNamespace(),
        )
        stderr = io.StringIO()
        with patch.dict(
            os.environ,
            {
                "QT_QPA_PLATFORM": "offscreen",
                "CIS_GUI_AUTO_EXIT_MS": "1000",
                "CIS_GUI_TEST_MODE": "",
                "CIS_RUN_GUI_TESTS": "",
            },
            clear=False,
        ), patch.object(desktop_app, "QApplication", FakeApp), patch.object(desktop_app, "WorkspaceViewModel", return_value=SimpleNamespace(ui_state=SimpleNamespace(last_page="home"))), patch.object(desktop_app, "MainWindow", FakeWindow), patch.object(desktop_app, "apply_theme"), patch.object(desktop_app.QTimer, "singleShot") as timer_mock:
            code = desktop_app.launch_gui(context, stderr=stderr, argv=["creator_intelligence_studio", "--gui"])
            self.assertEqual(code, 0)
            self.assertIsNone(os.environ.get("QT_QPA_PLATFORM"))
            self.assertIsNone(os.environ.get("CIS_GUI_AUTO_EXIT_MS"))
            self.assertIn("se ignoraron", stderr.getvalue().lower())
            self.assertFalse(timer_mock.called)
            app = created["app"]
            self.assertEqual(app.exec_calls, 1)
            self.assertEqual(app.quit_calls, 0)

    def test_launch_gui_allows_explicit_test_mode_and_auto_exit(self) -> None:
        created: dict[str, object] = {}

        class FakeApp:
            def __init__(self, argv):
                created["app"] = self
                self.exec_calls = 0
                self.quit_calls = 0

            def setApplicationName(self, _name):
                pass

            def platformName(self):
                return "offscreen"

            def exec(self):
                self.exec_calls += 1
                return 0

            def quit(self):
                self.quit_calls += 1

        class FakeWindow:
            def __init__(self, workspace):
                created["workspace"] = workspace

            def show(self):
                pass

            def raise_(self):
                pass

            def activateWindow(self):
                pass

        context = SimpleNamespace(
            settings=SimpleNamespace(application_name="Creator Intelligence Studio"),
            service=MagicMock(),
            media_service=MagicMock(),
            audio_service=MagicMock(),
            transcription_service=MagicMock(),
            acoustic_service=MagicMock(),
            visual_service=MagicMock(),
            multimodal_service=None,
            clip_service=None,
            ai_runtime_service=None,
            render_service=None,
            subtitle_service=None,
            analytics_service=None,
            analytics_lab_service=None,
            experiment_service=None,
            recommendation_service=None,
            planning_service=None,
            brief_service=None,
            production_service=None,
            creator_memory_service=None,
            creator_language_service=None,
            creative_packaging_service=None,
            youtube_service=None,
            instagram_service=None,
            tiktok_service=None,
            personalization_service=None,
            model_service=None,
            evaluation_service=None,
            diagnostic=SimpleNamespace(),
            paths=SimpleNamespace(),
        )
        with patch.dict(
            os.environ,
            {
                "QT_QPA_PLATFORM": "offscreen",
                "CIS_GUI_AUTO_EXIT_MS": "1000",
                "CIS_GUI_TEST_MODE": "1",
                "CIS_RUN_GUI_TESTS": "1",
            },
            clear=False,
        ), patch.object(desktop_app, "QApplication", FakeApp), patch.object(desktop_app, "WorkspaceViewModel", return_value=SimpleNamespace(ui_state=SimpleNamespace(last_page="home"))), patch.object(desktop_app, "MainWindow", FakeWindow), patch.object(desktop_app, "apply_theme"), patch.object(desktop_app.QTimer, "singleShot") as timer_mock:
            code = desktop_app.launch_gui(context, stderr=io.StringIO(), argv=["creator_intelligence_studio", "--gui"])
            self.assertEqual(code, 0)
            self.assertEqual(os.environ.get("QT_QPA_PLATFORM"), "offscreen")
            self.assertEqual(os.environ.get("CIS_GUI_AUTO_EXIT_MS"), "1000")
            self.assertTrue(timer_mock.called)
            self.assertEqual(timer_mock.call_args.args[0], 1000)
            self.assertEqual(created["app"].exec_calls, 1)
            self.assertEqual(created["app"].quit_calls, 0)

    def test_launch_gui_reports_main_window_creation_failure(self) -> None:
        context = SimpleNamespace(
            settings=SimpleNamespace(application_name="Creator Intelligence Studio"),
            service=MagicMock(),
            media_service=MagicMock(),
            audio_service=MagicMock(),
            transcription_service=MagicMock(),
            acoustic_service=MagicMock(),
            visual_service=MagicMock(),
            multimodal_service=None,
            clip_service=None,
            ai_runtime_service=None,
            render_service=None,
            subtitle_service=None,
            analytics_service=None,
            analytics_lab_service=None,
            experiment_service=None,
            recommendation_service=None,
            planning_service=None,
            brief_service=None,
            production_service=None,
            creator_memory_service=None,
            creator_language_service=None,
            creative_packaging_service=None,
            youtube_service=None,
            instagram_service=None,
            tiktok_service=None,
            personalization_service=None,
            model_service=None,
            evaluation_service=None,
            diagnostic=SimpleNamespace(),
            paths=SimpleNamespace(),
        )

        class FakeApp:
            def __init__(self, argv):
                pass

            def setApplicationName(self, _name):
                pass

            def platformName(self):
                return "windows"

            def exec(self):
                return 0

        with patch.dict(os.environ, {"CIS_GUI_TEST_MODE": ""}, clear=False), patch.object(desktop_app, "QApplication", FakeApp), patch.object(desktop_app, "WorkspaceViewModel", return_value=SimpleNamespace(ui_state=SimpleNamespace(last_page="home"))), patch.object(desktop_app, "MainWindow", side_effect=RuntimeError("boom")), patch.object(desktop_app, "apply_theme"), patch.object(desktop_app.QTimer, "singleShot") as timer_mock:
            stderr = io.StringIO()
            code = desktop_app.launch_gui(context, stderr=stderr, argv=["creator_intelligence_studio", "--gui"])

        self.assertEqual(code, 1)
        self.assertIn("Error inesperado durante el arranque grafico.", stderr.getvalue())
        self.assertIn("boom", stderr.getvalue())
        self.assertFalse(timer_mock.called)


class MainWindowGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_out_of_screen_geometry_recenters_to_primary_monitor(self) -> None:
        fixture = build_runtime_fixture()
        self.addCleanup(fixture.cleanup)
        workspace = DesktopWorkspaceFacade(fixture.service)
        workspace.ui_state_store = SimpleNamespace(
            encode_blob=lambda data: "bogus-geometry",
            decode_blob=lambda data: b"bogus-geometry",
            update=lambda state, **changes: SimpleNamespace(**{**state.__dict__, **changes}),
        )
        workspace.ui_state = SimpleNamespace(last_page="home", window_geometry="bogus-geometry", window_state=None, tasks=())

        class FakeScreen:
            def __init__(self, rect):
                self._rect = rect

            def availableGeometry(self):
                return self._rect

        fake_rect = QRect(0, 0, 1920, 1080)
        fake_screen = FakeScreen(fake_rect)
        stack, inspector_patch = _patch_main_window_views()
        with stack, inspector_patch, patch.object(main_window_module.QGuiApplication, "screens", return_value=[fake_screen]), patch.object(main_window_module.QGuiApplication, "primaryScreen", return_value=fake_screen):
            window = MainWindow(workspace)
            self.addCleanup(window.close)
            self.assertTrue(window.geometry().intersects(fake_rect))
            self.assertGreater(window.width(), 0)
            self.assertGreater(window.height(), 0)

    def test_main_window_defers_startup_recovery_until_post_show(self) -> None:
        fixture = build_runtime_fixture()
        self.addCleanup(fixture.cleanup)
        workspace = DesktopWorkspaceFacade(fixture.service)
        workspace.ui_state_store = SimpleNamespace(
            encode_blob=lambda data: data,
            decode_blob=lambda data: data,
            update=lambda state, **changes: SimpleNamespace(**{**state.__dict__, **changes}),
        )
        workspace.ui_state = SimpleNamespace(last_page="home", window_geometry=None, window_state=None, tasks=())
        calls: list[str] = []
        workspace.recover_ai_runtime_state = lambda: calls.append("recover")
        workspace.refresh = lambda: calls.append("refresh")

        stack, inspector_patch = _patch_main_window_views()
        with stack, inspector_patch:
            window = MainWindow(workspace)
            self.addCleanup(window.close)
            self.assertEqual(calls, [])
            window._run_post_show_bootstrap()

        self.assertEqual(calls, ["recover", "refresh"])


if __name__ == "__main__":
    unittest.main()
