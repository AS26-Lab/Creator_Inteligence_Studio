from __future__ import annotations

import logging
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from creator_intelligence_studio.application.services.clip_rendering_service import build_clip_render_service
from creator_intelligence_studio.domain.clip_ranking.entities import ClipCollection, ClipCollectionItem, ClipRankingRun, RankedClipCandidate
from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingProfile, ClipRankingReviewStatus, ClipRankingRunStatus
from creator_intelligence_studio.domain.subtitles.entities import SubtitleCue, SubtitleTrack
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueValidationStatus, SubtitleExportFormat, SubtitleSourceType, SubtitleTrackStatus
from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderDeliveryStatus, ClipRenderProfile, RenderOutputVerification
from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.domain.videos.entities import VideoAsset, VideoProcessingStatus, VideoSourceType
from creator_intelligence_studio.infrastructure.clip_rendering.ffmpeg_clip_renderer import ClipRenderExecutionResult, ClipRenderProgress
from creator_intelligence_studio.infrastructure.clip_rendering.filename_builder import build_render_filename
from creator_intelligence_studio.infrastructure.clip_rendering.render_plan_builder import build_render_plan
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_clip_rendering_repository import SQLiteClipRenderingRepository
from creator_intelligence_studio.infrastructure.subtitles.timing_validator import SubtitleTimingValidationResult
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


@dataclass(frozen=True, slots=True)
class _InspectionSummary:
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class _InspectionReport:
    file_available: bool
    is_stale: bool
    summary: _InspectionSummary


class _CatalogService:
    def __init__(self, creator: Creator, project: Project, video: VideoAsset) -> None:
        self._creator = creator
        self._project = project
        self._video = video

    def get_video(self, video_id: str):
        return self._video if video_id == self._video.id else None

    def get_project(self, project_id: str):
        return self._project if project_id == self._project.id else None

    def get_creator(self, creator_id: str):
        return self._creator if creator_id == self._creator.id else None


class _MediaService:
    def __init__(self, inspection: _InspectionReport) -> None:
        self._inspection = inspection

    def get_video_inspection(self, video_id: str):
        return self._inspection


class _ClipRepository:
    def __init__(self, collection: ClipCollection, items: tuple[ClipCollectionItem, ...]) -> None:
        self._collection = collection
        self._items = items

    def get_collection_by_id(self, collection_id: str):
        return self._collection if collection_id == self._collection.id else None

    def list_collection_items(self, collection_id: str):
        return self._items if collection_id == self._collection.id else ()


class _ClipService:
    def __init__(self, candidate: RankedClipCandidate, run: ClipRankingRun, collection: ClipCollection, items: tuple[ClipCollectionItem, ...]) -> None:
        self._candidate = candidate
        self._run = run
        self.clip_repository = _ClipRepository(collection, items)

    def get_ranked_candidate(self, candidate_id: str):
        return self._candidate if candidate_id == self._candidate.id else None

    def get_ranking_run(self, ranking_run_id: str):
        return self._run if ranking_run_id == self._run.id else None

    def is_clip_ranking_stale(self, video_id: str) -> bool:
        return False


class _SubtitleService:
    def __init__(self, report, track: SubtitleTrack, cue: SubtitleCue, export_root: Path) -> None:
        self._report = report
        self._track = track
        self._cue = cue
        self._export_root = export_root

    def get_subtitle_track(self, track_id: str):
        return self._report if track_id == self._track.id else SimpleNamespace(track=None, cues=(), validation=None, is_stale=False)

    def export_subtitles(self, track_id: str, format_name, output=None, custom_name=None):
        if track_id != self._track.id:
            raise AssertionError("unexpected track")
        format_enum = format_name if isinstance(format_name, SubtitleExportFormat) else SubtitleExportFormat(format_name)
        output_path = Path(output) if output is not None else self._export_root / f"track.{format_enum.value}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if format_enum == SubtitleExportFormat.SRT:
            content = "1\n00:00:00,000 --> 00:00:01,000\nHola mundo\n"
        elif format_enum == SubtitleExportFormat.VTT:
            content = "WEBVTT\n\n00:00.000 --> 00:01.000\nHola mundo\n"
        elif format_enum == SubtitleExportFormat.ASS:
            content = "[Script Info]\nTitle: Demo\n[Events]\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Hola mundo\n"
        else:
            content = "Hola mundo\n"
        output_path.write_text(content, encoding="utf-8")
        fingerprint = f"fp-{format_enum.value}"
        return SimpleNamespace(track=self._track, format=format_enum, content=content, path=str(output_path), fingerprint=fingerprint, verified=True)


