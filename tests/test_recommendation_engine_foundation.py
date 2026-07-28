from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.recommendation_engine_service import build_recommendation_engine_service
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_recommendation_repository import SQLiteRecommendationRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.recommendations_cli import handle_recommendations_command
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.recommendations_overview_view import RecommendationsOverviewView
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
    )


def _ns(**kwargs):
    return SimpleNamespace(**kwargs)


class FakeMemoryService:
    def list_profile_snapshots(self, creator_id: str):
        return [_ns(id=f"memory-{creator_id}-snapshot")]


class FakeLanguageService:
    def list_profile_snapshots(self, creator_id: str):
        return [_ns(id=f"language-{creator_id}-snapshot")]


class FakeAudienceService:
    def list_profiles(self, creator_id: str):
        return [_ns(id=f"audience-{creator_id}-snapshot")]


class FakeAnalyticsLabService:
    def list_reports(self, creator_id: str):
        return [_ns(id=f"analytics-{creator_id}-report")]


class FakeMarketService:
    def __init__(self, opportunities: dict[str, list[SimpleNamespace]]) -> None:
        self._opportunities = opportunities

    def list_opportunity_candidates(self, creator_id: str, market_id: str | None = None):
        return list(self._opportunities.get(creator_id, []))

    def list_snapshots(self, creator_id: str):
        return [_ns(id=f"market-{creator_id}-snapshot")]


class FakePlatformService:
    def __init__(self, disconnected: bool = False) -> None:
        self._disconnected = disconnected

    def list_connections(self, creator_id: str):
        if self._disconnected:
            return []
        return [_ns(id=f"platform-{creator_id}-conn", platform=_ns(value="youtube"))]

    def list_reports(self, creator_id: str):
        return [_ns(id=f"platform-{creator_id}-report")]


class FakePackagingService:
    def list_brand_profiles(self, creator_id: str):
        return [_ns(id=f"packaging-{creator_id}-snapshot")]


class FakeExperimentService:
    def __init__(self, database) -> None:
        self.database = database
        self.created: list[dict[str, object]] = []

    def list_experiments(self, creator_id: str):
        return [_ns(id=f"experiment-{creator_id}-existing")]

    def create_experiment(self, **kwargs):
        self.created.append(kwargs)
        experiment_id = str(uuid4())
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO experiment_definitions (
                    id, creator_id, name, description, experiment_type, platform, content_type, status,
                    hypothesis, rationale, primary_metric_key, expected_direction, minimum_sample_size,
                    start_date, end_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (
                    experiment_id,
                    kwargs["creator_id"],
                    kwargs["name"],
                    kwargs["description"],
                    kwargs["experiment_type"],
                    kwargs.get("platform"),
                    kwargs.get("content_type"),
                    "draft",
                    kwargs["hypothesis"],
                    kwargs["rationale"],
                    kwargs["primary_metric_key"],
                    kwargs["expected_direction"],
                    int(kwargs["minimum_sample_size"]),
                    kwargs.get("start_date"),
                    kwargs.get("end_date"),
                ),
            )
        return _ns(id=experiment_id)


def make_opportunity(
    *,
    id: str,
    title: str,
    summary: str,
    copying_risk: float,
    creator_fit: float,
    audience_fit: float,
    historical_fit: float,
    overall_fit: float,
    freshness_status: str = "fresh",
    platform: str = "youtube",
    platform_scope_json: str = "[\"youtube\"]",
    content_type_scope_json: str = "[\"video\"]",
    opportunity_type: str = "topic",
    saturation_level: str = "moderate",
):
    return _ns(
        id=id,
        title=title,
        summary=summary,
        copying_risk=copying_risk,
        creator_fit=creator_fit,
        audience_fit=audience_fit,
        historical_fit=historical_fit,
        overall_fit=overall_fit,
        freshness_status=freshness_status,
        platform=platform,
        platform_scope_json=platform_scope_json,
        content_type_scope_json=content_type_scope_json,
        opportunity_type=opportunity_type,
        saturation_level=saturation_level,
        evidence_quality="high" if copying_risk < 0.75 else "medium",
        confidence_level="medium",
        lifecycle_stage="growing",
        urgency="medium",
        market_id="market-1",
        topic_id="topic-1",
    )


