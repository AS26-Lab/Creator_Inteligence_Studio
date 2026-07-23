from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.personalization_training_service import build_personalization_training_service
from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetQualityReport
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetStatus, PersonalizationReadinessStatus
from creator_intelligence_studio.infrastructure.persistence.sqlite_personalization_model_repository import SQLitePersonalizationModelRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.main_window import MainWindow
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.personalization_models_view import PersonalizationModelsView

from tests.test_personalization_data_service import build_environment, build_workspace, make_diagnostic


def _build_model_service(settings, paths, catalog, clip_service, personalization_service, database):
    return build_personalization_training_service(
        settings=settings,
        paths=paths,
        catalog_service=catalog,
        clip_service=clip_service,
        dataset_service=personalization_service,
        model_repository=SQLitePersonalizationModelRepository(database),
        logger=logging.getLogger("test"),
    )


def _make_trainable_report(report):
    snapshot = replace(
        report.snapshot,
        status=PersonalizationDatasetStatus.COMPLETED,
        conflict_count=0,
        readiness_status=PersonalizationReadinessStatus.READY_FOR_BASELINE,
        readiness_score=max(report.snapshot.readiness_score, 0.8),
        warning_code=None,
        warning_message=None,
        error_code=None,
        error_message=None,
    )
    quality_report = report.quality_report
    if quality_report is not None:
        quality_report = replace(
            quality_report,
            leakage_risk_score=min(getattr(quality_report, "leakage_risk_score", 0.0), 0.1),
            readiness_status=PersonalizationReadinessStatus.READY_FOR_BASELINE,
            readiness_score=max(getattr(quality_report, "readiness_score", 0.0), 0.8),
        )
    else:
        quality_report = CreatorDatasetQualityReport(
            id=f"{report.snapshot.id}-quality",
            snapshot_id=report.snapshot.id,
            report_version="1",
            duplicate_ratio=0.0,
            overlap_ratio=0.0,
            missing_feature_ratio=0.0,
            class_balance_score=1.0,
            creator_coverage_score=1.0,
            temporal_coverage_score=1.0,
            source_diversity_score=1.0,
            label_consistency_score=1.0,
            leakage_risk_score=0.0,
            readiness_score=0.9,
            readiness_status=PersonalizationReadinessStatus.READY_FOR_BASELINE,
            recommendations=(),
            created_at=report.snapshot.created_at,
        )
    return replace(
        report,
        snapshot=snapshot,
        quality_report=quality_report,
        warnings=(),
        errors=(),
        is_stale=False,
    )


class PersonalizationModelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_training_baseline_activation_and_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, creator, project, video, transcription, report, clip_service, personalization_service = build_environment(root)
            model_service = _build_model_service(settings, paths, catalog, clip_service, personalization_service, database)

            dataset_report = _make_trainable_report(personalization_service.build_creator_dataset(creator.id))
            self.assertIsNotNone(dataset_report.snapshot)
            original_get_snapshot = personalization_service.get_dataset_snapshot
            original_get_latest = personalization_service.get_latest_creator_dataset
            personalization_service.get_dataset_snapshot = lambda snapshot_id, _report=dataset_report, _original=original_get_snapshot: _report if snapshot_id == _report.snapshot.id else _original(snapshot_id)
            personalization_service.get_latest_creator_dataset = lambda creator_id, _report=dataset_report, _original=original_get_latest: _report if creator_id == _report.creator.id else _original(creator_id)
            validation = model_service.validate_training_snapshot(dataset_report.snapshot.id)
            self.assertEqual(validation.snapshot.id, dataset_report.snapshot.id)
            self.assertTrue(validation.eligible)
            self.assertIn(validation.status, {"ready", "ready_with_warnings"})

            training_report = model_service.train_personalization_baseline(dataset_report.snapshot.id)
            self.assertIsNotNone(training_report.training_run)
            self.assertIn(training_report.training_run.status.value, {"completed", "completed_with_warnings"})
            self.assertTrue(training_report.artifact is not None)
            self.assertTrue(training_report.artifact.model_path.exists())
            self.assertTrue(training_report.artifact.manifest_path.exists())

            run_id = training_report.training_run.id
            metrics = model_service.get_training_metrics(run_id)
            self.assertTrue(metrics)

            predictions = model_service.list_training_predictions(run_id)
            self.assertTrue(predictions)

            active = model_service.activate_model(run_id)
            self.assertTrue(active.artifact_verified)
            current = model_service.get_active_creator_model(creator.id)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.registry_entry.training_run_id, run_id)

            ranking_report = clip_service.get_ranking_run(video.id)
            candidate_id = ranking_report.candidates[0].id
            score_report = model_service.score_candidate_for_creator(creator.id, candidate_id)
            self.assertGreaterEqual(score_report.positive_score, 0.0)
            self.assertLessEqual(score_report.positive_score, 1.0)
            explanation = model_service.explain_personalized_score(creator.id, candidate_id)
            self.assertIn("score", explanation)
            self.assertIn("top_positive_features", explanation)

            artifact_report = model_service.verify_model_artifact(run_id)
            self.assertTrue(artifact_report.artifact_verified)

            deactivate = model_service.deactivate_model(run_id)
            self.assertIsNotNone(deactivate)
            retire = model_service.retire_model(run_id)
            self.assertIsNotNone(retire)

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, creator, project, video, transcription, report, clip_service, personalization_service = build_environment(root)
            model_service = _build_model_service(settings, paths, catalog, clip_service, personalization_service, database)
            snapshot_report = _make_trainable_report(personalization_service.build_creator_dataset(creator.id))
            self.assertIsNotNone(snapshot_report.snapshot)
            original_get_snapshot = personalization_service.get_dataset_snapshot
            original_get_latest = personalization_service.get_latest_creator_dataset
            personalization_service.get_dataset_snapshot = lambda snapshot_id, _report=snapshot_report, _original=original_get_snapshot: _report if snapshot_id == _report.snapshot.id else _original(snapshot_id)
            personalization_service.get_latest_creator_dataset = lambda creator_id, _report=snapshot_report, _original=original_get_latest: _report if creator_id == _report.creator.id else _original(creator_id)
            model_service.train_personalization_baseline(snapshot_report.snapshot.id)

            workspace = build_workspace(settings, paths, catalog, clip_service, personalization_service)
            workspace.model_service = model_service
            view = PersonalizationModelsView(workspace)
            view.refresh()

            window = MainWindow(workspace)
            window.refresh_all()
            self.assertIn("models", window._page_keys)

            parser = build_parser()
            args = parser.parse_args(["models", "validate", "--snapshot-id", snapshot_report.snapshot.id, "--json"])
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
                personalization_service=personalization_service,
                model_service=model_service,
                diagnostic=make_diagnostic(paths.project_root),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["snapshot"]["id"], snapshot_report.snapshot.id)
