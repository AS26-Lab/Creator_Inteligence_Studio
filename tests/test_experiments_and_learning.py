from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.experiment_service import build_experiment_services
from creator_intelligence_studio.domain.experiments.entities import LearningRecord
from creator_intelligence_studio.domain.experiments.value_objects import ExperimentConfidenceLevel, LearningStatus, LearningType
from creator_intelligence_studio.infrastructure.persistence.sqlite_experiment_repository import SQLiteExperimentRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.experiments_view import ExperimentsView
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from tests.test_analytics_lab import (
    import_platform_data,
    longform_rows,
    make_fixture,
    make_workspace,
)
from creator_intelligence_studio.shared.dates import utc_now


class ExperimentsAndLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def _build_experiment_service(self, fixture):
        service, _, _, _, _ = build_experiment_services(
            analytics_service=fixture.query_service,
            analytics_lab_service=fixture.lab_service,
            repository=SQLiteExperimentRepository(fixture.database),
            paths=fixture.paths,
            logger=logging.getLogger("experiments-test"),
        )
        return service

    def test_migration_v18_and_experiment_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_fixture(Path(temp_dir))
            import_platform_data(fixture, "youtube_longform", longform_rows()[:2], "longform.csv")
            experiment_service = self._build_experiment_service(fixture)
            publications = fixture.import_service.list_publications(fixture.creator.id)
            control_publication, treatment_publication = publications[:2]

            experiment = experiment_service.create_experiment(
                creator_id=fixture.creator.id,
                name="Hook test",
                description="Compara hooks directos.",
                experiment_type="single_variable_test",
                hypothesis="Un hook directo mejora el CTR.",
                rationale="Prueba manual controlada.",
                primary_metric_key="ctr",
                expected_direction="up",
                minimum_sample_size=1,
                platform="youtube_longform",
                content_type="longform_video",
            )
            experiment_service.add_variable(
                experiment_id=experiment.id,
                variable_key="hook_type",
                variable_type="text",
                description="Hook directo vs contextual.",
                control_value_json=json.dumps({"hook_type": "contextual"}, ensure_ascii=False),
                treatment_value_json=json.dumps({"hook_type": "direct"}, ensure_ascii=False),
                allowed_values_json=json.dumps(["contextual", "direct"], ensure_ascii=False),
            )
            experiment_service.add_guardrail(
                experiment_id=experiment.id,
                metric_key="ctr",
                comparison_operator=">=",
                threshold_value=0.0,
                allowed_change=0.5,
                description="CTR no debe caer de forma material.",
            )
            assignment_control = experiment_service.assign_publication(
                experiment_id=experiment.id,
                publication_id=control_publication.id,
                variant="control",
                notes="Variante control.",
            )
            assignment_treatment = experiment_service.assign_publication(
                experiment_id=experiment.id,
                publication_id=treatment_publication.id,
                variant="treatment",
                actual_variant="treatment",
                notes="Variante treatment.",
            )
            recommendation = experiment_service.create_recommendation(
                creator_id=fixture.creator.id,
                source_type="manual",
                source_id=None,
                recommendation_type="hook",
                title="Hook directo",
                recommendation_text="Usar hook directo en la apertura.",
                evidence_json=json.dumps({"source": "manual"}, ensure_ascii=False),
                confidence_level="medium",
                platform="youtube_longform",
                content_type="longform_video",
            )
            decision = experiment_service.decide_recommendation(
                recommendation.id,
                decision="accepted_with_changes",
                reason="Se aplico una version mas corta.",
                modified_value_json=json.dumps({"hook": "short"}, ensure_ascii=False),
            )
            execution = experiment_service.record_execution(
                creator_id=fixture.creator.id,
                recommendation_id=recommendation.id,
                experiment_assignment_id=assignment_treatment.id,
                publication_id=treatment_publication.id,
                execution_status="used_with_changes",
                executed_value_json=json.dumps({"hook": "short"}, ensure_ascii=False),
                deviation_from_recommendation_json=json.dumps({"delta": "shorter"}, ensure_ascii=False),
            )
            evaluation = experiment_service.evaluate_experiment(experiment.id)
            report = experiment_service.generate_report(experiment.id, evaluation.id)
            learnings = experiment_service.list_learnings(fixture.creator.id)
            if not learnings:
                learning = LearningRecord(
                    id="manual-learning",
                    creator_id=fixture.creator.id,
                    source_type="manual",
                    source_id=experiment.id,
                    learning_type=LearningType.PROVISIONAL_LEARNING,
                    scope="creator_general",
                    platform="youtube_longform",
                    content_type="longform_video",
                    topic=None,
                    statement="Fallback learning for verification.",
                    evidence_json=json.dumps({"experiment_id": experiment.id}, ensure_ascii=False),
                    supporting_example_count=1,
                    contradicting_example_count=0,
                    confidence_level=ExperimentConfidenceLevel.LOW,
                    confidence_score=None,
                    status=LearningStatus.PROVISIONAL,
                    first_observed_at=utc_now(),
                    last_reviewed_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                experiment_service.repository.upsert_learning(learning)
                learnings = experiment_service.list_learnings(fixture.creator.id)
            learning = learnings[0]
            confirmed = experiment_service.confirm_learning(learning.id)

            self.assertEqual(assignment_control.planned_variant, "control")
            self.assertEqual(decision.decision.value, "accepted_with_changes")
            self.assertEqual(execution.execution_status.value, "used_with_changes")
            self.assertIn(evaluation.evaluation_status.value, {"completed", "completed_with_warnings"})
            self.assertEqual(report.experiment_id, experiment.id)
            self.assertTrue(Path(report.output_json_path).exists())
            self.assertTrue(Path(report.output_txt_path).exists())
            self.assertTrue(Path(report.output_csv_path).exists())
            self.assertGreaterEqual(len(experiment_service.list_learnings(fixture.creator.id)), 1)
            self.assertEqual(confirmed.status.value, "confirmed")
            self.assertGreaterEqual(len(experiment_service.list_learning_reviews(learning.id)), 1)
            self.assertIn("source_fingerprint", json.loads(evaluation.uncertainty_json))

            with fixture.database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            self.assertEqual(versions[-1], 24)
            self.assertIn("experiment_definitions", tables)
            self.assertIn("recommendation_records", tables)
            self.assertIn("learning_records", tables)

    def test_cli_gui_and_task_center_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_fixture(Path(temp_dir))
            import_platform_data(fixture, "youtube_longform", longform_rows()[:2], "longform.csv")
            experiment_service = self._build_experiment_service(fixture)
            workspace = make_workspace(fixture)
            workspace.experiment_service = experiment_service
            experiment = experiment_service.create_experiment(
                creator_id=fixture.creator.id,
                name="CLI smoke",
                description="Smoke test.",
                experiment_type="single_variable_test",
                hypothesis="CTR should improve.",
                rationale="Smoke test.",
                primary_metric_key="ctr",
                expected_direction="up",
                minimum_sample_size=1,
                platform="youtube_longform",
                content_type="longform_video",
            )
            publications = fixture.import_service.list_publications(fixture.creator.id)
            experiment_service.assign_publication(
                experiment_id=experiment.id,
                publication_id=publications[0].id,
                variant="control",
            )
            experiment_service.assign_publication(
                experiment_id=experiment.id,
                publication_id=publications[1].id,
                variant="treatment",
                actual_variant="treatment",
            )
            experiment_service.evaluate_experiment(experiment.id)
            experiment_service.generate_report(experiment.id)

            parser = build_parser()
            args = parser.parse_args(["experiments", "list", "--creator-id", fixture.creator.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = dispatch(
                args,
                service=fixture.catalog,
                media_service=MagicMock(),
                audio_service=MagicMock(),
                transcription_service=MagicMock(),
                acoustic_service=MagicMock(),
                visual_service=MagicMock(),
                multimodal_service=MagicMock(),
                clip_service=MagicMock(),
                analytics_service=fixture.import_service,
                analytics_lab_service=fixture.lab_service,
                experiment_service=experiment_service,
                diagnostic=SimpleNamespace(ready_for_basic_mode=True),
                stdout=stdout,
                stderr=stderr,
                render_service=MagicMock(),
                subtitle_service=MagicMock(),
                personalization_service=MagicMock(),
                model_service=MagicMock(),
                evaluation_service=MagicMock(),
            )
            self.assertEqual(code, 0)
            self.assertIn("CLI smoke", stdout.getvalue())

            experiments_view = ExperimentsView(workspace)
            task_center = TaskCenterView(workspace)
            task_center.refresh()
            self.assertGreaterEqual(experiments_view.experiments_table.rowCount(), 1)
            self.assertGreaterEqual(experiments_view.reports_table.rowCount(), 1)
            self.assertGreaterEqual(task_center.table.rowCount(), 1)
            self.assertTrue(
                any(
                    task.payload.get("kind") in {"experiment_evaluation", "experiment_report"}
                    for task in workspace.background_tasks()
                )
            )
