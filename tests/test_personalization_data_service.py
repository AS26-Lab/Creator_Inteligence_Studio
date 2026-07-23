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
from creator_intelligence_studio.application.services.personalization_dataset_service import build_personalization_dataset_service
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import MultimodalAnalysisStatus, MultimodalCandidateType
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationLabel
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_clip_ranking_repository import SQLiteClipRankingRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_multimodal_analysis_repository import SQLiteMultimodalAnalysisRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_personalization_repository import SQLitePersonalizationRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import SQLiteTranscriptionRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.personalization_data_view import PersonalizationDataView
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


def make_diagnostic(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        application_name="Creator Intelligence Studio",
        application_version="0.1.0",
        project_root=root,
        python_version="3.11.9",
        python_executable="python.exe",
        preferred_compute_backend="cuda",
        state=SimpleNamespace(ready_for_basic_mode=True),
        gpu_devices=(),
        warnings=(),
        to_json=lambda: "{}",
    )


def make_transcription(video_id: str) -> tuple[Transcription, list[TranscriptionSegment]]:
    now = datetime.now(timezone.utc)
    segments = [
        TranscriptionSegment(
            id="segment-1",
            transcription_id="transcription-1",
            segment_index=0,
            start_seconds=0.0,
            end_seconds=4.5,
            text="hola mundo",
            confidence=0.92,
            no_speech_probability=0.02,
            temperature=0.0,
            created_at=now,
        ),
        TranscriptionSegment(
            id="segment-2",
            transcription_id="transcription-1",
            segment_index=1,
            start_seconds=4.5,
            end_seconds=11.5,
            text="este es un ejemplo",
            confidence=0.90,
            no_speech_probability=0.03,
            temperature=0.0,
            created_at=now,
        ),
    ]
    transcription = Transcription(
        id="transcription-1",
        video_asset_id=video_id,
        prepared_audio_asset_id=None,
        status=TranscriptionStatus.COMPLETED,
        engine="faster-whisper",
        model_name="small",
        device="cuda",
        compute_type="int8_float16",
        requested_language="es",
        detected_language="es",
        language_probability=0.97,
        full_text="hola mundo este es un ejemplo",
        duration_seconds=12.0,
        processing_time_seconds=0.6,
        real_time_factor=0.05,
        segment_count=len(segments),
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
            start_seconds=4.0,
            end_seconds=11.5,
            candidate_type=MultimodalCandidateType.VISUAL_TRANSITION_WITH_SPEECH,
            score=0.72,
            confidence=0.76,
            title="Candidato 2",
            summary="Transicion visual con voz",
            evidence_json=json.dumps({"source": "synthetic"}, ensure_ascii=False),
            source_window_start=4.0,
            source_window_end=11.5,
            created_at=now,
        ),
    ]
    return SimpleNamespace(
        analysis=analysis,
        transcription=transcription,
        acoustic_analysis=SimpleNamespace(
            id="ac-1",
            average_energy=0.42,
            peak_energy=0.78,
            dynamic_range=0.31,
            pause_count=2,
            longest_pause_seconds=1.4,
            words_per_minute=124.0,
        ),
        visual_analysis=SimpleNamespace(
            id="vis-1",
            average_brightness=0.56,
            average_contrast=0.41,
            average_motion=0.64,
            peak_motion=0.82,
            detected_cut_count=2,
            detected_scene_count=2,
        ),
        windows=windows,
        candidates=candidates,
        available_sources=("transcription", "acoustic", "visual"),
        missing_sources=(),
        warnings=(),
        errors=(),
        progress_message=None,
        to_dict=lambda: {"analysis": analysis.to_dict(), "candidates": [candidate.to_dict() for candidate in candidates]},
    )


