from __future__ import annotations

import json
import logging
import tempfile
import threading
import time
import unittest
import wave
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.transcription_service import TranscriptionService
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.transcription.entities import TranscriptionStatus
from creator_intelligence_studio.domain.transcription.errors import TranscriptionBackendError
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionBackendInfo,
    TranscriptionExportFormat,
    TranscriptionModelInfo,
    TranscriptionModelStatus,
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegmentData,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import (
    SQLitePreparedAudioRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import (
    SQLiteTranscriptionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.infrastructure.transcription.cuda_runtime_loader import discover_cuda_runtime_locations
from creator_intelligence_studio.infrastructure.transcription.faster_whisper_engine import FasterWhisperEngine
from creator_intelligence_studio.infrastructure.transcription.model_manager import TranscriptionModelManager
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
        audio_cache_version="v1",
    )


def write_wav(path: Path, *, seconds: float = 1.0, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)


class FakeBackendEngine:
    def __init__(self, *, backend_available: bool = True, cancelable: bool = False) -> None:
        self.backend_available = backend_available
        self.cancelable = cancelable
        self.released = 0

    def verify_backend(self):
        return TranscriptionBackendInfo(
            available=self.backend_available,
            device_count=1 if self.backend_available else 0,
            supported_compute_types=("int8_float16", "int8"),
            cuda_runtime_available=True,
            cudnn_available=True,
            dll_directories=("nvidia/cublas/bin", "nvidia/cudnn/bin"),
            backend="cuda" if self.backend_available else "cpu",
            fallback_reason=None if self.backend_available else "CUDA no disponible.",
            errors=(),
            version="4.8.1",
            ctranslate2_version="4.8.1",
            faster_whisper_version="1.2.1",
        )

    def transcribe(
        self,
        *,
        video_asset_id: str,
        prepared_audio_asset_id: str,
        audio_path: Path,
        audio_size_bytes: int | None,
        audio_modified_at: str | None,
        options: TranscriptionOptions,
        cancellation_token=None,
        progress_callback=None,
    ) -> TranscriptionResult:
        segments = []
        if self.cancelable:
            time.sleep(0.05)
            if cancellation_token is not None and cancellation_token.cancelled():
                raise TranscriptionBackendError("La transcripcion fue cancelada por el usuario.")
        for index, (start, end, text) in enumerate(((0.0, 1.0, "hola"), (1.0, 2.0, "mundo"))):
            if cancellation_token is not None and cancellation_token.cancelled():
                raise TranscriptionBackendError("La transcripcion fue cancelada por el usuario.")
            if progress_callback is not None:
                progress_callback(SimpleNamespace(phase="Transcribiendo", progress_ratio=end / 2.0))
            segments.append(
                TranscriptionSegmentData(
                    segment_index=index,
                    start_seconds=start,
                    end_seconds=end,
                    text=text,
                    confidence=-0.1,
                )
            )
        return TranscriptionResult(
            transcription_id=None,
            video_asset_id=video_asset_id,
            prepared_audio_asset_id=prepared_audio_asset_id,
            status=TranscriptionStatus.COMPLETED.value,
            engine="faster-whisper",
            model_name=options.model_name,
            device="cuda" if options.device != "cpu" else "cpu",
            compute_type=options.compute_type or "int8_float16",
            requested_language=options.language,
            detected_language="es",
            language_probability=0.99,
            full_text="hola mundo",
            duration_seconds=2.0,
            processing_time_seconds=0.25,
            real_time_factor=0.125,
            segment_count=len(segments),
            word_timestamps_enabled=options.word_timestamps,
            vad_enabled=options.vad_filter,
            source_audio_size_bytes=audio_size_bytes,
            source_audio_modified_at=audio_modified_at,
            source_audio_fingerprint="fingerprint",
            configuration_fingerprint="configuration",
            engine_version="1.2.1",
            model_version=options.model_name,
            segments=tuple(segments),
            warnings=(),
            errors=(),
        )

    def release_model(self) -> None:
        self.released += 1


class FakeModelManager:
    def __init__(self, models_root: Path) -> None:
        self.models_root = models_root
        self.installed_models: set[str] = set()
        self.download_calls: list[str] = []
        self.model_infos = (
            TranscriptionModelInfo("base", "fast", str(models_root / "base"), False),
            TranscriptionModelInfo("small", "balanced", str(models_root / "small"), False),
            TranscriptionModelInfo("medium", "quality", str(models_root / "medium"), False),
        )

    def list_models(self):
        return tuple(self.get_model_status(info.model_name) for info in self.model_infos)

    def get_model_status(self, model_name: str):
        info = next(info for info in self.model_infos if info.model_name == model_name)
        if model_name in self.installed_models:
            return TranscriptionModelInfo(
                info.model_name,
                info.profile,
                info.path,
                True,
                info.size_bytes,
                "Modelo disponible en caché local.",
                TranscriptionModelStatus.INSTALLED,
            )
        return TranscriptionModelInfo(
            info.model_name,
            info.profile,
            info.path,
            False,
            info.size_bytes,
            "Modelo no instalado.",
            TranscriptionModelStatus.NOT_INSTALLED,
        )

    def verify_model(self, model_name: str):
        return self.get_model_status(model_name)

    def download_model(self, model_name: str, **kwargs):
        self.download_calls.append(model_name)
        self.installed_models.add(model_name)
        return self.get_model_status(model_name)

    def remove_model(self, model_name: str) -> bool:
        removed = model_name in self.installed_models
        self.installed_models.discard(model_name)
        return removed


def build_environment(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    video_repository = SQLiteVideoRepository(database)
    prepared_audio_repository = SQLitePreparedAudioRepository(database)
    transcription_repository = SQLiteTranscriptionRepository(database)
    return settings, paths, catalog, video_repository, prepared_audio_repository, transcription_repository


class TranscriptionInfrastructureTests(unittest.TestCase):
    def test_cuda_runtime_locations_are_discoverable(self) -> None:
        locations = discover_cuda_runtime_locations()
        self.assertTrue(locations.cuda_runtime_bin is not None)
        self.assertTrue(locations.cublas_bin is not None)
        self.assertTrue(locations.cuda_nvrtc_bin is not None)
        self.assertTrue(locations.cudnn_bin is not None)

    def test_model_manager_reports_expected_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = TranscriptionModelManager(root / "models")
            models = manager.list_models()
            self.assertEqual([model.model_name for model in models], ["base", "small", "medium"])

    def test_plan_runtime_falls_back_to_cpu_when_cuda_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = TranscriptionModelManager(root / "models")
            engine = FasterWhisperEngine(manager)
            with patch.object(
                engine,
                "verify_backend",
                return_value=TranscriptionBackendInfo(
                    available=False,
                    device_count=0,
                    supported_compute_types=(),
                    cuda_runtime_available=False,
                    cudnn_available=False,
                    dll_directories=(),
                    backend="cpu",
                    fallback_reason="CUDA no disponible.",
                    errors=(),
                    version="4.8.1",
                    ctranslate2_version="4.8.1",
                    faster_whisper_version="1.2.1",
                ),
            ):
                plan = engine.plan_runtime(
                    TranscriptionOptions(profile="balanced", model_name="small", device="auto")
                )
                self.assertEqual(plan.device, "cpu")
                self.assertEqual(plan.compute_type, "int8")
                with self.assertRaises(TranscriptionBackendError):
                    engine.plan_runtime(
                        TranscriptionOptions(profile="balanced", model_name="small", device="cuda")
                    )

    def test_model_manager_distinguishes_cache_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = TranscriptionModelManager(root / "models")

            not_installed = manager.get_model_status("small")
            self.assertEqual(not_installed.status, TranscriptionModelStatus.NOT_INSTALLED)

            marker = manager.resolve_model_path("small")
            marker.parent.mkdir(parents=True, exist_ok=True)
            (manager.cache_root / ".small.downloading").write_text("downloading", encoding="utf-8")
            downloading = manager.get_model_status("small")
            self.assertEqual(downloading.status, TranscriptionModelStatus.DOWNLOADING)

            manager.remove_model("small")
            incomplete_dir = manager.resolve_model_path("small")
            incomplete_dir.mkdir(parents=True, exist_ok=True)
            incomplete = manager.get_model_status("small")
            self.assertEqual(incomplete.status, TranscriptionModelStatus.INCOMPLETE)

            manager.remove_model("small")
            corrupt_file = manager.resolve_model_path("small")
            corrupt_file.parent.mkdir(parents=True, exist_ok=True)
            corrupt_file.write_text("not-a-directory", encoding="utf-8")
            corrupt = manager.get_model_status("small")
            self.assertEqual(corrupt.status, TranscriptionModelStatus.CORRUPT)

    def test_model_downloads_once_and_reuses_existing_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            calls: list[str] = []

            def fake_downloader(*, repo_id: str, cache_dir: str, **kwargs):
                calls.append(repo_id)
                cache_root = Path(cache_dir)
                repo_root = cache_root / "models--Systran--faster-whisper-small"
                snapshot = repo_root / "snapshots" / "abc123"
                snapshot.mkdir(parents=True, exist_ok=True)
                for filename in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
                    (snapshot / filename).write_text("x", encoding="utf-8")
                (repo_root / "refs").mkdir(parents=True, exist_ok=True)
                (repo_root / "refs" / "main").write_text("abc123", encoding="utf-8")
                return cache_dir

            manager = TranscriptionModelManager(root / "models", downloader=fake_downloader, logger=logging.getLogger("test"))

            class DummyWhisperModel:
                def __init__(self, *args, **kwargs):
                    return None

            with patch("faster_whisper.WhisperModel", DummyWhisperModel):
                first = manager.download_model("small", progress_callback=None, cancellation_token=None, force=False)
                second = manager.download_model("small", progress_callback=None, cancellation_token=None, force=False)

            self.assertEqual(first.status, TranscriptionModelStatus.INSTALLED)
            self.assertEqual(second.status, TranscriptionModelStatus.INSTALLED)
            self.assertEqual(len(calls), 1)
            self.assertTrue(manager.resolve_model_path("small").exists())

    def test_verify_model_marks_incompatible_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manager = TranscriptionModelManager(root / "models")
            model_root = manager.resolve_model_path("small")
            snapshot = model_root / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
            snapshot.mkdir(parents=True, exist_ok=True)
            for filename in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
                (snapshot / filename).write_text("x", encoding="utf-8")

            class BrokenWhisperModel:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError("unsupported model format")

            with patch("faster_whisper.WhisperModel", BrokenWhisperModel):
                verified = manager.verify_model("small")

            self.assertEqual(verified.status, TranscriptionModelStatus.INCOMPATIBLE)


class TranscriptionServiceTests(unittest.TestCase):
    def test_transcribe_persists_segments_exports_and_detects_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, catalog, video_repository, prepared_audio_repository, transcription_repository = build_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            audio_path = root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            write_wav(audio_path)
            prepared_audio = PreparedAudioAsset(
                id="audio-1",
                video_asset_id=video.id,
                source_inspection_id=None,
                status=PreparedAudioStatus.COMPLETED,
                relative_cache_path=str(audio_path.relative_to(root / "cache")),
                metadata_relative_path="videos/%s/audio/metadata.json" % video.id,
                format_name="wav",
                codec_name="pcm_s16le",
                sample_rate_hz=16000,
                channels=1,
                channel_layout="mono",
                bit_depth=16,
                duration_seconds=2.0,
                file_size_bytes=audio_path.stat().st_size,
                source_file_size_bytes=sample.stat().st_size,
                source_file_modified_at=datetime.now(timezone.utc),
                selected_stream_index=1,
                selected_stream_codec_name="aac",
                selected_stream_channels=2,
                selected_stream_channel_layout="stereo",
                selected_stream_sample_rate_hz=48000,
                selected_stream_language="es",
                selected_stream_is_default=True,
                extraction_started_at=datetime.now(timezone.utc),
                extraction_completed_at=datetime.now(timezone.utc),
                ffmpeg_version="ffmpeg version",
                cache_version="v1",
                normalization_sample_rate_hz=16000,
                normalization_channels=1,
                warning_code=None,
                warning_message=None,
                error_code=None,
                error_message=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            prepared_audio_repository.upsert(prepared_audio)

            fake_engine = FakeBackendEngine(backend_available=True)
            model_manager = FakeModelManager(paths.models_directory)
            service = TranscriptionService(
                settings=settings,
                paths=paths,
                video_repository=video_repository,
                prepared_audio_repository=prepared_audio_repository,
                transcription_repository=transcription_repository,
                model_manager=model_manager,
                engine=fake_engine,  # type: ignore[arg-type]
                logger=logging.getLogger("test"),
            )

            report = service.transcribe_video(
                video.id,
                TranscriptionOptions(profile="balanced", model_name="small", device="cuda", language="es"),
            )
            self.assertEqual(report.status, TranscriptionStatus.COMPLETED)
            self.assertEqual(report.transcription.model_name, "small")
            self.assertEqual([segment.segment_index for segment in report.segments], [0, 1])

            export_dir = root / "exports"
            txt = service.export_transcription(video.id, TranscriptionExportFormat.TXT, destination=export_dir / "transcript.txt")
            srt = service.export_transcription(video.id, TranscriptionExportFormat.SRT, destination=export_dir / "transcript.srt")
            js = service.export_transcription(video.id, TranscriptionExportFormat.JSON, destination=export_dir / "transcript.json")
            self.assertTrue(Path(txt.path).exists())
            self.assertTrue(Path(srt.path).exists())
            self.assertTrue(Path(js.path).exists())
            self.assertIn("hola mundo", Path(txt.path).read_text(encoding="utf-8"))
            self.assertIn("1", Path(srt.path).read_text(encoding="utf-8"))
            payload = json.loads(Path(js.path).read_text(encoding="utf-8"))
            self.assertEqual(payload["segment_count"], 2)
            self.assertEqual(payload["detected_language"], "es")

            asset = prepared_audio_repository.get_by_video_asset_id(video.id)
            self.assertIsNotNone(asset)
            stale_audio = replace(asset, file_size_bytes=asset.file_size_bytes + 1, updated_at=datetime.now(timezone.utc))
            prepared_audio_repository.upsert(stale_audio)
            self.assertTrue(service.is_transcription_stale(video.id))
            stale_report = service.get_transcription(video.id)
            self.assertEqual(stale_report.status, TranscriptionStatus.STALE)

    def test_transcription_cancel_is_cooperative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, catalog, video_repository, prepared_audio_repository, transcription_repository = build_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            audio_path = root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            write_wav(audio_path, seconds=2.0)
            prepared_audio = PreparedAudioAsset(
                id="audio-1",
                video_asset_id=video.id,
                source_inspection_id=None,
                status=PreparedAudioStatus.COMPLETED,
                relative_cache_path=str(audio_path.relative_to(root / "cache")),
                metadata_relative_path="videos/%s/audio/metadata.json" % video.id,
                format_name="wav",
                codec_name="pcm_s16le",
                sample_rate_hz=16000,
                channels=1,
                channel_layout="mono",
                bit_depth=16,
                duration_seconds=2.0,
                file_size_bytes=audio_path.stat().st_size,
                source_file_size_bytes=sample.stat().st_size,
                source_file_modified_at=datetime.now(timezone.utc),
                selected_stream_index=1,
                selected_stream_codec_name="aac",
                selected_stream_channels=2,
                selected_stream_channel_layout="stereo",
                selected_stream_sample_rate_hz=48000,
                selected_stream_language="es",
                selected_stream_is_default=True,
                extraction_started_at=datetime.now(timezone.utc),
                extraction_completed_at=datetime.now(timezone.utc),
                ffmpeg_version="ffmpeg version",
                cache_version="v1",
                normalization_sample_rate_hz=16000,
                normalization_channels=1,
                warning_code=None,
                warning_message=None,
                error_code=None,
                error_message=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            prepared_audio_repository.upsert(prepared_audio)

            fake_engine = FakeBackendEngine(backend_available=True, cancelable=True)
            model_manager = FakeModelManager(paths.models_directory)
            service = TranscriptionService(
                settings=settings,
                paths=paths,
                video_repository=video_repository,
                prepared_audio_repository=prepared_audio_repository,
                transcription_repository=transcription_repository,
                model_manager=model_manager,
                engine=fake_engine,  # type: ignore[arg-type]
                logger=logging.getLogger("test"),
            )

            result_holder: dict[str, object] = {}

            def run_transcription() -> None:
                result_holder["report"] = service.transcribe_video(
                    video.id,
                    TranscriptionOptions(profile="balanced", model_name="small", device="cuda", language="es"),
                )

            thread = threading.Thread(target=run_transcription)
            thread.start()
            time.sleep(0.01)
            self.assertTrue(service.cancel_transcription(video.id))
            thread.join(timeout=5)

            report = result_holder["report"]
            self.assertEqual(report.status, TranscriptionStatus.CANCELLED)
            stored = transcription_repository.get_by_video_asset_id(video.id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.status, TranscriptionStatus.CANCELLED)
            self.assertEqual(transcription_repository.list_segments(stored.id), [])
