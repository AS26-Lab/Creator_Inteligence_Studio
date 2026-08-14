from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.content_brief_service import build_content_brief_service
from creator_intelligence_studio.application.services.creator_feedback_service import CreatorFeedbackService
from creator_intelligence_studio.application.services.creator_preference_application_service import build_creator_preference_application_service
from creator_intelligence_studio.application.services.creator_preference_synthesis_service import (
    build_creator_preference_synthesis_service,
)
from creator_intelligence_studio.application.services.production_preparation_service import build_production_preparation_service
from creator_intelligence_studio.domain.creator_preferences import (
    CreatorConfirmedPreference,
    CreatorPreferenceCandidate,
    CreatorPreferenceCandidateStatus,
    CreatorPreferenceConfidence,
    CreatorPreferenceScope,
    CreatorPreferenceType,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_feedback_repository import (
    SQLiteCreatorFeedbackRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_preference_repository import (
    SQLiteCreatorPreferenceRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import SQLiteContentBriefRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_production_preparation_repository import (
    SQLiteProductionPreparationRepository,
)
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


class _SnapshotSource:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def _item(self):
        return SimpleNamespace(id=f"{self.prefix}-snapshot")

    def list_profile_snapshots(self, creator_id: str):
        return [self._item()]

    def get_profile_snapshot(self, creator_id: str):
        return self._item()

    def build_profile(self, creator_id: str):
        return self._item()

    def get_profile(self, creator_id: str):
        return self._item()

    def list_profiles(self, creator_id: str):
        return [self._item()]

    def generate_weekly_report(self, creator_id: str, *args, **kwargs):
        return self._item()

    def list_reports(self, creator_id: str):
        return [self._item()]

    def build_snapshot(self, creator_id: str, *args, **kwargs):
        return self._item()

    def list_snapshots(self, creator_id: str):
        return [self._item()]

    def list_connections(self, creator_id: str):
        return [self._item()]

    def list_integrations(self, creator_id: str):
        return [self._item()]

    def list_concepts(self, creator_id: str):
        return [self._item()]

    def list_versions(self, creator_id: str):
        return [self._item()]


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


def _load_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("preferences-application-test"))
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    project_id = "project-a"
    feedback_service = CreatorFeedbackService(
        repository=SQLiteCreatorFeedbackRepository(database),
        project_repository=catalog.project_repository,
        brief_service=_ArtifactLookup({}),
        production_service=_ArtifactLookup({}),
        planning_service=_ArtifactLookup({}),
        ai_runtime_service=_ArtifactLookup({}),
        logger=logging.getLogger("preferences-application-test"),
    )
    preference_repository = SQLiteCreatorPreferenceRepository(database)
    synthesis_service = build_creator_preference_synthesis_service(
        repository=preference_repository,
        feedback_service=feedback_service,
        logger=logging.getLogger("preferences-application-test"),
    )
    application_service = build_creator_preference_application_service(
        repository=preference_repository,
        logger=logging.getLogger("preferences-application-test"),
    )
    brief_service = build_content_brief_service(
        settings=settings,
        paths=paths,
        repository=SQLiteContentBriefRepository(database),
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=SimpleNamespace(),
        creator_memory_service=_SnapshotSource("memory"),
        creator_language_service=_SnapshotSource("language"),
        audience_service=_SnapshotSource("audience"),
        analytics_service=_SnapshotSource("analytics"),
        analytics_lab_service=_SnapshotSource("analytics-lab"),
        market_service=_SnapshotSource("market"),
        platform_service=_SnapshotSource("platform"),
        packaging_service=_SnapshotSource("packaging"),
        creator_preference_application_service=application_service,
        logger=logging.getLogger("preferences-application-test"),
    )
    production_service = build_production_preparation_service(
        settings=settings,
        paths=paths,
        repository=SQLiteProductionPreparationRepository(database),
        brief_service=brief_service,
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=SimpleNamespace(),
        creator_memory_service=_SnapshotSource("memory"),
        creator_language_service=_SnapshotSource("language"),
        audience_service=_SnapshotSource("audience"),
        platform_service=_SnapshotSource("platform"),
        packaging_service=_SnapshotSource("packaging"),
        creator_preference_application_service=application_service,
        logger=logging.getLogger("preferences-application-test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator_a=creator_a,
        creator_b=creator_b,
        project_id=project_id,
        preference_repository=preference_repository,
        synthesis_service=synthesis_service,
        application_service=application_service,
        brief_service=brief_service,
        production_service=production_service,
    )


def _confirmed_preference(
    *,
    preference_id: str,
    creator_id: str,
    scope: CreatorPreferenceScope,
    value: str,
    project_id: str | None = None,
    workflow_type: str | None = None,
    active: bool = True,
) -> CreatorConfirmedPreference:
    now = utc_now()
    return CreatorConfirmedPreference(
        id=preference_id,
        preference_key=f"pref-{preference_id}",
        creator_id=creator_id,
        project_id=project_id,
        workflow_type=workflow_type,
        scope=scope,
        preference_type=CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE,
        value_json=json.dumps(
            {
                "preference_type": CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE.value,
                "direction": value,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        source_candidate_id=None,
        confirmed_by="tester",
        confirmed_at=now,
        active=active,
        provenance_json=json.dumps({"source": "manual_confirmation"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at=now,
        updated_at=now,
    )


class CreatorPreferenceApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls.fixture = _load_fixture(Path(cls._temp_dir.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp_dir.cleanup()

    def test_confirmed_preferences_apply_and_are_bounded(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Length A")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-global-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
            )
        )
        bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            current_user_instruction="Write a neutral introduction for the brief.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=True,
            corpus_context_item_count=4,
        )
        self.assertEqual(bundle.preferences_used_count, 1)
        self.assertIn("preferir introducciones mas breves", bundle.rendered_context)
        self.assertTrue(bundle.request_trace["preferences_used"])
        self.assertEqual(bundle.application_state, "corpus_preferences")
        self.assertLessEqual(len(bundle.rendered_context), fixture.application_service.MAX_RENDERED_CHARS)
        self.assertEqual(
            bundle.bundle_fingerprint,
            fixture.application_service.build_application_bundle(
                creator_id=creator.id,
                workflow_type="content_brief",
                current_user_instruction="Write a neutral introduction for the brief.",
                primary_artifact_metadata={"artifact_id": "brief-a"},
                corpus_context_present=True,
                corpus_context_item_count=4,
            ).bundle_fingerprint,
        )

    def test_candidates_inactive_and_cross_creator_preferences_are_ignored(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Ignore A")
        other_creator = fixture.catalog.create_creator(display_name="Creator Ignore B")
        candidate = CreatorPreferenceCandidate(
            id=f"{creator.id}-candidate-short",
            candidate_key=f"{creator.id}-candidate-short-key",
            creator_id=creator.id,
            project_id=None,
            workflow_type=None,
            scope=CreatorPreferenceScope.CREATOR_GLOBAL,
            preference_type=CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE,
            proposed_value="shorter",
            evidence_count=3,
            supporting_signal_count=3,
            conflicting_signal_count=0,
            confidence=CreatorPreferenceConfidence.MEDIUM,
            status=CreatorPreferenceCandidateStatus.CANDIDATE,
            dismissed_evidence_count=0,
            source_signal_ids_json='["signal-1","signal-2","signal-3"]',
            explanation_json='{"summary":"He notado que sueles acortar los textos."}',
            algorithm_version="creator-preference-synthesis-v1",
            first_observed_at=utc_now(),
            last_observed_at=utc_now(),
            confirmed_preference_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        fixture.preference_repository.upsert_candidate(candidate)
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-inactive-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
                active=False,
            )
        )
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{other_creator.id}-pref-creator-b-long",
                creator_id=other_creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="longer",
            )
        )
        bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            current_user_instruction="Write a neutral introduction for the brief.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=False,
            corpus_context_item_count=0,
        )
        self.assertEqual(bundle.preferences_used_count, 0)
        self.assertEqual(bundle.applied_preferences, ())
        self.assertFalse(bundle.confirmed_preferences_present)

    def test_scope_precedence_and_workflow_isolation(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Scope A")
        project = fixture.catalog.create_project(creator_reference=creator.id, name="Project A", project_type="mixed")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-global-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
            )
        )
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-project-long",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.PROJECT_SPECIFIC,
                value="longer",
                project_id=project.id,
            )
        )
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-workflow-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.WORKFLOW_SPECIFIC,
                value="shorter",
                workflow_type="content_brief",
            )
        )
        project_bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            project_id=project.id,
            current_user_instruction="Draft an opening paragraph.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=False,
            corpus_context_item_count=0,
        )
        other_project_bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            project_id="project-b",
            current_user_instruction="Draft an opening paragraph.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=False,
            corpus_context_item_count=0,
        )
        self.assertIn("mas detalladas", project_bundle.rendered_context)
        self.assertEqual(project_bundle.applied_preferences[0].rendered_text, "solo para este proyecto: preferir introducciones mas detalladas.")
        self.assertIn("mas breves", other_project_bundle.rendered_context)

    def test_workflow_specific_preference_does_not_apply_outside_workflow(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Workflow A")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-workflow-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.WORKFLOW_SPECIFIC,
                value="shorter",
                workflow_type="content_brief",
            )
        )
        content_bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            current_user_instruction="Draft an opening paragraph.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=False,
            corpus_context_item_count=0,
        )
        strategic_bundle = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="strategic_planning",
            current_user_instruction="Draft an opening paragraph.",
            primary_artifact_metadata={"artifact_id": "plan-a"},
            corpus_context_present=False,
            corpus_context_item_count=0,
        )
        self.assertEqual(content_bundle.preferences_used_count, 1)
        self.assertEqual(strategic_bundle.preferences_used_count, 0)

    def test_current_user_and_project_instruction_override_preference_application(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Override A")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-global-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
            )
        )
        overridden = fixture.application_service.build_application_bundle(
            creator_id=creator.id,
            workflow_type="content_brief",
            current_user_instruction="Write a long cinematic introduction.",
            project_instruction="Write a long cinematic introduction for this project.",
            primary_artifact_metadata={"artifact_id": "brief-a"},
            corpus_context_present=True,
            corpus_context_item_count=2,
        )
        self.assertEqual(overridden.preferences_used_count, 0)
        self.assertTrue(overridden.request_trace["current_user_override"])
        self.assertTrue(overridden.request_trace["project_override"])
        self.assertTrue(any(item["reason"] == "overridden_by_current_user_instruction" for item in overridden.omitted_preferences))

    def test_content_brief_and_production_context_snapshots_include_preferences(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Snapshot A")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-global-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
            )
        )
        brief = fixture.brief_service.generate_brief(
            creator_id=creator.id,
            source_type="manual_request",
            source_id="",
        )
        brief_snapshot = fixture.brief_service.get_context_snapshot(brief.context_snapshot_id)
        brief_payload = json.loads(brief_snapshot.context_json)
        self.assertIsNotNone(brief_payload["creator_context_package"]["confirmed_preference_context"])
        self.assertIn("confirmed_preference_prompt", brief_payload["creator_context_package"])
        self.assertGreaterEqual(brief_payload["creator_context_usage"]["preference_item_count"], 1)

        brief = fixture.brief_service.review_brief(brief.id, decision="approve", reason="ready", reviewer="tester")
        production_snapshot = fixture.production_service.create_context_snapshot(
            creator.id,
            content_brief_id=brief.id,
            brief_version=int(getattr(brief, "version", 1) or 1),
        )
        production_payload = json.loads(production_snapshot.context_json)
        self.assertIsNotNone(production_payload["creator_context_package"]["confirmed_preference_context"])
        self.assertIsNotNone(production_payload.get("confirmed_preference_application"))

    def test_preferences_apply_preview_cli_and_matrix(self) -> None:
        fixture = self.fixture
        creator = fixture.catalog.create_creator(display_name="Creator Preview A")
        fixture.preference_repository.upsert_confirmed_preference(
            _confirmed_preference(
                preference_id=f"{creator.id}-pref-global-short",
                creator_id=creator.id,
                scope=CreatorPreferenceScope.CREATOR_GLOBAL,
                value="shorter",
            )
        )
        parser = build_parser()
        args = parser.parse_args(
            [
                "preferences",
                "apply-preview",
                "--creator-id",
                creator.id,
                "--workflow-type",
                "content_brief",
                "--json",
            ]
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        exit_code = handle_preferences_command(
            args,
            service=fixture.synthesis_service,
            application_service=fixture.application_service,
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("bundle", payload)
        self.assertEqual(len(payload["matrix"]), 4)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
