from __future__ import annotations

import io
import logging
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.creator_feedback_service import CreatorFeedbackService
from creator_intelligence_studio.application.services.creator_preference_synthesis_service import build_creator_preference_synthesis_service
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_feedback_repository import SQLiteCreatorFeedbackRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_preference_repository import SQLiteCreatorPreferenceRepository
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus, ProjectType
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import SQLiteProjectRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.preferences_cli import handle_preferences_command
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


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
    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get_brief(self, brief_id: str):
        return self._items.get(brief_id)

    def get_outline(self, outline_id: str):
        return self._items.get(outline_id)

    def get_plan(self, plan_id: str):
        return self._items.get(plan_id)

    def get_execution(self, execution_id: str):
        return self._items.get(execution_id)


def _make_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = SimpleNamespace()
    from creator_intelligence_studio.application.services.catalog_service import build_catalog_service

    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("preferences-test"))
    creator = catalog.create_creator(display_name="Creator A")
    project_repo = SQLiteProjectRepository(database)
    project = project_repo.create(
        Project(
            id="project-a",
            creator_id=creator.id,
            name="Project A",
            description=None,
            project_type=ProjectType.MIXED,
            status=ProjectStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    brief_lookup = {
        "brief-1": SimpleNamespace(id="brief-1", creator_id=creator.id),
        "brief-2": SimpleNamespace(id="brief-2", creator_id=creator.id),
        "brief-3": SimpleNamespace(id="brief-3", creator_id=creator.id),
        "brief-4": SimpleNamespace(id="brief-4", creator_id=creator.id),
        "brief-5": SimpleNamespace(id="brief-5", creator_id=creator.id),
        "brief-6": SimpleNamespace(id="brief-6", creator_id=creator.id),
    }
    brief_service = _ArtifactLookup(brief_lookup)
    feedback_service = CreatorFeedbackService(
        repository=SQLiteCreatorFeedbackRepository(database),
        project_repository=project_repo,
        brief_service=brief_service,
        production_service=_ArtifactLookup({}),
        planning_service=_ArtifactLookup({}),
        ai_runtime_service=_ArtifactLookup({}),
        logger=logging.getLogger("preferences-test"),
    )
    preference_service = build_creator_preference_synthesis_service(
        repository=SQLiteCreatorPreferenceRepository(database),
        feedback_service=feedback_service,
        logger=logging.getLogger("preferences-test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator=creator,
        project=project,
        feedback_service=feedback_service,
        preference_service=preference_service,
    )


def _record_length_edit(service: CreatorFeedbackService, *, creator_id: str, artifact_id: str, source_id: str, result_id: str, project_id: str | None = None, workflow_type: str = "content_brief", source_text: str = "one two three four five six", result_text: str = "short text") -> None:
    service.record_edit(
        creator_id=creator_id,
        project_id=project_id,
        workflow_type=workflow_type,
        artifact_type="content_brief",
        artifact_id=artifact_id,
        source_version_id=source_id,
        result_version_id=result_id,
        metadata={"source_text": source_text, "result_text": result_text},
    )


class CreatorPreferencesAndConfirmationTests(unittest.TestCase):
    def test_migration_v37_creates_preference_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings()
            paths = ProjectPaths.from_settings(Path(temp_dir), settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
            self.assertEqual(versions[-1], 37)
            self.assertIn("creator_preference_candidates", tables)
            self.assertIn("creator_preference_candidate_evidence", tables)
            self.assertIn("creator_preferences", tables)

    def test_synthesis_confirm_dismiss_and_rebuild_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _make_fixture(Path(temp_dir))
            service = fixture.preference_service
            creator_id = fixture.creator.id

            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-1", source_id="brief-1", result_id="brief-2")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-3", source_id="brief-3", result_id="brief-4")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-5", source_id="brief-5", result_id="brief-6")

            candidates = service.rebuild_candidates(creator_id)
            self.assertEqual(len(candidates), 1)
            candidate = candidates[0]
            self.assertEqual(candidate.preference_type.value, "content_length_preference")
            self.assertEqual(candidate.proposed_value, "shorter")
            self.assertEqual(candidate.status.value, "candidate")
            self.assertEqual(candidate.evidence_count, 3)
            self.assertIn("He notado", candidate.explanation_json)

            confirmed = service.confirm_candidate(candidate.id, confirmed_by="tester")
            self.assertEqual(confirmed.creator_id, creator_id)
            self.assertEqual(confirmed.active, True)

            confirmed_again = service.list_confirmed_preferences(creator_id)
            self.assertEqual(len(confirmed_again), 1)
            self.assertEqual(confirmed_again[0].id, confirmed.id)

            snapshot = service.preference_snapshot(creator_id)
            self.assertEqual(snapshot.confirmed_count, 1)
            self.assertGreaterEqual(snapshot.active_candidate_count, 1)

            service.dismiss_candidate(candidate.id, dismissed_by="tester", reason="no recordar")
            snapshot_after_dismiss = service.preference_snapshot(creator_id)
            self.assertEqual(snapshot_after_dismiss.dismissed_candidate_count, 1)

            rebuilt = service.rebuild_candidates(creator_id)
            self.assertEqual(len(rebuilt), 1)
            self.assertEqual(rebuilt[0].status.value, "confirmed")

            again = service.rebuild_candidates(creator_id)
            self.assertEqual(len(again), 1)

    def test_scope_conflicts_and_edit_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _make_fixture(Path(temp_dir))
            service = fixture.preference_service
            creator_id = fixture.creator.id
            project_id = fixture.project.id

            _record_length_edit(fixture.feedback_service, creator_id=creator_id, project_id=project_id, artifact_id="brief-1", source_id="brief-1", result_id="brief-2", source_text="a b c d e f g", result_text="short")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, project_id=project_id, artifact_id="brief-3", source_id="brief-3", result_id="brief-4", source_text="a b c d e f g", result_text="short")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, project_id=project_id, artifact_id="brief-5", source_id="brief-5", result_id="brief-6", source_text="a b c d e f g", result_text="short")
            project_candidates = service.rebuild_candidates(creator_id)
            self.assertEqual(len(project_candidates), 1)
            self.assertEqual(project_candidates[0].project_id, project_id)

            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-1", source_id="brief-1", result_id="brief-2", project_id=None, workflow_type="strategic_planning", source_text="short", result_text="a b c d e f g")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-3", source_id="brief-3", result_id="brief-4", project_id=None, workflow_type="strategic_planning", source_text="short", result_text="a b c d e f g")
            _record_length_edit(fixture.feedback_service, creator_id=creator_id, artifact_id="brief-5", source_id="brief-5", result_id="brief-6", project_id=None, workflow_type="strategic_planning", source_text="short", result_text="a b c d e f g")
            global_candidates = service.list_candidates(creator_id)
            self.assertGreaterEqual(len(global_candidates), 1)

            edited_confirm = service.edit_and_confirm_candidate(project_candidates[0].id, confirmed_by="tester", edited_value="Keep intros under 15 seconds.")
            self.assertIn("user_edit", edited_confirm.provenance_json)
            self.assertIn("15 seconds", edited_confirm.value_json)

            deactivated = service.deactivate_preference(edited_confirm.id)
            self.assertIsNotNone(deactivated)
            self.assertFalse(deactivated.active)
            reactivated = service.reactivate_preference(edited_confirm.id)
            self.assertIsNotNone(reactivated)
            self.assertTrue(reactivated.active)

    def test_cli_registration_and_json_surface(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["preferences", "audit-signals", "--json"])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = _make_fixture(Path(temp_dir))
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_preferences_command(args, service=fixture.preference_service, stdout=stdout, stderr=stderr)
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("matrix", payload)
