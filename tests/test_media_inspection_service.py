from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.bootstrap import BootstrapContext, ServiceContext, run as bootstrap_run
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
    build_media_inspection_service,
)
from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.media.value_objects import FractionValue, MediaToolInfo
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.media.ffmpeg_client import ThumbnailResult
from creator_intelligence_studio.infrastructure.media.parsers import parse_ffprobe_json, parse_ffprobe_streams
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import (
    ensure_schema_migrations_table,
    migration_1,
    run_migrations,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_inspection_repository import (
    SQLiteVideoInspectionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ffprobe"


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


def make_media_tools_report(*, ffprobe_available: bool = True, ffmpeg_available: bool = True) -> MediaToolsReport:
    ffprobe = MediaToolInfo(
        name="ffprobe",
        path="ffprobe.exe" if ffprobe_available else None,
        version="ffprobe version 8.1.2" if ffprobe_available else None,
        available=ffprobe_available,
        error_message=None if ffprobe_available else "ffprobe no disponible",
    )
    ffmpeg = MediaToolInfo(
        name="ffmpeg",
        path="ffmpeg.exe" if ffmpeg_available else None,
        version="ffmpeg version 8.1.2" if ffmpeg_available else None,
        available=ffmpeg_available,
        error_message=None if ffmpeg_available else "ffmpeg no disponible",
    )
    return MediaToolsReport(ffmpeg=ffmpeg, ffprobe=ffprobe, warnings=())


def make_service(root: Path) -> tuple[object, MediaInspectionService, ProjectPaths]:
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
    return catalog, media, paths


def make_audio_service():
    class _FakeAudioService:
        def prepare_audio(self, video_id: str, force: bool = False):
            return SimpleNamespace(status=SimpleNamespace(value="not_prepared"), is_stale=False)

        def get_prepared_audio(self, video_id: str):
            return None

        def is_prepared_audio_stale(self, video_id: str) -> bool:
            return False

        def verify_prepared_audio(self, video_id: str):
            return SimpleNamespace(status=SimpleNamespace(value="not_prepared"), is_stale=False)

        def delete_prepared_audio_cache(self, video_id: str):
            return SimpleNamespace(deleted_record=False, deleted_files=())

    return _FakeAudioService()


def make_transcription_service():
    report = SimpleNamespace(
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
    backend = SimpleNamespace(available=False, backend="cpu", device_count=0, supported_compute_types=(), to_dict=lambda: {})
    model = SimpleNamespace(model_name="small", installed=False, to_dict=lambda: {"model_name": "small"})
    verification = SimpleNamespace(
        backend=backend,
        model_statuses=(model,),
        notes=(),
        to_dict=lambda: {"backend": backend.to_dict(), "model_statuses": [model.to_dict()], "notes": []},
    )
    return SimpleNamespace(
        verify_transcription_backend=lambda: verification,
        list_models=lambda: (model,),
        get_model_status=lambda model_name: model,
        verify_model=lambda model_name: model,
        download_model=lambda model_name, **kwargs: model,
        remove_model=lambda model_name: False,
        transcribe_video=lambda *args, **kwargs: report,
        get_transcription=lambda *args, **kwargs: report,
        is_transcription_stale=lambda *args, **kwargs: False,
        cancel_transcription=lambda *args, **kwargs: False,
        delete_transcription=lambda *args, **kwargs: False,
        export_transcription=lambda *args, **kwargs: SimpleNamespace(path="cache/transcriptions/video/transcription.txt", to_dict=lambda: {}),
    )


def make_acoustic_service():
    report = SimpleNamespace(
        status=SimpleNamespace(value="not_analyzed"),
        is_stale=False,
        analysis=None,
        windows=(),
        events=(),
        warnings=(),
        errors=(),
        progress_message=None,
    )
    return SimpleNamespace(
        analyze_acoustics=lambda *args, **kwargs: report,
        get_acoustic_analysis=lambda *args, **kwargs: report,
        get_acoustic_timeline=lambda *args, **kwargs: (),
        list_acoustic_events=lambda *args, **kwargs: (),
        is_acoustic_analysis_stale=lambda *args, **kwargs: False,
        delete_acoustic_analysis=lambda *args, **kwargs: False,
        export_acoustic_analysis=lambda *args, **kwargs: SimpleNamespace(path="cache/acoustic/video/acoustic_analysis.json", to_dict=lambda: {}),
    )


def make_visual_service():
    report = SimpleNamespace(
        status=SimpleNamespace(value="not_analyzed"),
        is_stale=False,
        analysis=None,
        windows=(),
        scenes=(),
        events=(),
        warnings=(),
        errors=(),
        progress_message=None,
    )
    return SimpleNamespace(
        analyze_visuals=lambda *args, **kwargs: report,
        get_visual_analysis=lambda *args, **kwargs: report,
        get_visual_timeline=lambda *args, **kwargs: (),
        list_visual_scenes=lambda *args, **kwargs: (),
        list_visual_events=lambda *args, **kwargs: (),
        is_visual_analysis_stale=lambda *args, **kwargs: False,
        delete_visual_analysis=lambda *args, **kwargs: False,
        export_visual_analysis=lambda *args, **kwargs: SimpleNamespace(path="cache/visual/video/visual_analysis.json", to_dict=lambda: {}),
    )


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


class FFprobeParserTests(unittest.TestCase):
    def test_parse_video_with_audio_and_rotation(self) -> None:
        summary = parse_ffprobe_json(load_fixture("video_with_audio.json"))
        streams = parse_ffprobe_streams(load_fixture("video_with_audio.json"))
        self.assertEqual(summary.video_stream_count, 1)
        self.assertEqual(summary.audio_stream_count, 1)
        self.assertEqual(summary.width, 1920)
        self.assertEqual(summary.height, 1080)
        self.assertEqual(summary.rotation_degrees, 90)
        self.assertEqual(summary.frame_rate, FractionValue(30000, 1001))
        self.assertEqual(summary.average_frame_rate, FractionValue(30000, 1001))
        self.assertEqual(len(streams), 2)

    def test_parse_video_without_audio(self) -> None:
        summary = parse_ffprobe_json(load_fixture("video_only.json"))
        self.assertEqual(summary.video_stream_count, 1)
        self.assertEqual(summary.audio_stream_count, 0)
        self.assertEqual(summary.width, 1280)
        self.assertEqual(summary.height, 720)

    def test_parse_audio_without_video(self) -> None:
        summary = parse_ffprobe_json(load_fixture("audio_only.json"))
        self.assertEqual(summary.video_stream_count, 0)
        self.assertEqual(summary.audio_stream_count, 1)
        self.assertIsNone(summary.width)
        self.assertIsNone(summary.height)

    def test_parse_missing_fields(self) -> None:
        summary = parse_ffprobe_json({"format": {}, "streams": [{}]})
        self.assertEqual(summary.stream_count, 1)
        self.assertIsNone(summary.video_codec)
        self.assertIsNone(summary.duration_seconds)

    def test_parse_invalid_json_raises(self) -> None:
        with self.assertRaises(json.JSONDecodeError):
            parse_ffprobe_json("{invalid json")


class MediaToolLocatorTests(unittest.TestCase):
    def test_configured_paths_take_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "custom" / "ffmpeg" / "bin"
            config_dir.mkdir(parents=True, exist_ok=True)
            ffmpeg_path = config_dir / "ffmpeg.exe"
            ffprobe_path = config_dir / "ffprobe.exe"
            ffmpeg_path.write_text("ffmpeg", encoding="utf-8")
            ffprobe_path.write_text("ffprobe", encoding="utf-8")
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
                database_filename="creator_intelligence_studio.db",
                database_timeout_seconds=5.0,
                ffmpeg_path=str(ffmpeg_path),
                ffprobe_path=str(ffprobe_path),
                ffmpeg_bin_directory=None,
            )
            locator = MediaToolLocator(settings=settings, project_root=root, env={})
            with patch.object(locator, "_probe_version", return_value=("version", None)) as mock_probe, patch(
                "shutil.which",
                return_value=None,
            ):
                tools = locator.discover()
            self.assertEqual(tools.ffmpeg.path, str(ffmpeg_path))
            self.assertEqual(tools.ffprobe.path, str(ffprobe_path))
            self.assertEqual(mock_probe.call_count, 2)

    def test_portable_directory_is_used_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            portable_dir = root / "tools" / "ffmpeg" / "bin"
            portable_dir.mkdir(parents=True, exist_ok=True)
            (portable_dir / "ffmpeg.exe").write_text("ffmpeg", encoding="utf-8")
            (portable_dir / "ffprobe.exe").write_text("ffprobe", encoding="utf-8")
            locator = MediaToolLocator(project_root=root, env={})
            with patch.object(locator, "_probe_version", return_value=("version", None)), patch(
                "shutil.which",
                return_value=None,
            ):
                tools = locator.discover()
            self.assertEqual(tools.ffmpeg.path, str(portable_dir / "ffmpeg.exe"))
            self.assertEqual(tools.ffprobe.path, str(portable_dir / "ffprobe.exe"))


class MediaInspectionServiceTests(unittest.TestCase):
    def test_migration_v1_to_v2(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            db = build_database(settings, paths)
            with db.connect() as connection:
                ensure_schema_migrations_table(connection)
                migration_1(connection)
                connection.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (1, 'initial_schema', '2026-07-22T00:00:00Z')"
                )
                run_migrations(connection)
                versions = connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='video_inspections'"
                ).fetchall()
            self.assertEqual([row["version"] for row in versions], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
            self.assertEqual(len(tables), 1)

    def test_inspect_video_reuses_cache_and_force_reinspect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, media, _ = make_service(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            fake_payload = load_fixture("video_with_audio.json")
            fake_result = SimpleNamespace(raw_json=json.dumps(fake_payload), payload=fake_payload)
            fake_thumbnail = root / "cache" / "videos" / video.id / "thumbnails" / "thumbnail-v1.jpg"
            fake_thumbnail.parent.mkdir(parents=True, exist_ok=True)
            fake_thumbnail.write_bytes(b"thumb")

            with patch.object(media, "verify_media_tools", return_value=make_media_tools_report()), patch(
                "creator_intelligence_studio.application.services.media_inspection_service.FFprobeClient"
            ) as mock_ffprobe, patch(
                "creator_intelligence_studio.application.services.media_inspection_service.generate_initial_thumbnail",
                return_value=ThumbnailResult(path=fake_thumbnail, timestamp_seconds=1.0),
            ) as mock_thumbnail:
                mock_ffprobe.return_value.inspect.return_value = fake_result
                first = media.inspect_video(video.id)
                second = media.inspect_video(video.id)
                self.assertEqual(first.status, VideoInspectionStatus.COMPLETED)
                self.assertEqual(second.status, VideoInspectionStatus.COMPLETED)
                self.assertEqual(mock_ffprobe.return_value.inspect.call_count, 1)
                self.assertEqual(mock_thumbnail.call_count, 1)

            sample.write_bytes(b"video-bytes-updated")
            stale = media.get_video_inspection(video.id)
            self.assertIsNotNone(stale)
            self.assertTrue(stale.is_stale)

            with patch.object(media, "verify_media_tools", return_value=make_media_tools_report()), patch(
                "creator_intelligence_studio.application.services.media_inspection_service.FFprobeClient"
            ) as mock_ffprobe, patch(
                "creator_intelligence_studio.application.services.media_inspection_service.generate_initial_thumbnail",
                return_value=ThumbnailResult(path=fake_thumbnail, timestamp_seconds=1.0),
            ):
                mock_ffprobe.return_value.inspect.return_value = fake_result
                forced = media.inspect_video(video.id, force=True)
                self.assertEqual(forced.status, VideoInspectionStatus.COMPLETED)
                self.assertFalse(forced.is_stale)

    def test_file_missing_and_tool_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, media, _ = make_service(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            sample.unlink()
            with patch.object(media, "verify_media_tools", return_value=make_media_tools_report()):
                report = media.inspect_video(video.id)
            self.assertEqual(report.status, VideoInspectionStatus.FILE_MISSING)

            sample.write_bytes(b"video-bytes")
            with patch.object(media, "verify_media_tools", return_value=make_media_tools_report(ffprobe_available=False)):
                report = media.inspect_video(video.id, force=True)
            self.assertEqual(report.status, VideoInspectionStatus.TOOL_UNAVAILABLE)

    def test_generate_initial_thumbnail_requires_existing_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, media, _ = make_service(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            fake_payload = load_fixture("video_only.json")
            fake_result = SimpleNamespace(raw_json=json.dumps(fake_payload), payload=fake_payload)
            thumbnail_path = root / "cache" / "videos" / video.id / "thumbnails" / "thumbnail-v1.jpg"
            with patch.object(media, "verify_media_tools", return_value=make_media_tools_report()), patch(
                "creator_intelligence_studio.application.services.media_inspection_service.FFprobeClient"
            ) as mock_ffprobe, patch(
                "creator_intelligence_studio.application.services.media_inspection_service.generate_initial_thumbnail",
                return_value=ThumbnailResult(path=thumbnail_path, timestamp_seconds=1.0),
            ):
                mock_ffprobe.return_value.inspect.return_value = fake_result
                media.inspect_video(video.id)
                path = media.generate_initial_thumbnail(video.id)
            self.assertTrue(path.endswith("thumbnail-v1.jpg"))

    def test_real_integration_if_tools_available(self) -> None:
        ffmpeg_found = shutil.which("ffmpeg")
        ffprobe_found = shutil.which("ffprobe")
        if not (ffmpeg_found and ffprobe_found):
            self.skipTest("ffmpeg/ffprobe no estan disponibles en PATH.")
        ffmpeg_path = Path(ffmpeg_found)
        ffprobe_path = Path(ffprobe_found)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, media, _ = make_service(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            import subprocess

            subprocess.run(
                [
                    str(ffmpeg_path),
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=320x180:rate=25:duration=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:duration=1",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(sample),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            report = media.inspect_video(
                catalog.register_video(project_id=project.id, file_path=str(sample), title="Video").id,
                force=True,
            )
            self.assertEqual(report.status, VideoInspectionStatus.COMPLETED)
            self.assertTrue(report.file_available)
            self.assertIsNotNone(report.thumbnail_path)


class MediaCliTests(unittest.TestCase):
    def test_media_tools_cli_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            diagnostic = SimpleNamespace(
                application_name="Creator Intelligence Studio",
                application_version="0.1.0",
                project_root=root,
                os_name="Windows",
                os_version="10",
                os_architecture="64bit",
                python_version="3.11.9",
                python_executable="python.exe",
                cpu_reported="CPU",
                logical_processors=12,
                nvidia_smi_available=False,
                gpu_devices=(),
                nvidia_driver_version=None,
                cuda_version_reported=None,
                git_available=True,
                git_version="git version 2.54.0",
                free_space_bytes=123,
                preferred_compute_backend="cuda",
                state=SimpleNamespace(ready_for_basic_mode=True, cuda_driver_detected=False, cuda_runtime_not_verified=True, warnings=()),
                warnings=(),
                errors=(),
                to_json=lambda: "{}",
            )
            service = SimpleNamespace()
            media_service = SimpleNamespace(verify_media_tools=lambda: make_media_tools_report())
            context = ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=service,
                media_service=media_service,
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=context,
            ):
                code = bootstrap_run(argv=["media", "tools", "--json"], stdout=stdout, stderr=stderr)
            self.assertEqual(code, 0)
            json.loads(stdout.getvalue())
