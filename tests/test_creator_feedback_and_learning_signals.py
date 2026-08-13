from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from creator_intelligence_studio.application.services.content_brief_service import build_content_brief_service
from creator_intelligence_studio.application.services.creator_feedback_service import CreatorFeedbackService
from creator_intelligence_studio.application.services.production_preparation_service import build_production_preparation_service
from creator_intelligence_studio.application.services.strategic_planning_service import StrategicPlanningService
from creator_intelligence_studio.domain.creator_feedback import CreatorLearningSignalStatus, CreatorLearningSignalType
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import SQLiteContentBriefRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_feedback_repository import SQLiteCreatorFeedbackRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_production_preparation_repository import SQLiteProductionPreparationRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_strategic_planning_repository import SQLiteStrategicPlanningRepository
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths

from tests.test_content_brief_and_preproduction_foundation import make_brief_service
from tests.test_script_outline_and_production_preparation_foundation import make_production_fixture
from tests.test_strategic_planning_and_content_roadmap_foundation import FakeRecommendationService, SnapshotProvider


def make_settings() -> AppSettings:
    return AppSettings(
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
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
    )


class _ArtifactLookup:
    def __init__(self, *, briefs=None, outlines=None, plans=None, executions=None) -> None:
        self._briefs = briefs or {}
        self._outlines = outlines or {}
        self._plans = plans or {}
        self._executions = executions or {}

    def get_brief(self, brief_id: str):
        return self._briefs.get(brief_id)

    def get_outline(self, outline_id: str):
        return self._outlines.get(outline_id)

    def get_plan(self, plan_id: str):
        return self._plans.get(plan_id)

    def get_execution(self, execution_id: str):
        return self._executions.get(execution_id)


