from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.media_inspection_service import build_media_inspection_service
from creator_intelligence_studio.application.services.visual_analysis_service import build_visual_analysis_service
from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.visual_analysis.value_objects import VisualAnalysisOptions, VisualEventType
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_inspection_repository import SQLiteVideoInspectionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_visual_analysis_repository import SQLiteVisualAnalysisRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.infrastructure.visual_analysis.frame_metrics import compute_frame_metrics
from creator_intelligence_studio.infrastructure.visual_analysis.frame_sampler import SampledFrame
from creator_intelligence_studio.infrastructure.visual_analysis.scene_detector import build_scenes, detect_cut_candidates
from creator_intelligence_studio.infrastructure.visual_analysis.visual_event_detector import detect_visual_events
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.paths import ProjectPaths
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.visual_analysis_view import VisualAnalysisView


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


def make_environment(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    media = build_media_inspection_service(
        settings=settings,
        paths=paths,
        video_repository=SQLiteVideoRepository(database),
        inspection_repository=SQLiteVideoInspectionRepository(database),
        logger=logging.getLogger("test"),
    )
    visual = build_visual_analysis_service(
        settings=settings,
        paths=paths,
        video_repository=SQLiteVideoRepository(database),
        inspection_repository=SQLiteVideoInspectionRepository(database),
        visual_repository=SQLiteVisualAnalysisRepository(database),
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, media, visual


def generate_video(ffmpeg_path: str, destination: Path, *, variant: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if variant == "cut":
        args = [
            ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x90:d=1",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:d=1",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            str(destination),
        ]
    elif variant == "static":
        args = [
            ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x90:d=2",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            str(destination),
        ]
    else:
        raise ValueError("variant no soportado")
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or "ffmpeg fallo")


class VisualAnalysisCoreTests(unittest.TestCase):
    def test_metricas_cortos_corte_y_eventos(self) -> None:
        black = np.zeros((12, 12, 3), dtype=np.uint8)
        white = np.full((12, 12, 3), 255, dtype=np.uint8)
        frames = [
            SampledFrame(0, 0.0, 12, 12, black),
            SampledFrame(1, 0.5, 12, 12, black),
            SampledFrame(2, 1.0, 12, 12, white),
            SampledFrame(3, 1.5, 12, 12, black),
        ]
        metrics = compute_frame_metrics(frames)
        cuts = detect_cut_candidates(metrics, VisualAnalysisOptions())
        scenes = build_scenes(metrics, cuts, duration_seconds=2.0, min_scene_duration_seconds=0.5)
        events = detect_visual_events(metrics, cuts, VisualAnalysisOptions())

        labels = [metric.activity_label.value for metric in metrics]
        self.assertIn("possible_black_frame", labels)
        self.assertTrue(any(cut.cut_type.value in {VisualEventType.HARD_CUT.value, VisualEventType.GRADUAL_TRANSITION.value} for cut in cuts))
        self.assertGreaterEqual(len(scenes), 1)
        self.assertTrue(any(event.event_type == VisualEventType.BLACK_FRAME_CANDIDATE for event in events))


class VisualAnalysisIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_visual_analysis_completed_exports_and_stale(self) -> None:
        tool_root = Path(r"C:\Tools\ffmpeg\bin")
        ffmpeg_path = tool_root / "ffmpeg.exe"
        ffprobe_path = tool_root / "ffprobe.exe"
        if not ffmpeg_path.exists() or not ffprobe_path.exists():
            self.skipTest("ffmpeg/ffprobe no disponibles")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, media, visual = make_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            source = root / "cut.mp4"
            generate_video(str(ffmpeg_path), source, variant="cut")
            video = catalog.register_video(project_id=project.id, file_path=str(source), title="Corte sintetico")

            inspection = media.inspect_video(video.id)
            self.assertEqual(inspection.status, VideoInspectionStatus.COMPLETED)

            report = visual.analyze_visuals(video.id)
            self.assertEqual(report.status.value, "completed")
            self.assertGreaterEqual(len(report.windows), 1)
            self.assertGreaterEqual(len(report.scenes), 1)
            self.assertTrue((root / report.scenes[0].representative_keyframe_path).exists())

            json_export = visual.export_visual_analysis(video.id, "json")
            timeline_export = visual.export_visual_analysis(video.id, "timeline-csv")
            scenes_export = visual.export_visual_analysis(video.id, "scenes-csv")
            txt_export = visual.export_visual_analysis(video.id, "txt")
            self.assertTrue(Path(json_export.path).exists())
            self.assertTrue(Path(timeline_export.path).exists())
            self.assertTrue(Path(scenes_export.path).exists())
            self.assertTrue(Path(txt_export.path).exists())

            source.write_bytes(source.read_bytes() + b"0")
            self.assertTrue(visual.is_visual_analysis_stale(video.id))

    def test_visual_view_renders_fake_report(self) -> None:
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, media, visual = make_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            source = root / "static.mp4"
            ffmpeg_path = Path(r"C:\Tools\ffmpeg\bin") / "ffmpeg.exe"
            if not ffmpeg_path.exists():
                self.skipTest("ffmpeg no disponible")
            generate_video(str(ffmpeg_path), source, variant="static")
            video = catalog.register_video(project_id=project.id, file_path=str(source), title="Estatico")
            media.inspect_video(video.id)

            class _FakeVisualService:
                def analyze_visuals(self, *args, **kwargs):
                    return self.get_visual_analysis(*args, **kwargs)

                def get_visual_analysis(self, *args, **kwargs):
                    return SimpleNamespace(
                        status=SimpleNamespace(value="completed"),
                        is_stale=False,
                        analysis=SimpleNamespace(
                            detected_cut_count=1,
                            detected_scene_count=1,
                            keyframe_count=1,
                            average_motion=0.1,
                            peak_motion=0.2,
                            average_brightness=0.5,
                            average_contrast=0.2,
                            static_segment_count=1,
                            black_frame_event_count=0,
                            freeze_event_count=0,
                            duration_seconds=2.0,
                            sampled_frame_count=4,
                            brightness_variation=0.1,
                            source_file_size_bytes=1,
                            started_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
                            completed_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
                            analyzer_version="v1",
                        ),
                        windows=(
                            SimpleNamespace(
                                window_index=0,
                                start_seconds=0.0,
                                end_seconds=1.0,
                                activity_label=SimpleNamespace(value="static"),
                                is_speech=False,
                                normalized_energy=0.1,
                                motion_score=0.1,
                                brightness=0.5,
                                contrast=0.2,
                                saturation=0.1,
                                color_change_score=0.1,
                                pause_duration_seconds=0.0,
                            ),
                        ),
                        scenes=(
                            SimpleNamespace(
                                scene_index=0,
                                start_seconds=0.0,
                                end_seconds=2.0,
                                duration_seconds=2.0,
                                representative_keyframe_path="cache/videos/fake.png",
                                cut_in_score=0.4,
                                average_motion=0.1,
                                average_brightness=0.5,
                                average_contrast=0.2,
                            ),
                        ),
                        events=(),
                        warnings=(),
                        errors=(),
                    )

                def get_visual_timeline(self, *args, **kwargs):
                    return self.get_visual_analysis(*args, **kwargs).windows

                def list_visual_scenes(self, *args, **kwargs):
                    return self.get_visual_analysis(*args, **kwargs).scenes

                def list_visual_events(self, *args, **kwargs):
                    return ()

                def is_visual_analysis_stale(self, *args, **kwargs):
                    return False

                def delete_visual_analysis(self, *args, **kwargs):
                    return False

                def export_visual_analysis(self, *args, **kwargs):
                    return SimpleNamespace(path=str(root / "visual.json"))

            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=media,
                audio_service=SimpleNamespace(
                    get_prepared_audio=lambda *args, **kwargs: None,
                    is_prepared_audio_stale=lambda *args, **kwargs: False,
                    prepare_audio=lambda *args, **kwargs: None,
                    verify_prepared_audio=lambda *args, **kwargs: None,
                    clear_prepared_audio_cache=lambda *args, **kwargs: None,
                ),
                transcription_service=SimpleNamespace(
                    get_transcription=lambda *args, **kwargs: SimpleNamespace(
                        status=SimpleNamespace(value="not_transcribed"),
                        is_stale=False,
                        transcription=None,
                        segments=(),
                        backend=None,
                        model_status=None,
                        warnings=(),
                        errors=(),
                        progress_message=None,
                    )
                ),
                acoustic_service=SimpleNamespace(
                    get_acoustic_analysis=lambda *args, **kwargs: SimpleNamespace(
                        status=SimpleNamespace(value="not_analyzed"),
                        is_stale=False,
                        analysis=None,
                        windows=(),
                        events=(),
                        warnings=(),
                        errors=(),
                        progress_message=None,
                    )
                ),
                visual_service=_FakeVisualService(),
                diagnostic=SimpleNamespace(gpu_devices=()),
                settings=settings,
                paths=paths,
            )
            workspace.select_video(video.id)
            view = VisualAnalysisView(workspace)
            view.refresh()
            labels = {view.scene_table.horizontalHeaderItem(i).text() for i in range(view.scene_table.columnCount())}
            self.assertIn("#", labels)
            self.assertEqual(view.status_label.text(), "Estado: completed")
