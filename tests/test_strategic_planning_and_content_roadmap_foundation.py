from __future__ import annotations

import io
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.strategic_planning_service import StrategicPlanningService
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_strategic_planning_repository import SQLiteStrategicPlanningRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.planning_overview_view import PlanningOverviewView
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
        preferred_compute_backend="cuda",
        allow_cpu_basic_mode=True,
        external_ai_enabled=False,
        database_filename="creator_intelligence_studio.db",
        database_timeout_seconds=5.0,
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
    )


class SnapshotProvider:
    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id

    def _item(self):
        return SimpleNamespace(id=self.snapshot_id)

    def list_profile_snapshots(self, creator_id: str):
        return [self._item()]

    def list_profiles(self, creator_id: str):
        return [self._item()]

    def list_reports(self, creator_id: str):
        return [self._item()]

    def list_snapshots(self, creator_id: str):
        return [self._item()]

    def list_experiments(self, creator_id: str):
        return [self._item()]

    def list_content(self, creator_id: str):
        return [self._item()]

    def list_connections(self, creator_id: str):
        return [self._item()]


class FakeRecommendation:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, object]:
        return dict(self._payload)


class FakeRecommendationService:
    def __init__(self, recommendations: dict[str, dict[str, object]]) -> None:
        self._recommendations = recommendations

    def get_recommendation(self, recommendation_id: str):
        payload = self._recommendations.get(recommendation_id)
        if payload is None:
            raise KeyError(recommendation_id)
        return FakeRecommendation(payload)


