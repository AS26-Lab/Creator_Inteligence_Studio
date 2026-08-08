from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView


class _Workspace:
    def __init__(self) -> None:
        self.ui_state = SimpleNamespace(transcription_profile="balanced", preferred_transcription_device="auto")
        self.tasks = [
            BackgroundTaskRecord(
                task_id="task-1",
                title="Probar GPU",
                status="running",
                action_id="op-1",
                cancellable=True,
                created_at="2026-08-08T00:00:00Z",
                updated_at="2026-08-08T00:00:00Z",
                payload={
                    "kind": "component_action",
                    "action_type": "run_gpu_benchmark",
                    "component_id": None,
                },
            )
        ]
        self.cancel_requests: list[str] = []

    def background_tasks(self):
        return list(self.tasks)

    def request_local_component_action_cancellation(self, task_id: str):
        self.cancel_requests.append(task_id)
        self.tasks[0] = replace(
            self.tasks[0],
            status="cancel_requested",
            message="Estamos esperando a que la operacion llegue a un punto seguro para cancelarse.",
            cancel_requested_at="2026-08-08T00:00:01Z",
            updated_at="2026-08-08T00:00:01Z",
        )
        return self.tasks[0]

    def interrupt_background_task(self, task_id: str, message: str | None = None):
        self.tasks[0] = replace(self.tasks[0], status="interrupted", message=message, updated_at="2026-08-08T00:00:01Z")
        return self.tasks[0]

    def complete_background_task(self, task_id: str, message: str | None = None):
        return self.tasks[0]

    def fail_background_task(self, task_id: str, error: str):
        return self.tasks[0]


class ComponentOperationGuiTests(unittest.TestCase):
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

    def test_task_center_shows_canceling_and_requests_cooperative_cancel(self) -> None:
        workspace = _Workspace()
        view = TaskCenterView(workspace)
        self.addCleanup(view.close)

        view.refresh()
        self.assertEqual(view.table.item(0, 3).text(), "Running")
        view.table.selectRow(0)
        self.assertTrue(view.cancel_button.isEnabled())
        QTest.mouseClick(view.cancel_button, Qt.MouseButton.LeftButton)
        self.assertEqual(workspace.cancel_requests, ["task-1"])
        self.assertEqual(view.table.item(0, 3).text(), "Cancelando...")


if __name__ == "__main__":
    unittest.main()
