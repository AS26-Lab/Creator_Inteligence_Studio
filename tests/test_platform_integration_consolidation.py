from __future__ import annotations

import json
import logging
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from creator_intelligence_studio.application.bootstrap import _load_service_context
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.platform_integration_service import PlatformIntegrationService
from creator_intelligence_studio.domain.platform_integrations.connection_types import PlatformKind
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_platform_integration_repository import SQLitePlatformIntegrationRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class _Connection:
    id: str
    creator_id: str
    status: SimpleNamespace
    granted_scopes_json: str
    credential_reference: str
    connected_at: datetime
    last_verified_at: datetime | None = None
    disconnected_at: datetime | None = None
    google_account_identifier: str | None = None
    account_identifier: str | None = None
    credential_reference_secure: str | None = None


@dataclass(frozen=True, slots=True)
class _Profile:
    id: str
    creator_id: str
    selected_for_sync: bool = True


@dataclass(frozen=True, slots=True)
class _Channel:
    id: str
    creator_id: str
    selected_for_sync: bool = True


@dataclass(frozen=True, slots=True)
class _Account:
    id: str
    creator_id: str
    selected_for_sync: bool = True


@dataclass(frozen=True, slots=True)
class _Import:
    id: str
    creator_id: str
    source_filename: str
    status: SimpleNamespace
    channel_id: str | None = None


class FakeYouTubeService:
    def list_connections(self, creator_id: str):
        return [_Connection("yt-conn", creator_id, SimpleNamespace(value="verified"), '["youtube.read"]', "cred-yt", _now(), google_account_identifier="creator@example.com")]

    def list_channels(self, creator_id: str):
        return [_Channel("yt-channel", creator_id)]

    def verify_connection(self, connection_id: str):
        return SimpleNamespace(kind="verified", connection_id=connection_id)

    def disconnect_connection(self, connection_id: str):
        return SimpleNamespace(kind="disconnected", connection_id=connection_id)

    def revoke_connection(self, connection_id: str):
        return SimpleNamespace(kind="revoked", connection_id=connection_id)

    def get_connection(self, connection_id: str):
        return self.list_connections("creator-a")[0]

    def sync_channel(self, **kwargs):
        return SimpleNamespace(run=SimpleNamespace(id="yt-run-1"), warnings=("quota_warning",))

    def list_sync_runs(self, creator_id: str):
        return [SimpleNamespace(id="yt-run-1", creator_id=creator_id)]

    def list_sync_items(self, sync_run_id: str):
        return []

    def export_sync_report(self, run_id: str, format_name: str, *, destination: Path | None = None):
        destination = destination or Path(tempfile.gettempdir()) / f"{run_id}.{format_name}"
        destination.write_text("report", encoding="utf-8")
        return destination


class FakeInstagramService:
    def list_connections(self, creator_id: str):
        return [_Connection("ig-conn", creator_id, SimpleNamespace(value="connected"), '["instagram.basic"]', "cred-ig", _now(), account_identifier="creator_ig")]

    def list_accounts(self, creator_id: str):
        return [_Account("ig-account", creator_id)]

    def show_connection(self, connection_id: str):
        return self.list_connections("creator-a")[0]

    def verify_connection(self, connection_id: str):
        return SimpleNamespace(kind="verified", connection_id=connection_id)

    def disconnect_connection(self, connection_id: str):
        return SimpleNamespace(kind="disconnected", connection_id=connection_id)

    def revoke_connection(self, connection_id: str):
        return SimpleNamespace(kind="revoked", connection_id=connection_id)

    def sync_incremental(self, **kwargs):
        return SimpleNamespace(run=SimpleNamespace(id="ig-run-1"), warnings=())

    def list_sync_runs(self, creator_id: str):
        return [SimpleNamespace(id="ig-run-1", creator_id=creator_id)]

    def show_sync_run(self, run_id: str):
        return SimpleNamespace(id=run_id)

    def export_report(self, run_id: str, format_name: str, *, destination: Path | None = None):
        destination = destination or Path(tempfile.gettempdir()) / f"{run_id}.{format_name}"
        destination.write_text("report", encoding="utf-8")
        return destination


class FakeTikTokService:
    def list_connections(self, creator_id: str):
        return [_Connection("tt-conn", creator_id, SimpleNamespace(value="verified"), '["user.info.basic", "video.list"]', "cred-tt", _now(), account_identifier="creator_tt")]

    def list_profiles(self, creator_id: str):
        return [_Profile("tt-profile", creator_id)]

    def show_connection(self, connection_id: str):
        return self.list_connections("creator-a")[0]

    def verify_connection(self, connection_id: str):
        return SimpleNamespace(kind="verified", connection_id=connection_id)

    def disconnect_connection(self, connection_id: str):
        return SimpleNamespace(kind="disconnected", connection_id=connection_id)

    def revoke_connection(self, connection_id: str):
        return SimpleNamespace(kind="revoked", connection_id=connection_id)

    def sync_incremental(self, **kwargs):
        return SimpleNamespace(run=SimpleNamespace(id="tt-run-1"), warnings=("manual_import_only",))

    def list_sync_runs(self, creator_id: str):
        return [SimpleNamespace(id="tt-run-1", creator_id=creator_id)]

    def show_sync_run(self, run_id: str):
        return SimpleNamespace(id=run_id)

    def export_report(self, run_id: str, format_name: str, *, destination: Path | None = None):
        destination = destination or Path(tempfile.gettempdir()) / f"{run_id}.{format_name}"
        destination.write_text("report", encoding="utf-8")
        return destination


class FakeAnalyticsService:
    def list_imports(self, creator_id: str):
        return [_Import("manual-import-1", creator_id, "tiktok_manual.csv", SimpleNamespace(value="completed"), channel_id=None)]

    def list_channels(self, creator_id: str):
        return []


def make_bundle(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=logging.getLogger("test"))
    creator = catalog.create_creator(display_name="Creator A")
    repository = SQLitePlatformIntegrationRepository(database)
    service = PlatformIntegrationService(
        settings=settings,
        paths=paths,
        database=database,
        repository=repository,
        youtube_service=FakeYouTubeService(),
        instagram_service=FakeInstagramService(),
        tiktok_service=FakeTikTokService(),
        analytics_service=FakeAnalyticsService(),
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, creator, service


class PlatformIntegrationConsolidationTests(unittest.TestCase):
    def test_registry_overview_and_sync_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, _, creator, service = make_bundle(Path(temp_dir))
            connections = service.list_connections(creator.id)
            self.assertEqual({connection.platform.value for connection in connections}, {"youtube", "instagram", "tiktok", "manual_other"})
            overview = service.build_overview(creator.id)
            self.assertEqual({row.platform for row in overview}, {"youtube", "instagram", "tiktok", "manual_other"})
            result = service.start_sync(creator_id=creator.id, platforms=["youtube", "instagram", "tiktok"], mode="sequential", incremental=True)
            self.assertEqual(result.group.status.value, "completed_with_warnings")
            self.assertEqual(len(result.items), 3)
            report = service.build_report(creator.id, "integrations_summary")
            self.assertNotIn("access_token", report.report_json)
            self.assertNotIn("refresh_token", report.report_json)
            exported = service.export_report(report.id, "json")
            self.assertTrue(exported.exists())

    def test_privacy_summary_has_no_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, _, _, creator, service = make_bundle(Path(temp_dir))
            connection = service.list_connections(creator.id)[0]
            summary = service.build_privacy_summary(connection.id)
            self.assertTrue(summary["read_only"])
            self.assertTrue(summary["write_disabled"])
            self.assertFalse(summary["tokens_in_sqlite"])

