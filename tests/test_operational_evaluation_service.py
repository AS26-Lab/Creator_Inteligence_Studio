from __future__ import annotations

import io
import logging
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.operational_evaluation_service import build_operational_evaluation_service
from creator_intelligence_studio.domain.operational_evaluation.value_objects import OperationalEvaluationRunStatus
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationSplitName
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.operational_evaluation.demo_asset_factory import DemoAssetBundle
from creator_intelligence_studio.infrastructure.operational_evaluation.resource_sampler import ResourceSample
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_operational_evaluation_repository import SQLiteOperationalEvaluationRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.operational_evaluation_view import OperationalEvaluationView
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass
class _Entity:
    id: str
    name: str
    slug: str | None = None
    creator_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "slug": self.slug, "creator_id": self.creator_id}


class _FakeCatalogService:
    def __init__(self) -> None:
        self._creators: dict[str, _Entity] = {}
        self._projects: dict[str, _Entity] = {}
        self._videos: dict[str, _Entity] = {}
        self._index = 0

    def list_creators(self):
        return []

    def create_creator(self, *, display_name: str, slug: str | None = None, description: str | None = None):
        self._index += 1
        entity = _Entity(id=f"creator-{self._index}", name=display_name, slug=slug or f"creator-{self._index}")
        self._creators[slug or entity.id] = entity
        return entity

    def get_creator(self, creator_reference: str):
        if creator_reference in self._creators:
            return self._creators[creator_reference]
        for entity in self._creators.values():
            if entity.id == creator_reference:
                return entity
        raise KeyError(creator_reference)

    def list_projects(self, creator_reference: str):
        return [project for project in self._projects.values() if project.id.startswith(creator_reference)]

    def create_project(self, *, creator_reference: str, name: str, project_type: str, description: str | None = None):
        self._index += 1
        entity = _Entity(id=f"{creator_reference}-project-{self._index}", name=name, creator_id=creator_reference)
        self._projects[entity.id] = entity
        return entity

    def get_project(self, project_id: str):
        return self._projects[project_id]

    def register_video(self, *, project_id: str, file_path: str, title: str, notes: str | None = None):
        self._index += 1
        entity = _Entity(id=f"{project_id}-video-{self._index}", name=title, creator_id=self._projects[project_id].creator_id if project_id in self._projects else None)
        self._videos[entity.id] = entity
        return entity


class _FakeMediaService:
    def inspect_video(self, video_id: str, force: bool = False):
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            inspection=SimpleNamespace(to_dict=lambda: {"video_id": video_id}),
            summary=SimpleNamespace(
                duration_seconds=2.0,
                average_frame_rate=SimpleNamespace(to_float=lambda: 30.0),
                frame_rate=SimpleNamespace(to_float=lambda: 30.0),
                width=1280,
                height=720,
                video_codec="h264",
                audio_codec="aac",
                audio_channels=1,
                audio_sample_rate=16000,
                overall_bitrate=100_000,
                stream_count=2,
            ),
            thumbnail_path=None,
            warnings=(),
            errors=(),
        )


class _FakeAudioService:
    def __init__(self, root: Path) -> None:
        self._root = root

    def prepare_audio(self, video_id: str, force: bool = False):
        audio_path = self._root / "temp" / "evaluations" / "audio" / f"{video_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"RIFFdemo")
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            prepared_audio=SimpleNamespace(id=f"audio-{video_id}", file_path=str(audio_path)),
            selected_stream=SimpleNamespace(to_dict=lambda: {"index": 0}),
            wav_validation=SimpleNamespace(valid=True),
            cache_path=str(audio_path),
            metadata_path=str(audio_path.with_suffix(".json")),
            warnings=(),
            errors=(),
        )