def build_environment(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    creator = catalog.create_creator(display_name="Creador")
    project = catalog.create_project(creator_reference=creator.id, name="Proyecto", project_type="long_form")
    source = root / "sample.mp4"
    source.write_bytes(b"video-bytes")
    video = catalog.register_video(project_id=project.id, file_path=str(source), title="Video")

    transcription, segments = make_transcription(video.id)
    transcription_repository = SQLiteTranscriptionRepository(database)
    transcription_repository.upsert(transcription, segments)

    report = make_multimodal_report(video.id, transcription)
    multimodal_repository = SQLiteMultimodalAnalysisRepository(database)
    multimodal_repository.upsert(report.analysis, report.windows, report.candidates)

    clip_repository = SQLiteClipRankingRepository(database)
    clip_service = build_clip_ranking_service(
        settings=settings,
        paths=paths,
        catalog_service=catalog,
        multimodal_service=SimpleNamespace(get_multimodal_analysis=lambda _video_id: report),
        transcription_repository=transcription_repository,
        clip_repository=clip_repository,
        logger=logging.getLogger("test"),
    )
    ranking_report = clip_service.rank_clip_candidates(video.id)
    top_candidate = ranking_report.candidates[0]
    clip_service.approve_candidate(top_candidate.id)
    clip_service.rate_candidate(top_candidate.id, 5)
    clip_service.add_candidate_note(top_candidate.id, "nota humana")
    clip_service.set_candidate_tags(top_candidate.id, ["hook", "highlight"])
    clip_service.create_clip_collection(video.id, "Seleccion")
    clip_service.shortlist_candidate(top_candidate.id)
    if len(ranking_report.candidates) > 1:
        clip_service.reject_candidate(ranking_report.candidates[1].id)

    personalization_repository = SQLitePersonalizationRepository(database)
    personalization_service = build_personalization_dataset_service(
        settings=settings,
        paths=paths,
        catalog_service=catalog,
        clip_service=clip_service,
        personalization_repository=personalization_repository,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, creator, project, video, transcription, report, clip_service, personalization_service


def build_workspace(settings, paths, catalog, clip_service, personalization_service):
    return WorkspaceViewModel(
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
        multimodal_service=SimpleNamespace(get_multimodal_analysis=lambda _video_id: None),
        clip_service=clip_service,
        personalization_service=personalization_service,
        diagnostic=make_diagnostic(paths.project_root),
        settings=settings,
        paths=paths,
    )


class PersonalizationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_build_snapshot_quality_exports_and_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, creator, project, video, transcription, report, clip_service, personalization_service = build_environment(root)

            snapshot_report = personalization_service.build_creator_dataset(creator.id)
            self.assertEqual(snapshot_report.creator.id, creator.id)
            self.assertGreaterEqual(snapshot_report.snapshot.example_count, 2)
            self.assertGreaterEqual(snapshot_report.snapshot.conflict_count, 1)
            self.assertTrue(any(example.label == PersonalizationLabel.POSITIVE for example in snapshot_report.examples))
            self.assertTrue(any(example.label == PersonalizationLabel.NEGATIVE for example in snapshot_report.examples))
            self.assertFalse(snapshot_report.is_stale)

            json_export = personalization_service.export_dataset(snapshot_report.snapshot.id, "json")
            csv_export = personalization_service.export_dataset(snapshot_report.snapshot.id, "csv")
            jsonl_export = personalization_service.export_dataset(snapshot_report.snapshot.id, "jsonl")
            self.assertTrue(Path(json_export.path).exists())
            self.assertTrue(Path(csv_export.path).exists())
            self.assertTrue(Path(jsonl_export.path).exists())
            self.assertIn(snapshot_report.snapshot.id, json_export.content)
            self.assertIn("rank_score", csv_export.content)
            self.assertIn("label", jsonl_export.content)

            clip_service.multimodal_service = SimpleNamespace(
                get_multimodal_analysis=lambda _video_id: make_multimodal_report(video.id, transcription, version="v2")
            )
            self.assertTrue(personalization_service.is_dataset_stale(snapshot_report.snapshot.id))

            rebuilt_report = personalization_service.build_creator_dataset(creator.id, force=True)
            comparison = personalization_service.compare_dataset_snapshots(snapshot_report.snapshot.id, rebuilt_report.snapshot.id)
            self.assertTrue(comparison.configuration_fingerprint_changed or comparison.source_fingerprint_changed)
            self.assertGreaterEqual(len(personalization_service.list_creator_datasets(creator.id)), 2)

            readiness = personalization_service.get_creator_readiness(creator.id)
            self.assertEqual(readiness.creator.id, creator.id)
            latest = personalization_service.get_latest_creator_dataset(creator.id)
            self.assertEqual(latest.creator.id, creator.id)
            self.assertEqual(personalization_service.list_dataset_examples(rebuilt_report.snapshot.id, filters={"label": "positive"})[0].label, PersonalizationLabel.POSITIVE)

            archived = personalization_service.archive_dataset_snapshot(rebuilt_report.snapshot.id)
            self.assertEqual(archived.status.value, "archived")

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, creator, project, video, transcription, report, clip_service, personalization_service = build_environment(root)
            snapshot_report = personalization_service.build_creator_dataset(creator.id)

            parser = build_parser()
            args = parser.parse_args(["personalization", "latest", "--creator-id", creator.id, "--json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=clip_service,
                personalization_service=personalization_service,
                diagnostic=make_diagnostic(root),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(code, 0)
            json.loads(stdout.getvalue())

            args = parser.parse_args(["personalization", "export", "--snapshot-id", snapshot_report.snapshot.id, "--format", "json", "--json"])
            stdout = io.StringIO()
            code = dispatch(
                args,
                service=catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=clip_service,
                personalization_service=personalization_service,
                diagnostic=make_diagnostic(root),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(code, 0)
            export_payload = json.loads(stdout.getvalue())
            self.assertEqual(export_payload["snapshot"]["id"], snapshot_report.snapshot.id)

            workspace = build_workspace(settings, paths, catalog, clip_service, personalization_service)
            workspace.select_creator(creator.id)
            workspace.select_project(project.id)
            view = PersonalizationDataView(workspace)
            view.refresh()
            self.assertGreater(view.snapshots_table.rowCount(), 0)
            self.assertGreater(view.examples_table.rowCount(), 0)
            self.assertIn("Readiness", view.readiness_label.text())
