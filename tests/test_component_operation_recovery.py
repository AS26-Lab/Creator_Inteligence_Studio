from __future__ import annotations

import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.component_operation_recovery_service import ComponentOperationRecoveryService
from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.presentation.desktop.view_models.local_component_actions import (
    ComponentActionRequest,
    LocalComponentActionService,
)
from creator_intelligence_studio.shared.paths import ProjectPaths


def _paths(root: Path) -> ProjectPaths:
    return ProjectPaths(
        project_root=root,
        config_directory=root / "config",
        data_directory=root / "data",
        components_directory=root / "data" / "components",
        downloads_directory=root / "data" / "downloads",
        database_path=root / "data" / "app.db",
        logs_directory=root / "logs",
        models_directory=root / "models",
        artifacts_directory=root / "artifacts",
    )


class _DownloadService:
    def __init__(self) -> None:
        self.calls = 0

    def recover_interrupted_downloads(self):
        self.calls += 1
        return (SimpleNamespace(download_id="download-1"),)


class _RecoveryWorkspace:
    def __init__(self, *, paths: ProjectPaths, tasks: tuple[BackgroundTaskRecord, ...]) -> None:
        self.paths = paths
        self.ui_state = SimpleNamespace(tasks=tasks, transcription_profile="balanced", preferred_transcription_device="auto")
        self.component_manager_service = SimpleNamespace(paths=paths)
        self.download_service = _DownloadService()
        self._tasks = list(tasks)
        self.interrupt_calls: list[tuple[str, str | None]] = []
        self.update_calls: list[tuple[str, dict[str, object]]] = []

    def background_tasks(self):
        return list(self._tasks)

    def interrupt_background_task(self, task_id: str, message: str | None = None):
        self.interrupt_calls.append((task_id, message))
        updated = None
        for index, task in enumerate(self._tasks):
            if task.task_id != task_id:
                continue
            updated = replace(
                task,
                status="interrupted",
                message=message,
                cancellable=False,
                interrupted_at="2026-08-08T00:00:00Z",
                last_heartbeat_at="2026-08-08T00:00:00Z",
            )
            self._tasks[index] = updated
            break
        return updated

    def update_background_task(self, task_id: str, **changes):
        self.update_calls.append((task_id, dict(changes)))
        updated = None
        for index, task in enumerate(self._tasks):
            if task.task_id != task_id:
                continue
            updated = replace(task, **changes, updated_at="2026-08-08T00:00:01Z")
            self._tasks[index] = updated
            break
        return updated