def _build_direct_feedback_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("feedback-test"))
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    project_repo = SQLiteProjectRepository(database)
    project = project_repo.create(
        Project(
            id=str(uuid4()),
            creator_id=creator_a.id,
            name="Project A",
            description=None,
            project_type=ProjectType.MIXED,
            status=ProjectStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    feedback_repo = SQLiteCreatorFeedbackRepository(database)
    brief_service = _ArtifactLookup(
        briefs={
            "brief-a": SimpleNamespace(id="brief-a", creator_id=creator_a.id),
            "brief-b": SimpleNamespace(id="brief-b", creator_id=creator_a.id),
            "brief-c": SimpleNamespace(id="brief-c", creator_id=creator_a.id),
            "brief-d": SimpleNamespace(id="brief-d", creator_id=creator_a.id),
            "brief-e": SimpleNamespace(id="brief-e", creator_id=creator_a.id),
            "brief-f": SimpleNamespace(id="brief-f", creator_id=creator_b.id),
        }
    )
    feedback_service = CreatorFeedbackService(
        repository=feedback_repo,
        project_repository=project_repo,
        brief_service=brief_service,
        production_service=_ArtifactLookup(),
        planning_service=_ArtifactLookup(),
        ai_runtime_service=_ArtifactLookup(),
        logger=logging.getLogger("feedback-test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator_a=creator_a,
        creator_b=creator_b,
        project=project,
        feedback_repo=feedback_repo,
        feedback_service=feedback_service,
        brief_service=brief_service,
        project_repo=project_repo,
    )


class CreatorFeedbackAndLearningSignalsTests(unittest.TestCase):
    def test_migration_v36_is_idempotent_and_creates_feedback_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings()
            paths = ProjectPaths.from_settings(Path(temp_dir), settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            self.assertEqual(versions[-1], 37)
            self.assertIn("creator_feedback_events", tables)
            self.assertIn("creator_learning_signals", tables)
            self.assertIn("creator_learning_signal_evidence", tables)

    def test_feedback_events_are_idempotent_and_build_candidate_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_direct_feedback_fixture(Path(temp_dir))
            service = fixture.feedback_service
            creator_id = fixture.creator_a.id

            accept_a = service.record_acceptance(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-a",
            )
            duplicate_accept = service.record_acceptance(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-a",
            )
            service.record_acceptance(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-b",
            )
            service.record_acceptance(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-c",
            )
            service.record_rejection(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-d",
            )
            regenerated = service.record_regeneration(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-e",
            )
            edited = service.record_edit(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-b",
                source_version_id="brief-b",
                result_version_id="brief-c",
                metadata={
                    "source_text": "This is a longer draft with extra context.",
                    "result_text": "Shorter draft.",
                },
            )

            events = service.list_feedback_events(creator_id)
            signals = service.list_learning_signals(creator_id)
            acceptance_signals = service.list_learning_signals(creator_id, signal_type=CreatorLearningSignalType.ACCEPTANCE.value)
            length_signals = service.list_learning_signals(creator_id, signal_type=CreatorLearningSignalType.LENGTH_CHANGE.value)
            event_payload = json.loads(service.get_feedback_event(edited.id).metadata_json)
            snapshot = service.learning_snapshot(creator_id)
            health = service.health(creator_id)
            rebuilt = service.rebuild_learning_signals(creator_id)

            self.assertEqual(accept_a.id, duplicate_accept.id)
            self.assertEqual(len(events), 6)
            self.assertEqual(len(acceptance_signals), 1)
            self.assertEqual(acceptance_signals[0].evidence_count, 3)
            self.assertEqual(acceptance_signals[0].status, CreatorLearningSignalStatus.CANDIDATE)
            self.assertEqual(len(length_signals), 1)
            self.assertEqual(event_payload["diff_summary"]["algorithm_version"], "creator-text-diff-v1")
            self.assertEqual(event_payload["diff_summary"]["length_direction"], "shorter")
            self.assertEqual(regenerated.event_type.value, "regenerated")
            self.assertEqual(edited.event_type.value, "edited")
            self.assertGreaterEqual(len(signals), 4)
            self.assertEqual(snapshot.creator_id, creator_id)
            self.assertGreaterEqual(snapshot.candidate_signal_count, 1)
            self.assertEqual(health["candidate_signal_count"], snapshot.candidate_signal_count)
            self.assertTrue(rebuilt)

    def test_creator_isolation_and_project_scope_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_direct_feedback_fixture(Path(temp_dir))
            service = fixture.feedback_service
            creator_id = fixture.creator_a.id
            other_creator_id = fixture.creator_b.id

            with self.assertRaises(ValueError):
                service.record_acceptance(
                    creator_id=creator_id,
                    workflow_type="content_brief",
                    artifact_type="content_brief",
                    artifact_id="brief-f",
                )

            project_signal = service.record_acceptance(
                creator_id=creator_id,
                project_id=fixture.project.id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-a",
            )
            global_signal = service.record_acceptance(
                creator_id=creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id="brief-b",
            )
            project_signals = service.list_learning_signals(creator_id, project_id=fixture.project.id)
            global_signals = service.list_learning_signals(creator_id, project_id=None)

            self.assertEqual(project_signal.creator_id, creator_id)
            self.assertEqual(global_signal.creator_id, creator_id)
            self.assertEqual(len(project_signals), 1)
            self.assertEqual(len(global_signals), 2)
            self.assertEqual(project_signals[0].project_id, fixture.project.id)
            self.assertTrue(any(signal.project_id is None for signal in global_signals))

            with self.assertRaises(ValueError):
                service.record_acceptance(
                    creator_id=other_creator_id,
                    project_id=fixture.project.id,
                    workflow_type="content_brief",
                    artifact_type="content_brief",
                    artifact_id="brief-f",
                )

    def test_workflow_integrations_record_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, database, catalog, brief_service = make_brief_service(root, creator_id="creator-a")
            with database.connect() as connection:
                run_migrations(connection)
            creator = catalog.list_creators()[0]
            feedback_service = CreatorFeedbackService(
                repository=SQLiteCreatorFeedbackRepository(database),
                brief_service=brief_service,
                production_service=_ArtifactLookup(),
                planning_service=_ArtifactLookup(),
                ai_runtime_service=_ArtifactLookup(),
                logger=logging.getLogger("feedback-test"),
            )
            brief_service.creator_feedback_service = feedback_service

            request_a = brief_service.create_request(creator_id=creator.id, source_type="manual_request", source_id="feedback-a")
            request_b = brief_service.create_request(creator_id=creator.id, source_type="manual_request", source_id="feedback-b")
            brief_a = brief_service.generate_brief(request_id=request_a.id)
            brief_b = brief_service.generate_brief(request_id=request_b.id)
            brief_service.review_brief(brief_a.id, decision="approve", reason="ready", reviewer="tester")
            brief_service.review_brief(brief_b.id, decision="reject", reason="not ready", reviewer="tester")

            production_fixture = make_production_fixture(root)
            with production_fixture.database.connect() as connection:
                run_migrations(connection)
            production_feedback = CreatorFeedbackService(
                repository=SQLiteCreatorFeedbackRepository(production_fixture.database),
                brief_service=production_fixture.brief_service,
                production_service=production_fixture.production_service,
                planning_service=_ArtifactLookup(),
                ai_runtime_service=_ArtifactLookup(),
                logger=logging.getLogger("feedback-test"),
            )
            production_fixture.brief_service.creator_feedback_service = production_feedback
            production_fixture.production_service.creator_feedback_service = production_feedback
            request = production_fixture.production_service.create_request(creator_id=production_fixture.creator_a.id, content_brief_id=production_fixture.brief_a.id)
            outline = production_fixture.production_service.generate_outline(request_id=request.id)
            production_fixture.production_service.review_outline(outline.id, decision="approve", reason="ready", reviewer="tester")

            plan_fixture = _build_direct_feedback_fixture(Path(temp_dir) / "planning")
            planning_service = StrategicPlanningService(
                settings=plan_fixture.settings,
                paths=plan_fixture.paths,
                repository=SQLiteStrategicPlanningRepository(plan_fixture.database),
                recommendation_service=FakeRecommendationService({}),
                creator_memory_service=SnapshotProvider("memory-snapshot"),
                creator_language_service=SnapshotProvider("language-snapshot"),
                creator_context_assembly_service=SnapshotProvider("context-snapshot"),
                creator_context_policy_registry=None,
                audience_service=SnapshotProvider("audience-snapshot"),
                analytics_service=SnapshotProvider("analytics-snapshot"),
                analytics_lab_service=SnapshotProvider("analytics-lab-snapshot"),
                market_service=SnapshotProvider("market-snapshot"),
                experiment_service=SnapshotProvider("experiment-snapshot"),
                content_library_service=SnapshotProvider("content-snapshot"),
                platform_service=SnapshotProvider("platform-snapshot"),
                logger=logging.getLogger("feedback-test"),
            )
            plan_fixture.feedback_service.planning_service = planning_service
            planning_service.creator_feedback_service = plan_fixture.feedback_service
            snapshot = planning_service.create_context_snapshot(plan_fixture.creator_a.id, use_creator_context=False)
            plan = planning_service.create_plan(creator_id=plan_fixture.creator_a.id, name="Plan feedback", context_snapshot_id=snapshot.id, horizon_type="quarterly")
            planning_service.approve_plan(plan.id, reason="ready", reviewer="tester")

            brief_events = feedback_service.list_feedback_events(creator.id, workflow_type="content_brief")
            production_events = production_feedback.list_feedback_events(production_fixture.creator_a.id, workflow_type="production_preparation")
            planning_events = plan_fixture.feedback_service.list_feedback_events(plan_fixture.creator_a.id, workflow_type="strategic_planning")

            self.assertEqual(len(brief_events), 2)
            self.assertEqual({event.event_type.value for event in brief_events}, {"accepted", "rejected"})
            self.assertEqual(len(production_events), 1)
            self.assertEqual(production_events[0].event_type.value, "accepted")
            self.assertEqual(len(planning_events), 1)
            self.assertEqual(planning_events[0].event_type.value, "accepted")
