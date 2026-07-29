from __future__ import annotations

import io
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from creator_intelligence_studio.application.services.content_brief_service import build_content_brief_service
from creator_intelligence_studio.application.services.production_preparation_service import build_production_preparation_service
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import SQLiteContentBriefRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_production_preparation_repository import SQLiteProductionPreparationRepository
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.cli.production_cli import handle_production_command
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.production_overview_view import ProductionOverviewView
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from creator_intelligence_studio.shared.paths import ProjectPaths


def make_settings() -> AppSettings:
    return AppSettings(
        application_name="Creator Intelligence Studio",
        environment="development",
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


def _fake_snapshot_service(prefix: str):
    return SimpleNamespace(
        list_profile_snapshots=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        list_snapshots=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        list_profiles=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        build_profile=lambda creator_id: SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot"),
        list_connections=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        list_integrations=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        list_reports=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
        list_versions=lambda creator_id: [SimpleNamespace(id=f"{creator_id}-{prefix}-snapshot")],
    )


def make_production_fixture(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    creator_a = catalog.create_creator(display_name="Creator A")
    creator_b = catalog.create_creator(display_name="Creator B")
    brief_service = build_content_brief_service(
        settings=settings,
        paths=paths,
        repository=SQLiteContentBriefRepository(database),
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=catalog,
        creator_memory_service=_fake_snapshot_service("memory"),
        creator_language_service=_fake_snapshot_service("language"),
        audience_service=_fake_snapshot_service("audience"),
        analytics_service=SimpleNamespace(),
        analytics_lab_service=SimpleNamespace(),
        market_service=SimpleNamespace(),
        platform_service=SimpleNamespace(),
        packaging_service=_fake_snapshot_service("packaging"),
        logger=logging.getLogger("test"),
    )
    brief_request_a = brief_service.create_request(creator_id=creator_a.id, source_type="manual_request", source_id="source-a")
    brief_a = brief_service.generate_brief(request_id=brief_request_a.id)
    brief_service.review_brief(brief_a.id, decision="approve", reason="ready", reviewer="tester")
    brief_request_b = brief_service.create_request(creator_id=creator_b.id, source_type="manual_request", source_id="source-b")
    brief_b = brief_service.generate_brief(request_id=brief_request_b.id)
    brief_service.review_brief(brief_b.id, decision="approve", reason="ready", reviewer="tester")
    production_service = build_production_preparation_service(
        settings=settings,
        paths=paths,
        repository=SQLiteProductionPreparationRepository(database),
        brief_service=brief_service,
        planning_service=SimpleNamespace(),
        recommendation_service=SimpleNamespace(),
        experiment_service=SimpleNamespace(),
        content_library_service=catalog,
        creator_memory_service=_fake_snapshot_service("memory"),
        creator_language_service=_fake_snapshot_service("language"),
        audience_service=_fake_snapshot_service("audience"),
        platform_service=_fake_snapshot_service("platform"),
        packaging_service=_fake_snapshot_service("packaging"),
        logger=logging.getLogger("test"),
    )
    return SimpleNamespace(
        settings=settings,
        paths=paths,
        database=database,
        catalog=catalog,
        creator_a=creator_a,
        creator_b=creator_b,
        brief_service=brief_service,
        brief_a=brief_a,
        brief_b=brief_b,
        production_service=production_service,
    )


class ScriptOutlineAndProductionPreparationFoundationTests(unittest.TestCase):
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
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
            self.assertEqual(versions[-1], 30)
            self.assertIn("production_context_snapshots", tables)
            self.assertIn("script_outlines", tables)
            self.assertIn("production_reports", tables)

    def test_outline_generation_and_supersede_reuse_existing_child(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_production_fixture(Path(temp_dir))
            production = fixture.production_service
            request = production.create_request(creator_id=fixture.creator_a.id, content_brief_id=fixture.brief_a.id)
            duplicate_request = production.create_request(creator_id=fixture.creator_a.id, content_brief_id=fixture.brief_a.id)
            self.assertEqual(request.id, duplicate_request.id)
            outline = production.generate_outline(request_id=request.id)
            repeated = production.generate_outline(request_id=request.id)
            self.assertEqual(outline.id, repeated.id)
            versioned = production.version_outline(outline.id)
            self.assertEqual(versioned.parent_outline_id, outline.id)
            superseded = production.supersede_outline(outline.id, reason="replace")
            superseded_again = production.supersede_outline(outline.id, reason="replace")
            self.assertEqual(superseded.id, superseded_again.id)
            self.assertNotEqual(outline.creator_id, fixture.brief_b.creator_id)
            with self.assertRaises(Exception):
                production.create_request(creator_id=fixture.creator_b.id, content_brief_id=fixture.brief_a.id)

    def test_cli_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = make_production_fixture(Path(temp_dir))
            request = fixture.production_service.create_request(creator_id=fixture.creator_a.id, content_brief_id=fixture.brief_a.id)
            fixture.production_service.generate_outline(request_id=request.id)
            parser = build_parser()
            args = parser.parse_args(["production", "overview", "--creator-id", fixture.creator_a.id])
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = handle_production_command(args, service=fixture.production_service, stdout=stdout, stderr=stderr)
            self.assertEqual(exit_code, 0)
            self.assertIn(fixture.creator_a.id, stdout.getvalue())
            workspace = SimpleNamespace(
                selected_creator_id=fixture.creator_a.id,
                production_service=fixture.production_service,
                background_tasks=lambda: fixture.production_service.list_tasks(fixture.creator_a.id),
            )
            overview = ProductionOverviewView(workspace)
            tasks = TaskCenterView(workspace)
            self.assertGreaterEqual(overview.table.rowCount(), 1)
            self.assertGreaterEqual(tasks.table.rowCount(), 1)
