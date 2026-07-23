from __future__ import annotations

import io
import json
import logging
import math
import tempfile
import unittest
import wave
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import ServiceContext
from creator_intelligence_studio.application.bootstrap import run as bootstrap_run
from creator_intelligence_studio.application.services.acoustic_analysis_service import (
    AcousticAnalysisReport,
    build_acoustic_analysis_service,
)
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticAnalysisStatus, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticActivityLabel, AcousticEventType, AcousticTimelineWindowData
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionExportFormat, TranscriptionSegmentData
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.acoustic_analysis.frame_analyzer import analyze_frames
from creator_intelligence_studio.infrastructure.acoustic_analysis.metrics import (
    aggregate_windows,
    compute_global_metrics,
    detect_events,
    summarize_pauses,
)
from creator_intelligence_studio.infrastructure.acoustic_analysis.voice_activity_detector import detect_voice_activity
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_acoustic_analysis_repository import (
    SQLiteAcousticAnalysisRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import (
    SQLitePreparedAudioRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import (
    SQLiteTranscriptionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.presentation.desktop.app import launch_gui
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.acoustic_analysis_view import AcousticAnalysisView
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
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
    )


def write_wav(path: Path, samples: np.ndarray, *, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def silence(seconds: float, *, sample_rate: int = 16000) -> np.ndarray:
    return np.zeros(int(seconds * sample_rate), dtype=np.float32)


def tone(seconds: float, *, sample_rate: int = 16000, frequency: float = 220.0, amplitude: float = 0.35) -> np.ndarray:
    size = int(seconds * sample_rate)
    t = np.arange(size, dtype=np.float32) / sample_rate
    return amplitude * np.sin(2 * math.pi * frequency * t)


def modulated_tone(seconds: float, *, sample_rate: int = 16000, frequency: float = 210.0) -> np.ndarray:
    size = int(seconds * sample_rate)
    t = np.arange(size, dtype=np.float32) / sample_rate
    envelope = 0.2 + 0.8 * (0.5 + 0.5 * np.sin(2 * math.pi * 2.2 * t))
    return envelope * 0.35 * np.sin(2 * math.pi * frequency * t)


def noise(seconds: float, *, sample_rate: int = 16000, amplitude: float = 0.05) -> np.ndarray:
    rng = np.random.default_rng(12345)
    return rng.normal(0.0, amplitude, int(seconds * sample_rate)).astype(np.float32)


def clipping(seconds: float, *, sample_rate: int = 16000) -> np.ndarray:
    size = int(seconds * sample_rate)
    t = np.arange(size, dtype=np.float32) / sample_rate
    wave_values = np.sign(np.sin(2 * math.pi * 440.0 * t)).astype(np.float32)
    return wave_values


def low_volume(seconds: float, *, sample_rate: int = 16000) -> np.ndarray:
    return tone(seconds, sample_rate=sample_rate, amplitude=0.02)


def voice_like_audio() -> np.ndarray:
    return np.concatenate(
        [
            silence(0.35),
            modulated_tone(0.9),
            silence(0.25),
            clipping(0.5),
            silence(0.2),
            modulated_tone(0.8),
            silence(0.4),
        ]
    )


def make_environment(root: Path):
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
    acoustic_repository = SQLiteAcousticAnalysisRepository(database)
    acoustic_service = build_acoustic_analysis_service(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=acoustic_repository,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, acoustic_service


def make_prepared_audio(
    video,
    audio_path: Path,
    *,
    source_file_size: int,
    source_file_modified_at: datetime,
    duration_seconds: float,
) -> PreparedAudioAsset:
    return PreparedAudioAsset(
        id=f"audio-{video.id}",
        video_asset_id=video.id,
        source_inspection_id=None,
        status=PreparedAudioStatus.COMPLETED,
        relative_cache_path=str(audio_path.relative_to(audio_path.parents[3])),
        metadata_relative_path=None,
        format_name="wav",
        codec_name="pcm_s16le",
        sample_rate_hz=16000,
        channels=1,
        channel_layout="mono",
        bit_depth=16,
        duration_seconds=duration_seconds,
        file_size_bytes=audio_path.stat().st_size,
        source_file_size_bytes=source_file_size,
        source_file_modified_at=source_file_modified_at,
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


def make_transcription(
    video_id: str,
    prepared_audio_id: str,
    audio_path: Path,
    *,
    duration_seconds: float,
) -> tuple[Transcription, list[TranscriptionSegment]]:
    now = datetime.now(timezone.utc)
    segments = [
        TranscriptionSegment(
            id="segment-1",
            transcription_id="transcription-1",
            segment_index=0,
            start_seconds=0.35,
            end_seconds=1.25,
            text="hola mundo",
            confidence=-0.1,
            no_speech_probability=0.0,
            temperature=0.0,
            created_at=now,
        ),
        TranscriptionSegment(
            id="segment-2",
            transcription_id="transcription-1",
            segment_index=1,
            start_seconds=1.5,
            end_seconds=2.25,
            text="esta es una prueba",
            confidence=-0.1,
            no_speech_probability=0.0,
            temperature=0.0,
            created_at=now,
        ),
    ]
    transcription = Transcription(
        id="transcription-1",
        video_asset_id=video_id,
        prepared_audio_asset_id=prepared_audio_id,
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cuda",
        compute_type="int8_float16",
        requested_language="es",
        detected_language="es",
        language_probability=0.99,
        full_text="hola mundo esta es una prueba",
        duration_seconds=duration_seconds,
        processing_time_seconds=0.25,
        real_time_factor=0.1,
        segment_count=len(segments),
        word_timestamps_enabled=False,
        vad_enabled=False,
        source_audio_size_bytes=audio_path.stat().st_size,
        source_audio_modified_at=datetime.fromtimestamp(audio_path.stat().st_mtime, tz=timezone.utc),
        source_audio_fingerprint="audio-fingerprint",
        configuration_fingerprint="transcription-config",
        engine_version="1.2.1",
        model_version="small",
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    return transcription, segments


def make_cli_context(acoustic_service) -> ServiceContext:
    diagnostic = SimpleNamespace(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=Path("."),
        os_name="Windows",
        os_version="10.0.19045",
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
    dummy = SimpleNamespace()
    visual_service = SimpleNamespace(
        analyze_visuals=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None),
        get_visual_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None),
        get_visual_timeline=lambda *args, **kwargs: (),
        list_visual_scenes=lambda *args, **kwargs: (),
        list_visual_events=lambda *args, **kwargs: (),
        is_visual_analysis_stale=lambda *args, **kwargs: False,
        delete_visual_analysis=lambda *args, **kwargs: False,
        export_visual_analysis=lambda *args, **kwargs: SimpleNamespace(path="cache/visual/video/visual_analysis.json", to_dict=lambda: {}),
    )
    return ServiceContext(
        settings=make_settings(),
        paths=ProjectPaths.from_settings(Path("."), make_settings()),
        diagnostic=diagnostic,
        logger=logging.getLogger("test"),
        service=dummy,
        media_service=dummy,
        audio_service=dummy,
        transcription_service=dummy,
        acoustic_service=acoustic_service,
        visual_service=visual_service,
    )


class AcousticAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_migration_v5_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, *_ = make_environment(root)
            with database.connect() as connection:
                versions = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'acoustic_%'"
                ).fetchall()
                run_migrations(connection)
                idempotent_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
            self.assertEqual([row["version"] for row in versions], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
            self.assertGreaterEqual(len(tables), 3)
            self.assertEqual(idempotent_count, 11)

    def test_frame_metrics_and_vad_handle_silence_noise_clipping_low_volume(self) -> None:
        sample_rate = 16000
        silence_samples = silence(0.5)
        tone_samples = tone(0.5)
        noise_samples = noise(0.5)
        clip_samples = clipping(0.5)
        low_samples = low_volume(0.5)

        silence_frames = analyze_frames(silence_samples, sample_rate_hz=sample_rate)
        tone_frames = analyze_frames(tone_samples, sample_rate_hz=sample_rate)
        noise_frames = analyze_frames(noise_samples, sample_rate_hz=sample_rate)
        clip_frames = analyze_frames(clip_samples, sample_rate_hz=sample_rate)
        low_frames = analyze_frames(low_samples, sample_rate_hz=sample_rate)

        self.assertTrue(all(frame.rms_energy == 0.0 for frame in silence_frames))
        self.assertGreater(tone_frames[0].rms_energy, low_frames[0].rms_energy)
        self.assertAlmostEqual(clip_frames[0].peak_amplitude, 1.0, places=2)
        self.assertGreater(noise_frames[0].zero_crossing_rate, tone_frames[0].zero_crossing_rate)

        vad = detect_voice_activity(tone_frames + silence_frames, transcript_windows=[(0.0, 0.5)])
        self.assertTrue(bool(vad.is_speech.any()))
        self.assertGreater(float(vad.speech_probability.max()), 0.5)

    def test_analyze_acoustics_completed_exports_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, acoustic_service = make_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            audio_path = paths.project_root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            samples = voice_like_audio()
            write_wav(audio_path, samples)
            prepared_audio = make_prepared_audio(
                video,
                audio_path,
                source_file_size=sample.stat().st_size,
                source_file_modified_at=datetime.fromtimestamp(sample.stat().st_mtime, tz=timezone.utc),
                duration_seconds=len(samples) / 16000.0,
            )
            prepared_audio_repository.upsert(prepared_audio)

            transcription, segments = make_transcription(
                video.id,
                prepared_audio.id,
                audio_path,
                duration_seconds=len(samples) / 16000.0,
            )
            transcription_repository.upsert(transcription, segments)

            report = acoustic_service.analyze_acoustics(video.id)
            self.assertEqual(report.status, AcousticAnalysisStatus.COMPLETED)
            self.assertIsNotNone(report.analysis)
            self.assertGreater(len(report.windows), 0)
            self.assertGreater(report.analysis.speech_duration_seconds, 0.0)
            self.assertGreaterEqual(report.analysis.pause_count, 1)
            self.assertGreaterEqual(report.analysis.event_candidate_count, 1)
            self.assertIsNotNone(report.analysis.words_per_minute)

            json_export = acoustic_service.export_acoustic_analysis(video.id, "json")
            csv_export = acoustic_service.export_acoustic_analysis(video.id, "csv")
            txt_export = acoustic_service.export_acoustic_analysis(video.id, "txt")
            self.assertTrue(Path(json_export.path).exists())
            self.assertTrue(Path(csv_export.path).exists())
            self.assertTrue(Path(txt_export.path).exists())
            self.assertIn("speech_ratio", Path(json_export.path).read_text(encoding="utf-8"))
            self.assertIn("window_index", Path(csv_export.path).read_text(encoding="utf-8"))
            self.assertIn("Pausas", Path(txt_export.path).read_text(encoding="utf-8"))

            audio_path.write_bytes(audio_path.read_bytes() + b"\x00\x00")
            self.assertTrue(acoustic_service.is_acoustic_analysis_stale(video.id))
            stale_report = acoustic_service.get_acoustic_analysis(video.id)
            self.assertEqual(stale_report.status, AcousticAnalysisStatus.STALE)

    def test_long_silence_and_file_missing_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, acoustic_service = make_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")

            audio_path = paths.project_root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            samples = silence(2.7)
            write_wav(audio_path, samples)
            prepared_audio = make_prepared_audio(
                video,
                audio_path,
                source_file_size=sample.stat().st_size,
                source_file_modified_at=datetime.fromtimestamp(sample.stat().st_mtime, tz=timezone.utc),
                duration_seconds=len(samples) / 16000.0,
            )
            prepared_audio_repository.upsert(prepared_audio)

            report = acoustic_service.analyze_acoustics(video.id)
            self.assertEqual(report.analysis.pause_count, 1)
            self.assertEqual(report.analysis.event_candidate_count, 1)

            audio_path.unlink()
            missing = acoustic_service.get_acoustic_analysis(video.id)
            self.assertEqual(missing.status, AcousticAnalysisStatus.FILE_MISSING)

    def test_event_detector_candidates(self) -> None:
        windows = [
            AcousticTimelineWindowData(0, 0.0, 1.0, 0.95, True, 0.6, 0.8, 0.6, 0.12, 90.0, 2, 0.0, AcousticActivityLabel.SPEECH_HIGH),
            AcousticTimelineWindowData(1, 1.0, 2.0, 0.1, False, 0.05, 0.1, 0.05, 0.02, None, 0, 1.0, AcousticActivityLabel.SILENCE),
            AcousticTimelineWindowData(2, 2.0, 3.0, 0.2, False, 0.4, 0.95, 0.4, 0.22, None, 0, 1.0, AcousticActivityLabel.NON_SPEECH_ACTIVITY),
            AcousticTimelineWindowData(3, 3.0, 4.0, 0.85, True, 0.7, 0.9, 0.7, 0.18, 120.0, 3, 0.0, AcousticActivityLabel.SPEECH_HIGH),
        ]
        pause_summary = summarize_pauses(
            windows,
            pause_micro_max_seconds=0.25,
            pause_short_max_seconds=0.75,
            pause_medium_max_seconds=2.0,
        )
        events = detect_events(windows, pause_summary=pause_summary, transcript_segments=None)
        event_types = {event.event_type for event in events}
        self.assertIn(AcousticEventType.LONG_SILENCE, event_types)
        self.assertIn(AcousticEventType.ABRUPT_ENERGY_CHANGE, event_types)
        self.assertIn(AcousticEventType.TRANSIENT_PEAK, event_types)

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, acoustic_service = make_environment(root)
            creator = catalog.create_creator(display_name="Uno")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            sample = root / "sample.mp4"
            sample.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
            audio_path = paths.project_root / "cache" / "videos" / video.id / "audio" / "normalized_v1.wav"
            samples = voice_like_audio()
            write_wav(audio_path, samples)
            prepared_audio = make_prepared_audio(
                video,
                audio_path,
                source_file_size=sample.stat().st_size,
                source_file_modified_at=datetime.fromtimestamp(sample.stat().st_mtime, tz=timezone.utc),
                duration_seconds=len(samples) / 16000.0,
            )
            prepared_audio_repository.upsert(prepared_audio)
            transcription, segments = make_transcription(
                video.id,
                prepared_audio.id,
                audio_path,
                duration_seconds=len(samples) / 16000.0,
            )
            transcription_repository.upsert(transcription, segments)
            report = acoustic_service.analyze_acoustics(video.id)

            stdout = io.StringIO()
            stderr = io.StringIO()
            context = ServiceContext(
                settings=settings,
                paths=paths,
                diagnostic=SimpleNamespace(
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
                ),
                logger=logging.getLogger("test"),
                service=SimpleNamespace(),
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=acoustic_service,
                visual_service=SimpleNamespace(
                    analyze_visuals=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None),
                    get_visual_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None),
                    get_visual_timeline=lambda *args, **kwargs: (),
                    list_visual_scenes=lambda *args, **kwargs: (),
                    list_visual_events=lambda *args, **kwargs: (),
                    is_visual_analysis_stale=lambda *args, **kwargs: False,
                    delete_visual_analysis=lambda *args, **kwargs: False,
                    export_visual_analysis=lambda *args, **kwargs: SimpleNamespace(path="cache/visual/video/visual_analysis.json", to_dict=lambda: {}),
                ),
            )
            with patch("creator_intelligence_studio.application.bootstrap._load_service_context", return_value=context):
                code = bootstrap_run(argv=["acoustic", "show", "--video-id", video.id, "--json"], stdout=stdout, stderr=stderr)
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], AcousticAnalysisStatus.COMPLETED.value)

            app = QApplication.instance() or QApplication([])
            workspace = SimpleNamespace(
                selected_video=lambda: SimpleNamespace(id=video.id, title="Video"),
                get_acoustic_analysis=lambda _: report,
                analyze_acoustics=lambda *args, **kwargs: report,
                delete_acoustic_analysis=lambda *_: False,
                export_acoustic_analysis=lambda *_args, **_kwargs: SimpleNamespace(path=str(root / "out.json")),
            )
            view = AcousticAnalysisView(workspace)
            view.refresh()
            self.assertIn("completed", view.status_label.text())
            self.assertGreater(view.window_table.rowCount(), 0)
            self.assertGreater(view.timeline_scene.items().__len__(), 0)


if __name__ == "__main__":
    unittest.main()
