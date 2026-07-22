from __future__ import annotations

import logging
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.media_inspection_service import VideoInspectionReport
from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.media.value_objects import FractionValue
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


def make_media_service():
    tool = SimpleNamespace(path="C:/Tools/ffmpeg/bin/ffprobe.exe", version="ffprobe version", available=True, error_message=None)
    other_tool = SimpleNamespace(path="C:/Tools/ffmpeg/bin/ffmpeg.exe", version="ffmpeg version", available=True, error_message=None)
    tools_report = SimpleNamespace(ffmpeg=other_tool, ffprobe=tool, warnings=(), available=True)

    class _FakeMediaService:
        def verify_media_tools(self):
            return tools_report

        def get_video_inspection(self, video_id: str):
            return None

        def inspect_video(self, video_id: str, force: bool = False):
            raise AssertionError("No se esperaba inspeccion en esta prueba.")

        def is_inspection_stale(self, video_id: str) -> bool:
            return False

    return _FakeMediaService()


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
                media_service=make_media_service(),
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
                media_service=make_media_service(),
                diagnostic=diagnostic,
                settings=settings,
                paths=paths,
            )

            cards = workspace.dashboard_cards()

        self.assertEqual(cards[0].value, "Ninguno")
        self.assertEqual(cards[2].value, "0")

    def test_video_inspector_items_include_technical_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            service = build_catalog_service(settings, paths, logger=logging.getLogger("test"))
            diagnostic = make_diagnostic(root)
            workspace = WorkspaceViewModel(
                service=service,
                media_service=make_media_service(),
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
            inspection = VideoInspection(
                id="inspection-1",
                video_asset_id=video.id,
                inspection_status=VideoInspectionStatus.COMPLETED,
                inspected_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
                source_file_size_bytes=sample.stat().st_size,
                source_file_modified_at=datetime.fromtimestamp(sample.stat().st_mtime, tz=timezone.utc),
                duration_seconds=12.5,
                format_name="mov,mp4,m4a,3gp,3g2,mj2",
                format_long_name="QuickTime / MOV",
                overall_bitrate=1_000_000,
                stream_count=2,
                video_stream_count=1,
                audio_stream_count=1,
                subtitle_stream_count=0,
                width=1920,
                height=1080,
                display_aspect_ratio="16:9",
                pixel_aspect_ratio="1:1",
                frame_rate_numerator=30000,
                frame_rate_denominator=1001,
                average_frame_rate_numerator=30000,
                average_frame_rate_denominator=1001,
                video_codec="h264",
                video_codec_profile="High",
                pixel_format="yuv420p",
                video_bitrate=800000,
                audio_codec="aac",
                audio_sample_rate=48000,
                audio_channels=2,
                audio_channel_layout="stereo",
                audio_bitrate=128000,
                rotation_degrees=90,
                metadata_json="{}",
                ffprobe_version="ffprobe version",
                ffprobe_path="ffprobe.exe",
                ffmpeg_version="ffmpeg version",
                ffmpeg_path="ffmpeg.exe",
                thumbnail_relative_path="videos/1/thumbnails/thumbnail-v1.jpg",
                error_code=None,
                error_message=None,
                created_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
            )
            report = VideoInspectionReport(
                video=video,
                status=VideoInspectionStatus.COMPLETED,
                is_stale=False,
                file_available=True,
                inspection=inspection,
                thumbnail_path=str(root / "cache" / "videos" / video.id / "thumbnails" / "thumbnail-v1.jpg"),
            )

            items = workspace.video_inspector_items(video, report)

        labels = {item.label: item.value for item in items}
        self.assertEqual(labels["Estado de inspeccion"], "completed")
        self.assertEqual(labels["Resolucion"], "1920x1080")
        self.assertIn("fps", labels["FPS"])
        self.assertEqual(labels["Codec de video"], "h264")
        self.assertEqual(labels["Codec de audio"], "aac")
        self.assertEqual(labels["Canales"], "2")
        self.assertEqual(labels["Frecuencia de muestreo"], "48000 Hz")
        self.assertIn("bps", labels["Bitrate"])
        self.assertEqual(labels["Streams"], "2")
        self.assertEqual(labels["Vigencia"], "Vigente")