class _FakeTranscriptionService:
    def get_model_status(self, model_name: str):
        return SimpleNamespace(model_name=model_name, status=SimpleNamespace(value="installed"))

    def download_model(self, model_name: str, **kwargs):
        return self.get_model_status(model_name)

    def transcribe_video(self, video_id: str, options, **kwargs):
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        transcription = SimpleNamespace(
            id=f"tx-{video_id}",
            to_dict=lambda: {"id": f"tx-{video_id}"},
        )
        segment = SimpleNamespace(to_dict=lambda: {"segment_index": 0, "text": "hola"})
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            prepared_audio=SimpleNamespace(id=f"audio-{video_id}"),
            transcription=transcription,
            segments=(segment,),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            backend=SimpleNamespace(to_dict=lambda: {"backend": "cpu"}),
            model_status=SimpleNamespace(to_dict=lambda: {"status": "installed"}),
            warnings=(),
            errors=(),
            progress_message=None,
        )


class _FakeAcousticService:
    def analyze_acoustics(self, video_id: str, force: bool = False):
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            analysis=SimpleNamespace(to_dict=lambda: {"id": f"ac-{video_id}"}),
            windows=(),
            events=(),
            warnings=(),
            errors=(),
        )


class _FakeVisualService:
    def analyze_visuals(self, video_id: str, force: bool = False):
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            analysis=SimpleNamespace(to_dict=lambda: {"id": f"vis-{video_id}"}),
            windows=(),
            scenes=(),
            events=(),
            warnings=(),
            errors=(),
        )


def _fake_candidate(video_id: str, index: int, *, rank_score: float | None = None):
    candidate_id = f"{video_id}-candidate-{index + 1}"
    start_seconds = float(index * 1.5)
    end_seconds = start_seconds + 1.2
    score = rank_score if rank_score is not None else max(0.1, 0.9 - index * 0.1)
    return SimpleNamespace(
        id=candidate_id,
        ranking_run_id=f"ranking-{video_id}",
        multimodal_candidate_id=candidate_id,
        rank_position=index + 1,
        original_start_seconds=start_seconds,
        original_end_seconds=end_seconds,
        adjusted_start_seconds=start_seconds,
        adjusted_end_seconds=end_seconds,
        duration_seconds=end_seconds - start_seconds,
        candidate_type="clip",
        source_score=score,
        source_confidence=0.8,
        rank_score=score,
        quality_score=0.75,
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
        review_status=SimpleNamespace(value="unreviewed"),
        user_rating=None,
        user_note=None,
        explanation={"video_id": video_id, "candidate_index": index},
        tags=(),
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )


def _fake_multimodal_candidate(video_id: str, index: int):
    candidate_id = f"{video_id}-candidate-{index + 1}"
    return SimpleNamespace(
        id=candidate_id,
        start_seconds=float(index * 1.5),
        end_seconds=float(index * 1.5 + 1.2),
        combined_activity_score=0.7,
        transition_score=0.6,
        novelty_score=0.4,
        word_count=4,
        speech_ratio=0.5,
        silence_ratio=0.5,
        speech_rate=1.0,
        acoustic_energy=0.6,
        acoustic_change=0.1,
        visual_motion=0.2,
        visual_change=0.1,
        brightness=0.4,
        cut_count=1,
        acoustic_event_count=1,
        visual_event_count=1,
    )


class _FakeMultimodalService:
    def _build_report(self, video_id: str):
        candidates = tuple(_fake_multimodal_candidate(video_id, index) for index in range(4))
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            analysis=SimpleNamespace(id=f"mm-{video_id}", duration_seconds=6.0, to_dict=lambda: {"id": f"mm-{video_id}"}),
            windows=(),
            candidates=candidates,
            available_sources=("transcription", "acoustic", "visual"),
            missing_sources=(),
            warnings=(),
            errors=(),
            progress_message=None,
            transcription=SimpleNamespace(id=f"tx-{video_id}"),
            acoustic_analysis=SimpleNamespace(id=f"ac-{video_id}", average_energy=0.6, peak_energy=0.8, dynamic_range=0.2, pause_count=1, longest_pause_seconds=0.2, words_per_minute=120.0),
            visual_analysis=SimpleNamespace(id=f"vis-{video_id}", average_brightness=0.5, average_contrast=0.3, average_motion=0.2, peak_motion=0.4, detected_cut_count=1, detected_scene_count=1),
        )

    def analyze_multimodal(self, video_id: str, force: bool = False):
        return self._build_report(video_id)


