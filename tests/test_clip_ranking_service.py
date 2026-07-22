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

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.clip_ranking_service import build_clip_ranking_service
from creator_intelligence_studio.domain.multimodal_analysis.entities import (
    MultimodalAnalysis,
    MultimodalMomentCandidate,
    MultimodalTimelineWindow,
)
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import (
    MultimodalAnalysisStatus,
    MultimodalCandidateType,
)
from creator_intelligence_studio.domain.transcription.entities import (
    Transcription,
    TranscriptionSegment,
    TranscriptionStatus,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_clip_ranking_repository import SQLiteClipRankingRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_multimodal_analysis_repository import SQLiteMultimodalAnalysisRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.clip_ranking_view import ClipRankingView
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
    creator = catalog.create_creator(display_name="Creador")
    project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
    sample = root / "sample.mp4"
    sample.write_bytes(b"video-bytes")
    video = catalog.register_video(project_id=project.id, file_path=str(sample), title="Video")
    return settings, paths, database, catalog, creator, project, video


def make_transcription(video_id: str, prepared_audio_id: str = "audio-1") -> tuple[Transcription, list[TranscriptionSegment]]:
    now = datetime.now(timezone.utc)
    transcription = Transcription(
        id="trans-1",
        video_asset_id=video_id,
        prepared_audio_asset_id=prepared_audio_id,
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cuda",
        compute_type="int8_float16",
        requested_language="es",
        detected_language="es",
        language_probability=0.96,
        full_text="hola mundo este es un ejemplo",
        duration_seconds=12.0,
        processing_time_seconds=1.8,
        real_time_factor=0.15,
        segment_count=2,
        word_timestamps_enabled=False,
        vad_enabled=False,
        source_audio_size_bytes=2048,
        source_audio_modified_at=now,
        source_audio_fingerprint="audio-fp",
        configuration_fingerprint="transcription-cfg",
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
    segments = [
        TranscriptionSegment(
            id="seg-1",
            transcription_id=transcription.id,
            segment_index=0,
            start_seconds=0.0,
            end_seconds=5.0,
            text="hola mundo",
            confidence=0.91,
            no_speech_probability=0.03,
            temperature=0.0,
            created_at=now,
        ),
        TranscriptionSegment(
            id="seg-2",
            transcription_id=transcription.id,
            segment_index=1,
            start_seconds=5.0,
            end_seconds=11.5,
            text="este es un ejemplo",
            confidence=0.93,
            no_speech_probability=0.02,
            temperature=0.0,
            created_at=now,
        ),
    ]
    return transcription, segments


def make_multimodal_report(video_id: str, transcription: Transcription, *, version: str = "v1") -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    analysis = MultimodalAnalysis(
        id="mm-1",
        video_asset_id=video_id,
        transcription_id=None,
        acoustic_analysis_id=None,
        visual_analysis_id=None,
        status=MultimodalAnalysisStatus.COMPLETED,
        analyzer_version=version,
        configuration_fingerprint=f"cfg-{version}",
        source_fingerprint=f"src-{version}",
        duration_seconds=12.0,
        window_size_seconds=1.0,
        window_count=12,
        candidate_count=2,
        high_activity_candidate_count=1,
        transition_candidate_count=1,
        silence_candidate_count=0,
        started_at=now,
        completed_at=now,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    windows = [
        MultimodalTimelineWindow(
            id=f"win-{index}",
            multimodal_analysis_id=analysis.id,
            window_index=index,
            start_seconds=float(index),
            end_seconds=float(index + 1),
            transcript_text="hola mundo" if index < 5 else "este es un ejemplo",
            word_count=2,
            speech_ratio=0.82 if index < 5 else 0.66,
            silence_ratio=0.18 if index < 5 else 0.34,
            speech_rate=0.72 if index < 5 else 0.51,
            acoustic_energy=0.71 if index < 5 else 0.58,
            acoustic_change=0.32 if index == 4 else 0.10,
            visual_motion=0.78 if index == 4 else 0.46,
            visual_change=0.36 if index == 4 else 0.12,
            brightness=0.54,
            cut_count=1 if index == 4 else 0,
            scene_index=0 if index < 6 else 1,
            acoustic_event_count=1 if index == 4 else 0,
            visual_event_count=1 if index == 4 else 0,
            combined_activity_score=0.7 if index < 5 else 0.52,
            transition_score=0.65 if index == 4 else 0.24,
            novelty_score=0.58 if index == 4 else 0.20,
            confidence=0.84,
            evidence_json=json.dumps({"window_index": index}, ensure_ascii=False),
            created_at=now,
        )
        for index in range(12)
    ]
    candidates = [
        MultimodalMomentCandidate(
            id="mm-cand-1",
            multimodal_analysis_id=analysis.id,
            candidate_index=0,
            start_seconds=0.0,
            end_seconds=6.0,
            candidate_type=MultimodalCandidateType.HIGH_COMBINED_ACTIVITY,
            score=0.88,
            confidence=0.91,
            title="Candidato 1",
            summary="Actividad alta con voz y corte",
            evidence_json=json.dumps({"source": "synthetic"}, ensure_ascii=False),
            source_window_start=0.0,
            source_window_end=6.0,
            created_at=now,
        ),
        MultimodalMomentCandidate(
            id="mm-cand-2",
            multimodal_analysis_id=analysis.id,
            candidate_index=1,
            start_seconds=6.0,
            end_seconds=11.5,
            candidate_type=MultimodalCandidateType.VISUAL_TRANSITION_WITH_SPEECH,
            score=0.72,
            confidence=0.76,
            title="Candidato 2",
            summary="Transicion visual con voz",
            evidence_json=json.dumps({"source": "synthetic"}, ensure_ascii=False),
            source_window_start=6.0,
            source_window_end=11.5,
            created_at=now,
        ),
    ]
    return SimpleNamespace(
        analysis=analysis,
        transcription=transcription,
        acoustic_analysis=SimpleNamespace(id="ac-1"),
        visual_analysis=SimpleNamespace(id="vis-1"),
        windows=windows,
        candidates=candidates,
        available_sources=("transcription", "acoustic", "visual"),
        missing_sources=(),
        warnings=(),
        errors=(),
        progress_message=None,
        to_dict=lambda: {"analysis": analysis.to_dict(), "candidates": [candidate.to_dict() for candidate in candidates]},
    )


class FakeTranscriptionRepository:
    def __init__(self, transcription: Transcription, segments: list[TranscriptionSegment]) -> None:
        self.transcription = transcription
        self.segments = segments

    def get_by_video_asset_id(self, video_asset_id: str):
        return self.transcription if self.transcription.video_asset_id == video_asset_id else None

    def get_by_id(self, transcription_id: str):
        return self.transcription if self.transcription.id == transcription_id else None

    def list_segments(self, transcription_id: str):
        return list(self.segments) if self.transcription.id == transcription_id else []


class ClipRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def _build_service(self, root: Path):
        settings, paths, database, catalog, _, _, video = make_environment(root)
        transcription, segments = make_transcription(video.id)
        report = make_multimodal_report(video.id, transcription)
        multimodal_repository = SQLiteMultimodalAnalysisRepository(database)
        multimodal_repository.upsert(report.analysis, report.windows, report.candidates)
        clip_repository = SQLiteClipRankingRepository(database)
        clip_service = build_clip_ranking_service(
            settings=settings,
            paths=paths,
            catalog_service=catalog,
            multimodal_service=SimpleNamespace(get_multimodal_analysis=lambda _video_id: report),
            transcription_repository=FakeTranscriptionRepository(transcription, segments),
            clip_repository=clip_repository,
            logger=logging.getLogger("test"),
        )
        return settings, paths, database, catalog, video, transcription, report, clip_service

    def test_rank_feedback_and_exports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, _, video, _, _, clip_service = self._build_service(root)

            report = clip_service.rank_clip_candidates(video.id)
            self.assertEqual(report.status.value, "completed")
            self.assertEqual(len(report.candidates), 2)
            self.assertGreaterEqual(report.candidates[0].rank_score, report.candidates[1].rank_score)

            top_candidate = report.candidates[0]
            clip_service.approve_candidate(top_candidate.id)
            clip_service.rate_candidate(top_candidate.id, 5)
            clip_service.add_candidate_note(top_candidate.id, "nota humana")
            clip_service.set_candidate_tags(top_candidate.id, ["hook", "highlight"])
            clip_service.adjust_candidate_bounds(top_candidate.id, top_candidate.adjusted_start_seconds, top_candidate.adjusted_end_seconds)
            history = clip_service.get_candidate_review_history(top_candidate.id)
            self.assertGreaterEqual(len(history), 4)

            collection = clip_service.create_clip_collection(video.id, "Seleccion")
            item = clip_service.add_candidate_to_collection(collection.id, top_candidate.id)
            self.assertEqual(item.collection_id, collection.id)
            self.assertTrue(clip_service.remove_candidate_from_collection(collection.id, top_candidate.id))

            export_json = clip_service.export_clip_plan(video.id, "json", destination=root / "clip-plan.json")
            export_csv = clip_service.export_clip_plan(video.id, "csv", destination=root / "clip-plan.csv")
            export_edl = clip_service.export_clip_plan(video.id, "edl", destination=root / "clip-plan.edl")
            self.assertTrue(Path(export_json.path).exists())
            self.assertTrue(Path(export_csv.path).exists())
            self.assertTrue(Path(export_edl.path).exists())
            self.assertIn("ranking_run", export_json.content)

    def test_stale_and_profile_variation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, catalog, video, transcription, report, clip_service = self._build_service(root)
            clip_service.rank_clip_candidates(video.id)
            self.assertFalse(clip_service.is_clip_ranking_stale(video.id))
            clip_service.multimodal_service = SimpleNamespace(
                get_multimodal_analysis=lambda _video_id: make_multimodal_report(video.id, transcription, version="v2")
            )
            self.assertTrue(clip_service.is_clip_ranking_stale(video.id))
            balanced = clip_service.rank_clip_candidates(video.id, profile="balanced", force=True)
            speech = clip_service.rank_clip_candidates(video.id, profile="speech-focused", force=True)
            self.assertNotEqual(balanced.run.configuration_fingerprint, speech.run.configuration_fingerprint)

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, video, transcription, report, clip_service = self._build_service(root)
            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=SimpleNamespace(
                    verify_media_tools=lambda: SimpleNamespace(ffmpeg=SimpleNamespace(available=True), ffprobe=SimpleNamespace(available=True), warnings=(), available=True),
                    get_video_inspection=lambda video_id: None,
                    inspect_video=lambda *args, **kwargs: None,
                    is_inspection_stale=lambda video_id: False,
                ),
                audio_service=SimpleNamespace(
                    prepare_audio=lambda *args, **kwargs: None,
                    get_prepared_audio=lambda *args, **kwargs: None,
                    is_prepared_audio_stale=lambda *args, **kwargs: False,
                    verify_prepared_audio=lambda *args, **kwargs: None,
                    delete_prepared_audio_cache=lambda *args, **kwargs: SimpleNamespace(deleted_record=False, deleted_files=()),
                ),
                transcription_service=SimpleNamespace(
                    verify_transcription_backend=lambda: SimpleNamespace(to_dict=lambda: {}),
                    list_models=lambda: (),
                    get_model_status=lambda model_name: SimpleNamespace(status=SimpleNamespace(value="not_installed")),
                    verify_model=lambda model_name: SimpleNamespace(status=SimpleNamespace(value="not_installed")),
                    download_model=lambda *args, **kwargs: None,
                    remove_model=lambda *args, **kwargs: False,
                    transcribe_video=lambda *args, **kwargs: None,
                    get_transcription=lambda *args, **kwargs: None,
                    is_transcription_stale=lambda *args, **kwargs: False,
                    cancel_transcription=lambda *args, **kwargs: False,
                    delete_transcription=lambda *args, **kwargs: False,
                    export_transcription=lambda *args, **kwargs: SimpleNamespace(path="", to_dict=lambda: {}),
                ),
                acoustic_service=SimpleNamespace(
                    analyze_acoustics=lambda *args, **kwargs: None,
                    get_acoustic_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None),
                    get_acoustic_timeline=lambda *args, **kwargs: (),
                    list_acoustic_events=lambda *args, **kwargs: (),
                    is_acoustic_analysis_stale=lambda *args, **kwargs: False,
                    delete_acoustic_analysis=lambda *args, **kwargs: False,
                    export_acoustic_analysis=lambda *args, **kwargs: SimpleNamespace(path="", to_dict=lambda: {}),
                ),
                visual_service=SimpleNamespace(
                    analyze_visuals=lambda *args, **kwargs: None,
                    get_visual_analysis=lambda *args, **kwargs: SimpleNamespace(status=SimpleNamespace(value="not_analyzed"), is_stale=False, analysis=None),
                    get_visual_timeline=lambda *args, **kwargs: (),
                    list_visual_scenes=lambda *args, **kwargs: (),
                    list_visual_events=lambda *args, **kwargs: (),
                    is_visual_analysis_stale=lambda *args, **kwargs: False,
                    delete_visual_analysis=lambda *args, **kwargs: False,
                    export_visual_analysis=lambda *args, **kwargs: SimpleNamespace(path="", to_dict=lambda: {}),
                ),
                multimodal_service=SimpleNamespace(get_multimodal_analysis=lambda _video_id: report),
                clip_service=clip_service,
                diagnostic=SimpleNamespace(gpu_devices=(), preferred_compute_backend="cuda"),
                settings=settings,
                paths=paths,
            )
            workspace.select_project(video.project_id)
            workspace.select_video(video.id)
            clip_view = ClipRankingView(workspace)
            clip_view.refresh()
            parser = build_parser()
            args = parser.parse_args(["clips", "show", "--video-id", video.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=catalog,
                media_service=workspace.media_service,
                audio_service=workspace.audio_service,
                transcription_service=workspace.transcription_service,
                acoustic_service=workspace.acoustic_service,
                visual_service=workspace.visual_service,
                multimodal_service=workspace.multimodal_service,
                clip_service=clip_service,
                diagnostic=SimpleNamespace(to_json=lambda: "{}", state=SimpleNamespace(ready_for_basic_mode=True)),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(code, 0)
            self.assertIn("Estado de ranking de clips", stdout.getvalue())