def _make_entities(root: Path):
    now = datetime.now(timezone.utc)
    creator = Creator(
        id="creator-1",
        display_name="Demo Creator",
        slug="demo-creator",
        description=None,
        created_at=now,
        updated_at=now,
        status=CreatorStatus.ACTIVE,
    )
    project = Project(
        id="project-1",
        creator_id=creator.id,
        name="Demo Project",
        description=None,
        project_type=ProjectType.MIXED,
        status=ProjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    source = root / "source.mp4"
    source.write_bytes(b"demo-video")
    video = VideoAsset(
        id="video-1",
        project_id=project.id,
        title="Demo Video",
        source_path=str(source),
        original_filename="source.mp4",
        extension=".mp4",
        file_size_bytes=source.stat().st_size,
        file_modified_at=now,
        source_type=VideoSourceType.LOCAL_FILE,
        processing_status=VideoProcessingStatus.COMPLETED,
        registered_at=now,
        updated_at=now,
        notes=None,
        file_available=True,
    )
    candidate = RankedClipCandidate(
        id="candidate-1",
        ranking_run_id="ranking-run-1",
        multimodal_candidate_id="multi-1",
        rank_position=1,
        original_start_seconds=0.0,
        original_end_seconds=2.0,
        adjusted_start_seconds=0.25,
        adjusted_end_seconds=2.0,
        duration_seconds=1.75,
        candidate_type="clip",
        source_score=0.9,
        source_confidence=0.8,
        rank_score=0.87,
        quality_score=0.8,
        diversity_score=0.5,
        overlap_penalty=0.0,
        duration_score=0.7,
        opening_score=0.6,
        closing_score=0.6,
        speech_score=0.7,
        visual_score=0.7,
        acoustic_score=0.7,
        transition_score=0.6,
        novelty_score=0.4,
        evidence_strength_score=0.8,
        review_status=ClipRankingReviewStatus.APPROVED,
        user_rating=5,
        user_note=None,
        explanation={"title": "Hook"},
        tags=("demo",),
        created_at=now,
        updated_at=now,
    )
    run = ClipRankingRun(
        id="ranking-run-1",
        video_asset_id=video.id,
        multimodal_analysis_id="multimodal-1",
        creator_id=creator.id,
        project_id=project.id,
        status=ClipRankingRunStatus.COMPLETED,
        ranker_version="v1",
        configuration_fingerprint="rank-config",
        source_fingerprint="rank-source",
        candidate_count=1,
        ranked_candidate_count=1,
        selected_count=1,
        rejected_count=0,
        review_count=1,
        started_at=now,
        completed_at=now,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    collection = ClipCollection(
        id="collection-1",
        video_asset_id=video.id,
        name="Coleccion Demo",
        description=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    item = ClipCollectionItem(
        id="collection-item-1",
        collection_id=collection.id,
        ranked_clip_candidate_id=candidate.id,
        item_index=0,
        custom_title="Clip principal",
        custom_note=None,
        created_at=now,
    )
    inspection = _InspectionReport(file_available=True, is_stale=False, summary=_InspectionSummary(duration_seconds=10.0))
    return creator, project, video, candidate, run, collection, (item,), inspection


def _make_subtitle_track_report(video: VideoAsset, candidate: RankedClipCandidate, export_root: Path):
    now = datetime.now(timezone.utc)
    track = SubtitleTrack(
        id="subtitle-track-1",
        video_asset_id=video.id,
        transcription_id="transcription-1",
        ranked_clip_candidate_id=candidate.id,
        render_job_id=None,
        language="es",
        name="Demo Track",
        status=SubtitleTrackStatus.COMPLETED,
        source_type=SubtitleSourceType.CLIP_GENERATED,
        track_version=1,
        configuration_fingerprint="subtitle-config",
        source_fingerprint="subtitle-source",
        source_start_seconds=0.0,
        source_end_seconds=2.0,
        cue_count=1,
        total_text_length=10,
        is_default=True,
        is_locked=False,
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    cue = SubtitleCue(
        id="subtitle-cue-1",
        subtitle_track_id=track.id,
        cue_index=0,
        start_seconds=0.0,
        end_seconds=1.0,
        text="Hola mundo",
        original_text="Hola mundo",
        source_segment_ids_json='["segment-1"]',
        speaker_label=None,
        line_count=1,
        character_count=10,
        characters_per_second=10.0,
        words_per_minute=120.0,
        validation_status=SubtitleCueValidationStatus.VALID,
        warning_codes_json="[]",
        created_at=now,
        updated_at=now,
    )
    validation = SubtitleTimingValidationResult(
        cue_statuses=(SubtitleCueValidationStatus.VALID,),
        cue_warnings=((),),
        blocking_errors=(),
        warnings=(),
    )
    report = SimpleNamespace(
        video=video,
        transcription=SimpleNamespace(id="transcription-1", to_dict=lambda: {"id": "transcription-1"}),
        track=track,
        cues=(cue,),
        status=SubtitleTrackStatus.COMPLETED,
        is_stale=False,
        validation=validation,
        warnings=(),
        errors=(),
        progress_message=None,
        to_dict=lambda: {
            "track": track.to_dict(),
            "cues": [cue.to_dict()],
            "status": track.status.value,
            "is_stale": False,
        },
    )
    return report, track, cue


def _make_service(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    creator, project, video, candidate, run, collection, items, inspection = _make_entities(root)
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        connection.execute(
            """
            INSERT INTO creators (id, display_name, slug, description, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (creator.id, creator.display_name, creator.slug, creator.description, now, now, creator.status.value),
        )
        connection.execute(
            """
            INSERT INTO projects (id, creator_id, name, description, project_type, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project.id, project.creator_id, project.name, project.description, project.project_type.value, project.status.value, now, now),
        )
        connection.execute(
            """
            INSERT INTO video_assets (
                id, project_id, title, source_path, original_filename, extension,
                file_size_bytes, file_modified_at, source_type, processing_status,
                registered_at, updated_at, notes, file_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video.id,
                video.project_id,
                video.title,
                video.source_path,
                video.original_filename,
                video.extension,
                video.file_size_bytes,
                now,
                video.source_type.value,
                video.processing_status.value,
                now,
                now,
                video.notes,
                1 if video.file_available else 0,
            ),
        )
    catalog = _CatalogService(creator, project, video)
    media = _MediaService(inspection)
    clip_service = _ClipService(candidate, run, collection, items)
    with patch.object(MediaToolLocator, "discover", return_value=SimpleNamespace(ffmpeg=SimpleNamespace(available=True, path="ffmpeg.exe"), ffprobe=SimpleNamespace(available=True, path="ffprobe.exe"))):
        service = build_clip_render_service(
            settings=settings,
            paths=paths,
            catalog_service=catalog,
            media_service=media,
            clip_service=clip_service,
            repository=SQLiteClipRenderingRepository(database),
            logger=logging.getLogger("test"),
        )
    service._renderer.ffmpeg_path = Path("ffmpeg.exe")
    service._verifier.ffprobe_path = Path("ffprobe.exe")
    return service, candidate, collection


class ClipRenderingServiceTests(unittest.TestCase):
    def test_filename_builder_sanitizes_components(self) -> None:
        filename = build_render_filename(
            video_title="Video ../ Demo",
            clip_title='clip:*?"<>',
            start_seconds=1.25,
            end_seconds=4.75,
            profile=ClipRenderProfile.BALANCED,
            suffix="final render",
        )
        self.assertTrue(filename.endswith(".mp4"))
        self.assertNotIn("/", filename)
        self.assertNotIn("\\", filename)

    def test_render_candidate_persists_and_reuses_verified_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, candidate, _ = _make_service(Path(temp_dir))
            output_path = Path(temp_dir) / "exports" / "clips" / "demo.mp4"

            def fake_render(plan, *, cancellation_token=None, progress_callback=None, timeout_seconds=None):
                temp_output = Path(plan.temporary_output_path)
                temp_output.parent.mkdir(parents=True, exist_ok=True)
                temp_output.write_bytes(b"rendered-clip")
                final_output = Path(plan.output_path)
                final_output.parent.mkdir(parents=True, exist_ok=True)
                final_output.write_bytes(b"rendered-clip")
                if progress_callback is not None:
                    progress_callback("rendering", 1.0, {"message": "Renderizando"})
                return ClipRenderExecutionResult(
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed_seconds=0.1,
                    output_path=final_output,
                    temporary_output_path=temp_output,
                    fingerprint="render-fingerprint",
                    progress_events=(ClipRenderProgress("completed", 100.0, "Render completado"),),
                )

            def fake_verify(plan, output_path: Path):
                return RenderOutputVerification(
                    verified=True,
                    output_path=str(output_path),
                    size_bytes=output_path.stat().st_size,
                    duration_seconds=1.75,
                    video_codec="libx264",
                    audio_codec="aac",
                    width=1280,
                    height=720,
                    frame_rate=30.0,
                    audio_sample_rate=48000,
                    fingerprint="verification-fingerprint",
                    warnings=(),
                    errors=(),
                    details={"verified": True},
                )

            service._renderer.render = fake_render
            service._verifier.verify = fake_verify

            report = service.render_candidate(candidate.id, profile="balanced")
            self.assertFalse(report.reused_output)
            self.assertEqual(report.job.status.value, "completed")
            self.assertTrue(Path(report.job.output_path).exists())
            self.assertEqual(len(service.list_render_jobs()), 1)

            reused = service.render_candidate(candidate.id, profile="balanced")
            self.assertTrue(reused.reused_output)
            self.assertEqual(reused.job.id, report.job.id)
            self.assertEqual(len(service.list_render_jobs()), 1)
            self.assertEqual(output_path.suffix, ".mp4")

    def test_render_collection_creates_batch_and_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, candidate, collection = _make_service(Path(temp_dir))

            def fake_render(plan, *, cancellation_token=None, progress_callback=None, timeout_seconds=None):
                temp_output = Path(plan.temporary_output_path)
                temp_output.parent.mkdir(parents=True, exist_ok=True)
                temp_output.write_bytes(b"rendered-collection")
                final_output = Path(plan.output_path)
                final_output.parent.mkdir(parents=True, exist_ok=True)
                final_output.write_bytes(b"rendered-collection")
                return ClipRenderExecutionResult(
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed_seconds=0.1,
                    output_path=final_output,
                    temporary_output_path=temp_output,
                    fingerprint="render-fingerprint",
                    progress_events=(ClipRenderProgress("completed", 100.0, "Render completado"),),
                )

            def fake_verify(plan, output_path: Path):
                return RenderOutputVerification(
                    verified=True,
                    output_path=str(output_path),
                    size_bytes=output_path.stat().st_size,
                    duration_seconds=1.75,
                    video_codec="libx264",
                    audio_codec="aac",
                    width=1280,
                    height=720,
                    frame_rate=30.0,
                    audio_sample_rate=48000,
                    fingerprint="verification-fingerprint",
                    warnings=(),
                    errors=(),
                    details={"verified": True},
                )

            service._renderer.render = fake_render
            service._verifier.verify = fake_verify

            report = service.render_collection(collection.id, profile="balanced", explicit=True)
            self.assertEqual(report.batch.status.value, "completed")
            self.assertEqual(report.batch.job_count, 1)
            self.assertEqual(len(report.jobs), 1)
            self.assertEqual(report.jobs[0].collection_id, collection.id)
            self.assertEqual(service.list_render_batches_for_collection(collection.id)[0].id, report.batch.id)

    def test_subtitle_deliveries_sidecar_and_burn_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, candidate, _ = _make_service(root)
            now = datetime.now(timezone.utc)
            video_id = service.clip_service.get_ranking_run(candidate.ranking_run_id).video_asset_id
            video = service.catalog_service.get_video(video_id)
            subtitle_report, track, cue = _make_subtitle_track_report(video, candidate, root)

            class SubtitleService:
                def get_subtitle_track(self, track_id: str):
                    return subtitle_report

                def export_subtitles(self, track_id: str, format_name, output=None, custom_name=None):
                    format_enum = format_name if isinstance(format_name, SubtitleExportFormat) else SubtitleExportFormat(format_name)
                    output_path = Path(output) if output is not None else root / f"{track_id}.{format_enum.value}"
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    if format_enum == SubtitleExportFormat.SRT:
                        content = "1\n00:00:00,000 --> 00:00:01,000\nHola mundo\n"
                    elif format_enum == SubtitleExportFormat.VTT:
                        content = "WEBVTT\n\n00:00.000 --> 00:01.000\nHola mundo\n"
                    else:
                        content = "[Script Info]\nTitle: Demo\n[Events]\nDialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Hola mundo\n"
                    output_path.write_text(content, encoding="utf-8")
                    return SimpleNamespace(track=track, format=format_enum, content=content, path=str(output_path), fingerprint=f"fp-{format_enum.value}", verified=True)

            service.subtitle_service = SubtitleService()
            with service.repository._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO transcriptions (
                        id, video_asset_id, prepared_audio_asset_id, status, engine, model_name, device, compute_type,
                        requested_language, detected_language, language_probability, full_text, duration_seconds,
                        processing_time_seconds, real_time_factor, segment_count, word_timestamps_enabled, vad_enabled,
                        source_audio_size_bytes, source_audio_modified_at, source_audio_fingerprint,
                        configuration_fingerprint, engine_version, model_version, warning_code, warning_message,
                        error_code, error_message, started_at, completed_at, created_at, updated_at
                    ) VALUES (
                        :id, :video_asset_id, :prepared_audio_asset_id, :status, :engine, :model_name, :device, :compute_type,
                        :requested_language, :detected_language, :language_probability, :full_text, :duration_seconds,
                        :processing_time_seconds, :real_time_factor, :segment_count, :word_timestamps_enabled, :vad_enabled,
                        :source_audio_size_bytes, :source_audio_modified_at, :source_audio_fingerprint,
                        :configuration_fingerprint, :engine_version, :model_version, :warning_code, :warning_message,
                        :error_code, :error_message, :started_at, :completed_at, :created_at, :updated_at
                    )
                    """,
                    {
                        "id": "transcription-1",
                        "video_asset_id": video.id,
                        "prepared_audio_asset_id": None,
                        "status": "completed",
                        "engine": "faster-whisper",
                        "model_name": "small",
                        "device": "cpu",
                        "compute_type": "int8",
                        "requested_language": "es",
                        "detected_language": "es",
                        "language_probability": 0.99,
                        "full_text": "Hola mundo",
                        "duration_seconds": 2.0,
                        "processing_time_seconds": 1.0,
                        "real_time_factor": 0.5,
                        "segment_count": 1,
                        "word_timestamps_enabled": 0,
                        "vad_enabled": 1,
                        "source_audio_size_bytes": None,
                        "source_audio_modified_at": None,
                        "source_audio_fingerprint": "audio-fingerprint",
                        "configuration_fingerprint": "transcription-config",
                        "engine_version": "1",
                        "model_version": "small",
                        "warning_code": None,
                        "warning_message": None,
                        "error_code": None,
                        "error_message": None,
                        "started_at": now.isoformat(),
                        "completed_at": now.isoformat(),
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
                )
                connection.execute(
                    """
                    INSERT INTO subtitle_tracks (
                        id, video_asset_id, transcription_id, ranked_clip_candidate_id, render_job_id,
                        language, name, status, source_type, track_version, configuration_fingerprint,
                        source_fingerprint, source_start_seconds, source_end_seconds, cue_count,
                        total_text_length, is_default, is_locked, warning_code, warning_message,
                        error_code, error_message, created_at, updated_at, completed_at
                    ) VALUES (
                        :id, :video_asset_id, :transcription_id, :ranked_clip_candidate_id, :render_job_id,
                        :language, :name, :status, :source_type, :track_version, :configuration_fingerprint,
                        :source_fingerprint, :source_start_seconds, :source_end_seconds, :cue_count,
                        :total_text_length, :is_default, :is_locked, :warning_code, :warning_message,
                        :error_code, :error_message, :created_at, :updated_at, :completed_at
                    )
                    """,
                    track.to_dict(),
                )
                connection.execute(
                    """
                    INSERT INTO subtitle_cues (
                        id, subtitle_track_id, cue_index, start_seconds, end_seconds, text, original_text,
                        source_segment_ids_json, speaker_label, line_count, character_count,
                        characters_per_second, words_per_minute, validation_status, warning_codes_json,
                        created_at, updated_at
                    ) VALUES (
                        :id, :subtitle_track_id, :cue_index, :start_seconds, :end_seconds, :text, :original_text,
                        :source_segment_ids_json, :speaker_label, :line_count, :character_count,
                        :characters_per_second, :words_per_minute, :validation_status, :warning_codes_json,
                        :created_at, :updated_at
                    )
                    """,
                    cue.to_dict(),
                )

            def fake_render(plan, *, cancellation_token=None, progress_callback=None, timeout_seconds=None):
                temp_output = Path(plan.temporary_output_path)
                temp_output.parent.mkdir(parents=True, exist_ok=True)
                temp_output.write_bytes(b"rendered-clip")
                final_output = Path(plan.output_path)
                final_output.parent.mkdir(parents=True, exist_ok=True)
                final_output.write_bytes(b"rendered-clip")
                if progress_callback is not None:
                    progress_callback("rendering", 1.0, {"message": "Renderizando"})
                return ClipRenderExecutionResult(
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed_seconds=0.1,
                    output_path=final_output,
                    temporary_output_path=temp_output,
                    fingerprint="render-fingerprint",
                    progress_events=(ClipRenderProgress("completed", 100.0, "Render completado"),),
                )

            def fake_verify(plan, output_path: Path):
                return RenderOutputVerification(
                    verified=True,
                    output_path=str(output_path),
                    size_bytes=output_path.stat().st_size,
                    duration_seconds=1.75,
                    video_codec="libx264",
                    audio_codec="aac",
                    width=1280,
                    height=720,
                    frame_rate=30.0,
                    audio_sample_rate=48000,
                    fingerprint="verification-fingerprint",
                    warnings=(),
                    errors=(),
                    details={"verified": True},
                )

            service._renderer.render = fake_render
            service._verifier.verify = fake_verify

            render_report = service.render_candidate(candidate.id, profile="balanced")
            sidecar = service.create_sidecar_delivery(render_report.job.id, track.id, format_name="srt")
            self.assertTrue(Path(sidecar.delivery.output_path).exists())
            self.assertEqual(sidecar.delivery.subtitle_mode.value, "sidecar_srt")
            self.assertEqual(service.list_render_deliveries(render_report.job.id)[0].id, sidecar.delivery.id)

            burn_in = service.create_burn_in_render(candidate.id, track.id, profile="balanced", style_preset="clean")
            self.assertTrue(Path(burn_in.delivery.output_path).exists())
            self.assertEqual(burn_in.delivery.subtitle_mode.value, "burn_in")
            self.assertTrue(Path(burn_in.delivery.manifest_path).exists())
            self.assertGreaterEqual(len(service.list_render_deliveries(burn_in.job.id)), 1)

    def test_burn_in_cancellation_cleans_ass_and_marks_delivery_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service, candidate, _ = _make_service(root)
            now = datetime.now(timezone.utc)
            video_id = service.clip_service.get_ranking_run(candidate.ranking_run_id).video_asset_id
            video = service.catalog_service.get_video(video_id)
            subtitle_report, track, cue = _make_subtitle_track_report(video, candidate, root)

            class SubtitleService:
                def get_subtitle_track(self, track_id: str):
                    return subtitle_report

                def export_subtitles(self, track_id: str, format_name, output=None, custom_name=None):
                    raise AssertionError("burn-in should not export sidecar subtitles")

            service.subtitle_service = SubtitleService()
            with service.repository._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO transcriptions (
                        id, video_asset_id, prepared_audio_asset_id, status, engine, model_name, device, compute_type,
                        requested_language, detected_language, language_probability, full_text, duration_seconds,
                        processing_time_seconds, real_time_factor, segment_count, word_timestamps_enabled, vad_enabled,
                        source_audio_size_bytes, source_audio_modified_at, source_audio_fingerprint,
                        configuration_fingerprint, engine_version, model_version, warning_code, warning_message,
                        error_code, error_message, started_at, completed_at, created_at, updated_at
                    ) VALUES (
                        :id, :video_asset_id, :prepared_audio_asset_id, :status, :engine, :model_name, :device, :compute_type,
                        :requested_language, :detected_language, :language_probability, :full_text, :duration_seconds,
                        :processing_time_seconds, :real_time_factor, :segment_count, :word_timestamps_enabled, :vad_enabled,
                        :source_audio_size_bytes, :source_audio_modified_at, :source_audio_fingerprint,
                        :configuration_fingerprint, :engine_version, :model_version, :warning_code, :warning_message,
                        :error_code, :error_message, :started_at, :completed_at, :created_at, :updated_at
                    )
                    """,
                    {
                        "id": track.transcription_id,
                        "video_asset_id": video.id,
                        "prepared_audio_asset_id": None,
                        "status": "completed",
                        "engine": "faster-whisper",
                        "model_name": "small",
                        "device": "cpu",
                        "compute_type": "int8",
                        "requested_language": "es",
                        "detected_language": "es",
                        "language_probability": 0.99,
                        "full_text": "Hola mundo",
                        "duration_seconds": 2.0,
                        "processing_time_seconds": 1.0,
                        "real_time_factor": 0.5,
                        "segment_count": 1,
                        "word_timestamps_enabled": 0,
                        "vad_enabled": 1,
                        "source_audio_size_bytes": None,
                        "source_audio_modified_at": None,
                        "source_audio_fingerprint": "audio-fingerprint",
                        "configuration_fingerprint": "transcription-config-cancel",
                        "engine_version": "1",
                        "model_version": "small",
                        "warning_code": None,
                        "warning_message": None,
                        "error_code": None,
                        "error_message": None,
                        "started_at": now.isoformat(),
                        "completed_at": now.isoformat(),
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
                )
                connection.execute(
                    """
                    INSERT INTO subtitle_tracks (
                        id, video_asset_id, transcription_id, ranked_clip_candidate_id, render_job_id,
                        language, name, status, source_type, track_version, configuration_fingerprint,
                        source_fingerprint, source_start_seconds, source_end_seconds, cue_count,
                        total_text_length, is_default, is_locked, warning_code, warning_message,
                        error_code, error_message, created_at, updated_at, completed_at
                    ) VALUES (
                        :id, :video_asset_id, :transcription_id, :ranked_clip_candidate_id, :render_job_id,
                        :language, :name, :status, :source_type, :track_version, :configuration_fingerprint,
                        :source_fingerprint, :source_start_seconds, :source_end_seconds, :cue_count,
                        :total_text_length, :is_default, :is_locked, :warning_code, :warning_message,
                        :error_code, :error_message, :created_at, :updated_at, :completed_at
                    )
                    """,
                    track.to_dict(),
                )
                connection.execute(
                    """
                    INSERT INTO subtitle_cues (
                        id, subtitle_track_id, cue_index, start_seconds, end_seconds, text, original_text,
                        source_segment_ids_json, speaker_label, line_count, character_count,
                        characters_per_second, words_per_minute, validation_status, warning_codes_json,
                        created_at, updated_at
                    ) VALUES (
                        :id, :subtitle_track_id, :cue_index, :start_seconds, :end_seconds, :text, :original_text,
                        :source_segment_ids_json, :speaker_label, :line_count, :character_count,
                        :characters_per_second, :words_per_minute, :validation_status, :warning_codes_json,
                        :created_at, :updated_at
                    )
                    """,
                    cue.to_dict() | {"id": "subtitle-cue-cancel-1"},
                )

            def fake_render(plan, *, cancellation_token=None, progress_callback=None, timeout_seconds=None):
                if progress_callback is not None:
                    progress_callback("cancelled", 0.0, {"message": "Render cancelado"})
                return ClipRenderExecutionResult(
                    returncode=0,
                    stdout="",
                    stderr="",
                    elapsed_seconds=0.1,
                    output_path=Path(plan.output_path),
                    temporary_output_path=Path(plan.temporary_output_path),
                    fingerprint=None,
                    progress_events=(ClipRenderProgress("cancelled", 0.0, "Render cancelado"),),
                )

            service._renderer.render = fake_render

            report = service.create_burn_in_render(candidate.id, track.id, profile="balanced", style_preset="clean")
            self.assertEqual(report.delivery.status, ClipRenderDeliveryStatus.CANCELLED)
            self.assertEqual(report.errors, ("Render cancelado.",))
            self.assertFalse(report.delivery.manifest_path)
            self.assertFalse(Path(report.delivery.source_export_path).exists())
