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
from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderProfile, RenderOutputVerification
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
