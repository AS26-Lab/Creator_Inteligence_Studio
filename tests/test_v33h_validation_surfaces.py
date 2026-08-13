from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.strategic_planning_service import StrategicPlanningService
from creator_intelligence_studio.domain.projects.entities import ProjectType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_strategic_planning_repository import SQLiteStrategicPlanningRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.feedback_cli import handle_feedback_command
from creator_intelligence_studio.presentation.cli.planning_cli import handle_planning_command
from creator_intelligence_studio.shared.paths import ProjectPaths

from tests.test_creator_feedback_and_learning_signals import _build_direct_feedback_fixture
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


def _build_planning_fixture(temp_dir: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(temp_dir, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("v33h-test"))
    creator = catalog.create_creator(display_name="Creator A")
    project = catalog.create_project(creator_reference=creator.id, name="Project A", project_type=ProjectType.MIXED.value)
    planning_service = StrategicPlanningService(
        settings=settings,
        paths=paths,
        repository=SQLiteStrategicPlanningRepository(database),
        recommendation_service=FakeRecommendationService({}),
        creator_memory_service=SnapshotProvider("memory-snapshot"),
        creator_language_service=SnapshotProvider("language-snapshot"),
        audience_service=SnapshotProvider("audience-snapshot"),
        analytics_lab_service=SnapshotProvider("analytics-snapshot"),
        market_service=SnapshotProvider("market-snapshot"),
        experiment_service=SnapshotProvider("experiment-snapshot"),
        content_library_service=SnapshotProvider("content-snapshot"),
        platform_service=SnapshotProvider("platform-snapshot"),
        logger=logging.getLogger("v33h-test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator=creator,
        project=project,
        planning_service=planning_service,
    )


class V33HValidationSurfaceTests(unittest.TestCase):
    def test_new_cli_surfaces_are_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "planning",
                "context-snapshot-create",
                "--creator-id",
                "creator-a",
            ]
        )
        self.assertEqual(args.entity, "planning")
        self.assertEqual(args.action, "context-snapshot-create")

        feedback_args = parser.parse_args(
            [
                "feedback",
                "record-edit",
                "--creator-id",
                "creator-a",
                "--workflow-type",
                "content_brief",
                "--artifact-type",
                "content_brief",
                "--artifact-id",
                "brief-a",
                "--source-version-id",
                "brief-a",
                "--result-version-id",
                "brief-b",
            ]
        )
        self.assertEqual(feedback_args.entity, "feedback")
        self.assertEqual(feedback_args.action, "record-edit")

    def test_planning_context_snapshot_command_uses_canonical_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_planning_fixture(Path(temp_dir))
            stdout = io.StringIO()
            stderr = io.StringIO()
            args = build_parser().parse_args(
                [
                    "planning",
                    "context-snapshot-create",
                    "--creator-id",
                    fixture.creator.id,
                    "--project-id",
                    fixture.project.id,
                    "--json",
                ]
            )

            code = handle_planning_command(args, service=fixture.planning_service, stdout=stdout, stderr=stderr, catalog_service=fixture.catalog)

            payload = json.loads(stdout.getvalue())
            snapshot = fixture.planning_service.get_context_snapshot(payload["snapshot_id"])
            plan = fixture.planning_service.create_plan(creator_id=fixture.creator.id, name="Plan A", context_snapshot_id=snapshot.id)

        self.assertEqual(code, 0)
        self.assertEqual(payload["creator_id"], fixture.creator.id)
        self.assertEqual(payload["project_id"], fixture.project.id)
        self.assertEqual(payload["snapshot_type"], "planning_context_snapshot")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.creator_id, fixture.creator.id)
        self.assertEqual(plan.context_snapshot_id, snapshot.id)

    def test_feedback_record_edit_command_creates_idempotent_edited_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_direct_feedback_fixture(Path(temp_dir))
            stdout = io.StringIO()
            stderr = io.StringIO()
            args = build_parser().parse_args(
                [
                    "feedback",
                    "record-edit",
                    "--creator-id",
                    fixture.creator_a.id,
                    "--workflow-type",
                    "content_brief",
                    "--artifact-type",
                    "content_brief",
                    "--artifact-id",
                    "brief-b",
                    "--source-version-id",
                    "brief-b",
                    "--result-version-id",
                    "brief-c",
                    "--json",
                ]
            )

            code_first = handle_feedback_command(
                args,
                service=fixture.feedback_service,
                stdout=stdout,
                stderr=stderr,
                brief_service=fixture.brief_service,
            )
            first_payload = json.loads(stdout.getvalue())
            stdout.seek(0)
            stdout.truncate(0)
            code_second = handle_feedback_command(
                args,
                service=fixture.feedback_service,
                stdout=stdout,
                stderr=stderr,
                brief_service=fixture.brief_service,
            )
            second_payload = json.loads(stdout.getvalue())
            events = fixture.feedback_service.list_feedback_events(fixture.creator_a.id, event_type="edited")
            signals = fixture.feedback_service.list_learning_signals(fixture.creator_a.id)

        self.assertEqual(code_first, 0)
        self.assertEqual(code_second, 0)
        self.assertEqual(first_payload["event_type"], "edited")
        self.assertEqual(first_payload["source_version_id"], "brief-b")
        self.assertEqual(first_payload["result_version_id"], "brief-c")
        self.assertEqual(first_payload["diff_algorithm_version"], "creator-text-diff-v1")
        self.assertEqual(first_payload["id"], second_payload["id"])
        self.assertEqual(len(events), 1)
        self.assertGreaterEqual(len(signals), 1)

    def test_feedback_record_edit_rejects_cross_creator_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _build_direct_feedback_fixture(Path(temp_dir))
            stdout = io.StringIO()
            stderr = io.StringIO()
            args = build_parser().parse_args(
                [
                    "feedback",
                    "record-edit",
                    "--creator-id",
                    fixture.creator_a.id,
                    "--workflow-type",
                    "content_brief",
                    "--artifact-type",
                    "content_brief",
                    "--artifact-id",
                    "brief-a",
                    "--source-version-id",
                    "brief-f",
                    "--result-version-id",
                    "brief-a",
                    "--json",
                ]
            )

            code = handle_feedback_command(
                args,
                service=fixture.feedback_service,
                stdout=stdout,
                stderr=stderr,
                brief_service=fixture.brief_service,
            )

        self.assertEqual(code, 1)
        self.assertIn("no pertenece al creador", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
