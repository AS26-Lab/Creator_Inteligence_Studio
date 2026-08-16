from __future__ import annotations

import json
import logging
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.application.services.youtube_integration_service import (
    YouTubeIntegrationService,
    build_youtube_integration_service,
)
from creator_intelligence_studio.domain.creative_packaging.value_objects import PackagingAssetType
from creator_intelligence_studio.domain.youtube_integration.connection_types import (
    YouTubeConnectionStatus,
    YouTubeRemoteContentType,
)
from creator_intelligence_studio.domain.youtube_integration.entities import (
    YouTubeChannel,
    YouTubeConnection,
    YouTubeSyncRun,
)
from creator_intelligence_studio.domain.youtube_integration.errors import (
    YouTubeAuthorizationError,
    YouTubeConnectionError,
)
from creator_intelligence_studio.domain.youtube_integration.sync_types import (
    YouTubeSyncStatus,
    YouTubeSyncType,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_youtube_repository import SQLiteYouTubeRepository
from creator_intelligence_studio.infrastructure.youtube.analytics_api_client import YouTubeAnalyticsApiClient, YouTubeAnalyticsPage
from creator_intelligence_studio.infrastructure.youtube.channel_mapper import map_channel_payload
from creator_intelligence_studio.infrastructure.youtube.data_api_client import YouTubeApiPage, YouTubeDataApiClient
from creator_intelligence_studio.infrastructure.youtube.metric_mapper import map_metric_values
from creator_intelligence_studio.infrastructure.youtube.oauth_client import OAuthAuthorizationResult, OAuthTokenResult, YouTubeOAuthClient
from creator_intelligence_studio.infrastructure.youtube.credential_store import CredentialBundle, CredentialStore
from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES
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
        youtube_oauth_client_id="client-app-test",
    )


class MemoryCredentialStore(CredentialStore):
    def __init__(self) -> None:
        self._bundles: dict[str, CredentialBundle] = {}

    def save(self, reference: str, bundle: CredentialBundle) -> None:
        self._bundles[reference] = bundle

    def load(self, reference: str) -> CredentialBundle | None:
        return self._bundles.get(reference)

    def delete(self, reference: str) -> None:
        self._bundles.pop(reference, None)