class _FakeClipService:
    def __init__(self) -> None:
        self._rankings: dict[str, list[SimpleNamespace]] = {}
        self._candidates: dict[str, SimpleNamespace] = {}
        self._collections: dict[str, SimpleNamespace] = {}
        self._collection_items: dict[str, list[SimpleNamespace]] = {}
        self._multimodal_service = _FakeMultimodalService()

    def _ensure_candidates(self, video_id: str) -> list[SimpleNamespace]:
        if video_id not in self._rankings:
            candidates = [_fake_candidate(video_id, index) for index in range(4)]
            self._rankings[video_id] = candidates
            for candidate in candidates:
                self._candidates[candidate.id] = candidate
        return self._rankings[video_id]

    def _build_report(self, video_id: str):
        candidates = self._ensure_candidates(video_id)
        multimodal_report = self._multimodal_service._build_report(video_id)
        for candidate, multimodal_candidate in zip(candidates, multimodal_report.candidates, strict=False):
            candidate.multimodal_candidate_id = multimodal_candidate.id
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            multimodal_report=SimpleNamespace(
                analysis=multimodal_report.analysis,
                candidates=multimodal_report.candidates,
                transcription=multimodal_report.transcription,
                acoustic_analysis=multimodal_report.acoustic_analysis,
                visual_analysis=multimodal_report.visual_analysis,
                windows=(),
            ),
            run=SimpleNamespace(profile="balanced", video_asset_id=video_id, ranker_version="fake"),
            candidates=tuple(candidates),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            available_sources=(),
            missing_sources=(),
            warnings=(),
            errors=(),
            progress_message=None,
        )

    def rank_clip_candidates(self, video_id: str, profile: str = "balanced", force: bool = False):
        return self._build_report(video_id)

    def get_ranking_run(self, video_id: str):
        return self._build_report(video_id)

    def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
        return list(self._ensure_candidates(video_id))

    def get_ranked_candidate(self, candidate_id: str):
        return self._candidates[candidate_id]

    def _set_status(self, candidate_id: str, status: str):
        candidate = self.get_ranked_candidate(candidate_id)
        candidate.review_status = SimpleNamespace(value=status)
        return candidate

    def approve_candidate(self, candidate_id: str):
        return self._set_status(candidate_id, "approved")

    def reject_candidate(self, candidate_id: str):
        return self._set_status(candidate_id, "rejected")

    def shortlist_candidate(self, candidate_id: str):
        return self._set_status(candidate_id, "shortlisted")

    def mark_candidate_needs_review(self, candidate_id: str):
        return self._set_status(candidate_id, "needs_review")

    def rate_candidate(self, candidate_id: str, rating: int):
        candidate = self.get_ranked_candidate(candidate_id)
        candidate.user_rating = rating
        return candidate

    def add_candidate_note(self, candidate_id: str, note: str):
        candidate = self.get_ranked_candidate(candidate_id)
        candidate.user_note = note
        return candidate

    def set_candidate_tags(self, candidate_id: str, tags: list[str]):
        candidate = self.get_ranked_candidate(candidate_id)
        candidate.tags = tuple(tags)
        return candidate

    def adjust_candidate_bounds(self, candidate_id: str, start_seconds: float, end_seconds: float):
        candidate = self.get_ranked_candidate(candidate_id)
        candidate.adjusted_start_seconds = start_seconds
        candidate.adjusted_end_seconds = end_seconds
        candidate.duration_seconds = end_seconds - start_seconds
        return candidate

    def create_clip_collection(self, video_id: str, name: str, description: str | None = None):
        collection_id = f"collection-{video_id}-{len(self._collections) + 1}"
        collection = SimpleNamespace(
            id=collection_id,
            video_asset_id=video_id,
            name=name,
            description=description,
            status="active",
            to_dict=lambda: {"id": collection_id, "video_asset_id": video_id, "name": name, "description": description, "status": "active"},
        )
        self._collections[collection_id] = collection
        self._collection_items[collection_id] = []
        return collection

    def add_candidate_to_collection(self, collection_id: str, candidate_id: str):
        item = SimpleNamespace(
            id=f"{collection_id}-{candidate_id}",
            collection_id=collection_id,
            ranked_clip_candidate_id=candidate_id,
            item_index=len(self._collection_items.get(collection_id, [])),
        )
        self._collection_items.setdefault(collection_id, []).append(item)
        return item


