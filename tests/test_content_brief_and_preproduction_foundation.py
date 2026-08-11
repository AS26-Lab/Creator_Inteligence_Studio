from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.content_brief_service import build_content_brief_service
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import (
    SQLiteContentBriefRepository,
)
from creator_intelligence_studio.presentation.cli.briefs_cli import handle_briefs_command
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.briefs_overview_view import BriefsOverviewView
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
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


def _item(identifier: str, **kwargs):
    return SimpleNamespace(id=identifier, **kwargs)


class FixedSnapshotSource:
    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id

    def _item(self):
        return _item(self.snapshot_id)

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


class FakePlanningService:
    def __init__(self, creator_id: str) -> None:
        self.creator_id = creator_id
        self._roadmap = {
            "roadmap-a": _item(
                "roadmap-a",
                creator_id=creator_id,
                title="Roadmap A",
                description="Roadmap source",
                status="approved",
                strategic_plan_id="plan-a",
                platform_scope_json='["youtube"]',
                content_type_scope_json='["video"]',
                objective_scope_json='["discovery"]',
                copying_risk="moderate",
                rights_status="unknown",
            )
        }

    def get_roadmap_item(self, item_id: str):
        return self._roadmap.get(item_id)

    def show_roadmap_item(self, item_id: str):
        return self.get_roadmap_item(item_id)

    def get_plan(self, plan_id: str):
        return _item(plan_id, id=plan_id, name="Plan", status="active", platform_scope_json='["youtube"]')

    def list_dependencies_for_item(self, item_id: str):
        return []

    def list_tasks(self, creator_id: str):
        return [
            _item(
                f"planning-task-{creator_id}",
                to_dict=lambda: {
                    "id": f"planning-task-{creator_id}",
                    "plan_id": "plan-a",
                    "status": "draft",
                    "current_stage": "building_roadmap",
                    "progress_percent": 10.0,
                    "warnings": [],
                    "errors": [],
                    "created_at": "2026-07-28T00:00:00Z",
                    "updated_at": "2026-07-28T00:00:00Z",
                },
            )
        ]


class FakeRecommendationService:
    def __init__(self, creator_id: str) -> None:
        self.creator_id = creator_id
        self._recommendations = {
            "rec-a": _item(
                "rec-a",
                creator_id=creator_id,
                title="Recommendation A",
                summary="Recommendation source",
                status="approved",
                platform_scope_json='["youtube"]',
                content_type_scope_json='["video"]',
                objective_scope_json='["discovery"]',
                copying_risk="low",
                rights_status="unknown",
                experiment_id="exp-a",
                evidence_json=[],
                constraints_json=[],
            )
        }

    def get_recommendation(self, recommendation_id: str):
        return self._recommendations.get(recommendation_id)

    def show_recommendation(self, recommendation_id: str):
        return self.get_recommendation(recommendation_id)

    def get_candidate(self, recommendation_id: str):
        return self.get_recommendation(recommendation_id)

    def list_recommendations(self, creator_id: str):
        approved = self._recommendations.get("rec-a")
        return [approved] if approved and creator_id == self.creator_id else []

    def list_candidates(self, creator_id: str):
        return self.list_recommendations(creator_id)

    def build_background_tasks(self, creator_id: str):
        return [
            {
                "task_id": f"recommendation-task-{creator_id}",
                "title": "Recommendation",
                "status": "completed",
                "stage_name": "done",
                "video_id": None,
                "video_title": "Recommendation",
                "action_id": None,
                "progress_percent": 100.0,
                "message": "ok",
                "error": None,
                "cancellable": False,
                "created_at": "2026-07-28T00:00:00Z",
                "updated_at": "2026-07-28T00:00:00Z",
                "payload": {"kind": "recommendation_run"},
            }
        ]


class FakeExperimentService:
    def __init__(self, creator_id: str) -> None:
        self.creator_id = creator_id
        self._experiment = _item(
            "exp-a",
            creator_id=creator_id,
            title="Experiment A",
            name="Experiment A",
            status="active",
            hypothesis_json=[{"text": "hypothesis"}],
            platform_scope_json='["youtube"]',
            content_type_scope_json='["video"]',
            objective_scope_json='["discovery"]',
            copying_risk="low",
            rights_status="unknown",
        )

    def get_experiment(self, experiment_id: str):
        return self._experiment if experiment_id == self._experiment.id else None

    def show_experiment(self, experiment_id: str):
        return self.get_experiment(experiment_id)

    def list_experiments(self, creator_id: str):
        return [self._experiment] if creator_id == self.creator_id else []


