from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.hardware_capability_service import HardwareCapabilityService
from creator_intelligence_studio.application.services.ffmpeg_component_service import (
    FFmpegHealthCheckResult,
    FFmpegHealthChecker,
    FFmpegManagedComponentService,
    FFmpegVersionInfo,
)
from creator_intelligence_studio.application.services.transcription_capability_resolver import (
    TranscriptionCapabilityResolver,
)
from creator_intelligence_studio.domain.components.catalog import build_default_component_catalog, build_default_transcription_profiles
from creator_intelligence_studio.domain.components.entities import (
    ComponentCatalog,
    ComponentCatalogEntry,
    ComponentCategory,
    ComponentInstallation,
    ComponentInstallationStatus,
    ComponentInstallKind,
    ComponentEvent,
    ComponentEventType,
    RuntimeCheckRecord,
    RuntimeCheckStatus,
)
from creator_intelligence_studio.domain.components.repositories import ComponentManagerRepository
from creator_intelligence_studio.domain.hardware.entities import (
    DiskVolumeSummary,
    GpuSummary,
    HardwareCapabilityState,
    HardwareProfile,
)
from creator_intelligence_studio.domain.transcription.profiles import (
    TranscriptionProfileDefinition,
    TranscriptionProfileStatus,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
from creator_intelligence_studio.shared.paths import ProjectPaths


class InMemoryComponentRepository(ComponentManagerRepository):
    def __init__(
        self,
        *,
        catalog: ComponentCatalog | None = None,
        installations: tuple[ComponentInstallation, ...] = (),
        hardware_profile: HardwareProfile | None = None,
        transcription_profiles: tuple[TranscriptionProfileDefinition, ...] | None = None,
    ) -> None:
        self._catalog = catalog or build_default_component_catalog()
        self._installations = list(installations)
        self._hardware_profile = hardware_profile
        self._profiles = transcription_profiles or build_default_transcription_profiles()
        self._runtime_checks: list[RuntimeCheckRecord] = []
        self._events: list[ComponentEvent] = []

    def get_catalog(self) -> ComponentCatalog:
        return self._catalog

    def list_catalog_entries(self) -> tuple[ComponentCatalogEntry, ...]:
        return self._catalog.entries

    def get_catalog_entry(self, component_id: str) -> ComponentCatalogEntry | None:
        return self._catalog.get_entry(component_id)

    def upsert_catalog_entry(self, entry: ComponentCatalogEntry) -> ComponentCatalogEntry:
        self._catalog = ComponentCatalog(
            catalog_version=max(self._catalog.catalog_version, entry.catalog_version),
            entries=tuple([item for item in self._catalog.entries if item.component_id != entry.component_id] + [entry]),
            reviewed_at=self._catalog.reviewed_at,
        )
        return entry

    def list_installations(self) -> tuple[ComponentInstallation, ...]:
        return tuple(self._installations)

    def get_installation(self, component_id: str) -> ComponentInstallation | None:
        normalized = component_id.strip().lower()
        for installation in self._installations:
            if installation.component_id.lower() == normalized:
                return installation
        return None

    def upsert_installation(self, installation: ComponentInstallation) -> ComponentInstallation:
        self._installations = [item for item in self._installations if item.component_id != installation.component_id]
        self._installations.append(installation)
        return installation

    def list_hardware_profiles(self) -> tuple[HardwareProfile, ...]:
        return (self._hardware_profile,) if self._hardware_profile is not None else ()

    def upsert_hardware_profile(self, profile: HardwareProfile) -> HardwareProfile:
        self._hardware_profile = profile
        return profile

    def latest_hardware_profile(self) -> HardwareProfile | None:
        return self._hardware_profile

    def list_transcription_profiles(self) -> tuple[TranscriptionProfileDefinition, ...]:
        return self._profiles

    def get_transcription_profile(self, profile_id: str) -> TranscriptionProfileDefinition | None:
        normalized = profile_id.strip().lower()
        for profile in self._profiles:
            if profile.profile_id.lower() == normalized:
                return profile
        return None

    def upsert_transcription_profile(self, profile: TranscriptionProfileDefinition) -> TranscriptionProfileDefinition:
        raise NotImplementedError

    def list_runtime_checks(self) -> tuple[RuntimeCheckRecord, ...]:
        return tuple(self._runtime_checks)

    def upsert_runtime_check(self, record: RuntimeCheckRecord) -> RuntimeCheckRecord:
        self._runtime_checks.append(record)
        return record

    def append_event(self, event: ComponentEvent) -> ComponentEvent:
        self._events.append(event)
        return event

    def list_events(self) -> tuple[ComponentEvent, ...]:
        return tuple(self._events)


class HardwareCapabilityContractTests(unittest.TestCase):
    def _paths(self, temp_dir: str) -> ProjectPaths:
        settings = AppSettings(
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
        root = Path(temp_dir)
        paths = ProjectPaths.from_settings(root, settings)
        paths.ensure_runtime_directories()
        return paths

    def test_collect_inventory_cpu_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = HardwareCapabilityService(paths=paths, repository=repo)
            with (
                patch("creator_intelligence_studio.application.services.hardware_capability_service._detect_nvidia_gpu", return_value=GpuSummary(None, None, None, None, False, status=HardwareCapabilityState.NOT_DETECTED, notes="nvidia-smi no esta disponible.")),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._ctranslate2_cuda_status", return_value=(HardwareCapabilityState.NOT_DETECTED, None, "CUDA no reportada por CTranslate2.")),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._system_ram_bytes", return_value=(8 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024)),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._safe_disk_usage", return_value=(32 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024)),
            ):
                profile = service.collect_inventory(persist=False)

            self.assertEqual(profile.status, HardwareCapabilityState.NOT_DETECTED)
            self.assertEqual(profile.gpu.status, HardwareCapabilityState.NOT_DETECTED)
            self.assertEqual(profile.disk_volumes[0].status, HardwareCapabilityState.DETECTED)

    def test_collect_inventory_reports_gpu_not_tested_without_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = HardwareCapabilityService(paths=paths, repository=repo)
            with (
                patch("creator_intelligence_studio.application.services.hardware_capability_service._detect_nvidia_gpu", return_value=GpuSummary("nvidia", "GeForce RTX", "552.12", 8 * 1024 * 1024 * 1024, True, cuda_runtime_reported="12.4", ctranslate2_cuda_available=True, status=HardwareCapabilityState.REPORTED_NOT_TESTED, notes="GPU NVIDIA detectada; falta prueba funcional de transcripcion.")),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._ctranslate2_cuda_status", return_value=(HardwareCapabilityState.REPORTED_NOT_TESTED, "4.8.1", "device_count=1; supported=['int8', 'int8_float16']")),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._system_ram_bytes", return_value=(8 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024)),
                patch("creator_intelligence_studio.application.services.hardware_capability_service._safe_disk_usage", return_value=(32 * 1024 * 1024 * 1024, 64 * 1024 * 1024 * 1024)),
            ):
                profile = service.collect_inventory(persist=False)

            self.assertEqual(profile.status, HardwareCapabilityState.REPORTED_NOT_TESTED)
            self.assertEqual(profile.gpu.status, HardwareCapabilityState.REPORTED_NOT_TESTED)
            self.assertTrue(profile.warnings)


