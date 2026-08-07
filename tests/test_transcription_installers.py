from __future__ import annotations

import hashlib
import sys
import tempfile
import types
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from creator_intelligence_studio.application.services.transcription_installation_service import (
    ManagedTranscriptionModelInstaller,
    ManagedTranscriptionRuntimeInstaller,
)
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.downloads import VerifiedComponentArtifact
from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentEvent,
    ComponentInstallation,
    ComponentInstallKind,
    ComponentInstallationStatus,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import DiskVolumeSummary, GpuSummary, HardwareCapabilityState, HardwareProfile
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelStatus
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


class InMemoryComponentRepository(ComponentManagerRepository):
    def __init__(self) -> None:
        self._catalog = build_default_component_catalog()
        self._installations: dict[str, ComponentInstallation] = {}
        self._events: list[ComponentEvent] = []
        self._profiles = build_default_transcription_profiles()
        self._hardware = HardwareProfile(
            generated_at=utc_now() or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
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
            disk_volumes=(DiskVolumeSummary(path="C:\\", free_bytes=32 * 1024 * 1024 * 1024, total_bytes=64 * 1024 * 1024 * 1024, status=HardwareCapabilityState.DETECTED),),
            detection_source="local",
            status=HardwareCapabilityState.NOT_DETECTED,
            warnings=(),
            errors=(),
        )

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
        return (self._hardware,)

    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        self._hardware = profile
        return profile

    def latest_hardware_profile(self) -> HardwareProfile | None:
        return self._hardware

    def list_transcription_profiles(self):
        return self._profiles

    def get_transcription_profile(self, profile_id: str):
        normalized = profile_id.strip().lower()
        return next((profile for profile in self._profiles if profile.profile_id.lower() == normalized), None)

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


def _make_settings() -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="runtime.db",
        database_timeout_seconds=5.0,
        audio_cache_version="v1",
    )


def _paths(root: Path) -> ProjectPaths:
    paths = ProjectPaths.from_settings(root, _make_settings())
    paths.ensure_runtime_directories()
    return paths


def _runtime_bundle(root: Path) -> Path:
    bundle = root / "runtime-bundle"
    (bundle / "faster_whisper").mkdir(parents=True, exist_ok=True)
    (bundle / "faster_whisper" / "__init__.py").write_text("__version__ = '1.2.3'\n", encoding="utf-8")
    (bundle / "ctranslate2").mkdir(parents=True, exist_ok=True)
    (bundle / "ctranslate2" / "__init__.py").write_text("__version__ = '4.8.1'\n", encoding="utf-8")
    return bundle


def _model_bundle(root: Path) -> Path:
    bundle = root / "model-bundle"
    snapshot = bundle / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True, exist_ok=True)
    for filename in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
        (snapshot / filename).write_text("fixture", encoding="utf-8")
    (bundle / "models--Systran--faster-whisper-small" / "refs").mkdir(parents=True, exist_ok=True)
    (bundle / "models--Systran--faster-whisper-small" / "refs" / "main").write_text("abc123", encoding="utf-8")
    return bundle


class TranscriptionInstallerTests(unittest.TestCase):
    def test_runtime_install_local_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = _paths(root)
            repo = InMemoryComponentRepository()
            installer = ManagedTranscriptionRuntimeInstaller(paths=paths, repository=repo)
            bundle = _runtime_bundle(root)

            with patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(__version__="1.2.3")}):
                result = installer.install_local("transcription-runtime.faster-whisper", bundle, revision="1")

            self.assertEqual(result.state, "ready")
            installation = repo.get_installation("transcription-runtime.faster-whisper")
            self.assertIsNotNone(installation)
            self.assertEqual(installation.installation_status, ComponentInstallationStatus.READY)
            self.assertTrue(Path(result.active_path).exists())

    def test_model_install_local_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = _paths(root)
            repo = InMemoryComponentRepository()
            manager = TranscriptionModelManager(paths.models_directory)
            installer = ManagedTranscriptionModelInstaller(paths=paths, repository=repo, model_manager=manager)
            bundle = _model_bundle(root)

            class DummyWhisperModel:
                def __init__(self, *args, **kwargs):
                    return None

            with patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(WhisperModel=DummyWhisperModel)}):
                result = installer.install_local("transcription-model.small", bundle, revision="1")

            self.assertEqual(result.state, "ready")
            installation = repo.get_installation("transcription-model.small")
            self.assertIsNotNone(installation)
            self.assertEqual(installation.installation_status, ComponentInstallationStatus.READY)
            self.assertEqual(manager.get_model_status("small").status, TranscriptionModelStatus.INSTALLED)

    def test_model_install_from_verified_artifact_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = _paths(root)
            repo = InMemoryComponentRepository()
            manager = TranscriptionModelManager(paths.models_directory)
            installer = ManagedTranscriptionModelInstaller(paths=paths, repository=repo, model_manager=manager)
            bundle = _model_bundle(root)
            archive = root / "model.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in bundle.rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(bundle).as_posix())
            sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
            artifact = VerifiedComponentArtifact(
                download_id="download-1",
                component_id="transcription-model.small",
                verified_artifact_path=str(archive),
                partial_path=None,
                sha256=sha256,
                size_bytes=archive.stat().st_size,
                created_at=utc_now() or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                verified_at=utc_now() or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                source_url="http://example.test/model.zip",
            )

            class DummyWhisperModel:
                def __init__(self, *args, **kwargs):
                    return None

            with patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(WhisperModel=DummyWhisperModel)}):
                result = installer.install_local("transcription-model.small", archive, revision="1", artifact=artifact)

            self.assertEqual(result.state, "ready")
            self.assertEqual(repo.get_installation("transcription-model.small").installation_status, ComponentInstallationStatus.READY)

    def test_legacy_cache_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = _paths(root)
            manager = TranscriptionModelManager(paths.models_directory)
            legacy_root = manager.legacy_cache_root("small")
            snapshot = legacy_root / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
            snapshot.mkdir(parents=True, exist_ok=True)
            for filename in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
                (snapshot / filename).write_text("fixture", encoding="utf-8")
            info = manager.get_model_status("small")
            self.assertEqual(info.status, TranscriptionModelStatus.LEGACY_CACHE)
            self.assertFalse(info.managed)
            self.assertEqual(Path(info.path), legacy_root)

    def test_model_install_artifact_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = _paths(root)
            repo = InMemoryComponentRepository()
            manager = TranscriptionModelManager(paths.models_directory)
            installer = ManagedTranscriptionModelInstaller(paths=paths, repository=repo, model_manager=manager)
            bundle = _model_bundle(root)
            archive = root / "model.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in bundle.rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(bundle).as_posix())
            artifact = VerifiedComponentArtifact(
                download_id="download-2",
                component_id="transcription-model.small",
                verified_artifact_path=str(archive),
                partial_path=None,
                sha256="deadbeef",
                size_bytes=archive.stat().st_size,
                created_at=utc_now() or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                verified_at=utc_now() or __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                source_url="http://example.test/model.zip",
            )

            with self.assertRaises(Exception):
                installer.install_local("transcription-model.small", archive, revision="1", artifact=artifact)

