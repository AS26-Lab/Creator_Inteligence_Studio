from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.domain.components.entities import (
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.presentation.desktop.ui_state import BackgroundTaskRecord
from creator_intelligence_studio.presentation.desktop.view_models.local_component_actions import (
    ComponentActionRequest,
    LocalComponentActionService,
)
from creator_intelligence_studio.presentation.desktop.view_models.local_components import LocalComponentsViewModel


def _installation(component_id: str, status: ComponentInstallationStatus, *, managed: bool = True) -> ComponentInstallation:
    return ComponentInstallation(
        component_id=component_id,
        installation_status=status,
        installed_version="1.0",
        revision="1",
        install_type=ComponentInstallKind.MANAGED if managed else ComponentInstallKind.EXTERNALLY_DETECTED,
        location_path=str(Path("C:/managed") / component_id) if managed else str(Path("C:/external") / component_id),
        location_reference="managed_root" if managed else "external",
        detected_at=None,
        verified_at=None,
        health_status=RuntimeCheckStatus.READY if status == ComponentInstallationStatus.READY else RuntimeCheckStatus.NOT_CHECKED,
        source="test",
        managed=managed,
        metadata={},
    )


class FakeRepository:
    def __init__(self) -> None:
        self.profile = SimpleNamespace(model_revision="rev-1")

    def get_transcription_profile(self, profile_id: str):
        return self.profile


class FakeComponentManagerService:
    def __init__(self) -> None:
        self.repository = FakeRepository()
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def ffmpeg_install_local(self, source_path, *, source_label=None):
        self.calls.append(("ffmpeg_install_local", (str(source_path),), {"source_label": source_label}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready", "source_path": str(source_path), "source_label": source_label})

    def transcription_runtime_install_local(self, component_id, source_path, *, revision="1", artifact=None):
        self.calls.append(("runtime_install_local", (component_id, str(source_path)), {"revision": revision}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready", "component_id": component_id, "revision": revision})

    def transcription_model_install_local(self, component_id, source_path, *, revision, artifact=None):
        self.calls.append(("model_install_local", (component_id, str(source_path)), {"revision": revision}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready", "component_id": component_id, "revision": revision})

    def ffmpeg_verify_local(self):
        self.calls.append(("ffmpeg_verify_local", (), {}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})

    def transcription_runtime_verify_local(self, component_id):
        self.calls.append(("runtime_verify_local", (component_id,), {}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})

    def transcription_model_verify_local(self, component_id):
        self.calls.append(("model_verify_local", (component_id,), {}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})

    def ffmpeg_remove(self):
        self.calls.append(("ffmpeg_remove", (), {}))
        return SimpleNamespace(state="removed", to_dict=lambda: {"state": "removed"})

    def transcription_runtime_remove_local(self, component_id):
        self.calls.append(("runtime_remove_local", (component_id,), {}))
        return SimpleNamespace(state="removed", to_dict=lambda: {"state": "removed"})

    def transcription_model_remove_local(self, component_id):
        self.calls.append(("model_remove_local", (component_id,), {}))
        return SimpleNamespace(state="removed", to_dict=lambda: {"state": "removed"})

    def ffmpeg_repair_local(self, source_path=None):
        self.calls.append(("ffmpeg_repair_local", (str(source_path) if source_path else None,), {}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})

    def transcription_runtime_repair_local(self, component_id, source_path=None, *, revision="1", artifact=None):
        self.calls.append(("runtime_repair_local", (component_id, str(source_path) if source_path else None), {"revision": revision}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})

    def transcription_model_repair_local(self, component_id, source_path=None, *, revision, artifact=None):
        self.calls.append(("model_repair_local", (component_id, str(source_path) if source_path else None), {"revision": revision}))
        return SimpleNamespace(state="ready", to_dict=lambda: {"state": "ready"})


class FakeWorkspace:
    def __init__(self, *, report, installations) -> None:
        self.ui_state = SimpleNamespace(
            transcription_profile="balanced",
            preferred_transcription_device="auto",
            local_components_show_advanced_details=False,
        )
        self.component_manager_service = FakeComponentManagerService()
        self._report = report
        self._installations = tuple(installations)
        self.tasks: list[BackgroundTaskRecord] = []
        self.profile_updates: list[tuple[str | None, str | None]] = []
        self.benchmark_calls: list[dict[str, object]] = []

    def transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return self._report

    def component_manager_status(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(installations=self._installations)

    def transcription_execution_plan(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(selected_profile_id=self._report.selected_profile.profile_id)

    def transcription_capability_matrix(self, *, preferred_device: str = "auto"):
        return {"balanced": self._report}

    def background_tasks(self):
        return list(self.tasks)

    def register_background_task(self, **kwargs):
        task = BackgroundTaskRecord(task_id=f"task-{len(self.tasks) + 1}", created_at="2026-08-07T00:00:00Z", updated_at="2026-08-07T00:00:00Z", **kwargs)
        self.tasks.append(task)
        return task

    def update_background_task(self, task_id: str, **changes):
        updated = None
        for index, task in enumerate(self.tasks):
            if task.task_id == task_id:
                updated = replace(task, **changes, updated_at="2026-08-07T00:00:01Z")
                self.tasks[index] = updated
                break
        return updated

    def complete_background_task(self, task_id: str, message: str | None = None):
        return self.update_background_task(task_id, status="completed", progress_percent=100.0, message=message, cancellable=False)

    def fail_background_task(self, task_id: str, error: str):
        return self.update_background_task(task_id, status="failed", error=error, message=error, cancellable=False)

    def interrupt_background_task(self, task_id: str, message: str | None = None):
        return self.update_background_task(task_id, status="interrupted", message=message, cancellable=False)

    def set_transcription_preferences(self, *, device: str | None = None, profile: str | None = None):
        self.profile_updates.append((device, profile))

    def run_transcription_benchmark(self, **kwargs):
        self.benchmark_calls.append(dict(kwargs))
        return SimpleNamespace(to_dict=lambda: dict(kwargs))

    def execute_local_component_action(self, request):
        service = LocalComponentActionService(self)
        return service.execute(request)


class LocalComponentActionsTests(unittest.TestCase):
    def test_install_component_dispatches_task_and_backend(self) -> None:
        report = SimpleNamespace(
            readiness="missing_components",
            can_transcribe_now=False,
            primary_message="Faltan componentes.",
            secondary_message="Revisar configuracion.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado", model_revision="rev-1"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
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
            structured_suggested_actions=(
                SimpleNamespace(
                    action_id="install_ffmpeg",
                    action_type="install_component",
                    display_label="Instalar FFmpeg",
                    available_now=True,
                    blocking=True,
                    target_component="ffmpeg",
                    target_profile=None,
                    reason="missing_component",
                ),
            ),
        )
        workspace = FakeWorkspace(report=report, installations=[])
        vm = LocalComponentsViewModel(workspace)
        vm.refresh_status()

        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "bundle.zip"
            source.write_text("fake", encoding="utf-8")
            request = vm.build_action_request("install_ffmpeg", local_source=str(source), user_confirmation=True, source_context="file")
            self.assertIsNotNone(request)
            result = vm.execute_component_action(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(workspace.component_manager_service.calls[0][0], "ffmpeg_install_local")
        self.assertTrue(workspace.tasks)
        self.assertEqual(workspace.tasks[-1].status, "completed")
        self.assertEqual(workspace.tasks[-1].payload["kind"], "component_action")

    def test_verify_component_requires_available_action(self) -> None:
        report = SimpleNamespace(
            readiness="ready",
            can_transcribe_now=True,
            primary_message="Listo.",
            secondary_message="Todo bien.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado", model_revision="rev-1"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
            selected_device="cpu",
            compute_type=None,
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
                    action_id="verify_ffmpeg",
                    action_type="verify_component",
                    display_label="Comprobar FFmpeg",
                    available_now=True,
                    blocking=False,
                    target_component="ffmpeg",
                    target_profile=None,
                    reason="verification_available",
                ),
            ),
        )
        workspace = FakeWorkspace(report=report, installations=[_installation("ffmpeg", ComponentInstallationStatus.READY)])
        vm = LocalComponentsViewModel(workspace)
        vm.refresh_status()

        request = vm.build_action_request("verify_ffmpeg", user_confirmation=False, source_context="button")
        result = vm.execute_component_action(request)

        self.assertEqual(result.status, "completed")
        self.assertEqual(workspace.component_manager_service.calls[0][0], "ffmpeg_verify_local")

    def test_remove_component_rejects_non_managed_installation(self) -> None:
        report = SimpleNamespace(
            readiness="ready",
            can_transcribe_now=True,
            primary_message="Listo.",
            secondary_message="Todo bien.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado", model_revision="rev-1"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
            selected_device="cpu",
            compute_type=None,
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
                    action_id="remove_ffmpeg",
                    action_type="remove_component",
                    display_label="Eliminar FFmpeg",
                    available_now=True,
                    blocking=True,
                    target_component="ffmpeg",
                    target_profile=None,
                    reason="managed_installation",
                ),
            ),
        )
        workspace = FakeWorkspace(report=report, installations=[_installation("ffmpeg", ComponentInstallationStatus.READY, managed=False)])
        vm = LocalComponentsViewModel(workspace)
        vm.refresh_status()

        request = vm.build_action_request("remove_ffmpeg", user_confirmation=True, source_context="button")
        result = vm.execute_component_action(request)

        self.assertEqual(result.status, "failed")
        self.assertIn("no esta soportada", (result.safe_error or "").lower())


if __name__ == "__main__":
    unittest.main()