class _FakeDatasetService:
    def __init__(self) -> None:
        self._snapshots: dict[str, SimpleNamespace] = {}

    def build_creator_dataset(self, creator_id: str, project_id: str | None = None, force: bool = False):
        snapshot = SimpleNamespace(
            id=f"snapshot-{creator_id}",
            creator_id=creator_id,
            project_id=project_id,
            status=SimpleNamespace(value="completed"),
            example_count=12,
            positive_count=6,
            negative_count=4,
            neutral_count=2,
            excluded_count=0,
            conflict_count=0,
            train_count=8,
            validation_count=2,
            test_count=2,
            readiness_score=0.9,
            readiness_status=SimpleNamespace(value="ready_for_baseline"),
            to_dict=lambda: {"id": f"snapshot-{creator_id}", "status": "completed"},
        )
        report = SimpleNamespace(
            creator=_Entity(id=creator_id, name="creator"),
            project=_Entity(id=project_id, name="project", creator_id=creator_id) if project_id else None,
            snapshot=snapshot,
            feature_schema=SimpleNamespace(to_dict=lambda: {"version": "1"}),
            examples=(),
            conflicts=(),
            quality_report=SimpleNamespace(to_dict=lambda: {"readiness_score": 1.0}),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            warnings=(),
            errors=(),
            progress_message=None,
        )
        self._snapshots[snapshot.id] = report
        return report

    def get_dataset_snapshot(self, snapshot_id: str):
        return self._snapshots[snapshot_id]

    def get_creator_readiness(self, creator_id: str):
        latest_snapshot = self._snapshots.get(f"snapshot-{creator_id}")
        return SimpleNamespace(
            creator=_Entity(id=creator_id, name="creator"),
            latest_snapshot=latest_snapshot.snapshot if latest_snapshot else SimpleNamespace(id=f"snapshot-{creator_id}", to_dict=lambda: {"id": f"snapshot-{creator_id}"}),
            readiness_status=SimpleNamespace(value="ready_for_baseline"),
            readiness_score=0.9,
            recommendations=(),
            snapshot_count=1 if latest_snapshot else 0,
            is_stale=False if latest_snapshot else True,
            warnings=(),
        )


class _FakeModelService:
    def __init__(self) -> None:
        self._training_run = None
        self._active_report = None

    def train_personalization_baseline(self, snapshot_id: str, force: bool = False, progress_callback=None):
        training_run = SimpleNamespace(
            id=f"run-{snapshot_id}",
            status=SimpleNamespace(value="completed"),
            to_dict=lambda: {"id": f"run-{snapshot_id}", "status": "completed"},
        )
        self._training_run = training_run
        return SimpleNamespace(
            outcome_status=SimpleNamespace(value="completed"),
            training_run=training_run,
            metrics=(),
            baseline_summary=(),
            validation=SimpleNamespace(to_dict=lambda: {"ok": True}),
            test=SimpleNamespace(to_dict=lambda: {"ok": True}),
            baselines=(),
            splits=(),
            artifact=SimpleNamespace(to_dict=lambda: {"artifact": True}),
            warnings=(),
            errors=(),
        )

    def get_training_run(self, training_run_id: str):
        if self._training_run is not None and self._training_run.id == training_run_id:
            return self._training_run
        return None

    def verify_model_artifact(self, training_run_id: str):
        return SimpleNamespace(
            registry_entry=SimpleNamespace(training_run_id=training_run_id, status=SimpleNamespace(value="candidate"), is_active=False),
            artifact_verified=True,
            manifest={"training_run_id": training_run_id},
            warnings=(),
        )

    def activate_model(self, training_run_id: str):
        self._active_report = SimpleNamespace(
            registry_entry=SimpleNamespace(training_run_id=training_run_id, status=SimpleNamespace(value="active"), is_active=True),
            artifact_verified=True,
            manifest={"training_run_id": training_run_id},
            warnings=(),
        )
        return self._active_report

    def get_active_creator_model(self, creator_id: str, project_id: str | None = None):
        return self._active_report

    def score_candidates_for_video(self, creator_id: str, video_id: str):
        return [SimpleNamespace(to_dict=lambda: {"creator_id": creator_id, "video_id": video_id, "score": 0.8})]