class FakeContentLibraryService:
    def __init__(self, creator_id: str) -> None:
        self.creator_id = creator_id
        self._content = _item(
            "content-a",
            creator_id=creator_id,
            title="Content A",
            summary="Content draft",
            status="draft",
            platform_scope_json='["youtube"]',
            content_type_scope_json='["video"]',
            objective_scope_json='["discovery"]',
            references=[],
            constraints=[],
        )

    def get_content_item(self, content_id: str):
        return self._content if content_id == self._content.id else None

    def get_content(self, content_id: str):
        return self.get_content_item(content_id)

    def show_content(self, content_id: str):
        return self.get_content_item(content_id)

    def get_item(self, content_id: str):
        return self.get_content_item(content_id)

    def list_content(self, creator_id: str):
        return [self._content] if creator_id == self.creator_id else []


def make_brief_service(root: Path, *, creator_id: str):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("test"))
    creator_a = catalog.create_creator(display_name="Creator A")
    catalog.create_creator(display_name="Creator B")
    effective_creator_id = creator_a.id
    with database.connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO planning_context_snapshots (
                id, creator_id, context_version, recommendation_snapshot_id, creator_memory_snapshot_id,
                creator_language_snapshot_id, audience_snapshot_id, analytics_snapshot_id, market_snapshot_id,
                experiment_snapshot_id, content_library_snapshot_id, platform_snapshot_id, source_fingerprint,
                context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "planning-context-a",
                effective_creator_id,
                "v28",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "planning-context-a-fingerprint",
                "{}",
                "2026-07-28T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO strategic_plans (
                id, creator_id, name, description, status, horizon_type, start_date, end_date, timezone,
                primary_objective_id, context_snapshot_id, version, parent_plan_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "plan-a",
                effective_creator_id,
                "Plan A",
                "Test plan",
                "active",
                "quarterly",
                None,
                None,
                "America/Mexico_City",
                None,
                "planning-context-a",
                1,
                None,
                "2026-07-28T00:00:00Z",
                "2026-07-28T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO roadmap_items (
                id, creator_id, strategic_plan_id, planning_cycle_id, strategic_initiative_id, campaign_id,
                content_series_id, recommendation_candidate_id, experiment_id, internal_content_id, item_type,
                title, description, status, priority_level, sequence_order, tentative_start, tentative_end,
                confirmed_start, confirmed_end, platform_scope_json, content_type_scope_json, objective_scope_json,
                estimated_effort, estimated_duration_hours, assigned_capacity_units, confidence_level,
                source_fingerprint, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "roadmap-a",
                effective_creator_id,
                "plan-a",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "content_concept",
                "Roadmap A",
                "Roadmap source",
                "approved",
                "high",
                1,
                None,
                None,
                None,
                None,
                "[\"youtube\"]",
                "[\"video\"]",
                "[\"discovery\"]",
                "medium",
                1.0,
                1.0,
                "medium",
                "roadmap-a-fingerprint",
                "2026-07-28T00:00:00Z",
                "2026-07-28T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO recommendation_context_snapshots (
                id, creator_id, context_type, context_version, creator_memory_snapshot_id,
                creator_language_snapshot_id, audience_snapshot_id, analytics_snapshot_id, market_snapshot_id,
                platform_snapshot_id, experiment_snapshot_id, packaging_snapshot_id, source_fingerprint,
                context_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rec-context-a",
                effective_creator_id,
                "planning",
                "v27",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "rec-context-a-fingerprint",
                "{}",
                "2026-07-28T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO recommendation_runs (
                id, creator_id, request_id, context_snapshot_id, status, configuration_json, candidate_count,
                generated_count, skipped_count, warning_count, error_count, started_at, completed_at,
                error_code, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-a",
                effective_creator_id,
                None,
                "rec-context-a",
                "completed",
                "{}",
                1,
                1,
                0,
                0,
                0,
                "2026-07-28T00:00:00Z",
                "2026-07-28T00:00:00Z",
                None,
                None,
                "2026-07-28T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO recommendation_candidates (
                id, creator_id, recommendation_run_id, source_opportunity_candidate_id, recommendation_type,
                objective_type, title, summary, platform_scope_json, content_type_scope_json, audience_scope_json,
                market_scope_json, topic_scope_json, time_horizon, status, priority_level, priority_score,
                confidence_level, confidence_score, freshness_status, expires_at, creator_fit, audience_fit,
                historical_fit, market_fit, platform_fit, strategic_fit, authenticity_fit, timing_fit,
                differentiation_potential, operational_feasibility, expected_learning_value, copying_risk,
                overall_risk, created_at, updated_at
            ) VALUES (
                :id, :creator_id, :recommendation_run_id, :source_opportunity_candidate_id, :recommendation_type,
                :objective_type, :title, :summary, :platform_scope_json, :content_type_scope_json, :audience_scope_json,
                :market_scope_json, :topic_scope_json, :time_horizon, :status, :priority_level, :priority_score,
                :confidence_level, :confidence_score, :freshness_status, :expires_at, :creator_fit, :audience_fit,
                :historical_fit, :market_fit, :platform_fit, :strategic_fit, :authenticity_fit, :timing_fit,
                :differentiation_potential, :operational_feasibility, :expected_learning_value, :copying_risk,
                :overall_risk, :created_at, :updated_at
            )
            """,
            {
                "id": "rec-a",
                "creator_id": effective_creator_id,
                "recommendation_run_id": "run-a",
                "source_opportunity_candidate_id": None,
                "recommendation_type": "content_structure",
                "objective_type": "discovery",
                "title": "Recommendation A",
                "summary": "Recommendation source",
                "platform_scope_json": "[\"youtube\"]",
                "content_type_scope_json": "[\"video\"]",
                "audience_scope_json": "[]",
                "market_scope_json": "[]",
                "topic_scope_json": "[]",
                "time_horizon": "quarterly",
                "status": "approved",
                "priority_level": "high",
                "priority_score": 0.9,
                "confidence_level": "medium",
                "confidence_score": 0.7,
                "freshness_status": "fresh",
                "expires_at": None,
                "creator_fit": 0.8,
                "audience_fit": 0.8,
                "historical_fit": 0.6,
                "market_fit": 0.6,
                "platform_fit": 0.7,
                "strategic_fit": 0.9,
                "authenticity_fit": 0.8,
                "timing_fit": 0.7,
                "differentiation_potential": 0.7,
                "operational_feasibility": 0.6,
                "expected_learning_value": 0.6,
                "copying_risk": 0.1,
                "overall_risk": 0.2,
                "created_at": "2026-07-28T00:00:00Z",
                "updated_at": "2026-07-28T00:00:00Z",
            },
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO experiment_definitions (
                id, creator_id, name, description, experiment_type, platform, content_type, status,
                hypothesis, rationale, primary_metric_key, expected_direction, minimum_sample_size,
                start_date, end_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "exp-a",
                effective_creator_id,
                "Experiment A",
                "Experiment source",
                "manual_observation",
                "youtube",
                "video",
                "active",
                "Hypothesis for testing",
                "Test rationale",
                "watch_time",
                "increase",
                10,
                None,
                None,
                "2026-07-28T00:00:00Z",
                "2026-07-28T00:00:00Z",
            ),
        )
    planning = FakePlanningService(effective_creator_id)
    recommendations = FakeRecommendationService(effective_creator_id)
    experiments = FakeExperimentService(effective_creator_id)
    content = FakeContentLibraryService(effective_creator_id)
    shared = FixedSnapshotSource(f"snapshot-{creator_id}")
    service = build_content_brief_service(
        settings=settings,
        paths=paths,
        repository=SQLiteContentBriefRepository(database),
        planning_service=planning,
        recommendation_service=recommendations,
        experiment_service=experiments,
        content_library_service=content,
        creator_memory_service=shared,
        creator_language_service=shared,
        audience_service=shared,
        analytics_service=shared,
        analytics_lab_service=shared,
        market_service=shared,
        platform_service=shared,
        packaging_service=shared,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, service


class ContentBriefFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_migration_v30_is_idempotent_and_creates_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings()
            paths = ProjectPaths.from_settings(Path(temp_dir), settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                run_migrations(connection)
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("brief_context_snapshots", tables)
                self.assertIn("content_briefs", tables)
                self.assertIn("brief_reports", tables)
                schema_version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                self.assertEqual(schema_version, 34)

    def test_brief_generation_links_sources_and_preserves_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, database, catalog, service = make_brief_service(root, creator_id="creator-a")
            creator_a = catalog.list_creators()[0]
            creator_b = catalog.list_creators()[1]
            brief_a = service.generate_brief(creator_id=creator_a.id, source_type="roadmap_item", source_id="roadmap-a")
            brief_b = service.generate_brief(creator_id=creator_b.id, source_type="manual_request", source_id="")
            self.assertEqual(brief_a.status.value, "needs_review")
            self.assertNotEqual(brief_a.creator_id, brief_b.creator_id)
            self.assertEqual(len(service.list_briefs(creator_a.id)), 1)
            self.assertEqual(len(service.list_briefs(creator_b.id)), 1)
            self.assertEqual(len(service.list_context_snapshots(creator_a.id)), 1)
            self.assertEqual(len(service.list_requests(creator_a.id)), 1)
            self.assertNotEqual(brief_a.id, brief_b.id)
            self.assertNotEqual(brief_a.context_snapshot_id, brief_b.context_snapshot_id)
            self.assertNotEqual(service.build_overview(creator_a.id)["creator_id"], service.build_overview(creator_b.id)["creator_id"])
            self.assertNotEqual(brief_a.status.value, "ready_for_production")
            with database.connect() as connection:
                brief_count = connection.execute("SELECT COUNT(*) FROM content_briefs").fetchone()[0]
            self.assertEqual(brief_count, 2)

    def test_request_and_brief_deduplicate_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, _, _, catalog, service = make_brief_service(root, creator_id="creator-a")
            creator_id = catalog.list_creators()[0].id
            request_a = service.create_request(creator_id=creator_id, source_type="roadmap_item", source_id="roadmap-a")
            request_b = service.create_request(creator_id=creator_id, source_type="roadmap_item", source_id="roadmap-a")
            self.assertEqual(request_a.id, request_b.id)
            brief = service.generate_brief(request_id=request_a.id)
            repeated = service.generate_brief(request_id=request_a.id)
            self.assertEqual(brief.id, repeated.id)
            versioned = service.version_brief(brief.id, reason="reviewed")
            self.assertEqual(versioned.version, 2)
            self.assertEqual(versioned.parent_brief_id, brief.id)
            superseded = service.supersede_brief(brief.id, reason="replace")
            self.assertEqual(superseded.id, versioned.id)
            original = service.get_brief(brief.id)
            self.assertEqual(original.status.value, "superseded")

    def test_reference_sources_and_reports_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, _, _, catalog, service = make_brief_service(root, creator_id="creator-a")
            creator_id = catalog.list_creators()[0].id
            recommendation_brief = service.generate_brief(creator_id=creator_id, source_type="approved_recommendation", source_id="rec-a")
            experiment_brief = service.generate_brief(creator_id=creator_id, source_type="experiment", source_id="exp-a")
            content_brief = service.generate_brief(creator_id=creator_id, source_type="internal_content_draft", source_id="content-a")
            self.assertEqual(recommendation_brief.recommendation_candidate_id, "rec-a")
            self.assertEqual(experiment_brief.experiment_id, "exp-a")
            self.assertEqual(content_brief.internal_content_id, "content-a")
            report = service.build_report(content_brief_id=content_brief.id, creator_id=creator_id, report_type="content_brief_summary")
            csv_path = service.export_report(report.id, "csv")
            self.assertTrue(csv_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("objective", content.lower())

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, _, catalog, service = make_brief_service(root, creator_id="creator-a")
            creator_id = catalog.list_creators()[0].id
            parser = build_parser()
            args = parser.parse_args(["briefs", "overview", "--creator-id", creator_id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_briefs_command(args, service=service, stdout=stdout, stderr=stderr)
            self.assertEqual(exit_code, 0)
            self.assertIn(creator_id, stdout.getvalue())
            service.generate_brief(creator_id=creator_id, source_type="manual_request", source_id="")
            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                diagnostic=SimpleNamespace(gpu_devices=[]),
                settings=settings,
                paths=paths,
                planning_service=SimpleNamespace(list_tasks=lambda creator_id: []),
                brief_service=service,
                recommendation_service=SimpleNamespace(build_background_tasks=lambda creator_id: []),
                creator_memory_service=SimpleNamespace(),
                creator_language_service=SimpleNamespace(),
                creative_packaging_service=SimpleNamespace(),
                youtube_service=SimpleNamespace(),
                instagram_service=SimpleNamespace(),
                tiktok_service=SimpleNamespace(),
                audience_service=SimpleNamespace(),
                platform_service=SimpleNamespace(),
                market_service=SimpleNamespace(build_background_tasks=lambda creator_id: []),
            )
            workspace.select_creator(creator_id)
            overview = BriefsOverviewView(workspace)
            tasks = TaskCenterView(workspace)
            overview.refresh()
            tasks.refresh()
            self.assertGreaterEqual(len(workspace.background_tasks()), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
