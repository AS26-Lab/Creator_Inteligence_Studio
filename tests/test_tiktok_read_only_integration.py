from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - optional GUI dependency
    QApplication = None

from creator_intelligence_studio.application.commands.tiktok_commands import ExportTikTokSyncReportCommand
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.tiktok_integration_service import build_tiktok_integration_service
from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokConnectionStatus, TikTokLinkMethod
from creator_intelligence_studio.domain.tiktok_integration.value_objects import READ_ONLY_SCOPES, TikTokOAuthAuthorizationResult, TikTokOAuthTokenResult, validate_desktop_redirect_uri
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_tiktok_repository import SQLiteTikTokRepository
from creator_intelligence_studio.infrastructure.tiktok.credential_store import TikTokCredentialBundle
from creator_intelligence_studio.infrastructure.tiktok.display_api_client import TikTokDisplayApiClient
from creator_intelligence_studio.infrastructure.tiktok.profile_mapper import map_profile_payload
from creator_intelligence_studio.presentation.cli.tiktok_cli import build_tiktok_parser, handle_tiktok
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.task_center_view import TaskCenterView
from creator_intelligence_studio.presentation.desktop.views.tiktok_integration_view import TikTokIntegrationView
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
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
    )


class MemoryCredentialStore:
    def __init__(self) -> None:
        self._bundles: dict[str, TikTokCredentialBundle] = {}

    def save(self, reference: str, bundle: TikTokCredentialBundle) -> None:
        self._bundles[reference] = bundle

    def load(self, reference: str):
        return self._bundles.get(reference)

    def delete(self, reference: str) -> None:
        self._bundles.pop(reference, None)


class FakeTikTokOAuthClient:
    def __init__(self) -> None:
        self.begin_calls: list[tuple[str, tuple[str, ...], str | None]] = []
        self.exchange_calls: list[tuple[str, str | None, str, str]] = []
        self.refresh_calls: list[tuple[str, str | None, str]] = []
        self.revoke_calls: list[tuple[str, str | None, str]] = []

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None):
        self.begin_calls.append((client_id, scopes, redirect_uri))
        return TikTokOAuthAuthorizationResult(
            authorization_url="https://www.tiktok.com/v2/auth/authorize/?stub=1",
            state=state or "state",
            redirect_uri=redirect_uri or "http://127.0.0.1:8765/callback",
            code_verifier="verifier-1234567890-verifier-1234567890-verifier",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None):
        self.exchange_calls.append((client_id, client_secret, code, redirect_uri))
        return TikTokOAuthTokenResult(
            access_token=f"access-{code}",
            refresh_token=f"refresh-{code}",
            token_type="Bearer",
            expires_in=3600,
            refresh_expires_in=7200,
            granted_scopes=READ_ONLY_SCOPES,
            open_id="open-a",
            union_id="union-a",
            expires_at="2026-08-01T00:00:00Z",
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str):
        self.refresh_calls.append((client_id, client_secret, refresh_token))
        return TikTokOAuthTokenResult(
            access_token="refreshed-token",
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=3600,
            refresh_expires_in=7200,
            granted_scopes=READ_ONLY_SCOPES,
            open_id="open-a",
            union_id="union-a",
            expires_at="2026-08-01T00:00:00Z",
        )

    def revoke(self, *, client_id: str, client_secret: str | None, token: str) -> bool:
        self.revoke_calls.append((client_id, client_secret, token))
        return True


@dataclass
class FakeResponse:
    payload: dict[str, object]
    headers: dict[str, str] | None = None


