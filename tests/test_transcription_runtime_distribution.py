from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.application.services.transcription_capability_resolver import TranscriptionCapabilityResolver
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentEvent,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import DiskVolumeSummary, GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelInfo, TranscriptionModelStatus
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


class _RuntimeRepository(ComponentManagerRepository):
    def __init__(self) -> None:
        self._catalog = build_default_component_catalog()
        self._installations: dict[str, ComponentInstallation] = {}
        self._events: list[ComponentEvent] = []

    def get_catalog(self) -> ComponentCatalog:
        return self._catalog

    def list_catalog_entries(self) -> tuple[ComponentCatalogEntry, ...]:
        return self._catalog.entries

    def get_catalog_entry(self, component_id: str) -> ComponentCatalogEntry | None:
        return self._catalog.get_entry(component_id)

    def upsert_catalog_entry(self, entry: ComponentCatalogEntry) -> ComponentCatalogEntry:
        raise NotImplementedError

    def list_installations(self) -> tuple[ComponentInstallation, ...]:
        return tuple(self._installations.values())

    def get_installation(self, component_id: str) -> ComponentInstallation | None:
        return self._installations.get(component_id.lower())

    def upsert_installation(self, installation: ComponentInstallation) -> ComponentInstallation:
        self._installations[installation.component_id.lower()] = installation
        return installation

    def list_hardware_profiles(self) -> tuple[HardwareProfile, ...]:
        return ()

    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        return profile

    def latest_hardware_profile(self) -> HardwareProfile | None:
        return None

    def list_transcription_profiles(self) -> tuple:
        return build_default_transcription_profiles()

    def get_transcription_profile(self, profile_id: str):
        normalized = profile_id.strip().lower()
        return next((profile for profile in build_default_transcription_profiles() if profile.profile_id.lower() == normalized), None)

    def upsert_transcription_profile(self, profile):
        raise NotImplementedError

    def list_runtime_checks(self):
        return ()

    def upsert_runtime_check(self, record):
        raise NotImplementedError

    def append_event(self, event: ComponentEvent) -> ComponentEvent:
        self._events.append(event)
        return event

    def list_events(self) -> tuple[ComponentEvent, ...]:
        return tuple(self._events)


class _MissingModelManager:
    def model_component_id(self, model_name: str) -> str:
        return f"transcription-model.{model_name.strip().lower()}"

    def resolve_installed_model(self, model_name: str) -> TranscriptionModelInfo:
        normalized = model_name.strip().lower()
        return TranscriptionModelInfo(
            model_name=normalized,
            profile=normalized,
            path=None,
            installed=False,
            status=TranscriptionModelStatus.NOT_INSTALLED,
            component_id=self.model_component_id(normalized),
        )


def _paths(temp_dir: str) -> ProjectPaths:
    root = Path(temp_dir)
    paths = ProjectPaths(
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
    paths.ensure_runtime_directories()
    return paths


def _hardware_profile() -> HardwareProfile:
    return HardwareProfile(
        generated_at=utc_now(),
        platform="Windows",
        architecture="AMD64",
        cpu_logical_count=8,
        cpu_summary="test",
        ram_total_bytes=8 * 1024 * 1024 * 1024,
        ram_available_bytes=4 * 1024 * 1024 * 1024,
        gpu=GpuSummary(None, None, None, None, False, status=HardwareCapabilityState.NOT_DETECTED),
        driver_summary=None,
        cuda_reported=None,
        ctranslate2_cuda_status=HardwareCapabilityState.NOT_DETECTED,
        disk_volumes=(DiskVolumeSummary(path="C:\\", free_bytes=32 * 1024 * 1024 * 1024, total_bytes=64 * 1024 * 1024 * 1024),),
        detection_source="local",
        status=HardwareCapabilityState.NOT_DETECTED,
        warnings=(),
        errors=(),
    )


class TranscriptionRuntimeDistributionTests(unittest.TestCase):
    def test_component_inventory_marks_import_only_runtime_as_external(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(temp_dir)
            repo = _RuntimeRepository()
            service = ComponentManagerService(paths=paths, repository=repo)

            fake_faster_whisper = SimpleNamespace(__version__="1.2.1")
            fake_ctranslate2 = SimpleNamespace(__version__="4.8.1")
            with patch(
                "creator_intelligence_studio.application.services.component_manager_service.importlib.import_module",
                side_effect=lambda name: fake_faster_whisper if name == "faster_whisper" else fake_ctranslate2 if name == "ctranslate2" else __import__(name),
            ):
                installations = service.inspect_installations()

        runtime = next(item for item in installations if item.component_id == "transcription-runtime.faster-whisper")
        self.assertEqual(runtime.installation_status, ComponentInstallationStatus.EXTERNALLY_DETECTED)
        self.assertFalse(runtime.managed)
        self.assertEqual(runtime.health_status, RuntimeCheckStatus.NOT_CHECKED)

    def test_resolver_reports_missing_runtime_on_clean_machine(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = _paths(temp_dir)
            repo = _RuntimeRepository()
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=paths, model_manager=_MissingModelManager())
            with patch(
                "creator_intelligence_studio.application.services.transcription_capability_resolver.importlib.import_module",
                side_effect=ImportError("missing"),
            ):
                report = resolver.resolve(requested_profile="balanced", preferred_device="auto")

        self.assertEqual(report.runtime_resolution.installation.distribution_state.value, "missing")
        self.assertIn("transcription-runtime.faster-whisper", report.missing_component_ids)
        self.assertFalse(report.can_transcribe_now)


if __name__ == "__main__":
    unittest.main()