class _BenchmarkWorkspace:
    def __init__(self) -> None:
        self.ui_state = SimpleNamespace(
            transcription_profile="balanced",
            preferred_transcription_device="auto",
            local_components_show_advanced_details=False,
        )
        self.component_manager_service = SimpleNamespace(repository=SimpleNamespace())
        self._tasks: list[BackgroundTaskRecord] = []
        self.benchmark_started = threading.Event()
        self.benchmark_cancelled = threading.Event()
        self._report = SimpleNamespace(
            readiness="ready",
            can_transcribe_now=True,
            primary_message="Listo.",
            secondary_message="",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado", model_revision="1"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
            selected_device="gpu",
            compute_type="int8",
            ffmpeg_status=SimpleNamespace(value="ready"),
            ffprobe_status=SimpleNamespace(value="ready"),
            runtime_status=SimpleNamespace(value="ready"),
            model_status=SimpleNamespace(value="ready"),
            gpu_status=SimpleNamespace(name="DETECTED"),
            benchmark_status=None,
            benchmark_age_seconds=None,
            technical_summary=None,
            blockers=(),
            structured_suggested_actions=(
                SimpleNamespace(
                    action_id="run_gpu_benchmark",
                    action_type="run_gpu_benchmark",
                    display_label="Probar GPU",
                    available_now=True,
                    blocking=False,
                    target_component=None,
                    target_profile="balanced",
                    reason=None,
                ),
            ),
        )
        self.component_manager_calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.action_service = LocalComponentActionService(self)

    def transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return self._report

    def component_manager_status(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(installations=())

    def transcription_execution_plan(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(selected_profile_id="balanced")

    def transcription_capability_matrix(self, *, preferred_device: str = "auto"):
        return {"balanced": self._report}

    def background_tasks(self):
        return list(self._tasks)

    def register_background_task(self, **kwargs):
        task = BackgroundTaskRecord(task_id=f"task-{len(self._tasks) + 1}", created_at="2026-08-08T00:00:00Z", updated_at="2026-08-08T00:00:00Z", **kwargs)
        self._tasks.append(task)
        return task

    def update_background_task(self, task_id: str, **changes):
        updated = None
        for index, task in enumerate(self._tasks):
            if task.task_id != task_id:
                continue
            updated = replace(task, **changes, updated_at="2026-08-08T00:00:01Z")
            self._tasks[index] = updated
            break
        return updated

    def complete_background_task(self, task_id: str, message: str | None = None):
        return self.update_background_task(task_id, status="completed", progress_percent=100.0, message=message, cancellable=False)

    def fail_background_task(self, task_id: str, error: str):
        return self.update_background_task(task_id, status="failed", error=error, message=error, cancellable=False)

    def interrupt_background_task(self, task_id: str, message: str | None = None):
        return self.update_background_task(task_id, status="interrupted", message=message, cancellable=False)

    def run_transcription_benchmark(self, **kwargs):
        self.component_manager_calls.append(("run_transcription_benchmark", (), dict(kwargs)))
        token = kwargs.get("cancellation_token")
        self.benchmark_started.set()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            task = self._tasks[0] if self._tasks else None
            if (token is not None and callable(getattr(token, "cancelled", None)) and token.cancelled()) or (
                task is not None and str(task.status).lower() == "cancel_requested"
            ):
                self.benchmark_cancelled.set()
                return SimpleNamespace(status="cancelled", to_dict=lambda: {"status": "cancelled"})
            time.sleep(0.01)
        return SimpleNamespace(status="completed", to_dict=lambda: {"status": "completed"})

    def execute_local_component_action(self, request):
        return self.action_service.execute(request)

    def request_local_component_action_cancellation(self, task_id: str):
        return self.action_service.request_cancellation(task_id)


class ComponentOperationRecoveryTests(unittest.TestCase):
    def test_startup_recovery_marks_active_component_tasks_interrupted_and_cleans_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            paths.ensure_runtime_directories()
            ffmpeg_staging = paths.components_directory / "ffmpeg" / ".staging-old"
            runtime_staging = paths.components_directory / "transcription-runtime" / "transcription-runtime.faster-whisper" / ".staging-old"
            model_staging = paths.models_directory / "transcription" / "faster-whisper" / "transcription-model.small" / ".staging-old"
            for staging in (ffmpeg_staging, runtime_staging, model_staging):
                staging.mkdir(parents=True, exist_ok=True)
                (staging / "marker.txt").write_text("staging", encoding="utf-8")

            task = BackgroundTaskRecord(
                task_id="task-1",
                title="Instalar componente",
                status="running",
                action_id="op-1",
                cancellable=True,
                created_at="2026-08-08T00:00:00Z",
                updated_at="2026-08-08T00:00:00Z",
                payload={"kind": "component_action", "action_type": "install_component", "component_id": "transcription-model.small"},
            )
            workspace = _RecoveryWorkspace(paths=paths, tasks=(task,))
            report = ComponentOperationRecoveryService(workspace).recover_startup_state()

            self.assertEqual(workspace.download_service.calls, 1)
            self.assertEqual(report.recovered_download_tasks, ("download-1",))
            self.assertEqual(len(report.interrupted_tasks), 1)
            self.assertEqual(report.interrupted_tasks[0].lifecycle_state, "interrupted")
            self.assertIn("interrumpio", (report.interrupted_tasks[0].safe_error_message or "").lower())
            self.assertFalse(ffmpeg_staging.exists())
            self.assertFalse(runtime_staging.exists())
            self.assertFalse(model_staging.exists())
            self.assertEqual(workspace.background_tasks()[0].status, "interrupted")

    def test_gpu_benchmark_cancellation_requests_and_completes_as_cancelled(self) -> None:
        workspace = _BenchmarkWorkspace()
        service = LocalComponentActionService(workspace)
        request = ComponentActionRequest(
            action_type="run_gpu_benchmark",
            component_id=None,
            profile="balanced",
            user_confirmation=True,
            source_context="button",
        )

        result_holder: dict[str, object] = {}

        def _run() -> None:
            result_holder["result"] = service.execute(request)

        worker = threading.Thread(target=_run)
        worker.start()
        self.assertTrue(workspace.benchmark_started.wait(timeout=2.0))
        self.assertTrue(workspace.background_tasks())
        task_id = workspace.background_tasks()[0].task_id
        workspace.request_local_component_action_cancellation(task_id)
        worker.join(timeout=5.0)
        self.assertFalse(worker.is_alive())

        result = result_holder["result"]
        self.assertEqual(getattr(result, "status", None), "cancelled")
        self.assertEqual(workspace.background_tasks()[0].status, "cancelled")
        self.assertTrue(workspace.benchmark_cancelled.is_set())
        self.assertIsNotNone(workspace.background_tasks()[0].cancel_requested_at)
        self.assertIsNotNone(workspace.background_tasks()[0].cancelled_at)


if __name__ == "__main__":
    unittest.main()