class FakeTikTokDisplayApiClient(TikTokDisplayApiClient):
    def __init__(self) -> None:
        self.api_version = "v2"
        self.user_payload = {
            "data": {
                "user": {
                    "open_id": "open-a",
                    "union_id": "union-a",
                    "display_name": "Creator A",
                    "username": "creator_a",
                    "avatar_url": "https://example.invalid/avatar.jpg",
                    "bio_description": "Entertainment creator",
                    "profile_deep_link": "snssdk123://user/profile/open_a",
                    "profile_web_link": "https://www.tiktok.com/@creator_a",
                    "is_verified": True,
                    "follower_count": 1200,
                    "following_count": 120,
                    "likes_count": 3200,
                    "video_count": 3,
                }
            }
        }
        self.video_pages: dict[str | None, dict[str, object]] = {
            None: {
                "data": {
                    "videos": [
                        {
                            "id": "video-1",
                            "create_time": 1_720_000_000,
                            "cover_image_url": "https://example.invalid/video-1-cover-v1.jpg",
                            "share_url": "https://www.tiktok.com/@creator_a/video/1",
                            "video_description": "First version",
                            "duration": 18,
                            "height": 1920,
                            "width": 1080,
                            "title": "Hello TikTok",
                            "embed_link": "https://www.tiktok.com/embed/v2/1",
                            "like_count": 10,
                            "comment_count": 1,
                            "share_count": 2,
                            "view_count": 100,
                        },
                        {
                            "id": "video-2",
                            "create_time": 1_720_000_100,
                            "cover_image_url": "https://example.invalid/video-2-cover-v1.jpg",
                            "share_url": "https://www.tiktok.com/@creator_a/video/2",
                            "video_description": "Second video",
                            "duration": 22,
                            "height": 1920,
                            "width": 1080,
                            "title": "Second",
                            "embed_link": "https://www.tiktok.com/embed/v2/2",
                            "like_count": 20,
                            "comment_count": 2,
                            "share_count": 3,
                            "view_count": 200,
                        },
                    ],
                    "cursor": "1",
                    "has_more": True,
                }
            },
            1: {
                "data": {
                    "videos": [
                        {
                            "id": "video-3",
                            "create_time": 1_720_000_200,
                            "cover_image_url": "https://example.invalid/video-3-cover-v1.jpg",
                            "share_url": "https://www.tiktok.com/@creator_a/video/3",
                            "video_description": "Third video",
                            "duration": 30,
                            "height": 1920,
                            "width": 1080,
                            "title": "Third",
                            "embed_link": "https://www.tiktok.com/embed/v2/3",
                            "like_count": 30,
                            "comment_count": 3,
                            "share_count": 4,
                            "view_count": 300,
                        }
                    ],
                    "cursor": None,
                    "has_more": False,
                }
            },
        }
        self.query_payloads: dict[str, dict[str, object]] = {}

    def get_user_info(self, *, token: str, fields: tuple[str, ...]):  # noqa: ARG002
        return self.user_payload

    def list_videos(self, *, token: str, cursor: int | None = None, max_count: int | None = None, fields: tuple[str, ...]):  # noqa: ARG002
        payload = self.video_pages.get(cursor, {"data": {"videos": [], "cursor": None, "has_more": False}})
        return payload

    def query_videos(self, *, token: str, video_ids: tuple[str, ...], fields: tuple[str, ...]):  # noqa: ARG002
        videos = []
        for video_id in video_ids:
            videos.append(
                self.query_payloads.get(
                    video_id,
                    {
                        "id": video_id,
                        "view_count": 999,
                        "like_count": 99,
                        "comment_count": 9,
                        "share_count": 5,
                        "cover_image_url": f"https://example.invalid/{video_id}-cover-v2.jpg",
                        "title": f"Title for {video_id}",
                        "video_description": f"Description for {video_id}",
                    },
                )
            )
        return {"data": {"videos": videos, "cursor": None, "has_more": False}}


def make_bundle(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, database=database, logger=None)
    analytics_repository = SQLiteAnalyticsRepository(database)
    creative_packaging_repository = SQLiteCreativePackagingRepository(database)
    repository = SQLiteTikTokRepository(database)
    service = build_tiktok_integration_service(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=FakeTikTokOAuthClient(),
        credential_store=MemoryCredentialStore(),
        display_api_client=FakeTikTokDisplayApiClient(),
        logger=None,
    )
    creator = catalog.create_creator(display_name="Creator A")
    return settings, paths, database, catalog, repository, service, creator


