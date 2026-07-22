from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.bootstrap import (
    BootstrapContext,
    ServiceContext,
    run as bootstrap_run,
)
from creator_intelligence_studio.application.services.catalog_service import (
    build_catalog_service,
)
from creator_intelligence_studio.domain.errors import ConflictError, ValidationError
from creator_intelligence_studio.domain.projects.entities import ProjectStatus
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    DiagnosticState,
    EnvironmentDiagnostic,
)
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
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


def make_diagnostic(root: Path, *, basic_mode: bool = True) -> EnvironmentDiagnostic:
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
        nvidia_smi_available=False,
        preferred_compute_backend="cuda",
        state=DiagnosticState(
            ready_for_basic_mode=basic_mode,
            cuda_driver_detected=False,
            cuda_runtime_not_verified=True,
            warnings=("CUDA no verificada",),
        ),
        warnings=("CUDA no verificada",),
        errors=(),
    )


def make_service(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    service = build_catalog_service(settings, paths, logger=logging.getLogger("test"))
    return service, settings, paths


def make_media_service():
    tool = SimpleNamespace(path="C:/Tools/ffmpeg/bin/ffprobe.exe", version="ffprobe version", available=True, error_message=None)
    other_tool = SimpleNamespace(path="C:/Tools/ffmpeg/bin/ffmpeg.exe", version="ffmpeg version", available=True, error_message=None)
    report = SimpleNamespace(ffmpeg=other_tool, ffprobe=tool, warnings=(), available=True)

    class _FakeMediaService:
        def verify_media_tools(self):
            return report

        def get_video_inspection(self, video_id: str):
            return None

        def inspect_video(self, video_id: str, force: bool = False):
            raise AssertionError("No se esperaba inspeccion en esta prueba.")

        def is_inspection_stale(self, video_id: str) -> bool:
            return False

    return _FakeMediaService()


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


class CatalogServiceTests(unittest.TestCase):
    def test_migration_initial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            db = build_database(settings, paths)
            with db.connect() as connection:
                run_migrations(connection)
                versions = connection.execute(
                    "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
                ).fetchall()
            self.assertEqual(len(versions), 6)
            self.assertEqual(versions[0]["version"], 1)
            self.assertEqual(versions[1]["version"], 2)
            self.assertEqual(versions[2]["version"], 3)
            self.assertEqual(versions[3]["version"], 4)
            self.assertEqual(versions[4]["version"], 5)
            self.assertEqual(versions[5]["version"], 6)
            self.assertEqual(versions[0]["name"], "initial_schema")

    def test_migrations_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            db = build_database(settings, paths)
            with db.connect() as connection:
                run_migrations(connection)
                run_migrations(connection)
                count = connection.execute(
                    "SELECT COUNT(*) FROM schema_migrations"
                ).fetchone()[0]
            self.assertEqual(count, 6)

    def test_foreign_keys_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            db = build_database(settings, paths)
            with db.connect() as connection:
                value = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            self.assertEqual(value, 1)

    def test_create_creator_and_auto_slug(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Heybermu")
            self.assertEqual(creator.slug, "heybermu")
            self.assertEqual(creator.display_name, "Heybermu")

    def test_reject_duplicate_slug(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            service.create_creator(display_name="Uno", slug="uno")
            with self.assertRaises(ConflictError):
                service.create_creator(display_name="Dos", slug="uno")

    def test_archive_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Uno")
            archived = service.archive_creator(creator.id)
            self.assertEqual(archived.status.value, "archived")
            self.assertEqual(service.get_creator(creator.id).status.value, "archived")

    def test_create_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            self.assertEqual(project.creator_id, creator.id)
            self.assertEqual(project.status.value, "active")

    def test_reject_project_for_archived_creator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Uno")
            service.archive_creator(creator.id)
            with self.assertRaises(ConflictError):
                service.create_project(
                    creator_reference=creator.id,
                    name="Video principal",
                    project_type="long_form",
                )

    def test_archive_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            archived = service.archive_project(project.id)
            self.assertEqual(archived.status, ProjectStatus.ARCHIVED)

    def test_register_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = service.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )
            self.assertTrue(video.file_available)
            self.assertEqual(video.extension, ".mp4")

    def test_reject_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, _, _ = make_service(Path(temp_dir))
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            with self.assertRaises(ValidationError):
                service.register_video(
                    project_id=project.id,
                    file_path=str(Path(temp_dir) / "missing.mp4"),
                    title="Titulo provisional",
                )

    def test_reject_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            folder = root / "folder.mp4"
            folder.mkdir()
            with self.assertRaises(ValidationError):
                service.register_video(
                    project_id=project.id,
                    file_path=str(folder),
                    title="Titulo provisional",
                )

    def test_reject_invalid_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.txt"
            sample.write_bytes(b"not-video")
            with self.assertRaises(ValidationError):
                service.register_video(
                    project_id=project.id,
                    file_path=str(sample),
                    title="Titulo provisional",
                )

    def test_reject_video_in_archived_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            service.archive_project(project.id)
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            with self.assertRaises(ConflictError):
                service.register_video(
                    project_id=project.id,
                    file_path=str(sample),
                    title="Titulo provisional",
                )

    def test_list_videos_by_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            registered = service.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )
            videos = service.list_videos(project.id)
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0].id, registered.id)
            self.assertTrue(videos[0].file_available)
            self.assertTrue(service.get_video(registered.id).file_available)

    def test_verify_available_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = service.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )
            report = service.verify_video_availability(video.id)
            self.assertEqual(report.status, "available")
            self.assertFalse(report.metadata_changed)

    def test_detect_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = service.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )
            sample.unlink()
            report = service.verify_video_availability(video.id)
            self.assertEqual(report.status, "missing")
            self.assertFalse(report.metadata_changed)

    def test_detect_metadata_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator = service.create_creator(display_name="Uno")
            project = service.create_project(
                creator_reference=creator.id,
                name="Video principal",
                project_type="long_form",
            )
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = service.register_video(
                project_id=project.id,
                file_path=str(sample),
                title="Titulo provisional",
            )
            sample.write_bytes(b"video-bytes-updated")
            report = service.verify_video_availability(video.id)
            self.assertEqual(report.status, "available")
            self.assertTrue(report.metadata_changed)

    def test_isolation_between_creators(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, _, _ = make_service(root)
            creator_one = service.create_creator(display_name="Uno")
            creator_two = service.create_creator(display_name="Dos")
            project_one = service.create_project(
                creator_reference=creator_one.id,
                name="Proyecto 1",
                project_type="long_form",
            )
            project_two = service.create_project(
                creator_reference=creator_two.id,
                name="Proyecto 2",
                project_type="long_form",
            )
            sample_one = root / "sample1.mp4"
            sample_two = root / "sample2.mp4"
            sample_one.write_bytes(b"video-one")
            sample_two.write_bytes(b"video-two")
            service.register_video(
                project_id=project_one.id,
                file_path=str(sample_one),
                title="Video 1",
            )
            service.register_video(
                project_id=project_two.id,
                file_path=str(sample_two),
                title="Video 2",
            )
            self.assertEqual(len(service.list_projects(creator_one.id)), 1)
            self.assertEqual(len(service.list_projects(creator_two.id)), 1)
            self.assertEqual(len(service.list_videos(project_one.id)), 1)
            self.assertEqual(len(service.list_videos(project_two.id)), 1)

    def test_cli_basic_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            service = build_catalog_service(settings, paths, logger=logging.getLogger("test"))
            diagnostic = make_diagnostic(root)
            context = ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
                service=service,
                media_service=make_media_service(),
                audio_service=make_audio_service(),
                transcription_service=make_transcription_service(),
                acoustic_service=make_acoustic_service(),
                visual_service=make_visual_service(),
            )
            bootstrap_context = BootstrapContext(
                settings=settings,
                paths=paths,
                diagnostic=diagnostic,
                logger=logging.getLogger("test"),
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch(
                "creator_intelligence_studio.application.bootstrap._load_context",
                return_value=bootstrap_context,
            ):
                code = bootstrap_run(argv=["--diagnostic-json"], stdout=stdout, stderr=stderr)
            self.assertEqual(code, 0)
            json.loads(stdout.getvalue())

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=context,
            ):
                code = bootstrap_run(
                    argv=["creator", "create", "--name", "Prueba"],
                    stdout=stdout,
                    stderr=stderr,
                )
            self.assertEqual(code, 0)
            self.assertIn("Creador creado correctamente", stdout.getvalue())