def _build_service(tmp_root: Path):
    settings = AppSettings(
        application_name="Creator Intelligence Studio",
        environment="test",
        log_level="INFO",
        data_directory="data",
        logs_directory="logs",
        models_directory="models",
        artifacts_directory="artifacts",
        preferred_compute_backend="cpu",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
    )
    paths = ProjectPaths.from_settings(tmp_root, settings)
    paths.ensure_runtime_directories()
    database = SQLiteDatabase(tmp_root / "data" / "evaluation.db", timeout_seconds=1.0)
    with database.connect() as connection:
        run_migrations(connection)
    service = build_operational_evaluation_service(
        settings=settings,
        paths=paths,
        catalog_service=_FakeCatalogService(),
        media_service=_FakeMediaService(),
        audio_service=_FakeAudioService(paths.project_root),
        transcription_service=_FakeTranscriptionService(),
        acoustic_service=_FakeAcousticService(),
        visual_service=_FakeVisualService(),
        multimodal_service=_FakeMultimodalService(),
        clip_service=_FakeClipService(),
        personalization_service=_FakeDatasetService(),
        model_service=_FakeModelService(),
        repository=SQLiteOperationalEvaluationRepository(database),
        logger=logging.getLogger("test"),
    )
    return service, paths, settings


class OperationalEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_pipeline_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, paths, _ = _build_service(Path(temp_dir))
            bundle = DemoAssetBundle(
                audio_path=paths.project_root / "temp" / "evaluations" / "smoke_pipeline" / "demo_audio.wav",
                video_path=paths.project_root / "temp" / "evaluations" / "smoke_pipeline" / "demo_video.mp4",
                notes=("demo",),
            )
            bundle.audio_path.parent.mkdir(parents=True, exist_ok=True)
            bundle.audio_path.write_bytes(b"RIFFdemo")
            bundle.video_path.write_bytes(b"demo")
            sample = ResourceSample(
                ram_total_bytes=1024,
                ram_available_bytes=512,
                vram_total_mib=8192,
                vram_used_mib=1024,
                vram_free_mib=7168,
                cpu_count=8,
                disk_free_bytes=1024,
            )
            with patch("creator_intelligence_studio.application.services.operational_evaluation_service.create_demo_assets", return_value=bundle), patch(
                "creator_intelligence_studio.application.services.operational_evaluation_service.sample_resources",
                side_effect=[sample, sample],
            ):
                report = service.run_scenario("smoke_pipeline")
            self.assertEqual(report.run.status, OperationalEvaluationRunStatus.COMPLETED)
            self.assertGreaterEqual(report.run.stage_count, 1)
            self.assertTrue(service.export(report.run.id, "json").exists())

    def test_split_by_video_assertion_ignores_excluded_examples(self) -> None:
        train_and_excluded = {
            "video-train": {PersonalizationSplitName.TRAIN.value, PersonalizationSplitName.EXCLUDED.value},
            "video-validation": {PersonalizationSplitName.VALIDATION.value, PersonalizationSplitName.EXCLUDED.value},
        }
        self.assertTrue(
            all(
                len(
                    {
                        split_name
                        for split_name in splits
                        if split_name
                        in {
                            PersonalizationSplitName.TRAIN.value,
                            PersonalizationSplitName.VALIDATION.value,
                            PersonalizationSplitName.TEST.value,
                        }
                    }
                )
                <= 1
                for splits in train_and_excluded.values()
            )
        )
        train_and_test = {"video-cross": {PersonalizationSplitName.TRAIN.value, PersonalizationSplitName.TEST.value}}
        self.assertFalse(
            all(
                len(
                    {
                        split_name
                        for split_name in splits
                        if split_name
                        in {
                            PersonalizationSplitName.TRAIN.value,
                            PersonalizationSplitName.VALIDATION.value,
                            PersonalizationSplitName.TEST.value,
                        }
                    }
                )
                <= 1
                for splits in train_and_test.values()
            )
        )
        group_key_cross_split = {"group-1": {PersonalizationSplitName.TRAIN.value, PersonalizationSplitName.TEST.value}}
        self.assertFalse(
            all(
                len(
                    {
                        split_name
                        for split_name in splits
                        if split_name
                        in {
                            PersonalizationSplitName.TRAIN.value,
                            PersonalizationSplitName.VALIDATION.value,
                            PersonalizationSplitName.TEST.value,
                        }
                    }
                )
                <= 1
                for splits in group_key_cross_split.values()
            )
        )
        excluded_only = {"video-excluded": {PersonalizationSplitName.EXCLUDED.value}}
        self.assertTrue(
            all(
                len(
                    {
                        split_name
                        for split_name in splits
                        if split_name
                        in {
                            PersonalizationSplitName.TRAIN.value,
                            PersonalizationSplitName.VALIDATION.value,
                            PersonalizationSplitName.TEST.value,
                        }
                    }
                )
                <= 1
                for splits in excluded_only.values()
            )
        )

    def test_controlled_workflow_ignores_excluded_examples_in_split_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, paths, _ = _build_service(Path(temp_dir))

            class _SplitAwareDatasetService:
                def __init__(self) -> None:
                    self._report = None

                def build_creator_dataset(self, creator_id: str, project_id: str | None = None, force: bool = False):
                    snapshot_id = f"snapshot-{creator_id}"
                    examples = (
                        SimpleNamespace(video_asset_id="video-shared", split_name=SimpleNamespace(value="train")),
                        SimpleNamespace(video_asset_id="video-shared", split_name=SimpleNamespace(value="excluded")),
                        SimpleNamespace(video_asset_id="video-validation", split_name=SimpleNamespace(value="validation")),
                        SimpleNamespace(video_asset_id="video-test", split_name=SimpleNamespace(value="test")),
                    )
                    snapshot = SimpleNamespace(
                        id=snapshot_id,
                        creator_id=creator_id,
                        project_id=project_id,
                        status=SimpleNamespace(value="completed"),
                        example_count=len(examples),
                        positive_count=2,
                        negative_count=1,
                        neutral_count=0,
                        excluded_count=1,
                        conflict_count=0,
                        train_count=1,
                        validation_count=1,
                        test_count=1,
                        readiness_score=0.9,
                        readiness_status=SimpleNamespace(value="ready_for_baseline"),
                        to_dict=lambda: {"id": snapshot_id, "status": "completed"},
                    )
                    report = SimpleNamespace(
                        creator=_Entity(id=creator_id, name="creator", slug="creator"),
                        project=_Entity(id=project_id or "project", name="project", creator_id=creator_id) if project_id else None,
                        snapshot=snapshot,
                        feature_schema=SimpleNamespace(to_dict=lambda: {"version": "1"}),
                        examples=examples,
                        conflicts=(),
                        quality_report=SimpleNamespace(to_dict=lambda: {"readiness_score": 0.9}),
                        status=SimpleNamespace(value="completed"),
                        is_stale=False,
                        warnings=(),
                        errors=(),
                        progress_message=None,
                    )
                    self._report = report
                    return report

                def get_dataset_snapshot(self, snapshot_id: str):
                    return self._report

                def get_creator_readiness(self, creator_id: str):
                    latest_snapshot = self._report.snapshot if self._report else None
                    return SimpleNamespace(
                        creator=_Entity(id=creator_id, name="creator", slug="creator"),
                        latest_snapshot=latest_snapshot,
                        readiness_status=SimpleNamespace(value="ready_for_baseline"),
                        readiness_score=0.9,
                        recommendations=(),
                        snapshot_count=1 if latest_snapshot else 0,
                        is_stale=False if latest_snapshot else True,
                        warnings=(),
                    )

            service.personalization_service = _SplitAwareDatasetService()

            def _bundle_factory(*, project_root, scenario_id, run_id, style, narration_text, duration_seconds, asset_index):
                asset_dir = project_root / "temp" / "evaluations" / scenario_id / run_id / f"asset_{asset_index + 1}"
                asset_dir.mkdir(parents=True, exist_ok=True)
                video_path = asset_dir / "demo_video.mp4"
                audio_path = asset_dir / "demo_audio.wav"
                video_path.write_bytes(f"video-{asset_index}".encode("utf-8"))
                audio_path.write_bytes(b"RIFFdemo")
                return DemoAssetBundle(audio_path=audio_path, video_path=video_path, notes=(f"asset-{asset_index}",))

            sample = ResourceSample(
                ram_total_bytes=1024,
                ram_available_bytes=512,
                vram_total_mib=8192,
                vram_used_mib=1024,
                vram_free_mib=7168,
                cpu_count=8,
                disk_free_bytes=1024,
            )
            with patch("creator_intelligence_studio.application.services.operational_evaluation_service.create_demo_assets", side_effect=_bundle_factory), patch(
                "creator_intelligence_studio.application.services.operational_evaluation_service.sample_resources",
                side_effect=[sample, sample],
            ):
                report = service.run_scenario("controlled_creator_workflow")
            self.assertEqual(report.run.status, OperationalEvaluationRunStatus.COMPLETED)
            self.assertEqual(report.run.assertion_fail_count, 0)
            self.assertGreater(report.run.assertion_pass_count, 0)

    def test_cli_and_view_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service, paths, settings = _build_service(Path(temp_dir))

            parser = build_parser()
            args = parser.parse_args(["evaluation", "scenarios"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=SimpleNamespace(
                    list_creators=lambda: (),
                    list_projects=lambda *_args, **_kwargs: (),
                    list_videos=lambda *_args, **_kwargs: (),
                ),
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=SimpleNamespace(),
                personalization_service=None,
                diagnostic=SimpleNamespace(state=SimpleNamespace(ready_for_basic_mode=True), to_json=lambda: "{}"),
                stdout=stdout,
                stderr=stderr,
                evaluation_service=SimpleNamespace(
                    list_scenarios=lambda: service.list_scenarios(),
                    list_runs=lambda scenario_id=None: (),
                    get_report=lambda run_id: None,
                    list_stages=lambda run_id: (),
                    list_metrics=lambda run_id: (),
                    list_assertions=lambda run_id: (),
                    list_artifacts=lambda run_id: (),
                    run_scenario=lambda scenario_id, force=False, progress_callback=None: service.run_scenario(scenario_id),
                    retry_stage=lambda run_id, stage_name: service.run_scenario("smoke_pipeline"),
                    cancel=lambda run_id: False,
                    export=lambda run_id, format_name, destination=None: service.export(run_id, format_name, destination=destination),
                    clean=lambda run_id, dry_run=False: {"run_id": run_id, "dry_run": dry_run},
                    compare_runs=lambda baseline_run_id, candidate_run_id: service.compare_runs(baseline_run_id, candidate_run_id),
                ),
                model_service=None,
            )
            self.assertEqual(code, 0)
            self.assertIn("smoke_pipeline", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

            workspace = WorkspaceViewModel(
                service=_FakeCatalogService(),
                media_service=_FakeMediaService(),
                audio_service=_FakeAudioService(paths.project_root),
                transcription_service=_FakeTranscriptionService(),
                acoustic_service=_FakeAcousticService(),
                visual_service=_FakeVisualService(),
                multimodal_service=_FakeMultimodalService(),
                clip_service=_FakeClipService(),
                personalization_service=_FakeDatasetService(),
                model_service=_FakeModelService(),
                evaluation_service=service,
                diagnostic=SimpleNamespace(),
                settings=settings,
                paths=paths,
            )
            view = OperationalEvaluationView(workspace)
            view.refresh()
            self.assertGreaterEqual(view.scenario_combo.count(), 2)


if __name__ == "__main__":
    unittest.main()