class TranscriptionCapabilityContractTests(unittest.TestCase):
    def _runtime_profile(self) -> HardwareProfile:
        return HardwareProfile(
            generated_at=datetime.now(tz=timezone.utc),
            platform="Windows",
            architecture="AMD64",
            cpu_logical_count=8,
            cpu_summary="Windows AMD64; logical=8",
            ram_total_bytes=16 * 1024 * 1024 * 1024,
            ram_available_bytes=8 * 1024 * 1024 * 1024,
            gpu=GpuSummary(
                vendor=None,
                name=None,
                driver_version=None,
                vram_total_bytes=None,
                cuda_visible=False,
                status=HardwareCapabilityState.NOT_DETECTED,
            ),
            driver_summary=None,
            cuda_reported=None,
            ctranslate2_cuda_status=HardwareCapabilityState.NOT_DETECTED,
            disk_volumes=(DiskVolumeSummary(path="C:\\tmp", free_bytes=64 * 1024 * 1024 * 1024, total_bytes=128 * 1024 * 1024 * 1024, status=HardwareCapabilityState.DETECTED),),
            detection_source="local",
            status=HardwareCapabilityState.NOT_DETECTED,
            warnings=(),
            errors=(),
        )

    def _resolver(
        self,
        temp_dir: str,
        *,
        installations: tuple[ComponentInstallation, ...],
        hardware_profile: HardwareProfile | None = None,
        profiles: tuple[TranscriptionProfileDefinition, ...] | None = None,
    ) -> TranscriptionCapabilityResolver:
        settings = AppSettings(
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
        paths = ProjectPaths.from_settings(Path(temp_dir), settings)
        paths.ensure_runtime_directories()
        repository = InMemoryComponentRepository(installations=installations, hardware_profile=hardware_profile, transcription_profiles=profiles)
        model_manager = TranscriptionModelManager(paths.models_directory)
        return TranscriptionCapabilityResolver(repository=repository, paths=paths, model_manager=model_manager)

    def _installation(self, component_id: str, status: ComponentInstallationStatus) -> ComponentInstallation:
        return ComponentInstallation(
            component_id=component_id,
            installation_status=status,
            installed_version="1.0",
            revision="1",
            install_type=ComponentInstallKind.EXTERNALLY_DETECTED,
            location_path=None,
            location_reference=None,
            detected_at=None,
            verified_at=None,
            health_status=RuntimeCheckStatus.READY if status == ComponentInstallationStatus.READY else RuntimeCheckStatus.NOT_CHECKED,
            source="test",
            managed=False,
            metadata={},
        )

    def test_ready_on_cpu_with_balanced_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolver = self._resolver(
                temp_dir,
                installations=(
                    self._installation("ffmpeg", ComponentInstallationStatus.READY),
                    self._installation("ffprobe", ComponentInstallationStatus.READY),
                    self._installation("transcription-runtime.ctranslate2", ComponentInstallationStatus.READY),
                    self._installation("transcription-model.small", ComponentInstallationStatus.READY),
                ),
            )
            report = resolver.resolve(requested_profile="balanced", preferred_device="auto")
        self.assertEqual(report.readiness, "ready")
        self.assertEqual(report.selected_profile.profile_id, "balanced")
        self.assertEqual(report.model_status, ComponentInstallationStatus.READY)
        self.assertEqual(report.missing_component_ids, ())

    def test_balanced_falls_back_to_fast_when_balanced_model_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolver = self._resolver(
                temp_dir,
                installations=(
                    self._installation("ffmpeg", ComponentInstallationStatus.READY),
                    self._installation("ffprobe", ComponentInstallationStatus.READY),
                    self._installation("transcription-runtime.ctranslate2", ComponentInstallationStatus.READY),
                    self._installation("transcription-model.base", ComponentInstallationStatus.READY),
                ),
            )
            report = resolver.resolve(requested_profile="balanced", preferred_device="auto")
        self.assertEqual(report.recommended_profile.profile_id, "fast")
        self.assertEqual(report.selected_profile.profile_id, "fast")

    def test_gpu_reported_not_tested_promotes_warning_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolver = self._resolver(
                temp_dir,
                installations=(
                    self._installation("ffmpeg", ComponentInstallationStatus.READY),
                    self._installation("ffprobe", ComponentInstallationStatus.READY),
                    self._installation("transcription-runtime.ctranslate2", ComponentInstallationStatus.READY),
                    self._installation("transcription-model.small", ComponentInstallationStatus.READY),
                ),
                hardware_profile=HardwareProfile(
                    generated_at=datetime.now(tz=timezone.utc),
                    platform="Windows",
                    architecture="AMD64",
                    cpu_logical_count=8,
                    cpu_summary="Windows AMD64; logical=8",
                    ram_total_bytes=16 * 1024 * 1024 * 1024,
                    ram_available_bytes=8 * 1024 * 1024 * 1024,
                    gpu=GpuSummary(
                        vendor="nvidia",
                        name="GeForce RTX",
                        driver_version="552.12",
                        vram_total_bytes=8 * 1024 * 1024 * 1024,
                        cuda_visible=True,
                        cuda_runtime_reported="12.4",
                        ctranslate2_cuda_available=True,
                        status=HardwareCapabilityState.REPORTED_NOT_TESTED,
                        notes="GPU NVIDIA detectada; falta prueba funcional de transcripcion.",
                    ),
                    driver_summary="552.12",
                    cuda_reported="12.4",
                    ctranslate2_cuda_status=HardwareCapabilityState.REPORTED_NOT_TESTED,
                    disk_volumes=(DiskVolumeSummary(path="C:\\tmp", free_bytes=64 * 1024 * 1024 * 1024, total_bytes=128 * 1024 * 1024 * 1024, status=HardwareCapabilityState.DETECTED),),
                    detection_source="local",
                    status=HardwareCapabilityState.REPORTED_NOT_TESTED,
                    warnings=("Se detecto una GPU NVIDIA, pero falta ejecutar una prueba de transcripcion para confirmarla.",),
                    errors=(),
                ),
            )
            report = resolver.resolve(requested_profile="balanced", preferred_device="gpu")
        self.assertEqual(report.readiness, "ready_with_warnings")
        self.assertIn("GPU", " ".join(report.warnings))

    def test_missing_ffmpeg_blocks_and_explains_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            resolver = self._resolver(
                temp_dir,
                installations=(
                    self._installation("ffprobe", ComponentInstallationStatus.READY),
                    self._installation("transcription-runtime.ctranslate2", ComponentInstallationStatus.READY),
                    self._installation("transcription-model.small", ComponentInstallationStatus.READY),
                ),
            )
            report = resolver.resolve(requested_profile="balanced", preferred_device="auto")
        presentation = resolver.present(report)
        self.assertEqual(report.readiness, "missing_components")
        self.assertIn("ffmpeg", report.missing_component_ids)
        self.assertIn("componente multimedia", presentation.message.lower())


class ComponentCatalogContractTests(unittest.TestCase):
    def test_default_catalog_includes_current_foundation_entries(self) -> None:
        catalog = build_default_component_catalog()
        component_ids = {entry.component_id for entry in catalog.entries}
        self.assertIn("ffmpeg", component_ids)
        self.assertIn("ffprobe", component_ids)
        self.assertIn("transcription-runtime.faster-whisper", component_ids)
        self.assertIn("transcription-model.small", component_ids)
        self.assertIn("transcription-model.medium", component_ids)
        self.assertEqual(catalog.catalog_version, 1)

    def test_ffmpeg_is_the_only_product_source_in_default_catalog(self) -> None:
        catalog = build_default_component_catalog()
        ffmpeg = catalog.get_entry("ffmpeg")
        self.assertIsNotNone(ffmpeg)
        self.assertEqual(ffmpeg.source_type, "approved_product_source")
        self.assertEqual(ffmpeg.source_provider, "btbn")
        self.assertEqual(ffmpeg.upstream_project, "ffmpeg")
        self.assertEqual(ffmpeg.license_variant, "lgpl")
        self.assertEqual(ffmpeg.release_tag, "autobuild-2026-08-09-13-03")
        self.assertEqual(ffmpeg.asset_name, "ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip")
        self.assertEqual(ffmpeg.expected_sha256, "6b4edff47f121d2ed218b1b19d17f67aed08f9f1c9cbcee576fd0548a748c412")
        self.assertEqual(ffmpeg.expected_download_bytes, 145937826)

        runtime = catalog.get_entry("transcription-runtime.faster-whisper")
        self.assertIsNotNone(runtime)
        self.assertIsNone(runtime.source_url)
        self.assertIsNone(runtime.expected_sha256)
        self.assertNotEqual(runtime.source_type, "approved_product_source")

        model = catalog.get_entry("transcription-model.small")
        self.assertIsNotNone(model)
        self.assertIsNone(model.source_url)
        self.assertIsNone(model.expected_sha256)
        self.assertNotEqual(model.source_type, "approved_product_source")

    def test_default_profiles_include_balanced_as_provisional_default(self) -> None:
        profiles = build_default_transcription_profiles()
        profile_ids = {profile.profile_id for profile in profiles}
        self.assertEqual(profile_ids, {"fast", "balanced", "maximum_quality", "custom"})
        balanced = next(profile for profile in profiles if profile.profile_id == "balanced")
        self.assertEqual(balanced.status, TranscriptionProfileStatus.PROVISIONAL)
        self.assertEqual(balanced.version, 1)


class _ReadyHealthChecker:
    def check_bundle(self, *, ffmpeg_path: Path, ffprobe_path: Path, fixture_root: Path) -> FFmpegHealthCheckResult:
        version = FFmpegVersionInfo(raw_line="ffmpeg version 1.2.3", parsed_version="1.2.3", build_metadata=None)
        return FFmpegHealthCheckResult(
            state="ready",
            ffmpeg_exists=True,
            ffprobe_exists=True,
            ffmpeg_version=version,
            ffprobe_version=FFmpegVersionInfo(raw_line="ffprobe version 1.2.3", parsed_version="1.2.3", build_metadata=None),
            ffmpeg_path=str(ffmpeg_path),
            ffprobe_path=str(ffprobe_path),
            fixture_path=str(fixture_root / "health-fixtures" / "ffmpeg_health.wav"),
            warnings=(),
            error_message=None,
            detected_architecture="AMD64",
            verified_at=datetime.now(tz=timezone.utc),
        )


class _BrokenHealthChecker:
    def check_bundle(self, *, ffmpeg_path: Path, ffprobe_path: Path, fixture_root: Path) -> FFmpegHealthCheckResult:
        return FFmpegHealthCheckResult(
            state="corrupt",
            ffmpeg_exists=True,
            ffprobe_exists=True,
            ffmpeg_version=None,
            ffprobe_version=None,
            ffmpeg_path=str(ffmpeg_path),
            ffprobe_path=str(ffprobe_path),
            fixture_path=str(fixture_root / "health-fixtures" / "ffmpeg_health.wav"),
            warnings=("corrupt",),
            error_message="corrupt",
            detected_architecture="AMD64",
            verified_at=datetime.now(tz=timezone.utc),
        )


class FfmpegBoundaryContractTests(unittest.TestCase):
    def _paths(self, temp_dir: str) -> ProjectPaths:
        settings = AppSettings(
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
        root = Path(temp_dir)
        paths = ProjectPaths.from_settings(root, settings)
        paths.ensure_runtime_directories()
        return paths

    def test_install_local_package_success_and_managed_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = FFmpegManagedComponentService(paths=paths, repository=repo, health_checker=_ReadyHealthChecker())
            source = Path(temp_dir) / "package"
            source.mkdir()
            (source / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (source / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            (source / "LICENSE.txt").write_text("license", encoding="utf-8")

            result = service.install_local(source)
            self.assertEqual(result.state, "ready")
            self.assertIsNotNone(result.installation)
            self.assertTrue(Path(result.active_path).exists())
            resolution = service.resolve_media_tools()
            self.assertEqual(resolution.resolution.source, "managed")
            self.assertTrue(resolution.available)

    def test_install_local_does_not_mutate_path_or_use_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = FFmpegManagedComponentService(paths=paths, repository=repo, health_checker=_ReadyHealthChecker())
            source = Path(temp_dir) / "package"
            source.mkdir()
            (source / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (source / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            original_path = os.environ.get("PATH")
            with patch("urllib.request.urlopen", side_effect=AssertionError("network not allowed")):
                result = service.install_local(source)
            self.assertEqual(result.state, "ready")
            self.assertEqual(os.environ.get("PATH"), original_path)

    def test_health_check_uses_argument_list_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ffmpeg = root / "ffmpeg.exe"
            ffprobe = root / "ffprobe.exe"
            ffmpeg.write_text("ffmpeg", encoding="utf-8")
            ffprobe.write_text("ffprobe", encoding="utf-8")
            checker = FFmpegHealthChecker(timeout_seconds=1.0)
            calls: list[dict[str, object]] = []

            def fake_run(*args, **kwargs):
                calls.append({"args": args, "kwargs": kwargs})
                self.assertFalse(kwargs.get("shell", False))
                command = args[0]
                executable = Path(command[0]).stem.lower()
                if "-version" in command:
                    return SimpleNamespace(returncode=0, stdout=f"{executable} version 1.2.3\nbuild: test\n", stderr="")
                if "-print_format" in command:
                    return SimpleNamespace(returncode=0, stdout="{}", stderr="")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with patch("creator_intelligence_studio.application.services.ffmpeg_component_service.subprocess.run", side_effect=fake_run):
                result = checker.check_bundle(ffmpeg_path=ffmpeg, ffprobe_path=ffprobe, fixture_root=root)

            self.assertEqual(result.state, "ready")
            self.assertTrue(calls)
            self.assertTrue(all(isinstance(call["args"][0], list) for call in calls))

    def test_install_local_path_traversal_blocked(self) -> None:
        import zipfile

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = FFmpegManagedComponentService(paths=paths, repository=repo, health_checker=_ReadyHealthChecker())
            archive = Path(temp_dir) / "traversal.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../ffmpeg.exe", "evil")
                zf.writestr("ffprobe.exe", "ok")

            result = service.install_local(archive)
            self.assertEqual(result.state, "failed")
            self.assertIn("Traversal", " ".join(result.errors))

    def test_managed_broken_falls_back_to_external(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = FFmpegManagedComponentService(paths=paths, repository=repo, health_checker=_BrokenHealthChecker())
            managed_root = paths.components_directory / "ffmpeg" / "1.0" / "active"
            managed_root.mkdir(parents=True)
            (managed_root / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (managed_root / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            repo.upsert_installation(
                ComponentInstallation(
                    component_id="ffmpeg",
                    installation_status=ComponentInstallationStatus.REPAIR_REQUIRED,
                    installed_version="1.0",
                    revision="1.0",
                    install_type=ComponentInstallKind.MANAGED,
                    location_path=str(managed_root),
                    location_reference="managed_root",
                    detected_at=datetime.now(tz=timezone.utc),
                    verified_at=datetime.now(tz=timezone.utc),
                    health_status=RuntimeCheckStatus.FAILED,
                    source="local_package",
                    managed=True,
                    metadata={"source_path": str(managed_root)},
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )
            repo.upsert_installation(
                ComponentInstallation(
                    component_id="ffprobe",
                    installation_status=ComponentInstallationStatus.REPAIR_REQUIRED,
                    installed_version="1.0",
                    revision="1.0",
                    install_type=ComponentInstallKind.MANAGED,
                    location_path=str(managed_root),
                    location_reference="managed_root",
                    detected_at=datetime.now(tz=timezone.utc),
                    verified_at=datetime.now(tz=timezone.utc),
                    health_status=RuntimeCheckStatus.FAILED,
                    source="local_package",
                    managed=True,
                    metadata={"source_path": str(managed_root)},
                    created_at=datetime.now(tz=timezone.utc),
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )
            with patch.object(service, "_discover_external") as discover_external:
                discover_external.return_value = service._build_media_tools(
                    ffmpeg_path=Path(temp_dir) / "external" / "ffmpeg.exe",
                    ffprobe_path=Path(temp_dir) / "external" / "ffprobe.exe",
                    source="external",
                    installation_type="externally_detected",
                    health=_ReadyHealthChecker().check_bundle(
                        ffmpeg_path=Path(temp_dir) / "external" / "ffmpeg.exe",
                        ffprobe_path=Path(temp_dir) / "external" / "ffprobe.exe",
                        fixture_root=paths.components_directory,
                    ),
                    reason="external_discovery",
                    managed_location=None,
                    version="1.0",
                )
                resolved = service.resolve_media_tools()
            self.assertEqual(resolved.resolution.source, "external")

    def test_remove_managed_reports_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._paths(temp_dir)
            repo = InMemoryComponentRepository()
            service = FFmpegManagedComponentService(paths=paths, repository=repo, health_checker=_ReadyHealthChecker())
            source = Path(temp_dir) / "package"
            source.mkdir()
            (source / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (source / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            service.install_local(source)
            with patch.object(service, "_discover_external") as discover_external:
                discover_external.return_value = service._build_media_tools(
                    ffmpeg_path=Path(temp_dir) / "external" / "ffmpeg.exe",
                    ffprobe_path=Path(temp_dir) / "external" / "ffprobe.exe",
                    source="external",
                    installation_type="externally_detected",
                    health=_ReadyHealthChecker().check_bundle(
                        ffmpeg_path=Path(temp_dir) / "external" / "ffmpeg.exe",
                        ffprobe_path=Path(temp_dir) / "external" / "ffprobe.exe",
                        fixture_root=paths.components_directory,
                    ),
                    reason="external_discovery",
                    managed_location=None,
                    version="1.0",
                )
                result = service.remove()
            self.assertIn(result.state, {"removed", "fallback_selected"})


if __name__ == "__main__":
    unittest.main()
