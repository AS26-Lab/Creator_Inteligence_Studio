from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.domain.components.entities import (
    ComponentInstallKind,
    ComponentInstallation,
    ComponentInstallationStatus,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.presentation.desktop.view_models.local_components import LocalComponentsViewModel


def _installation(component_id: str, status: ComponentInstallationStatus, *, version: str | None = "1.0") -> ComponentInstallation:
    return ComponentInstallation(
        component_id=component_id,
        installation_status=status,
        installed_version=version,
        revision="1",
        install_type=ComponentInstallKind.MANAGED,
        location_path=str(Path("C:/managed") / component_id),
        location_reference="managed_root",
        detected_at=None,
        verified_at=None,
        health_status=RuntimeCheckStatus.READY if status == ComponentInstallationStatus.READY else RuntimeCheckStatus.NOT_CHECKED,
        source="test",
        managed=True,
        metadata={},
    )


class FakeWorkspace:
    def __init__(self, *, report, installations, matrix, tasks=None) -> None:
        self.ui_state = SimpleNamespace(
            transcription_profile="balanced",
            preferred_transcription_device="auto",
            local_components_show_advanced_details=False,
        )
        self._report = report
        self._installations = tuple(installations)
        self._matrix = dict(matrix)
        self._tasks = list(tasks or [])
        self.profile_updates: list[tuple[str | None, str | None]] = []
        self.advanced_details_updates: list[bool] = []
        self.benchmark_calls: list[dict[str, object]] = []

    def transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return self._report

    def component_manager_status(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(installations=self._installations)

    def transcription_execution_plan(self, *, profile: str = "balanced", preferred_device: str = "auto"):
        return SimpleNamespace(selected_profile_id=self._report.selected_profile.profile_id if self._report and self._report.selected_profile else profile)

    def transcription_capability_matrix(self, *, preferred_device: str = "auto"):
        return dict(self._matrix)

    def background_tasks(self):
        return list(self._tasks)

    def set_transcription_preferences(self, *, device: str | None = None, profile: str | None = None):
        self.profile_updates.append((device, profile))

    def set_local_components_advanced_details_visible(self, visible: bool) -> None:
        self.advanced_details_updates.append(visible)

    def run_transcription_benchmark(self, **kwargs):
        self.benchmark_calls.append(dict(kwargs))
        return SimpleNamespace(to_dict=lambda: kwargs)


class LocalComponentsViewModelTests(unittest.TestCase):
    def test_ready_status_uses_report_and_installations(self) -> None:
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
            benchmark_age_seconds=12.0,
            technical_summary="summary",
            blockers=(),
            structured_suggested_actions=(
                SimpleNamespace(
                    action_id="run_gpu_benchmark",
                    action_type="run_gpu_benchmark",
                    description="Probar GPU",
                    available_now=True,
                    blocking=True,
                    target_component=None,
                    target_profile="balanced",
                    reason="gpu_untested",
                ),
            ),
        )
        installations = [
            _installation("ffmpeg", ComponentInstallationStatus.READY),
            _installation("ffprobe", ComponentInstallationStatus.READY),
            _installation("transcription-runtime.faster-whisper", ComponentInstallationStatus.READY),
            _installation("transcription-model.small", ComponentInstallationStatus.READY),
        ]
        workspace = FakeWorkspace(report=report, installations=installations, matrix={"balanced": report})
        vm = LocalComponentsViewModel(workspace)

        status = vm.refresh_status()

        self.assertTrue(status.can_transcribe_now)
        self.assertEqual(status.recommended_profile_label, "Equilibrado")
        self.assertEqual(status.selected_device_label, "GPU")
        self.assertEqual(status.component_cards[0].state_label, "Listo")
        self.assertEqual(status.component_cards[-1].primary_action_label, "Probar GPU")

    def test_execute_action_updates_preferences_and_benchmark(self) -> None:
        report = SimpleNamespace(
            readiness="ready_with_warnings",
            can_transcribe_now=True,
            primary_message="Listo con advertencias.",
            secondary_message="GPU sin comprobar.",
            requested_profile="balanced",
            requested_device="auto",
            selected_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            recommended_profile=SimpleNamespace(profile_id="balanced", display_name="Equilibrado"),
            selected_model_component_id="transcription-model.small",
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
                    action_id="choose_balanced",
                    action_type="choose_profile",
                    description="Usar este perfil",
                    available_now=True,
                    blocking=False,
                    target_component=None,
                    target_profile="balanced",
                    reason=None,
                ),
                SimpleNamespace(
                    action_id="run_gpu_benchmark",
                    action_type="run_gpu_benchmark",
                    description="Probar GPU",
                    available_now=True,
                    blocking=True,
                    target_component=None,
                    target_profile="balanced",
                    reason="gpu_untested",
                ),
            ),
        )
        installations = [_installation("ffmpeg", ComponentInstallationStatus.READY)]
        workspace = FakeWorkspace(report=report, installations=installations, matrix={"balanced": report})
        vm = LocalComponentsViewModel(workspace)
        vm.refresh_status()

        self.assertTrue(vm.execute_available_action("choose_balanced"))
        self.assertEqual(workspace.profile_updates[-1], (None, "balanced"))
        self.assertTrue(vm.execute_available_action("run_gpu_benchmark"))
        self.assertEqual(workspace.benchmark_calls[-1]["preferred_device"], "gpu")

    def test_download_task_is_presented_without_mutation(self) -> None:
        report = SimpleNamespace(
            readiness="limited_mode",
            can_transcribe_now=False,
            primary_message="Modo limitado.",
            secondary_message="Falta componente.",
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
        tasks = [
            SimpleNamespace(
                task_id="download-1",
                title="Descarga de componente",
                status="downloading",
                payload={
                    "kind": "component_download",
                    "component_id": "transcription-model.small",
                    "source_summary": "Origen local",
                    "progress": {
                        "percentage": 45.0,
                        "downloaded_bytes": 450,
                        "total_bytes": 1000,
                        "speed_bytes_per_second": 100,
                        "eta_seconds": 5.0,
                    },
                },
            )
        ]
        workspace = FakeWorkspace(report=report, installations=[], matrix={}, tasks=tasks)
        vm = LocalComponentsViewModel(workspace)

        status = vm.refresh_status()

        self.assertEqual(len(status.download_tasks), 1)
        self.assertEqual(status.download_tasks[0].progress_label, "45.0%")
        self.assertEqual(status.download_tasks[0].eta_label, "5.0 s")


if __name__ == "__main__":
    unittest.main()
