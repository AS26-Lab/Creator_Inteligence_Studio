from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.component_manager_service import ComponentManagerService
from creator_intelligence_studio.application.services.transcription_capability_resolver import TranscriptionCapabilityResolver
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic import collect_environment_diagnostic
from creator_intelligence_studio.infrastructure.packaging import (
    WINDOWS_RUNTIME_MANIFEST_FILENAME,
    WindowsAppRuntimeManifest,
    build_windows_runtime_manifest,
    load_windows_runtime_manifest,
    resolve_windows_app_bundle_root,
    resolve_windows_runtime_manifest_path,
    write_windows_runtime_manifest,
)
from creator_intelligence_studio.shared.paths import ProjectPaths, discover_project_root

from tests.test_transcription_runtime_distribution import _MissingModelManager, _RuntimeRepository, _hardware_profile
from scripts import build_windows_app as build_windows_app_script


def _settings() -> AppSettings:
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
    )


class WindowsAppPackagingTests(unittest.TestCase):
    def test_runtime_manifest_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            manifest = build_windows_runtime_manifest(
                bundle_root=bundle_root,
                packaging_tool="PyInstaller",
                packaging_tool_version="6.14.2",
                build_revision="abc1234",
                notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
                python_version="3.11.9",
                faster_whisper_version="1.2.1",
                ctranslate2_version="4.8.1",
            )
            path = write_windows_runtime_manifest(bundle_root, manifest)
            loaded = load_windows_runtime_manifest(bundle_root)
            self.assertTrue(path.exists())
            self.assertEqual(path.name, WINDOWS_RUNTIME_MANIFEST_FILENAME)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.runtime_format_version, manifest.runtime_format_version)
            self.assertEqual(loaded.packaging_tool, "PyInstaller")
            self.assertEqual(loaded.build_revision, "abc1234")

    def test_discover_project_root_uses_bundle_root_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            bundle_root.mkdir(parents=True, exist_ok=True)
            executable = bundle_root / "CreatorIntelligenceStudio.exe"
            executable.write_text("", encoding="utf-8")
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)):
                root = discover_project_root()

        self.assertEqual(root, bundle_root)
        self.assertEqual(resolve_windows_app_bundle_root(executable=executable), bundle_root)

    def test_packaged_paths_use_local_app_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            bundle_root.mkdir(parents=True, exist_ok=True)
            executable = bundle_root / "CreatorIntelligenceStudio.exe"
            executable.write_text("", encoding="utf-8")
            local_app_data = Path(temp_dir) / "AppData" / "Local"
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)), patch.dict("os.environ", {"LOCALAPPDATA": str(local_app_data)}, clear=False):
                paths = ProjectPaths.from_settings(bundle_root, _settings())

        self.assertTrue(str(paths.data_directory).startswith(str(local_app_data)))
        self.assertTrue(str(paths.logs_directory).startswith(str(local_app_data)))
        self.assertTrue(str(paths.models_directory).startswith(str(local_app_data)))
        self.assertTrue(str(paths.artifacts_directory).startswith(str(local_app_data)))
        self.assertEqual(resolve_windows_runtime_manifest_path(bundle_root).parent, bundle_root / "runtime")

    def test_resolver_reports_application_bundled_when_manifest_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            bundle_root.mkdir(parents=True, exist_ok=True)
            executable = bundle_root / "CreatorIntelligenceStudio.exe"
            executable.write_text("", encoding="utf-8")
            manifest = WindowsAppRuntimeManifest(
                runtime_format_version=1,
                application_name="Creator Intelligence Studio",
                application_version="0.1.0",
                creator_intelligence_studio_version="0.1.0",
                packaging_tool="PyInstaller",
                packaging_tool_version="6.14.2",
                python_version="3.11.9",
                faster_whisper_version="1.2.1",
                ctranslate2_version="4.8.1",
                platform="Windows",
                architecture="x86_64",
                cpu_supported=True,
                gpu_supported=False,
                build_revision="abc1234",
                build_timestamp="2026-08-10T00:00:00+00:00",
                bundle_kind="onedir",
                notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
                runtime_root=str(bundle_root / "runtime"),
                libraries_root=str(bundle_root / "libraries"),
                resources_root=str(bundle_root / "resources"),
            )
            write_windows_runtime_manifest(bundle_root, manifest)
            repo = _RuntimeRepository()
            resolver = TranscriptionCapabilityResolver(repository=repo, paths=_paths(bundle_root), model_manager=_MissingModelManager())
            fake_faster_whisper = SimpleNamespace(__version__="1.2.1")
            fake_ctranslate2 = SimpleNamespace(__version__="4.8.1", get_cuda_device_count=lambda: 0, get_supported_compute_types=lambda device: ("int8",))
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)), patch(
                "creator_intelligence_studio.application.services.transcription_capability_resolver.importlib.import_module",
                side_effect=lambda name: fake_faster_whisper if name == "faster_whisper" else fake_ctranslate2 if name == "ctranslate2" else __import__(name),
            ):
                report = resolver.resolve(requested_profile="balanced", preferred_device="auto")

        self.assertEqual(report.runtime_resolution.installation.distribution_state.value, "application_bundled")
        self.assertTrue(report.runtime_resolution.installation.managed)
        self.assertEqual(report.runtime_resolution.installation.location_reference, "application_bundle")

    def test_component_inventory_marks_packaged_runtime_as_bundled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            bundle_root.mkdir(parents=True, exist_ok=True)
            executable = bundle_root / "CreatorIntelligenceStudio.exe"
            executable.write_text("", encoding="utf-8")
            manifest = WindowsAppRuntimeManifest(
                runtime_format_version=1,
                application_name="Creator Intelligence Studio",
                application_version="0.1.0",
                creator_intelligence_studio_version="0.1.0",
                packaging_tool="PyInstaller",
                packaging_tool_version="6.14.2",
                python_version="3.11.9",
                faster_whisper_version="1.2.1",
                ctranslate2_version="4.8.1",
                platform="Windows",
                architecture="x86_64",
                cpu_supported=True,
                gpu_supported=False,
                build_revision="abc1234",
                build_timestamp="2026-08-10T00:00:00+00:00",
                bundle_kind="onedir",
                notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
            )
            write_windows_runtime_manifest(bundle_root, manifest)
            repo = _RuntimeRepository()
            service = ComponentManagerService(paths=_paths(bundle_root), repository=repo)
            fake_faster_whisper = SimpleNamespace(__version__="1.2.1")
            fake_ctranslate2 = SimpleNamespace(__version__="4.8.1")
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)), patch(
                "creator_intelligence_studio.application.services.component_manager_service.importlib.import_module",
                side_effect=lambda name: fake_faster_whisper if name == "faster_whisper" else fake_ctranslate2 if name == "ctranslate2" else __import__(name),
            ):
                installations = service.inspect_installations()

        runtime = next(item for item in installations if item.component_id == "transcription-runtime.faster-whisper")
        self.assertEqual(runtime.installation_status.value, "ready")
        self.assertEqual(runtime.location_reference, "application_bundle")
        self.assertTrue(runtime.managed)

    def test_environment_diagnostic_reports_packaged_runtime_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "CreatorIntelligenceStudio"
            bundle_root.mkdir(parents=True, exist_ok=True)
            executable = bundle_root / "CreatorIntelligenceStudio.exe"
            executable.write_text("", encoding="utf-8")
            manifest = WindowsAppRuntimeManifest(
                runtime_format_version=1,
                application_name="Creator Intelligence Studio",
                application_version="0.1.0",
                creator_intelligence_studio_version="0.1.0",
                packaging_tool="PyInstaller",
                packaging_tool_version="6.14.2",
                python_version="3.11.9",
                faster_whisper_version="1.2.1",
                ctranslate2_version="4.8.1",
                platform="Windows",
                architecture="x86_64",
                cpu_supported=True,
                gpu_supported=False,
                build_revision="abc1234",
                build_timestamp="2026-08-10T00:00:00+00:00",
                bundle_kind="onedir",
                notices_reference="docs/TRANSCRIPTION_RUNTIME_LICENSING.md",
            )
            write_windows_runtime_manifest(bundle_root, manifest)
            settings = _settings()
            paths = ProjectPaths.from_settings(bundle_root, settings)
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)), patch(
                "creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic.shutil.which",
                return_value=None,
            ):
                diagnostic = collect_environment_diagnostic(settings=settings, paths=paths)

        self.assertTrue(diagnostic.packaged_application)
        self.assertEqual(diagnostic.application_root, str(bundle_root))
        self.assertIsNotNone(diagnostic.runtime_manifest)
        self.assertEqual(diagnostic.runtime_manifest["packaging_tool"], "PyInstaller")

    def test_build_script_writes_manifest_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir) / "dist"
            with patch.object(build_windows_app_script, "_detect_pyinstaller", return_value=("PyInstaller", "6.14.2")):
                report = build_windows_app_script.build_windows_app(
                    project_root=Path(temp_dir),
                    staging_root=staging_root,
                    invoke_packager=False,
                )
            manifest_path = Path(report.manifest_path)
            self.assertTrue(manifest_path.exists())
            self.assertTrue(report.success)
            self.assertEqual(report.packaging_tool, "PyInstaller")
            self.assertEqual(report.bundle_kind, "onedir")
            self.assertIn(str(staging_root / "CreatorIntelligenceStudio" / "CreatorIntelligenceStudio.exe"), report.output_paths)


def _paths(temp_dir: Path) -> ProjectPaths:
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


if __name__ == "__main__":
    unittest.main()
