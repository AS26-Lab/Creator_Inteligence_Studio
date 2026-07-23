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

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name}


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
        entity = _Entity(id=f"creator-{self._index}", name=display_name)
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
        entity = _Entity(id=f"{creator_reference}-project-{self._index}", name=name)
        self._projects[entity.id] = entity
        return entity

    def get_project(self, project_id: str):
        return self._projects[project_id]

    def register_video(self, *, project_id: str, file_path: str, title: str, notes: str | None = None):
        self._index += 1
        entity = _Entity(id=f"{project_id}-video-{self._index}", name=title)
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


class _FakeMultimodalService:
    def analyze_multimodal(self, video_id: str, force: bool = False):
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            analysis=SimpleNamespace(to_dict=lambda: {"id": f"mm-{video_id}"}),
            windows=(),
            candidates=(),
            available_sources=("transcription", "acoustic", "visual"),
            missing_sources=(),
            warnings=(),
            errors=(),
            progress_message=None,
        )


class _FakeClipService:
    def rank_clip_candidates(self, video_id: str, profile: str = "balanced", force: bool = False):
        candidate = SimpleNamespace(id=f"{video_id}-candidate-1", to_dict=lambda: {"id": f"{video_id}-candidate-1"})
        return SimpleNamespace(
            video=_Entity(id=video_id, name="video"),
            multimodal_report=SimpleNamespace(analysis=SimpleNamespace(to_dict=lambda: {})),
            run=SimpleNamespace(profile=profile, video_asset_id=video_id),
            candidates=(candidate,),
            status=SimpleNamespace(value="completed"),
            is_stale=False,
            available_sources=(),
            missing_sources=(),
            warnings=(),
            errors=(),
            progress_message=None,
        )

    def get_ranking_run(self, video_id: str):
        return self.rank_clip_candidates(video_id)

    def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
        return [SimpleNamespace(id=f"{video_id}-candidate-1"), SimpleNamespace(id=f"{video_id}-candidate-2")]

    def approve_candidate(self, candidate_id: str):
        return SimpleNamespace(id=candidate_id, to_dict=lambda: {"id": candidate_id, "status": "approved"})

    def reject_candidate(self, candidate_id: str):
        return SimpleNamespace(id=candidate_id, to_dict=lambda: {"id": candidate_id, "status": "rejected"})

    def shortlist_candidate(self, candidate_id: str):
        return SimpleNamespace(id=candidate_id, to_dict=lambda: {"id": candidate_id, "status": "shortlisted"})


class _FakeDatasetService:
    def build_creator_dataset(self, creator_id: str, project_id: str | None = None, force: bool = False):
        snapshot = SimpleNamespace(id=f"snapshot-{creator_id}", to_dict=lambda: {"id": f"snapshot-{creator_id}"})
        return SimpleNamespace(
            creator=_Entity(id=creator_id, name="creator"),
            project=_Entity(id=project_id, name="project") if project_id else None,
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

    def get_creator_readiness(self, creator_id: str):
        return SimpleNamespace(
            creator=_Entity(id=creator_id, name="creator"),
            latest_snapshot=SimpleNamespace(id=f"snapshot-{creator_id}", to_dict=lambda: {"id": f"snapshot-{creator_id}"}),
            readiness_status=SimpleNamespace(value="ready_for_baseline"),
            readiness_score=0.9,
            recommendations=(),
            snapshot_count=1,
            is_stale=False,
            warnings=(),
        )


class _FakeModelService:
    def train_personalization_baseline(self, snapshot_id: str, force: bool = False, progress_callback=None):
        training_run = SimpleNamespace(id=f"run-{snapshot_id}", to_dict=lambda: {"id": f"run-{snapshot_id}"})
        return SimpleNamespace(
            outcome_status=SimpleNamespace(value="completed"),
            training_run=training_run,
            validation=SimpleNamespace(to_dict=lambda: {"ok": True}),
            test=SimpleNamespace(to_dict=lambda: {"ok": True}),
            baselines=(),
            splits=(),
            artifact=SimpleNamespace(to_dict=lambda: {"artifact": True}),
            warnings=(),
            errors=(),
        )

    def verify_model_artifact(self, training_run_id: str):
        return SimpleNamespace(
            registry_entry=SimpleNamespace(training_run_id=training_run_id),
            artifact_verified=True,
            manifest={"training_run_id": training_run_id},
            warnings=(),
        )

    def activate_model(self, training_run_id: str):
        return SimpleNamespace(
            registry_entry=SimpleNamespace(training_run_id=training_run_id),
            artifact_verified=True,
            manifest={"training_run_id": training_run_id},
            warnings=(),
        )

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
