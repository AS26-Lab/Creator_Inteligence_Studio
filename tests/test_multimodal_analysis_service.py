from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.bootstrap import ServiceContext
from creator_intelligence_studio.application.commands.multimodal_commands import AnalyzeMultimodalCommand
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.multimodal_analysis_service import build_multimodal_analysis_service
from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticActivityLabel, AcousticAnalysisStatus, AcousticEventType
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import (
    MultimodalAnalysisStatus,
    MultimodalCandidateType,
    MultimodalMomentCandidateData,
    MultimodalTimelineWindowData,
)
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow
from creator_intelligence_studio.domain.visual_analysis.value_objects import VisualActivityLabel, VisualAnalysisStatus, VisualEventType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.multimodal_analysis.feature_normalizer import normalize_series
from creator_intelligence_studio.infrastructure.multimodal_analysis.moment_candidate_detector import detect_candidate_seeds, merge_candidate_seeds
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_acoustic_analysis_repository import SQLiteAcousticAnalysisRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_multimodal_analysis_repository import SQLiteMultimodalAnalysisRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import SQLitePreparedAudioRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import SQLiteVideoRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_visual_analysis_repository import SQLiteVisualAnalysisRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.multimodal_analysis_view import MultimodalAnalysisView
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
    visual_repository = SQLiteVisualAnalysisRepository(database)
    multimodal_repository = SQLiteMultimodalAnalysisRepository(database)
    multimodal_service = build_multimodal_analysis_service(
        settings=settings,
        paths=paths,
        video_repository=video_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=acoustic_repository,
        visual_repository=visual_repository,
        multimodal_repository=multimodal_repository,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, visual_repository, multimodal_repository, multimodal_service


def make_video_context(root: Path):
    settings, paths, database, catalog, *_ = make_environment(root)
    creator = catalog.create_creator(display_name="Creador")
    project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
    source = root / "sample.mp4"
    source.write_bytes(b"video-bytes")
    video = catalog.register_video(project_id=project.id, file_path=str(source), title="Video sintetico")
    return settings, paths, database, catalog, video


def make_prepared_audio(video_id: str) -> PreparedAudioAsset:
    now = datetime.now(timezone.utc)
    return PreparedAudioAsset(
        id="audio-1",
        video_asset_id=video_id,
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
        duration_seconds=6.0,
        file_size_bytes=1,
        source_file_size_bytes=1,
        source_file_modified_at=now,
        selected_stream_index=0,
        selected_stream_codec_name="aac",
        selected_stream_channels=2,
        selected_stream_channel_layout="stereo",
        selected_stream_sample_rate_hz=48000,
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


def make_transcription(video_id: str, prepared_audio_id: str | None = None) -> tuple[Transcription, list[TranscriptionSegment]]:
    now = datetime.now(timezone.utc)
    segments = [
        TranscriptionSegment(
            id="segment-1",
            transcription_id="transcription-1",
            segment_index=0,
            start_seconds=0.0,
            end_seconds=1.0,
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
            start_seconds=2.0,
            end_seconds=3.0,
            text="esta es una prueba",
            confidence=-0.2,
            no_speech_probability=0.0,
            temperature=0.0,
            created_at=now,
        ),
    ]
    transcription = Transcription(
        id="transcription-1",
        video_asset_id=video_id,
        prepared_audio_asset_id=prepared_audio_id or "audio-1",
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cuda",
        compute_type="int8_float16",
        requested_language="es",
        detected_language="es",
        language_probability=0.97,
        full_text="hola mundo esta es una prueba",
        duration_seconds=6.0,
        processing_time_seconds=0.2,
        real_time_factor=0.1,
        segment_count=len(segments),
        word_timestamps_enabled=False,
        vad_enabled=False,
        source_audio_size_bytes=1234,
        source_audio_modified_at=now,
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


def make_acoustic(video_id: str) -> tuple[AcousticAnalysis, list[AcousticTimelineWindow], list[AcousticEvent]]:
    now = datetime.now(timezone.utc)
    windows = [
        AcousticTimelineWindow(
            id=f"aw-{index}",
            acoustic_analysis_id="acoustic-1",
            window_index=index,
            start_seconds=float(index),
            end_seconds=float(index + 1),
            speech_probability=0.8 if index in {0, 1, 2} else 0.15,
            is_speech=index in {0, 1, 2},
            rms_energy=0.2 + index * 0.05,
            peak_amplitude=0.4 + index * 0.05,
            normalized_energy=0.2 + index * 0.1,
            zero_crossing_rate=0.05,
            speech_rate_estimate=80.0 if index in {0, 1, 2} else 0.0,
            word_count=2 if index in {0, 1, 2} else 0,
            pause_duration_seconds=0.0 if index in {0, 1, 2} else 0.8,
            activity_label=AcousticActivityLabel.SPEECH_NORMAL if index in {0, 1, 2} else AcousticActivityLabel.SILENCE,
            created_at=now,
        )
        for index in range(6)
    ]
    events = [
        AcousticEvent(
            id="ae-1",
            acoustic_analysis_id="acoustic-1",
            event_index=0,
            start_seconds=0.0,
            end_seconds=0.5,
            event_type=AcousticEventType.ABRUPT_ENERGY_CHANGE,
            confidence=0.88,
            evidence_json=json.dumps({"kind": "energy_jump"}),
            created_at=now,
        )
    ]
    analysis = AcousticAnalysis(
        id="acoustic-1",
        video_asset_id=video_id,
        prepared_audio_asset_id="audio-1",
        transcription_id="transcription-1",
        status=AcousticAnalysisStatus.COMPLETED,
        analyzer_version="v1",
        configuration_fingerprint="acoustic-config",
        source_audio_fingerprint="acoustic-fingerprint",
        duration_seconds=6.0,
        speech_duration_seconds=3.0,
        silence_duration_seconds=3.0,
        speech_ratio=0.5,
        silence_ratio=0.5,
        words_per_minute=90.0,
        voiced_words_per_minute=90.0,
        average_energy=0.4,
        peak_energy=0.8,
        dynamic_range=0.4,
        pause_count=2,
        average_pause_seconds=0.6,
        longest_pause_seconds=1.1,
        short_pause_count=1,
        medium_pause_count=1,
        long_pause_count=0,
        low_activity_segment_count=1,
        abrupt_change_count=1,
        event_candidate_count=len(events),
        started_at=now,
        completed_at=now,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    return analysis, windows, events


def make_visual(video_id: str) -> tuple[VisualAnalysis, list[VisualTimelineWindow], list[VisualScene], list[VisualEvent]]:
    now = datetime.now(timezone.utc)
    windows = [
        VisualTimelineWindow(
            id=f"vw-{index}",
            visual_analysis_id="visual-1",
            window_index=index,
            start_seconds=float(index),
            end_seconds=float(index + 1),
            sampled_frame_count=1,
            brightness=0.3 + index * 0.1,
            contrast=0.2 + index * 0.05,
            saturation=0.25,
            motion_score=0.2 + index * 0.15,
            color_change_score=0.1 + index * 0.1,
            is_static=index in {4, 5},
            is_black=False,
            is_possible_freeze=index == 5,
            activity_label=VisualActivityLabel.HIGH_MOTION if index in {1, 2, 3} else VisualActivityLabel.NORMAL_EXPOSURE,
            created_at=now,
        )
        for index in range(6)
    ]
    scenes = [
        VisualScene(
            id="scene-1",
            visual_analysis_id="visual-1",
            scene_index=0,
            start_seconds=0.0,
            end_seconds=3.0,
            duration_seconds=3.0,
            representative_keyframe_path="cache/videos/video/visual/keyframes/scene-0000.jpg",
            cut_in_score=0.7,
            average_motion=0.35,
            average_brightness=0.4,
            average_contrast=0.25,
            created_at=now,
        ),
        VisualScene(
            id="scene-2",
            visual_analysis_id="visual-1",
            scene_index=1,
            start_seconds=3.0,
            end_seconds=6.0,
            duration_seconds=3.0,
            representative_keyframe_path="cache/videos/video/visual/keyframes/scene-0001.jpg",
            cut_in_score=0.5,
            average_motion=0.45,
            average_brightness=0.55,
            average_contrast=0.3,
            created_at=now,
        ),
    ]
    events = [
        VisualEvent(
            id="ve-1",
            visual_analysis_id="visual-1",
            event_index=0,
            start_seconds=0.9,
            end_seconds=1.1,
            event_type=VisualEventType.HARD_CUT,
            confidence=0.91,
            evidence_json=json.dumps({"kind": "hard_cut"}),
            created_at=now,
        )
    ]
    analysis = VisualAnalysis(
        id="visual-1",
        video_asset_id=video_id,
        source_inspection_id=None,
        status=VisualAnalysisStatus.COMPLETED,
        analyzer_version="v1",
        configuration_fingerprint="visual-config",
        source_fingerprint="visual-fingerprint",
        source_file_size_bytes=1234,
        source_file_modified_at=now,
        duration_seconds=6.0,
        sampled_frame_count=len(windows),
        detected_cut_count=len(events),
        detected_scene_count=len(scenes),
        keyframe_count=len(scenes),
        static_segment_count=1,
        black_frame_event_count=0,
        freeze_event_count=1,
        average_brightness=0.45,
        brightness_variation=0.2,
        average_contrast=0.28,
        average_motion=0.3,
        peak_motion=0.7,
        started_at=now,
        completed_at=now,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    return analysis, windows, scenes, events


class MultimodalAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_alignment_normalization_and_candidate_fusion_helpers(self) -> None:
        windows = [
            MultimodalTimelineWindowData(
                window_index=0,
                start_seconds=0.0,
                end_seconds=1.0,
                transcript_text="hola",
                word_count=1,
                speech_ratio=0.8,
                silence_ratio=0.2,
                speech_rate=60.0,
                acoustic_energy=0.9,
                acoustic_change=0.1,
                visual_motion=0.7,
                visual_change=0.3,
                brightness=0.5,
                cut_count=1,
                scene_index=0,
                acoustic_event_count=1,
                visual_event_count=1,
                combined_activity_score=0.9,
                transition_score=0.8,
                novelty_score=0.7,
                confidence=0.9,
                evidence={},
            ),
            MultimodalTimelineWindowData(
                window_index=1,
                start_seconds=1.0,
                end_seconds=2.0,
                transcript_text="mundo",
                word_count=1,
                speech_ratio=0.7,
                silence_ratio=0.3,
                speech_rate=55.0,
                acoustic_energy=0.85,
                acoustic_change=0.15,
                visual_motion=0.65,
                visual_change=0.25,
                brightness=0.55,
                cut_count=1,
                scene_index=0,
                acoustic_event_count=1,
                visual_event_count=1,
                combined_activity_score=0.88,
                transition_score=0.77,
                novelty_score=0.6,
                confidence=0.85,
                evidence={},
            ),
        ]
        seeds = detect_candidate_seeds(windows, SimpleNamespace(**{"window_size_seconds": 1.0, "high_activity_threshold": 0.72, "transition_threshold": 0.65, "low_activity_threshold": 0.25, "hook_window_seconds": 30.0}), duration_seconds=2.0)
        candidates = merge_candidate_seeds(
            seeds,
            SimpleNamespace(
                candidate_merge_gap_seconds=1.0,
                candidate_max_duration_seconds=30.0,
            ),
        )
        normalized = normalize_series([0.2, 1.0, 0.6])

        self.assertEqual(len(candidates), 1)
        self.assertGreater(candidates[0].score, 0.7)
        self.assertGreater(normalized[-1], normalized[0])

    def test_multimodal_analysis_completed_exports_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, visual_repository, multimodal_repository, multimodal_service = make_environment(root)
            creator = catalog.create_creator(display_name="Creador")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            source = root / "sample.mp4"
            source.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(source), title="Video")

            prepared_audio = make_prepared_audio(video.id)
            prepared_audio_repository.upsert(prepared_audio)
            transcription, transcription_segments = make_transcription(video.id, prepared_audio.id)
            acoustic, acoustic_windows, acoustic_events = make_acoustic(video.id)
            visual, visual_windows, visual_scenes, visual_events = make_visual(video.id)
            transcription_repository.upsert(transcription, transcription_segments)
            acoustic_repository.upsert(acoustic, acoustic_windows, acoustic_events)
            visual_repository.upsert(visual, visual_windows, visual_scenes, visual_events)

            report = multimodal_service.analyze_multimodal(video.id)
            self.assertEqual(report.status, MultimodalAnalysisStatus.COMPLETED)
            self.assertGreaterEqual(len(report.windows), 1)
            self.assertGreaterEqual(len(report.candidates), 1)
            self.assertIn("transcription", report.available_sources)
            self.assertIn("acoustic", report.available_sources)
            self.assertIn("visual", report.available_sources)
            self.assertFalse(report.is_stale)

            candidate = multimodal_service.get_moment_candidate(report.candidates[0].id)
            self.assertEqual(candidate.id, report.candidates[0].id)

            json_export = multimodal_service.export_multimodal_analysis(video.id, "json")
            timeline_export = multimodal_service.export_multimodal_analysis(video.id, "timeline-csv")
            candidates_export = multimodal_service.export_multimodal_analysis(video.id, "candidates-csv")
            txt_export = multimodal_service.export_multimodal_analysis(video.id, "txt")
            self.assertTrue(Path(json_export.path).exists())
            self.assertTrue(Path(timeline_export.path).exists())
            self.assertTrue(Path(candidates_export.path).exists())
            self.assertTrue(Path(txt_export.path).exists())

            updated_transcription, transcription_segments = make_transcription(video.id)
            updated_transcription = Transcription(
                id=updated_transcription.id,
                video_asset_id=updated_transcription.video_asset_id,
                prepared_audio_asset_id=updated_transcription.prepared_audio_asset_id,
                status=updated_transcription.status,
                engine=updated_transcription.engine,
                model_name=updated_transcription.model_name,
                device=updated_transcription.device,
                compute_type=updated_transcription.compute_type,
                requested_language=updated_transcription.requested_language,
                detected_language=updated_transcription.detected_language,
                language_probability=updated_transcription.language_probability,
                full_text=updated_transcription.full_text,
                duration_seconds=updated_transcription.duration_seconds,
                processing_time_seconds=updated_transcription.processing_time_seconds,
                real_time_factor=updated_transcription.real_time_factor,
                segment_count=updated_transcription.segment_count,
                word_timestamps_enabled=updated_transcription.word_timestamps_enabled,
                vad_enabled=updated_transcription.vad_enabled,
                source_audio_size_bytes=updated_transcription.source_audio_size_bytes,
                source_audio_modified_at=updated_transcription.source_audio_modified_at,
                source_audio_fingerprint=updated_transcription.source_audio_fingerprint,
                configuration_fingerprint="transcription-config-updated",
                engine_version=updated_transcription.engine_version,
                model_version=updated_transcription.model_version,
                warning_code=updated_transcription.warning_code,
                warning_message=updated_transcription.warning_message,
                error_code=updated_transcription.error_code,
                error_message=updated_transcription.error_message,
                started_at=updated_transcription.started_at,
                completed_at=updated_transcription.completed_at,
                created_at=updated_transcription.created_at,
                updated_at=updated_transcription.updated_at,
            )
            transcription_repository.upsert(updated_transcription, transcription_segments)
            self.assertTrue(multimodal_service.is_multimodal_analysis_stale(video.id))

    def test_cli_multimodal_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video_repository, prepared_audio_repository, transcription_repository, acoustic_repository, visual_repository, multimodal_repository, multimodal_service = make_environment(root)
            creator = catalog.create_creator(display_name="Creador")
            project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
            source = root / "sample.mp4"
            source.write_bytes(b"video-bytes")
            video = catalog.register_video(project_id=project.id, file_path=str(source), title="Video")
            prepared_audio = make_prepared_audio(video.id)
            prepared_audio_repository.upsert(prepared_audio)
            transcription, transcription_segments = make_transcription(video.id, prepared_audio.id)
            acoustic, acoustic_windows, acoustic_events = make_acoustic(video.id)
            visual, visual_windows, visual_scenes, visual_events = make_visual(video.id)
            transcription_repository.upsert(transcription, transcription_segments)
            acoustic_repository.upsert(acoustic, acoustic_windows, acoustic_events)
            visual_repository.upsert(visual, visual_windows, visual_scenes, visual_events)
            multimodal_service.analyze_multimodal(video.id)

            parser = build_parser()
            args = parser.parse_args(["multimodal", "show", "--video-id", video.id, "--json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            result = dispatch(
                args,
                service=catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=multimodal_service,
                diagnostic=SimpleNamespace(ready_for_basic_mode=True, to_json=lambda: "{}"),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(result, 0)
            parsed = json.loads(stdout.getvalue())
            self.assertIn("analysis", parsed)

            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=SimpleNamespace(get_video_inspection=lambda *args, **kwargs: None, is_inspection_stale=lambda *args, **kwargs: False, inspect_video=lambda *args, **kwargs: None, verify_media_tools=lambda: None),
                audio_service=SimpleNamespace(get_prepared_audio=lambda *args, **kwargs: None, is_prepared_audio_stale=lambda *args, **kwargs: False, prepare_audio=lambda *args, **kwargs: None, verify_prepared_audio=lambda *args, **kwargs: None, clear_prepared_audio_cache=lambda *args, **kwargs: None),
                transcription_service=SimpleNamespace(get_transcription=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_transcribed"), is_stale=False, transcription=None, segments=(), backend=None, model_status=None, warnings=(), errors=(), progress_message=None)),
                acoustic_service=SimpleNamespace(get_acoustic_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), events=(), warnings=(), errors=(), progress_message=None)),
                visual_service=SimpleNamespace(get_visual_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None, windows=(), scenes=(), events=(), warnings=(), errors=(), progress_message=None)),
                multimodal_service=SimpleNamespace(
                    get_multimodal_analysis=lambda *args, **kwargs: SimpleNamespace(
                        status=SimpleNamespace(value="completed"),
                        is_stale=False,
                        analysis=SimpleNamespace(window_count=1, candidate_count=1, high_activity_candidate_count=1, transition_candidate_count=0, silence_candidate_count=0, duration_seconds=6.0, analyzer_version="v1", configuration_fingerprint="cfg", source_fingerprint="src", started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), warning_code=None, warning_message=None, error_code=None, error_message=None),
                        windows=(
                            SimpleNamespace(window_index=0, start_seconds=0.0, end_seconds=1.0, combined_activity_score=0.9, transition_score=0.7, novelty_score=0.6),
                        ),
                        candidates=(
                            SimpleNamespace(candidate_index=0, start_seconds=0.0, end_seconds=1.0, candidate_type=SimpleNamespace(value="high_combined_activity"), score=0.9, confidence=0.8, title="High Combined Activity", summary="summary", evidence_json="{}", source_window_start=0.0, source_window_end=1.0, id="candidate-1"),
                        ),
                        available_sources=("transcription", "acoustic", "visual"),
                        missing_sources=(),
                        warnings=(),
                        errors=(),
                        progress_message=None,
                    ),
                    analyze_multimodal=lambda *args, **kwargs: None,
                    get_multimodal_timeline=lambda *args, **kwargs: (),
                    list_moment_candidates=lambda *args, **kwargs: (),
                    get_moment_candidate=lambda *args, **kwargs: None,
                    is_multimodal_analysis_stale=lambda *args, **kwargs: False,
                    delete_multimodal_analysis=lambda *args, **kwargs: False,
                    export_multimodal_analysis=lambda *args, **kwargs: SimpleNamespace(path=str(root / "multimodal.json"), to_dict=lambda: {}),
                ),
                diagnostic=SimpleNamespace(gpu_devices=()),
                settings=settings,
                paths=paths,
            )
            workspace.select_video(video.id)
            view = MultimodalAnalysisView(workspace)
            view.refresh()
            self.assertIn("Estado: completed", view.status_label.text())