class FakeOAuthClient(YouTubeOAuthClient):
    def __init__(self) -> None:
        self.begin_calls: list[tuple[str, tuple[str, ...], str | None]] = []
        self.exchange_calls: list[tuple[str, str | None, str, str]] = []
        self.refresh_calls: list[tuple[str, str | None, str]] = []
        self.revoke_calls: list[str] = []
        self.verify_calls: list[tuple[str, tuple[str, ...]]] = []

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None, code_verifier: str | None = None) -> OAuthAuthorizationResult:
        self.begin_calls.append((client_id, scopes, redirect_uri))
        return OAuthAuthorizationResult(
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth?stub=1",
            state=state or "state",
            redirect_uri=redirect_uri or "http://localhost/callback",
            code_verifier=code_verifier or "verifier",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult:
        self.exchange_calls.append((client_id, client_secret, code, redirect_uri))
        return OAuthTokenResult(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            google_account_identifier="creator@example.com",
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult:
        self.refresh_calls.append((client_id, client_secret, refresh_token))
        return OAuthTokenResult(
            access_token="refreshed-token",
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            google_account_identifier="creator@example.com",
        )

    def revoke(self, token: str) -> bool:
        self.revoke_calls.append(token)
        return True

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:
        self.verify_calls.append((token, scopes))
        return {
            "google_account_identifier": "creator@example.com",
            "granted_scopes": scopes,
            "missing_scopes": (),
        }

    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True) -> tuple[OAuthAuthorizationResult, str]:  # noqa: ARG002
        result = self.begin_authorization(client_id=client_id, scopes=scopes)
        return result, "interactive-auth-code"


@dataclass(frozen=True, slots=True)
class FakePage:
    items: tuple[dict[str, object], ...]
    next_page_token: str | None = None


class FakeYouTubeDataApiClient(YouTubeDataApiClient):
    def __init__(self, *, channel_pages: dict[str | None, FakePage], video_pages: dict[tuple[str, str | None], FakePage]) -> None:
        self._channel_pages = channel_pages
        self._video_pages = video_pages
        self.channel_calls: list[str | None] = []
        self.video_calls: list[tuple[str | None, str | None]] = []

    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:  # noqa: ARG002
        self.channel_calls.append(page_token)
        page = self._channel_pages.get(page_token, FakePage(()))
        return YouTubeApiPage(
            items=page.items,
            next_page_token=page.next_page_token,
            prev_page_token=None,
            raw_json=json.dumps({"items": list(page.items), "nextPageToken": page.next_page_token}, ensure_ascii=False),
        )

    def list_videos(self, *, channel_id: str | None = None, ids: tuple[str, ...] | None = None, page_token: str | None = None, max_results: int = 50, part: str = "snippet,contentDetails,statistics,status,topicDetails") -> YouTubeApiPage:  # noqa: ARG002
        self.video_calls.append((channel_id, page_token))
        page = self._video_pages.get((channel_id or "", page_token), FakePage(()))
        return YouTubeApiPage(
            items=page.items,
            next_page_token=page.next_page_token,
            prev_page_token=None,
            raw_json=json.dumps({"items": list(page.items), "nextPageToken": page.next_page_token}, ensure_ascii=False),
        )


class FakeYouTubeAnalyticsApiClient(YouTubeAnalyticsApiClient):
    def __init__(self, metric_rows: dict[str, list[list[object]]]) -> None:
        self.metric_rows = metric_rows
        self.calls: list[tuple[str, str | None]] = []

    def query(self, *, ids: str, metrics: str, dimensions: str | None = None, filters: str | None = None, start_date: str | None = None, end_date: str | None = None, max_results: int = 200, sort: str | None = None) -> YouTubeAnalyticsPage:  # noqa: ARG002
        self.calls.append((metrics, filters))
        rows = self.metric_rows.get(metrics, [])
        return YouTubeAnalyticsPage(
            rows=tuple({"row": row} for row in rows),
            raw_json=json.dumps({"rows": rows}, ensure_ascii=False),
        )


def make_remote_channel_payload() -> dict[str, object]:
    return {
        "id": "UC999000AAA",
        "snippet": {
            "title": "Creator A Channel",
            "description": "A channel description",
            "publishedAt": "2026-07-01T12:00:00Z",
            "country": "MX",
            "thumbnails": {
                "default": {"url": "https://img.example/channel_default.jpg", "width": 88, "height": 88},
            },
        },
        "statistics": {
            "subscriberCount": "1234",
            "videoCount": "2",
            "viewCount": "54321",
            "hiddenSubscriberCount": False,
        },
        "brandingSettings": {"channel": {"customUrl": "creator-a"}},
    }


def make_remote_video_payload(video_id: str, *, title: str, duration: str, thumbnail_url: str, is_short: bool = False) -> dict[str, object]:
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": f"Description for {title}",
            "publishedAt": "2026-07-02T12:00:00Z",
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
            "categoryId": "27",
            "thumbnails": {
                "default": {"url": thumbnail_url, "width": 120, "height": 90},
                "medium": {"url": thumbnail_url.replace("default", "medium"), "width": 320, "height": 180},
            },
        },
        "contentDetails": {"duration": duration},
        "status": {"privacyStatus": "public"},
        "isShort": is_short,
    }