def make_bundle(root: Path, opportunities_factory, *, disconnected: bool = False):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("test"))
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    opportunities = opportunities_factory(creator_a, creator_b)
    experiment_service = FakeExperimentService(database)
    service = build_recommendation_engine_service(
        settings=settings,
        paths=paths,
        database=database,
        repository=SQLiteRecommendationRepository(database),
        catalog_service=catalog,
        creator_memory_service=FakeMemoryService(),
        creator_language_service=FakeLanguageService(),
        audience_service=FakeAudienceService(),
        analytics_lab_service=FakeAnalyticsLabService(),
        market_service=FakeMarketService(opportunities),
        platform_service=FakePlatformService(disconnected=disconnected),
        creative_packaging_service=FakePackagingService(),
        experiment_service=experiment_service,
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, creator_a, creator_b, service, experiment_service


class RecommendationEngineFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._qt_app = QApplication.instance() or QApplication([])

    def test_migration_v27_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = make_settings()
            paths = ProjectPaths.from_settings(Path(temp_dir), settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                first = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                run_migrations(connection)
                second = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(first, 28)
            self.assertEqual(second, 28)
            self.assertTrue({"recommendation_context_snapshots", "recommendation_candidates", "recommendation_reports"}.issubset(tables))

    def test_generation_review_feedback_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def opportunities_factory(creator_a, creator_b):
                return {
                    creator_a.id: [
                        make_opportunity(
                            id="opp-a-1",
                            title="Series educativa",
                            summary="Alta afinidad",
                            copying_risk=0.15,
                            creator_fit=0.86,
                            audience_fit=0.8,
                            historical_fit=0.9,
                            overall_fit=0.84,
                        ),
                        make_opportunity(
                            id="opp-a-2",
                            title="Packaging extremo",
                            summary="Alta popularidad pero copia riesgosa",
                            copying_risk=0.92,
                            creator_fit=0.78,
                            audience_fit=0.65,
                            historical_fit=0.72,
                            overall_fit=0.75,
                            freshness_status="recent",
                            opportunity_type="format",
                        ),
                    ],
                    creator_b.id: [
                        make_opportunity(
                            id="opp-b-1",
                            title="Tema stale",
                            summary="Caducado",
                            copying_risk=0.1,
                            creator_fit=0.2,
                            audience_fit=0.3,
                            historical_fit=0.15,
                            overall_fit=0.18,
                            freshness_status="stale",
                        )
                    ],
                }

            _, _, database, _, creator_a, creator_b, service, experiment_service = make_bundle(Path(temp_dir), opportunities_factory)
            request = service.create_request(
                creator_id=creator_a.id,
                request_type="discover_opportunities",
                objective_type="audience_growth",
                platform_scope_json=json.dumps(["youtube", "instagram"], ensure_ascii=False),
                content_type_scope_json=json.dumps(["video", "short"], ensure_ascii=False),
                time_horizon="30d",
                constraints_json=json.dumps([{"constraint_type": "creator_boundary", "source": "user", "description": "No copiar frases"}], ensure_ascii=False),
                preferences_json=json.dumps({"max_recommendations_per_run": 3}, ensure_ascii=False),
            )
            request_b = service.create_request(
                creator_id=creator_b.id,
                request_type="discover_opportunities",
                objective_type="audience_growth",
                platform_scope_json=json.dumps(["youtube"], ensure_ascii=False),
                content_type_scope_json=json.dumps(["video"], ensure_ascii=False),
                time_horizon="30d",
            )
            result = service.generate_recommendations(request_id=request.id)
            service.generate_recommendations(request_id=request_b.id)
            recommendations = service.list_recommendations(creator_a.id)
            blocked = [item for item in recommendations if item.priority_level.value == "blocked"]
            self.assertGreaterEqual(len(recommendations), 2)
            self.assertTrue(blocked)
            self.assertEqual(result.run.status.value, "completed_with_warnings")
            self.assertEqual(len(service.list_context_snapshots(creator_a.id)), 1)
            self.assertEqual(len(service.list_runs(creator_a.id)), 1)
            self.assertGreaterEqual(len(service.list_evidence(recommendations[0].id)), 1)
            self.assertGreaterEqual(len(service.list_risks(recommendations[0].id)), 1)
            self.assertGreaterEqual(len(service.list_alternatives(recommendations[0].id)), 1)
            self.assertGreaterEqual(len(service.list_metrics(recommendations[0].id)), 1)
            self.assertGreaterEqual(len(service.list_invalidation_criteria(recommendations[0].id)), 1)
            review = service.review_recommendation(recommendations[0].id, decision="approve", reason="Encaja con la identidad")
            feedback = service.add_feedback(recommendations[0].id, feedback_type="useful", rating=5, feedback_text="Buena base")
            link = service.convert_to_experiment(recommendations[0].id)
            execution = service.mark_executed(recommendations[0].id, content_id="content-1")
            outcome = service.add_outcome(recommendations[0].id, file_path=str(Path(temp_dir) / "outcome.json"))
            report = service.build_report(creator_a.id, "prioritized_recommendations")
            exported = service.export_report(report.id, "csv")
            exported_txt = service.export_report(report.id, "txt")
            exported_json = service.export_report(report.id, "json")
            self.assertEqual(review.decision.value, "approve")
            self.assertEqual(feedback.feedback_type.value, "useful")
            self.assertEqual(link.link_type, "converted_to_experiment")
            self.assertEqual(execution.execution_status, "executed")
            self.assertTrue(outcome.source_fingerprint)
            self.assertTrue(exported.exists())
            self.assertTrue(exported_txt.exists())
            self.assertTrue(exported_json.exists())
            self.assertTrue(experiment_service.created)
            self.assertNotIn("access_token", exported_json.read_text(encoding="utf-8"))
            self.assertEqual(service.build_overview(creator_a.id)["blocked"], len(blocked))
            self.assertEqual(service.build_overview(creator_b.id)["recommendations"], 1)

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def opportunities_factory(creator_a, creator_b):
                return {
                    creator_a.id: [make_opportunity(id="opp-a", title="Tutorial de piano", summary="Ajuste alto", copying_risk=0.1, creator_fit=0.9, audience_fit=0.85, historical_fit=0.88, overall_fit=0.86)],
                    creator_b.id: [make_opportunity(id="opp-b", title="Packaging extremo", summary="riesgo", copying_risk=0.9, creator_fit=0.4, audience_fit=0.3, historical_fit=0.2, overall_fit=0.25)],
                }

            _, _, _, catalog, creator_a, creator_b, service, _ = make_bundle(Path(temp_dir), opportunities_factory, disconnected=True)
            request = service.create_request(
                creator_id=creator_a.id,
                request_type="discover_opportunities",
                objective_type="audience_growth",
                platform_scope_json=json.dumps(["youtube"], ensure_ascii=False),
                content_type_scope_json=json.dumps(["video"], ensure_ascii=False),
            )
            request_b = service.create_request(
                creator_id=creator_b.id,
                request_type="discover_opportunities",
                objective_type="audience_growth",
                platform_scope_json=json.dumps(["youtube"], ensure_ascii=False),
                content_type_scope_json=json.dumps(["video"], ensure_ascii=False),
            )
            parser = build_parser()
            args = parser.parse_args(["recommendations", "generate", "--request-id", request.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = handle_recommendations_command(args, service=service, stdout=stdout, stderr=stderr)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, 0)
            self.assertIn("run", payload)
            self.assertIn("recommendations", payload)
            service.generate_recommendations(request_id=request_b.id)
            workspace = WorkspaceViewModel(
                service=catalog,
                media_service=SimpleNamespace(),
                audio_service=SimpleNamespace(),
                transcription_service=SimpleNamespace(),
                acoustic_service=SimpleNamespace(),
                visual_service=SimpleNamespace(),
                multimodal_service=SimpleNamespace(),
                clip_service=SimpleNamespace(),
                render_service=SimpleNamespace(),
                subtitle_service=SimpleNamespace(),
                diagnostic=SimpleNamespace(),
                settings=make_settings(),
                paths=ProjectPaths.from_settings(Path(temp_dir), make_settings()),
                recommendation_service=service,
            )
            workspace.selected_creator_id = creator_a.id
            view = RecommendationsOverviewView(workspace)
            view.refresh()
            self.assertIn("Recommendations", view.title_label.text())
            self.assertGreaterEqual(len(workspace.recommendation_service.build_background_tasks(creator_a.id)), 1)
            self.assertNotEqual(service.list_recommendations(creator_a.id)[0].creator_id, service.list_recommendations(creator_b.id)[0].creator_id)
