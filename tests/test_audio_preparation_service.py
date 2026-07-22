from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
import wave
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.bootstrap import ServiceContext, run as bootstrap_run
from creator_intelligence_studio.application.services.audio_preparation_service import (
    AudioPreparationService,
    PreparedAudioReport,
)
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.domain.audio.entities import PreparedAudioStatus
from creator_intelligence_studio.domain.audio.services import build_audio_candidates, select_audio_stream
from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.media.value_objects import FractionValue, MediaStreamInfo
from creator_intelligence_studio.infrastructure.audio.ffmpeg_audio_extractor import FFmpegAudioExtractionResult
from creator_intelligence_studio.infrastructure.audio.wav_inspector import inspect_wav_file
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import DiagnosticState, EnvironmentDiagnostic
from creator_intelligence_studio.infrastructure.media.ffmpeg_client import ThumbnailResult
from creator_intelligence_studio.infrastructure.media.parsers import parse_ffprobe_json, parse_ffprobe_streams
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import (
    SQLitePreparedAudioRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_inspection_repository import (
    SQLiteVideoInspectionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.presentation.desktop.view_models.models import VideoFiltersViewModel
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
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
        ffmpeg_path=None,
        ffprobe_path=None,
        ffmpeg_bin_directory=None,
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
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
        nvidia_smi_available=False,
        preferred_compute_backend="cuda",
        state=DiagnosticState(
            ready_for_basic_mode=True,
            cuda_driver_detected=False,
            cuda_runtime_not_verified=True,
            warnings=("CUDA no verificada",),
        ),
        warnings=("CUDA no verificada",),
        errors=(),
    )


def make_catalog_and_media(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    return catalog, settings, paths, database


def make_inspection_report(video, *, metadata_json: dict[str, object], stale: bool = False):
    return SimpleNamespace(
        video=video,
        status=VideoInspectionStatus.COMPLETED,
        is_stale=stale,
        file_available=True,
        inspection=SimpleNamespace(
            id="inspection-1",
            metadata_json=json.dumps(metadata_json),
            inspected_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
        ),
        summary=None,
        thumbnail_path=None,
        warnings=(),
        errors=(),
    )


def make_audio_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    database,
    inspection_service,
    ffmpeg_available: bool = True,
):
    tool_locator = SimpleNamespace(
        locate=lambda name: SimpleNamespace(
            available=ffmpeg_available,
            path=str(paths.project_root / "tools" / "ffmpeg.exe") if ffmpeg_available else None,
            version="ffmpeg version 8.1.2" if ffmpeg_available else None,
            error_message=None if ffmpeg_available else "ffmpeg no disponible",
        )
    )
    return AudioPreparationService(
        settings=settings,
        paths=paths,
        video_repository=SQLiteVideoRepository(database),
        inspection_service=inspection_service,
        audio_repository=SQLitePreparedAudioRepository(database),
        logger=logging.getLogger("test"),
        tool_locator=tool_locator,
    )


def persist_inspection(database, video, inspection_id: str, metadata_json: dict[str, object]) -> None:
    repository = SQLiteVideoInspectionRepository(database)
    inspection = VideoInspection(
        id=inspection_id,
        video_asset_id=video.id,
        inspection_status=VideoInspectionStatus.COMPLETED,
        inspected_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
        source_file_size_bytes=video.file_size_bytes,
        source_file_modified_at=video.file_modified_at,
        duration_seconds=None,
        format_name=None,
        format_long_name=None,
        overall_bitrate=None,
        stream_count=1,
        video_stream_count=1,
        audio_stream_count=1,
        subtitle_stream_count=0,
        width=None,
        height=None,
        display_aspect_ratio=None,
        pixel_aspect_ratio=None,
        frame_rate_numerator=None,
        frame_rate_denominator=None,
        average_frame_rate_numerator=None,
        average_frame_rate_denominator=None,
        video_codec=None,
        video_codec_profile=None,
        pixel_format=None,
        video_bitrate=None,
        audio_codec=None,
        audio_sample_rate=None,
        audio_channels=None,
        audio_channel_layout=None,
        audio_bitrate=None,
        rotation_degrees=None,
        metadata_json=json.dumps(metadata_json),
        ffprobe_version="ffprobe version 8.1.2",
        ffprobe_path="ffprobe.exe",
        ffmpeg_version="ffmpeg version 8.1.2",
        ffmpeg_path="ffmpeg.exe",
        thumbnail_relative_path=None,
        error_code=None,
        error_message=None,
        created_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
    )
    repository.upsert(inspection)


class FakeExtractor:
    def __init__(self) -> None:
        self.calls = 0

    def extract(
        self,
        *,
        source_path: Path,
        selected_stream_index: int,
        destination_path: Path,
        sample_rate_hz: int,
        channels: int = 1,
    ) -> FFmpegAudioExtractionResult:
        self.calls += 1
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate_hz)
            wav_file.writeframes(b"\x00\x00" * (sample_rate_hz * channels // 10))
        return FFmpegAudioExtractionResult(path=destination_path, stderr=None)


class AudioPreparationDomainTests(unittest.TestCase):
    def test_select_audio_stream_policy(self) -> None:
        candidates = [
            SimpleNamespace(index=1, channels=1, sample_rate_hz=16000, language="es", is_default=False),
            SimpleNamespace(index=2, channels=2, sample_rate_hz=48000, language="en", is_default=True),
            SimpleNamespace(index=3, channels=6, sample_rate_hz=44100, language="fr", is_default=False),
        ]
        selected = select_audio_stream(candidates, preferred_language="fr")
        self.assertEqual(selected.index, 3)
        selected = select_audio_stream(candidates)
        self.assertEqual(selected.index, 2)
        selected = select_audio_stream(candidates, preferred_language="de")
        self.assertEqual(selected.index, 2)

    def test_wav_inspection_valid_and_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wav_path = root / "sample.wav"
            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 1600)
            result = inspect_wav_file(wav_path)
            self.assertTrue(result.valid)
            self.assertEqual(result.sample_rate_hz, 16000)
            self.assertEqual(result.channels, 1)
            self.assertEqual(result.bit_depth, 16)

            bad_path = root / "bad.wav"
            bad_path.write_bytes(b"not-a-wav")
            with self.assertRaises(Exception):
                inspect_wav_file(bad_path)


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


class AudioPreparationServiceTests(unittest.TestCase):
    def test_prepare_audio_completed_reuses_cache_and_force_reextracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, settings, paths, database = make_catalog_and_media(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            metadata = {
                "streams": [
                    {"index": 0, "codec_type": "video"},
                    {"index": 1, "codec_type": "audio", "disposition": {"default": 1}, "tags": {"language": "es"}},
                ]
            }
            inspection_report = make_inspection_report(video, metadata_json=metadata)

            class _FakeInspectionService:
                def get_video_inspection(self, video_id: str):
                    return inspection_report

            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=SimpleNamespace(
                    locate=lambda name: SimpleNamespace(
                        available=True,
                        path=str(paths.project_root / "tools" / "ffmpeg.exe"),
                        version="ffmpeg version 8.1.2",
                        error_message=None,
                    )
        ),
    )


            persist_inspection(database, video, "inspection-1", metadata)
            extractor = FakeExtractor()
            with patch(
                "creator_intelligence_studio.application.services.audio_preparation_service.FFmpegAudioExtractor",
                return_value=extractor,
            ):
                report = service.prepare_audio(video.id)
                self.assertEqual(report.status, PreparedAudioStatus.COMPLETED)
                self.assertFalse(report.is_stale)
                self.assertIsNotNone(report.wav_validation)
                self.assertTrue(report.wav_validation.valid)
                second = service.prepare_audio(video.id)
                self.assertEqual(second.status, PreparedAudioStatus.COMPLETED)
                forced = service.prepare_audio(video.id, force=True)
                self.assertEqual(forced.status, PreparedAudioStatus.COMPLETED)
            self.assertEqual(extractor.calls, 2)

    def test_prepare_audio_reports_no_audio_and_tool_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, settings, paths, database = make_catalog_and_media(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            class _FakeInspectionService:
                def get_video_inspection(self, video_id: str):
                    return make_inspection_report(video, metadata_json={"streams": [{"index": 0, "codec_type": "video"}]})

            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=SimpleNamespace(
                    locate=lambda name: SimpleNamespace(
                        available=True,
                        path=str(paths.project_root / "tools" / "ffmpeg.exe"),
                        version="ffmpeg version 8.1.2",
                        error_message=None,
                    )
                ),
            )
            persist_inspection(database, video, "inspection-1", {"streams": [{"index": 0, "codec_type": "video"}]})
            no_audio = service.prepare_audio(video.id)
            self.assertEqual(no_audio.status, PreparedAudioStatus.NO_AUDIO_STREAM)

            class _UnavailableLocator:
                def locate(self, name: str):
                    return SimpleNamespace(available=False, path=None, version=None, error_message="ffmpeg no disponible")

            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=_UnavailableLocator(),
            )
            with patch.object(service, "_load_audio_streams", return_value=[SimpleNamespace(index=1, channels=2, sample_rate_hz=48000, language=None, is_default=True)]):
                unavailable = service.prepare_audio(video.id)
            self.assertEqual(unavailable.status, PreparedAudioStatus.TOOL_UNAVAILABLE)

    def test_stale_detection_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, settings, paths, database = make_catalog_and_media(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            inspection_report = make_inspection_report(
                video,
                metadata_json={"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]},
            )

            class _FakeInspectionService:
                def get_video_inspection(self, video_id: str):
                    return inspection_report

            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=SimpleNamespace(
                    locate=lambda name: SimpleNamespace(
                        available=True,
                        path=str(paths.project_root / "tools" / "ffmpeg.exe"),
                        version="ffmpeg version 8.1.2",
                        error_message=None,
                    )
                ),
            )
            persist_inspection(database, video, "inspection-1", {"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]})
            extractor = FakeExtractor()
            with patch(
                "creator_intelligence_studio.application.services.audio_preparation_service.FFmpegAudioExtractor",
                return_value=extractor,
            ):
                report = service.prepare_audio(video.id)
            sample.write_bytes(b"video-bytes-updated")
            self.assertTrue(service.is_prepared_audio_stale(video.id))
            stale_report = service.verify_prepared_audio(video.id)
            self.assertTrue(stale_report.is_stale)
            metadata_path = Path(report.metadata_path)
            metadata_path.unlink()
            incomplete = service.get_prepared_audio(video.id)
            self.assertEqual(incomplete.status, PreparedAudioStatus.FILE_MISSING)
            deleted = service.delete_prepared_audio_cache(video.id)
            self.assertTrue(deleted.deleted_record)
            self.assertTrue(deleted.deleted_files)
            self.assertIsNone(service.get_prepared_audio(video.id).prepared_audio)

    def test_invalid_audio_output_is_rejected_and_partial_files_are_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, settings, paths, database = make_catalog_and_media(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            inspection_report = make_inspection_report(
                video,
                metadata_json={"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]},
            )

            class _FakeInspectionService:
                def get_video_inspection(self, video_id: str):
                    return inspection_report

            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=SimpleNamespace(
                    locate=lambda name: SimpleNamespace(
                        available=True,
                        path=str(paths.project_root / "tools" / "ffmpeg.exe"),
                        version="ffmpeg version 8.1.2",
                        error_message=None,
                    )
                ),
            )
            inspection_report.inspection.id = "inspection-invalid"
            persist_inspection(database, video, "inspection-invalid", {"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]})

            class _BadExtractor:
                def extract(self, **kwargs):
                    destination_path = kwargs["destination_path"]
                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    destination_path.write_bytes(b"not-a-wav")
                    return FFmpegAudioExtractionResult(path=destination_path, stderr=None)

            with patch(
                "creator_intelligence_studio.application.services.audio_preparation_service.FFmpegAudioExtractor",
                return_value=_BadExtractor(),
            ):
                report = service.prepare_audio(video.id)

            self.assertEqual(report.status, PreparedAudioStatus.FAILED)
            self.assertFalse(Path(report.cache_path).exists())
            self.assertFalse(Path(report.metadata_path).exists())

    def test_audio_cli_json_and_view_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog, settings, paths, database = make_catalog_and_media(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            report = make_inspection_report(
                video,
                metadata_json={"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]},
            )

            class _FakeInspectionService:
                def get_video_inspection(self, video_id: str):
                    return report

            persist_inspection(database, video, "inspection-1", {"streams": [{"index": 1, "codec_type": "audio", "disposition": {"default": 1}}]})
            service = AudioPreparationService(
                settings=settings,
                paths=paths,
                video_repository=SQLiteVideoRepository(database),
                inspection_service=_FakeInspectionService(),
                audio_repository=SQLitePreparedAudioRepository(database),
                logger=logging.getLogger("test"),
                tool_locator=SimpleNamespace(
                    locate=lambda name: SimpleNamespace(
                        available=True,
                        path=str(paths.project_root / "tools" / "ffmpeg.exe"),
                        version="ffmpeg version 8.1.2",
                        error_message=None,
                    )
                ),
            )
            extractor = FakeExtractor()
            with patch(
                "creator_intelligence_studio.application.services.audio_preparation_service.FFmpegAudioExtractor",
                return_value=extractor,
            ):
                prepared = service.prepare_audio(video.id)
            self.assertEqual(prepared.status, PreparedAudioStatus.COMPLETED)
            self.assertIn("normalized", prepared.cache_path or "")

            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=_FakeInspectionService(),
                audio_service=service,
                transcription_service=make_transcription_service(),
                diagnostic=make_diagnostic(root),
                settings=settings,
                paths=paths,
            )
            items = workspace.video_inspector_items(video, report, prepared)
            labels = {item.label: item.value for item in items}
            self.assertEqual(labels["Audio preparado"], "Preparado")
            self.assertEqual(labels["Sample rate"], "16000 Hz")
            self.assertEqual(labels["Canales"], "1")
            self.assertIn("cache", labels["Ruta de caché"])

            stdout = io.StringIO()
            stderr = io.StringIO()
            context = ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=make_diagnostic(root),
                logger=logging.getLogger("test"),
                service=catalog,
                media_service=_FakeInspectionService(),
                audio_service=service,
                transcription_service=make_transcription_service(),
            )
            with patch(
                "creator_intelligence_studio.application.bootstrap._load_service_context",
                return_value=context,
            ):
                code = bootstrap_run(argv=["audio", "show", "--video-id", video.id, "--json"], stdout=stdout, stderr=stderr)
            self.assertEqual(code, 0)
            json.loads(stdout.getvalue())