def build_service_bundle(root: Path):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    analytics_repository = SQLiteAnalyticsRepository(database)
    creative_packaging_repository = SQLiteCreativePackagingRepository(database)
    youtube_repository = SQLiteYouTubeRepository(database)
    service = build_youtube_integration_service(
        settings=settings,
        paths=paths,
        repository=youtube_repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=FakeOAuthClient(),
        credential_store=MemoryCredentialStore(),
        data_api_client=FakeYouTubeDataApiClient(channel_pages={}, video_pages={}),
        analytics_api_client=FakeYouTubeAnalyticsApiClient({}),
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, analytics_repository, creative_packaging_repository, youtube_repository, service


class YouTubeIntegrationTests(unittest.TestCase):
    def test_migration_v21_and_read_only_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, _, _, _, _, _ = build_service_bundle(root)
            with database.connect() as connection:
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                youtube_columns = {row[1] for row in connection.execute("PRAGMA table_info(youtube_connections)").fetchall()}
            self.assertEqual(versions[-1], 31)
            self.assertTrue({"youtube_connections", "youtube_channels", "youtube_remote_videos", "youtube_sync_runs", "youtube_metric_imports", "youtube_content_links"}.issubset(tables))
            self.assertFalse({"access_token", "refresh_token"}.intersection(youtube_columns))
            self.assertEqual(READ_ONLY_SCOPES, (
                "https://www.googleapis.com/auth/youtube.readonly",
                "https://www.googleapis.com/auth/yt-analytics.readonly",
            ))

    def test_read_only_sync_linking_title_history_and_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, analytics_repository, creative_packaging_repository, youtube_repository, service = build_service_bundle(root)
            oauth = FakeOAuthClient()
            credential_store = MemoryCredentialStore()
            channel_payload = make_remote_channel_payload()
            video_one = make_remote_video_payload("yt-video-1", title="Primer titulo", duration="PT8M30S", thumbnail_url="https://img.example/video1_default.jpg", is_short=False)
            video_two = make_remote_video_payload("yt-video-2", title="Short rapido", duration="PT35S", thumbnail_url="https://img.example/video2_default.jpg", is_short=True)
            analytics_map = {
                "views": [[1200]],
                "engagedViews": [[900]],
                "estimatedMinutesWatched": [[240]],
                "averageViewDuration": [[180]],
                "viewerPercentage": [[68]],
                "likes": [[120]],
                "comments": [[14]],
                "shares": [[9]],
                "subscribersGained": [[18]],
                "subscribersLost": [[1]],
                "impressions": [[5000]],
                "impressionClickThroughRate": [[0.041]],
                "returningViewers": [[220]],
                "uniqueViewers": [[880]],
            }
            data_api = FakeYouTubeDataApiClient(
                channel_pages={
                    None: FakePage(items=(channel_payload,), next_page_token="page-2"),
                    "page-2": FakePage(items=({"id": "UC999000BBB", "snippet": {"title": "Other channel"}},), next_page_token=None),
                },
                video_pages={
                    ("UC999000AAA", None): FakePage(items=(video_one,), next_page_token="videos-2"),
                    ("UC999000AAA", "videos-2"): FakePage(items=(video_two,), next_page_token=None),
                },
            )
            analytics_api = FakeYouTubeAnalyticsApiClient(analytics_map)
            service = build_youtube_integration_service(
                settings=settings,
                paths=paths,
                repository=youtube_repository,
                database=database,
                analytics_repository=analytics_repository,
                creative_packaging_repository=creative_packaging_repository,
                oauth_client=oauth,
                credential_store=credential_store,
                data_api_client=data_api,
                analytics_api_client=analytics_api,
                logger=logging.getLogger("test"),
            )

            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")
            project = catalog.create_project(creator_reference=creator_a.id, name="YouTube Project", project_type="mixed")
            local_video_path = root / "local_reference.mp4"
            local_video_path.write_bytes(b"fake video content")
            local_video = catalog.register_video(project_id=project.id, file_path=str(local_video_path), title="Local reference video")

            connection_result = service.connect_account(
                creator_id=creator_a.id,
                client_id="client-a",
                authorization_code="auth-code",
            )
            self.assertEqual(connection_result.connection.status, YouTubeConnectionStatus.VERIFIED)
            self.assertEqual(oauth.exchange_calls[0][0], "client-a")
            self.assertGreaterEqual(len(oauth.refresh_calls), 1)
            self.assertIsNotNone(credential_store.load(connection_result.connection.credential_reference))

            with database.connect() as connection:
                youtube_columns = {row[1] for row in connection.execute("PRAGMA table_info(youtube_connections)").fetchall()}
                self.assertFalse({"access_token", "refresh_token"}.intersection(youtube_columns))

            local_channel = service.repository.upsert_channel(
                map_channel_payload(
                    creator_id=creator_a.id,
                    connection_id=connection_result.connection.id,
                    payload=channel_payload,
                    remote_fingerprint="channel-fingerprint-1",
                )
            )
            selected = service.select_channel(local_channel.id)
            self.assertTrue(selected.selected_for_sync)

            result = service.sync_incremental(creator_id=creator_a.id, channel_id=local_channel.id)
            self.assertIn(result.run.status, {YouTubeSyncStatus.COMPLETED, YouTubeSyncStatus.COMPLETED_WITH_WARNINGS})
            self.assertEqual(result.run.creator_id, creator_a.id)
            self.assertGreaterEqual(len(data_api.channel_calls), 2)
            self.assertFalse(result.report.errors, result.report.errors)
            self.assertEqual(len(result.videos), 2)
            self.assertEqual(len(service.list_remote_videos(local_channel.id)), 2)

            remote_video = service.get_remote_video("yt-video-1")
            self.assertIsNotNone(remote_video)
            self.assertEqual(remote_video.content_type, YouTubeRemoteContentType.YOUTUBE_LONGFORM)
            self.assertEqual(len(service.list_video_thumbnails("yt-video-1")), 2)
            self.assertGreaterEqual(len(service.list_metric_imports(creator_a.id)), 2)
            metric_import = service.list_metric_imports(creator_a.id)[0]
            metric_values = service.list_metric_values(metric_import.id)
            self.assertTrue(any(item.metric_key == "views" for item in metric_values))

            publication = next(item for item in analytics_repository.list_publications(creator_a.id) if item.external_publication_id == "yt-video-1")
            self.assertEqual(publication.external_publication_id, "yt-video-1")
            self.assertEqual(publication.title, "Primer titulo")
            title_asset = next(
                asset
                for asset in creative_packaging_repository.list_assets(creator_a.id)
                if asset.asset_type == PackagingAssetType.TITLE and asset.publication_id == publication.id
            )
            thumbnail_asset = next(
                asset
                for asset in creative_packaging_repository.list_assets(creator_a.id)
                if asset.asset_type == PackagingAssetType.THUMBNAIL and asset.publication_id == publication.id
            )
            title_asset_id = title_asset.id
            thumbnail_asset_id = thumbnail_asset.id

            link = service.link_content(
                creator_id=creator_a.id,
                remote_video_id="yt-video-1",
                publication_id=publication.id,
                video_asset_id=local_video.id,
                link_method="exact_youtube_id",
                confidence_level="high",
                status="linked",
            )
            self.assertEqual(link.creator_id, creator_a.id)
            self.assertEqual(service.list_content_links(creator_a.id)[0].video_asset_id, local_video.id)

            result_again = service.sync_incremental(creator_id=creator_a.id, channel_id=local_channel.id)
            publication_after_second_sync = next(item for item in analytics_repository.list_publications(creator_a.id) if item.external_publication_id == "yt-video-1")
            self.assertEqual(publication_after_second_sync.id, publication.id)
            self.assertEqual(publication_after_second_sync.title, "Primer titulo")
            self.assertEqual(len(creative_packaging_repository.list_title_versions(title_asset_id)), 1)
            self.assertEqual(len(creative_packaging_repository.list_thumbnail_versions(thumbnail_asset_id)), 1)
            self.assertIn(result_again.run.status, {YouTubeSyncStatus.COMPLETED, YouTubeSyncStatus.COMPLETED_WITH_WARNINGS})

            # Update the remote title and thumbnail to verify history instead of overwrite.
            data_api._video_pages[("UC999000AAA", None)] = FakePage(
                items=(make_remote_video_payload("yt-video-1", title="Titulo actualizado", duration="PT8M30S", thumbnail_url="https://img.example/video1_default_v2.jpg", is_short=False),),
                next_page_token="videos-2",
            )
            data_api._video_pages[("UC999000AAA", "videos-2")] = FakePage(items=(video_two,), next_page_token=None)
            result_third = service.sync_incremental(creator_id=creator_a.id, channel_id=local_channel.id)
            self.assertIn(result_third.run.status, {YouTubeSyncStatus.COMPLETED, YouTubeSyncStatus.COMPLETED_WITH_WARNINGS})
            self.assertEqual(len([item for item in analytics_repository.list_publications(creator_a.id) if item.external_publication_id == "yt-video-1"]), 1)
            publication_after_third_sync = next(item for item in analytics_repository.list_publications(creator_a.id) if item.external_publication_id == "yt-video-1")
            self.assertEqual(publication_after_third_sync.title, "Titulo actualizado")
            self.assertEqual(len(creative_packaging_repository.list_title_versions(title_asset_id)), 2)
            self.assertEqual(len(creative_packaging_repository.list_thumbnail_versions(thumbnail_asset_id)), 2)

            with self.assertRaises(YouTubeConnectionError):
                service.sync_incremental(creator_id=creator_b.id, channel_id=local_channel.id)

    def test_write_scopes_rejected_and_interrupt_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings, paths, database, catalog, analytics_repository, creative_packaging_repository, youtube_repository, service = build_service_bundle(root)
            oauth = FakeOAuthClient()
            store = MemoryCredentialStore()
            service = build_youtube_integration_service(
                settings=settings,
                paths=paths,
                repository=youtube_repository,
                database=database,
                analytics_repository=analytics_repository,
                creative_packaging_repository=creative_packaging_repository,
                oauth_client=oauth,
                credential_store=store,
                data_api_client=FakeYouTubeDataApiClient(channel_pages={}, video_pages={}),
                analytics_api_client=FakeYouTubeAnalyticsApiClient({}),
                logger=logging.getLogger("test"),
            )

            with self.assertRaises(YouTubeAuthorizationError):
                service.connect_account(
                    creator_id=catalog.create_creator(display_name="Creator X").id,
                    client_id="client-x",
                    authorization_code="auth-code",
                    scopes=("https://www.googleapis.com/auth/youtube.upload",),
                )

            creator = catalog.create_creator(display_name="Creator Sync")
            project = catalog.create_project(creator_reference=creator.id, name="Project Sync", project_type="mixed")
            local_video_path = root / "sync_reference.mp4"
            local_video_path.write_bytes(b"fake video content")
            local_video = catalog.register_video(project_id=project.id, file_path=str(local_video_path), title="Sync reference")
            connection_result = service.connect_account(creator_id=creator.id, client_id="client-sync", authorization_code="auth-code")

            local_channel = service.repository.upsert_channel(
                YouTubeChannel(
                    id=str(uuid4()),
                    creator_id=creator.id,
                    connection_id=connection_result.connection.id,
                    youtube_channel_id="UCSYNC0001",
                    title="Sync channel",
                    description=None,
                    custom_url=None,
                    country="MX",
                    published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                    thumbnail_url=None,
                    subscriber_count=100,
                    video_count=1,
                    view_count=1000,
                    hidden_subscriber_count=False,
                    selected_for_sync=True,
                    last_synced_at=None,
                    remote_fingerprint="channel-sync",
                    created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                )
            )
            running = YouTubeSyncRun(
                id=str(uuid4()),
                creator_id=creator.id,
                connection_id=connection_result.connection.id,
                channel_id=local_channel.id,
                sync_type=YouTubeSyncType.INCREMENTAL_SYNC,
                status=YouTubeSyncStatus.SYNCING_CONTENT,
                configuration_json=json.dumps({"full_resync": False}, ensure_ascii=False),
                cursor_json=json.dumps({"page_token": "resume-token"}, ensure_ascii=False),
                discovered_count=1,
                imported_count=0,
                updated_count=0,
                skipped_count=0,
                warning_count=0,
                error_count=0,
                quota_cost_estimate=1.0,
                started_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                completed_at=None,
                error_code=None,
                error_message=None,
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            )
            service.repository.upsert_sync_run(running)
            interrupted = service.interrupt_sync_run(running.id, reason="cancelled")
            self.assertEqual(interrupted.status, YouTubeSyncStatus.INTERRUPTED)
            resumed = service.resume_sync(running.id)
            self.assertEqual(resumed.run.creator_id, creator.id)
            self.assertIn(resumed.run.status, {YouTubeSyncStatus.COMPLETED, YouTubeSyncStatus.COMPLETED_WITH_WARNINGS})
            revoked = service.revoke_connection(connection_result.connection.id)
            self.assertEqual(revoked.status, YouTubeConnectionStatus.REVOKED)
            self.assertTrue(oauth.revoke_calls)
            self.assertIsNone(store.load(connection_result.connection.credential_reference))


if __name__ == "__main__":
    unittest.main()