class TikTokReadOnlyIntegrationTests(unittest.TestCase):
    def test_validate_desktop_redirect_uri_and_migration_v24(self) -> None:
        self.assertTrue(validate_desktop_redirect_uri("http://127.0.0.1:8765/callback"))
        self.assertTrue(validate_desktop_redirect_uri("http://localhost:8080/callback"))
        self.assertFalse(validate_desktop_redirect_uri("https://example.com/callback"))

        with tempfile.TemporaryDirectory() as temp_dir:
            settings, paths, database, _, _, _, _ = make_bundle(Path(temp_dir))
            with database.connect() as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("tiktok_connections", tables)
                self.assertIn("tiktok_remote_videos", tables)
                self.assertIn("tiktok_metric_imports", tables)
                columns = [row[1] for row in connection.execute("PRAGMA table_info(tiktok_connections)")]
                self.assertNotIn("access_token", columns)
                self.assertNotIn("refresh_token", columns)
            # run migrations again to ensure idempotence
            with database.connect() as connection:
                run_migrations(connection)

    def test_connect_sync_metrics_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, _, repository, service, creator = make_bundle(Path(temp_dir))

            connection_result = service.connect_account(
                creator_id=creator.id,
                client_id="client-a",
                client_secret="secret-a",
                authorization_code="code-a",
                redirect_uri="http://127.0.0.1:8765/callback",
                scopes=READ_ONLY_SCOPES,
                account_identifier="creator_a",
            )
            self.assertEqual(connection_result.connection.status, TikTokConnectionStatus.VERIFIED)

            profile = repository.upsert_profile(
                map_profile_payload(
                    {
                        "open_id": "open-a",
                        "union_id": "union-a",
                        "display_name": "Creator A",
                        "username": "creator_a",
                        "bio_description": "Entertainment creator",
                        "profile_deep_link": "snssdk123://user/profile/open_a",
                        "profile_web_link": "https://www.tiktok.com/@creator_a",
                        "is_verified": True,
                        "follower_count": 1200,
                        "following_count": 120,
                        "likes_count": 3200,
                        "video_count": 3,
                    },
                    creator_id=creator.id,
                    connection_id=connection_result.connection.id,
                    open_id="open-a",
                    api_version="v2",
                )
            )
            sync_result = service.sync_videos(profile_id=profile.id, max_count=20)
            self.assertGreaterEqual(len(sync_result.remote_videos), 3)
            self.assertEqual(sync_result.run.status.value, "completed")

            remote = repository.get_remote_video_by_tiktok_id(creator.id, "video-1")
            self.assertIsNotNone(remote)
            self.assertEqual(len(repository.list_video_text_versions(remote.id)), 1)
            self.assertEqual(len(repository.list_cover_versions(remote.id)), 1)

            display = service.display_api_client  # type: ignore[assignment]
            assert isinstance(display, FakeTikTokDisplayApiClient)
            display.video_pages[None]["data"]["videos"][0]["title"] = "Hello TikTok v2"
            display.video_pages[None]["data"]["videos"][0]["cover_image_url"] = "https://example.invalid/video-1-cover-v2.jpg"
            display.query_payloads["video-1"] = {
                "id": "video-1",
                "view_count": 150,
                "like_count": 12,
                "comment_count": 2,
                "share_count": 4,
                "cover_image_url": "https://example.invalid/video-1-cover-v2.jpg",
                "title": "Hello TikTok v2",
                "video_description": "First version updated",
            }
            sync_result_2 = service.sync_incremental(profile_id=profile.id, max_count=20)
            self.assertEqual(sync_result_2.run.status.value, "completed")
            remote = repository.get_remote_video_by_tiktok_id(creator.id, "video-1")
            self.assertIsNotNone(remote)
            self.assertGreaterEqual(len(repository.list_video_text_versions(remote.id)), 2)
            self.assertGreaterEqual(len(repository.list_cover_versions(remote.id)), 2)

            metrics_result = service.sync_public_metrics(profile_id=profile.id)
            self.assertGreaterEqual(len(metrics_result.metric_imports), 1)
            self.assertGreaterEqual(len(metrics_result.metric_values), 1)
            self.assertGreaterEqual(len(service.sync_history(creator.id)), 3)

    def test_read_only_scopes_refresh_revoke_and_no_token_in_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, database, _, repository, service, creator = make_bundle(Path(temp_dir))
            with self.assertRaises(Exception):
                service.connect_account(
                    creator_id=creator.id,
                    client_id="client-a",
                    client_secret="secret-a",
                    authorization_code="code-a",
                    redirect_uri="http://127.0.0.1:8765/callback",
                    scopes=("video.publish",),
                    account_identifier="creator_a",
                )

            connection = service.connect_account(
                creator_id=creator.id,
                client_id="client-a",
                client_secret="secret-a",
                authorization_code="code-a",
                redirect_uri="http://127.0.0.1:8765/callback",
                scopes=READ_ONLY_SCOPES,
                account_identifier="creator_a",
            ).connection
            refreshed = service.refresh_connection(connection.id)
            self.assertEqual(refreshed.connection.status, TikTokConnectionStatus.VERIFIED)
            revoked = service.revoke_connection(connection.id)
            self.assertEqual(revoked.connection.status, TikTokConnectionStatus.REVOKED)

            profile = repository.upsert_profile(
                map_profile_payload(
                    {
                        "open_id": "open-a",
                        "display_name": "Creator A",
                    },
                    creator_id=creator.id,
                    connection_id=connection.id,
                    open_id="open-a",
                    api_version="v2",
                )
            )
            with self.assertRaises(Exception):
                service.sync_profile(profile_id=profile.id)

            with database.connect() as conn:
                row = conn.execute("SELECT * FROM tiktok_connections LIMIT 1").fetchone()
                self.assertIsNotNone(row)
                self.assertNotIn("access_token", row.keys())
                self.assertNotIn("refresh_token", row.keys())

    @unittest.skipIf(QApplication is None, "PySide6 no esta disponible")
    def test_gui_and_task_center_surface(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([])

        stub_workspace = SimpleNamespace(
            selected_creator_id="creator-a",
            list_tiktok_connections=lambda creator_id: [],
            list_tiktok_profiles=lambda creator_id: [],
            list_tiktok_videos=lambda profile_id: [],
            list_tiktok_content_links=lambda creator_id: [],
            list_tiktok_metric_imports=lambda creator_id, profile_id=None: [],
            list_tiktok_rate_limit_usage=lambda connection_id: [],
            list_tiktok_sync_runs=lambda creator_id: [],
            background_tasks=lambda: [
                SimpleNamespace(
                    task_id="run-1",
                    title="Sincronizacion de TikTok",
                    video_title="profile-a",
                    video_id=None,
                    stage_name="incremental_sync",
                    status="queued",
                    progress_percent=0.0,
                    message="queued",
                    error=None,
                    cancellable=True,
                    updated_at="2026-07-27T00:00:00Z",
                    payload={"kind": "tiktok_sync"},
                )
            ],
            export_tiktok_sync_report=lambda run_id, format_name="json", destination=None: Path("report.json"),
            interrupt_tiktok_sync_run=lambda run_id, reason=None: None,
            resume_tiktok_sync_run=lambda run_id: None,
            selected_creator=lambda: None,
            selected_project=lambda: None,
            ui_state=SimpleNamespace(last_page="home"),
            diagnostic=SimpleNamespace(gpu_devices=[]),
        )

        view = TikTokIntegrationView(stub_workspace)
        self.assertGreaterEqual(view.tabs.count(), 9)

        task_view = TaskCenterView(stub_workspace)
        self.assertEqual(task_view.table.rowCount(), 1)

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="entity")
        build_tiktok_parser(subparsers)
        args = parser.parse_args(["tiktok", "connections", "--creator-id", "creator-a", "--json"])
        self.assertEqual(args.entity, "tiktok")
        self.assertEqual(args.action, "connections")

