from __future__ import annotations

import logging
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.subtitle_service import build_subtitle_service
from creator_intelligence_studio.application.services.video_pipeline_service import VideoPipelineService
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionModelStatus
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_subtitle_repository import SQLiteSubtitleRepository
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
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


def make_transcription(video_id: str) -> tuple[Transcription, list[TranscriptionSegment]]:
    now = datetime.now(timezone.utc)
    transcription = Transcription(
        id=f"tx-{video_id}",
        video_asset_id=video_id,
        prepared_audio_asset_id=f"audio-{video_id}",
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cpu",
        compute_type="int8",
        requested_language="es",
        detected_language="es",
        language_probability=0.99,
        full_text="Hola mundo. Esta es una prueba de subtitulos.",
        duration_seconds=4.0,
        processing_time_seconds=1.2,
        real_time_factor=0.3,
        segment_count=2,
        word_timestamps_enabled=False,
        vad_enabled=False,
        source_audio_size_bytes=1024,
        source_audio_modified_at=now,
        source_audio_fingerprint="audio-fingerprint",
        configuration_fingerprint="config-fingerprint",
        engine_version="1.0",
        model_version="1.0",
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    segments = [
        TranscriptionSegment(
            id=f"seg-{video_id}-1",
            transcription_id=transcription.id,
            segment_index=0,
            start_seconds=0.0,
            end_seconds=1.8,
            text="Hola mundo.",
            confidence=0.98,
            no_speech_probability=0.0,
            temperature=0.0,
            created_at=now,
        ),
        TranscriptionSegment(
            id=f"seg-{video_id}-2",
            transcription_id=transcription.id,
            segment_index=1,
            start_seconds=1.8,
            end_seconds=4.0,
            text="Esta es una prueba de subtitulos.",
            confidence=0.97,
            no_speech_probability=0.0,
            temperature=0.0,
            created_at=now,
        ),
    ]
    return transcription, segments


def build_environment(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    catalog = build_catalog_service(settings=settings, paths=paths, logger=logging.getLogger("test"), database=database)
    creator = catalog.create_creator(display_name="Creator Demo", slug="creator-demo")
    project = catalog.create_project(creator_reference=creator.id, name="Project Demo", project_type="long_form")
    video_file = root / "demo.mp4"
    video_file.write_bytes(b"video-bytes")
    video = catalog.register_video(project_id=project.id, file_path=str(video_file), title="Demo Video")
    transcription, segments = make_transcription(video.id)
    now = datetime.now(timezone.utc)
    prepared_audio = PreparedAudioAsset(
        id=f"audio-{video.id}",
        video_asset_id=video.id,
        source_inspection_id=None,
        status=PreparedAudioStatus.COMPLETED,
        relative_cache_path=None,
        metadata_relative_path=None,
        format_name="wav",
        codec_name="pcm_s16le",
        sample_rate_hz=16000,
        channels=1,
        channel_layout="mono",
        bit_depth=16,
        duration_seconds=transcription.duration_seconds,
        file_size_bytes=1024,
        source_file_size_bytes=video.file_size_bytes,
        source_file_modified_at=now,
        selected_stream_index=0,
        selected_stream_codec_name="pcm_s16le",
        selected_stream_channels=1,
        selected_stream_channel_layout="mono",
        selected_stream_sample_rate_hz=16000,
        selected_stream_language="es",
        selected_stream_is_default=True,
        extraction_started_at=now,
        extraction_completed_at=now,
        ffmpeg_version="ffmpeg version",
        cache_version="v1",
        normalization_sample_rate_hz=16000,
        normalization_channels=1,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    SQLitePreparedAudioRepository(database).upsert(prepared_audio)
    SQLiteTranscriptionRepository(database).upsert(transcription, segments)

    class TranscriptionService:
        def get_transcription(self, video_id: str):
            return SimpleNamespace(transcription=transcription, status=TranscriptionStatus.COMPLETED, is_stale=False)

        def list_transcription_segments(self, transcription_id: str):
            return list(segments)

    transcription_service = TranscriptionService()

    candidate = SimpleNamespace(
        id=f"candidate-{video.id}",
        ranking_run_id=f"ranking-{video.id}",
        multimodal_candidate_id=f"candidate-{video.id}",
        review_status=SimpleNamespace(value="approved"),
        adjusted_start_seconds=0.5,
        adjusted_end_seconds=2.5,
        rank_score=0.91,
        explanation={"title": "Clip demo"},
    )

    class ClipService:
        def get_ranked_candidate(self, candidate_id: str):
            return candidate if candidate_id == candidate.id else None

        def get_ranking_run(self, ranking_run_id: str):
            return SimpleNamespace(video_asset_id=video.id)

        def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
            return [candidate]

    clip_service = ClipService()

    subtitle_service = build_subtitle_service(
        settings=settings,
        paths=paths,
        catalog_service=catalog,
        transcription_service=transcription_service,
        clip_service=clip_service,
        repository=SQLiteSubtitleRepository(database),
        logger=logging.getLogger("test"),
    )
    return settings, paths, catalog, video, candidate, transcription_service, clip_service, subtitle_service


class SubtitleServiceTests(unittest.TestCase):
    def test_generate_video_clip_and_export_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, video, candidate, _, _, subtitle_service = build_environment(root)

            video_report = subtitle_service.generate_video_subtitles(video.id)
            clip_report = subtitle_service.generate_clip_subtitles(candidate.id)
            export_report = subtitle_service.export_subtitles(video_report.track.id, SubtitleExportFormat.SRT)
            imported_report = subtitle_service.import_subtitles(video.id, Path(export_report.path), format=SubtitleExportFormat.SRT)

            self.assertTrue(Path(export_report.path).exists())
            self.assertTrue(export_report.verified)
            self.assertIn(imported_report.track.source_type.value, {"imported_srt", "manual"})
            self.assertGreater(len(imported_report.cues), 0)

        self.assertIn(video_report.status.value, {"completed", "completed_with_warnings"})
        self.assertGreater(len(video_report.cues), 0)
        self.assertEqual(video_report.track.source_type.value, "transcription_generated")
        self.assertEqual(clip_report.track.source_type.value, "clip_generated")
        self.assertAlmostEqual(clip_report.track.source_start_seconds, candidate.adjusted_start_seconds, places=3)

    def test_edit_history_restore_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, video, _, _, _, subtitle_service = build_environment(root)

            report = subtitle_service.generate_video_subtitles(video.id)
            cue = report.cues[0]
            updated = subtitle_service.update_cue_text(cue.id, "Texto editado")
            deleted = subtitle_service.delete_cue(cue.id)
            restored = subtitle_service.restore_cue(cue.id)
            history = subtitle_service.get_subtitle_edit_history(report.track.id)
            cue_history = subtitle_service.get_cue_edit_history(cue.id)

        self.assertEqual(updated.track.id, report.track.id)
        self.assertLess(len(deleted.cues), len(report.cues))
        self.assertEqual(len(restored.cues), len(report.cues))
        self.assertTrue(any(event.action == "delete_cue" for event in history))
        self.assertTrue(any(event.action == "update_cue_text" for event in history))
        self.assertIsInstance(cue_history, list)

    def test_pipeline_recommends_subtitles_after_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            catalog = build_catalog_service(settings=settings, paths=paths, logger=logging.getLogger("test"), database=database)
            creator = catalog.create_creator(display_name="Creator Demo", slug="creator-demo")
            project = catalog.create_project(creator_reference=creator.id, name="Project Demo", project_type="long_form")
            video_file = root / "pipeline.mp4"
            video_file.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(video_file), title="Pipeline Video")
            transcription, segments = make_transcription(video.id)

            class MediaService:
                def get_video_inspection(self, video_id: str):
                    return SimpleNamespace(status=SimpleNamespace(value="completed"), inspection=SimpleNamespace(inspected_at=datetime.now(timezone.utc)), is_stale=False, file_available=True, warnings=(), errors=(), summary=None)

                def inspect_video(self, video_id: str, force: bool = False):
                    return self.get_video_inspection(video_id)

            class AudioService:
                def get_prepared_audio(self, video_id: str):
                    return SimpleNamespace(status=SimpleNamespace(value="completed"), prepared_audio=SimpleNamespace(extraction_completed_at=datetime.now(timezone.utc)), is_stale=False, warnings=(), errors=())

                def prepare_audio(self, video_id: str, force: bool = False):
                    return self.get_prepared_audio(video_id)

            class TranscriptionService:
                def get_transcription(self, video_id: str):
                    return SimpleNamespace(transcription=transcription, status=TranscriptionStatus.COMPLETED, is_stale=False, warnings=(), errors=())

                def list_transcription_segments(self, transcription_id: str):
                    return list(segments)

                def get_model_status(self, model_name: str):
                    return SimpleNamespace(model_name=model_name, status=TranscriptionModelStatus.INSTALLED, notes="ok")

            class SimpleAnalysis:
                def __init__(self, name: str) -> None:
                    self.name = name

                def get(self, video_id: str):
                    return SimpleNamespace(status=SimpleNamespace(value="completed"), analysis=SimpleNamespace(completed_at=datetime.now(timezone.utc)), is_stale=False, errors=(), warnings=())

            class ClipService:
                def get_ranking_run(self, video_id: str):
                    return SimpleNamespace(
                        video=SimpleNamespace(to_dict=lambda: {}),
                        multimodal_report=None,
                        run=SimpleNamespace(completed_at=datetime.now(timezone.utc), selected_count=1),
                        candidates=(),
                        status=SimpleNamespace(value="completed"),
                        is_stale=False,
                        available_sources=(),
                        missing_sources=(),
                        warnings=(),
                        errors=(),
                        progress_message=None,
                    )

                def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
                    return ()

                def get_ranked_candidate(self, candidate_id: str):
                    return None

            subtitle_service = build_subtitle_service(
                settings=settings,
                paths=paths,
                catalog_service=catalog,
                transcription_service=TranscriptionService(),
                clip_service=ClipService(),
                repository=SQLiteSubtitleRepository(database),
                logger=logging.getLogger("test"),
            )
            pipeline = VideoPipelineService(
                catalog_service=catalog,
                media_service=MediaService(),
                audio_service=AudioService(),
                transcription_service=TranscriptionService(),
                acoustic_service=SimpleNamespace(get_acoustic_analysis=lambda video_id: SimpleNamespace(status=SimpleNamespace(value="completed"), analysis=SimpleNamespace(completed_at=datetime.now(timezone.utc)), is_stale=False, warnings=(), errors=(), progress_message=None), analyze_acoustics=lambda *args, **kwargs: None),
                visual_service=SimpleNamespace(get_visual_analysis=lambda video_id: SimpleNamespace(status=SimpleNamespace(value="completed"), analysis=SimpleNamespace(completed_at=datetime.now(timezone.utc)), is_stale=False, warnings=(), errors=(), progress_message=None), analyze_visuals=lambda *args, **kwargs: None),
                multimodal_service=SimpleNamespace(get_multimodal_analysis=lambda video_id: SimpleNamespace(status=SimpleNamespace(value="completed"), analysis=SimpleNamespace(completed_at=datetime.now(timezone.utc)), is_stale=False, warnings=(), errors=(), progress_message=None), analyze_multimodal=lambda *args, **kwargs: None),
                clip_service=ClipService(),
                subtitle_service=subtitle_service,
                personalization_service=None,
            )
            status = pipeline.get_video_pipeline_status(video.id)

        self.assertEqual(status.stages[-1].name, "subtitles")
        self.assertEqual(status.recommended_action, "Preparar subtitulos")
        self.assertEqual(status.overall_status, "completed")

    def test_migration_v13_creates_subtitle_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        self.assertIn(13, versions)
        self.assertIn("subtitle_tracks", tables)
        self.assertIn("subtitle_cues", tables)
        self.assertIn("subtitle_edit_events", tables)
        self.assertIn("subtitle_exports", tables)
