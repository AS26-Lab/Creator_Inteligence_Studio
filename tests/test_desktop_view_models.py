from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
    GpuInfo,
)
from creator_intelligence_studio.presentation.desktop.view_models.models import VideoFiltersViewModel
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.shared.paths import ProjectPaths


def make_settings() -> AppSettings:
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
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
    )


def make_diagnostic(root: Path) -> EnvironmentDiagnostic:
    return EnvironmentDiagnostic(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=root,
        os_name="Windows",
        os_version="10.0.19045",
        os_architecture="64bit",
        python_version="3.11.9",
        python_executable="python.exe",
        cpu_reported="CPU",
        logical_processors=12,
        nvidia_smi_available=True,
        gpu_devices=(GpuInfo(name="NVIDIA GeForce RTX 2080", driver_version="576.52", memory_total_mib=8192),),
        nvidia_driver_version="576.52",
        cuda_version_reported="12.9",
        git_available=True,
        git_version="git version 2.54.0",
        free_space_bytes=123,
        preferred_compute_backend="cuda",
        state=DiagnosticState(
            ready_for_basic_mode=True,
            cuda_driver_detected=True,
            cuda_runtime_not_verified=True,
            warnings=("CUDA runtime no verificado",),
        ),
        warnings=("CUDA runtime no verificado",),
        errors=(),
    )


class DesktopViewModelTests(unittest.TestCase):
    def test_workspace_view_model_selection_and_transforms(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            service = build_catalog_service(settings, paths, logger=logging.getLogger("test"))
            diagnostic = make_diagnostic(root)
            workspace = WorkspaceViewModel(
                service=service,
                diagnostic=diagnostic,
                settings=settings,
                paths=paths,
            )

            creator = workspace.create_creator(display_name="Heybermu")
            project = workspace.create_project(
                creator_reference=creator.id,
                name="Proyecto principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = workspace.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )

            creator_rows = workspace.creator_rows()
            project_rows = workspace.project_rows()
            video_rows = workspace.video_rows(VideoFiltersViewModel())
            cards = workspace.dashboard_cards()
            system_items = workspace.system_items()

        self.assertEqual(workspace.selected_creator_id, creator.id)
        self.assertEqual(workspace.selected_project_id, project.id)
        self.assertEqual(len(creator_rows), 1)
        self.assertEqual(len(project_rows), 1)
        self.assertEqual(len(video_rows), 1)
        self.assertEqual(video_rows[0].id, video.id)
        self.assertIn("Disponible", video_rows[0].processing_status)
        self.assertEqual(cards[0].value, "Heybermu")
        self.assertTrue(any(item.label == "Base local" for item in system_items))

    def test_empty_dashboard_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            service = build_catalog_service(settings, paths, logger=logging.getLogger("test"))
            diagnostic = make_diagnostic(root)
            workspace = WorkspaceViewModel(
                service=service,
                diagnostic=diagnostic,
                settings=settings,
                paths=paths,
            )

            cards = workspace.dashboard_cards()

        self.assertEqual(cards[0].value, "Ninguno")
        self.assertEqual(cards[2].value, "0")