def seed_recommendation_candidate(connection, *, creator_id: str, recommendation_id: str, title: str) -> None:
    context_id = f"context-{recommendation_id}"
    run_id = f"run-{recommendation_id}"
    connection.execute(
        """
        INSERT OR REPLACE INTO recommendation_context_snapshots (
            id, creator_id, context_type, context_version,
            creator_memory_snapshot_id, creator_language_snapshot_id, audience_snapshot_id,
            analytics_snapshot_id, market_snapshot_id, platform_snapshot_id,
            experiment_snapshot_id, packaging_snapshot_id,
            source_fingerprint, context_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            context_id,
            creator_id,
            "planning",
            "v28",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            f"fingerprint-{recommendation_id}",
            "{}",
            "2026-07-28T00:00:00Z",
        ),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO recommendation_runs (
            id, creator_id, request_id, context_snapshot_id, status, configuration_json,
            candidate_count, generated_count, skipped_count, warning_count, error_count,
            started_at, completed_at, error_code, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            creator_id,
            None,
            context_id,
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
            id, creator_id, recommendation_run_id, source_opportunity_candidate_id,
            recommendation_type, objective_type, title, summary,
            platform_scope_json, content_type_scope_json, audience_scope_json,
            market_scope_json, topic_scope_json, time_horizon, status,
            priority_level, priority_score, confidence_level, confidence_score,
            freshness_status, expires_at, creator_fit, audience_fit, historical_fit,
            market_fit, platform_fit, strategic_fit, authenticity_fit, timing_fit,
            differentiation_potential, operational_feasibility, expected_learning_value,
            copying_risk, overall_risk, created_at, updated_at
        ) VALUES (
            :id, :creator_id, :recommendation_run_id, :source_opportunity_candidate_id,
            :recommendation_type, :objective_type, :title, :summary,
            :platform_scope_json, :content_type_scope_json, :audience_scope_json,
            :market_scope_json, :topic_scope_json, :time_horizon, :status,
            :priority_level, :priority_score, :confidence_level, :confidence_score,
            :freshness_status, :expires_at, :creator_fit, :audience_fit, :historical_fit,
            :market_fit, :platform_fit, :strategic_fit, :authenticity_fit, :timing_fit,
            :differentiation_potential, :operational_feasibility, :expected_learning_value,
            :copying_risk, :overall_risk, :created_at, :updated_at
        )
        """,
        {
            "id": recommendation_id,
            "creator_id": creator_id,
            "recommendation_run_id": run_id,
            "source_opportunity_candidate_id": None,
            "recommendation_type": "content",
            "objective_type": "unknown",
            "title": title,
            "summary": f"Summary for {title}",
            "platform_scope_json": "[]",
            "content_type_scope_json": "[]",
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
            "historical_fit": 0.5,
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


class StrategicPlanningFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def _build_environment(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        settings = make_settings()
        paths = ProjectPaths.from_settings(root, settings)
        paths.ensure_runtime_directories()
        database = build_database(settings, paths)
        with database.connect() as connection:
            run_migrations(connection)
        catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
        creator = catalog.create_creator(display_name="Strategic Creator")
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
            logger=logging.getLogger("test"),
        )
        return temp_dir, settings, paths, database, catalog, creator, planning_service

    def test_migration_v27_to_v28_and_idempotent(self) -> None:
        temp_dir, settings, paths, database, catalog, creator, planning_service = self._build_environment()
        with temp_dir:
            with database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                first_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
                run_migrations(connection)
                second_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
            self.assertEqual(versions[-1], 31)
            self.assertIn("planning_context_snapshots", tables)
            self.assertIn("strategic_plans", tables)
            self.assertIn("planning_backlog_items", tables)
            self.assertIn("planning_reports", tables)
            self.assertEqual(first_count, second_count)

    def test_context_snapshot_plan_versioning_and_no_auto_activation(self) -> None:
        temp_dir, settings, paths, database, catalog, creator, planning_service = self._build_environment()
        with temp_dir:
            planning_service.recommendation_service = FakeRecommendationService({})
            snapshot = planning_service.create_context_snapshot(creator.id)
            duplicate_snapshot = planning_service.create_context_snapshot(creator.id)
            self.assertEqual(snapshot.id, duplicate_snapshot.id)

            plan = planning_service.create_plan(creator_id=creator.id, name="Q4 Strategy", context_snapshot_id=snapshot.id, horizon_type="quarterly")
            self.assertEqual(plan.status.value, "draft")
            self.assertEqual(plan.creator_id, creator.id)

            objective = planning_service.create_objective(
                strategic_plan_id=plan.id,
                objective_type="reach",
                title="Increase discovery",
                metrics=[{"metric_role": "primary", "metric_key": "views", "availability_status": "available"}],
            )
            conflict = planning_service.create_objective(
                strategic_plan_id=plan.id,
                objective_type="brand_consistency",
                title="Hold identity",
                metrics=[{"metric_role": "primary", "metric_key": "brand_consistency", "availability_status": "manual_import_required"}],
            )
            objectives = planning_service.list_objectives(plan.id)
            conflicts = planning_service.list_conflicts(plan.id)
            metrics = planning_service.list_objective_metrics(objective.id)
            self.assertEqual(len(objectives), 2)
            self.assertEqual(len(metrics), 1)
            self.assertTrue(conflicts)
            self.assertEqual(conflicts[0].conflict_type.value, "objective_conflict")

            submitted = planning_service.submit_plan_for_review(plan.id, reason="needs review")
            self.assertEqual(submitted.status.value, "needs_review")
            approved = planning_service.approve_plan(plan.id, reason="approved")
            self.assertEqual(approved.status.value, "approved")
            activated = planning_service.activate_plan(plan.id, reason="manual")
            self.assertEqual(activated.status.value, "active")
            versioned = planning_service.version_plan(plan.id)
            self.assertEqual(versioned.parent_plan_id, plan.id)
            self.assertEqual(versioned.version, 2)
            superseded = planning_service.supersede_plan(plan.id, replacement_name="Q4 Strategy replacement", reason="replace")
            self.assertEqual(planning_service.get_plan(plan.id).status.value, "superseded")
            self.assertEqual(superseded.parent_plan_id, plan.id)

    def test_recommendation_intake_capacity_dependency_content_linking_and_dedup(self) -> None:
        temp_dir, settings, paths, database, catalog, creator, planning_service = self._build_environment()
        with temp_dir:
            with database.connect() as connection:
                seed_recommendation_candidate(connection, creator_id=creator.id, recommendation_id="rec-approved", title="Experiment de reto")
                seed_recommendation_candidate(connection, creator_id=creator.id, recommendation_id="rec-duplicate", title="Contenido duplicado")
                connection.commit()

            planning_service.recommendation_service = FakeRecommendationService(
                {
                    "rec-approved": {"id": "rec-approved", "title": "Experiment de reto", "summary": "Piloto", "status": "approved", "priority_level": "high", "confidence_level": "medium"},
                    "rec-blocked": {"id": "rec-blocked", "title": "Bloqueada", "summary": "No pursue", "status": "blocked", "priority_level": "medium", "confidence_level": "low"},
                    "rec-expired": {"id": "rec-expired", "title": "Expirada", "summary": "Fuera de tiempo", "status": "expired", "priority_level": "low", "confidence_level": "low"},
                    "rec-duplicate": {"id": "rec-duplicate", "title": "Contenido duplicado", "summary": "Duplicado", "status": "approved", "priority_level": "high", "confidence_level": "medium"},
                }
            )

            snapshot = planning_service.create_context_snapshot(creator.id)
            plan = planning_service.create_plan(creator_id=creator.id, name="Creator A", context_snapshot_id=snapshot.id, horizon_type="quarterly")
            planning_service.create_capacity_profile(
                strategic_plan_id=plan.id,
                creator_id=creator.id,
                name="Weekly capacity",
                available_hours=8,
                available_capacity_units=8,
            )
            blocked = planning_service.intake_recommendation(strategic_plan_id=plan.id, recommendation_id="rec-blocked")
            expired = planning_service.intake_recommendation(strategic_plan_id=plan.id, recommendation_id="rec-expired")
            approved = planning_service.intake_recommendation(strategic_plan_id=plan.id, recommendation_id="rec-approved")
            duplicate = planning_service.intake_recommendation(strategic_plan_id=plan.id, recommendation_id="rec-approved")
            duplicate_backlog = planning_service.intake_recommendation(strategic_plan_id=plan.id, recommendation_id="rec-blocked")

            self.assertEqual(blocked["status"], "blocked")
            self.assertIn("backlog_item", blocked)
            self.assertEqual(expired["status"], "expired")
            self.assertIn("backlog_item", expired)
            self.assertIsNotNone(approved["initiative"])
            self.assertIsNotNone(approved["roadmap_item"])
            self.assertEqual(approved["initiative"]["recommendation_candidate_id"], "rec-approved")
            self.assertEqual(duplicate["initiative"]["id"], approved["initiative"]["id"])
            self.assertEqual(duplicate["roadmap_item"]["id"], approved["roadmap_item"]["id"])
            self.assertEqual(duplicate_backlog["backlog_item"]["id"], blocked["backlog_item"]["id"])

            roadmap_item_id = approved["roadmap_item"]["id"]
            planning_service.update_roadmap_item(
                roadmap_item_id,
                assigned_capacity_units=10,
                estimated_duration_hours=10,
                tentative_start="2026-08-01T00:00:00Z",
                tentative_end="2026-08-03T00:00:00Z",
            )
            load = planning_service.calculate_capacity_load(plan.id)
            feasibility = planning_service.evaluate_feasibility(roadmap_item_id)
            self.assertEqual(load["status"], "overloaded")
            self.assertTrue(load["overload"])
            self.assertEqual(feasibility.status.value, "feasible_with_constraints")

            content_link = planning_service.link_content_item(
                strategic_plan_id=plan.id,
                creator_id=creator.id,
                target_type="roadmap_item",
                target_id=roadmap_item_id,
                internal_content_id="content-1",
            )
            duplicate_content_link = planning_service.link_content_item(
                strategic_plan_id=plan.id,
                creator_id=creator.id,
                target_type="roadmap_item",
                target_id=roadmap_item_id,
                internal_content_id="content-1",
            )
            self.assertEqual(content_link.id, duplicate_content_link.id)

            summary = planning_service.build_overview(plan.id)
            self.assertTrue(summary["overload"])
            self.assertEqual(summary["creator_id"], creator.id)

    def test_dependencies_cycles_and_task_center(self) -> None:
        temp_dir, settings, paths, database, catalog, creator, planning_service = self._build_environment()
        with temp_dir:
            snapshot = planning_service.create_context_snapshot(creator.id)
            plan = planning_service.create_plan(creator_id=creator.id, name="Plan B", context_snapshot_id=snapshot.id, horizon_type="monthly")
            first = planning_service.add_roadmap_item(strategic_plan_id=plan.id, title="Item A", item_type="content_project", source_fingerprint="item-a")
            second = planning_service.add_roadmap_item(strategic_plan_id=plan.id, title="Item B", item_type="content_project", source_fingerprint="item-b")
            dependency = planning_service.create_dependency(
                roadmap_item_id=second.id,
                depends_on_roadmap_item_id=first.id,
                dependency_type="finish_to_start",
                reason="order",
            )
            with self.assertRaises(Exception):
                planning_service.create_dependency(
                    roadmap_item_id=first.id,
                    depends_on_roadmap_item_id=second.id,
                    dependency_type="finish_to_start",
                    reason="cycle",
                )
            milestone = planning_service.create_milestone(roadmap_item_id=first.id, title="Review", milestone_type="production_ready")
            risk = planning_service.create_roadmap_item_risk(
                roadmap_item_id=first.id,
                creator_id=creator.id,
                risk_type="capacity",
                severity="high",
                description="Capacity risk",
                blocking=True,
            )
            scenario_a = planning_service.build_scenario(plan.id, "balanced")
            scenario_b = planning_service.build_scenario(plan.id, "low_capacity")
            comparison = planning_service.compare_scenarios(scenario_a.id, scenario_b.id)
            report = planning_service.build_report(strategic_plan_id=plan.id, creator_id=creator.id, report_type="strategic_plan_summary")

            self.assertEqual(milestone.title, "Review")
            self.assertEqual(risk.blocking, True)
            self.assertIn("tradeoffs", comparison)
            self.assertEqual(report.report_type, "strategic_plan_summary")
            self.assertTrue(planning_service.list_dependencies(plan.id))
            self.assertTrue(planning_service.list_milestones(first.id))

            workspace = WorkspaceViewModel(
                service=SimpleNamespace(
                    list_creators=lambda: [creator],
                    list_projects=lambda creator_id: (),
                    get_creator=lambda creator_id: creator,
                ),
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                diagnostic=SimpleNamespace(gpu_devices=[], nvidia_driver_version=None),
                settings=settings,
                paths=paths,
                planning_service=planning_service,
            )
            workspace.selected_creator_id = creator.id
            planning_tasks = workspace.background_tasks()
            self.assertTrue(any(task.payload.get("kind") == "planning_run" for task in planning_tasks))

            task_view = TaskCenterView(workspace)
            task_view.refresh()
            self.assertGreaterEqual(task_view.table.rowCount(), 1)
            self.assertIn("Planning estrategico", {task.title for task in planning_tasks})

            planning_overview = PlanningOverviewView(SimpleNamespace(selected_creator_id=creator.id, planning_service=planning_service))
            planning_overview.refresh()
            self.assertIn("Plan activo", planning_overview.subtitle.text())

    def test_cli_help_mentions_planning(self) -> None:
        parser = build_parser()
        self.assertIn("planning", parser.format_help())


if __name__ == "__main__":
    unittest.main()
