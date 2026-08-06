from __future__ import annotations

import io
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from creator_intelligence_studio.application.services.component_manager_service import (
    ComponentManagerStatus,
    TranscriptionCapabilityPresentation,
    TranscriptionCapabilityReport,
)
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog
from creator_intelligence_studio.domain.components.entities import (
    ComponentEvent,
    ComponentEventType,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.hardware.entities import DiskVolumeSummary, GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.components.catalog import build_default_transcription_profiles
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch


class FakeComponentManagerService:
    def __init__(self) -> None:
        catalog = build_default_component_catalog()
        hardware_profile = HardwareProfile(
            generated_at=datetime.now(timezone.utc),
            platform="Windows",
            architecture="AMD64",
            cpu_logical_count=8,
            cpu_summary="Windows AMD64; logical=8",
            ram_total_bytes=16 * 1024 * 1024 * 1024,
            ram_available_bytes=8 * 1024 * 1024 * 1024,
            gpu=GpuSummary(None, None, None, None, False, status=HardwareCapabilityState.NOT_DETECTED),
            driver_summary=None,
            cuda_reported=None,
            ctranslate2_cuda_status=HardwareCapabilityState.NOT_DETECTED,
            disk_volumes=(DiskVolumeSummary(path="C:\\tmp", free_bytes=32 * 1024 * 1024 * 1024, total_bytes=64 * 1024 * 1024 * 1024),),
            detection_source="local",
            status=HardwareCapabilityState.NOT_DETECTED,
            warnings=(),
            errors=(),
        )
        runtime_check = RuntimeCheckRecord(
            component_id="transcription-runtime.ctranslate2",
            status=RuntimeCheckStatus.READY,
            runtime_importable=True,
            runtime_version="4.8.1",
            device_count=0,
            supported_compute_types=("int8",),
            notes=None,
            warning_message=None,
            error_code=None,
            error_message=None,
            metadata={},
        )
        capability = TranscriptionCapabilityReport(
            readiness="ready",
            requested_profile="balanced",
            selected_profile=build_default_transcription_profiles()[1],
            recommended_profile=build_default_transcription_profiles()[1],
            selected_model_component=catalog.get_entry("transcription-model.small"),
            selected_device="auto",
            compute_type="int8",
            ffmpeg_status=ComponentInstallationStatus.READY,
            ffprobe_status=ComponentInstallationStatus.READY,
            runtime_status=RuntimeCheckStatus.READY,
            model_status=ComponentInstallationStatus.READY,
            gpu_status=HardwareCapabilityState.NOT_DETECTED,
            evidence_references=("catalog_version=1",),
        )
        presentation = TranscriptionCapabilityPresentation(title="Listo", message="Tu computadora esta lista para transcribir con el perfil Equilibrado.")
        self._status = ComponentManagerStatus(
            catalog=catalog,
            installations=(
                ComponentInstallation(
                    component_id="ffmpeg",
                    installation_status=ComponentInstallationStatus.READY,
                    installed_version="7.0",
                    revision=None,
                    install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
                    location_path="C:\\ffmpeg\\bin\\ffmpeg.exe",
                    location_reference="path",
                    detected_at=None,
                    verified_at=None,
                    health_status=RuntimeCheckStatus.READY,
                    source="test",
                    managed=False,
                ),
            ),
            hardware=__import__("creator_intelligence_studio.application.services.hardware_capability_service", fromlist=["HardwareCapabilityReport"]).HardwareCapabilityReport(
                hardware_profile=hardware_profile,
                runtime_check=runtime_check,
            ),
            capability=capability,
            presentation=presentation,
            events=(
                ComponentEvent(
                    event_type=ComponentEventType.CATALOG_LOADED,
                    message_safe="Catalogo cargado.",
                ),
            ),
        )

    def status(self, *, profile: str = "balanced", preferred_device: str = "auto") -> ComponentManagerStatus:
        return self._status

    def resolve_transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto") -> TranscriptionCapabilityReport:
        return self._status.capability

    def describe_transcription_capability(self, *, profile: str = "balanced", preferred_device: str = "auto") -> TranscriptionCapabilityPresentation:
        return self._status.presentation


class ComponentManagerCliTests(unittest.TestCase):
    def test_components_status_and_capability_are_read_only(self) -> None:
        parser = build_parser()
        service = FakeComponentManagerService()
        diagnostic = SimpleNamespace(state=SimpleNamespace(ready_for_basic_mode=True), to_json=lambda: "{}")

        args = parser.parse_args(["components", "status", "--json"])
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = dispatch(
            args,
            service=None,
            media_service=None,
            audio_service=None,
            transcription_service=None,
            acoustic_service=None,
            visual_service=None,
            multimodal_service=None,
            clip_service=None,
            diagnostic=diagnostic,
            stdout=stdout,
            stderr=stderr,
            component_manager_service=service,
        )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("catalog", payload)
        self.assertIn("capability", payload)
        self.assertEqual(stderr.getvalue(), "")

        args = parser.parse_args(["components", "capability", "--json"])
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = dispatch(
            args,
            service=None,
            media_service=None,
            audio_service=None,
            transcription_service=None,
            acoustic_service=None,
            visual_service=None,
            multimodal_service=None,
            clip_service=None,
            diagnostic=diagnostic,
            stdout=stdout,
            stderr=stderr,
            component_manager_service=service,
        )
        self.assertEqual(code, 0)
        capability = json.loads(stdout.getvalue())
        self.assertIn("capability", capability)
        self.assertIn("presentation", capability)
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
