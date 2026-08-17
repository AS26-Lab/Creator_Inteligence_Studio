from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - optional GUI dependency
    QApplication = None

from creator_intelligence_studio.application import bootstrap
from creator_intelligence_studio.application.services.instagram_integration_service import PROFILE_READ_FIELDS, build_instagram_integration_service
from creator_intelligence_studio.domain.instagram_integration.connection_types import (
    InstagramAuthProvider,
    InstagramConnectionStatus,
    InstagramProfessionalAccountType,
)
from creator_intelligence_studio.domain.integrations.contracts import IntegrationErrorCategory
from creator_intelligence_studio.domain.instagram_integration.errors import InstagramAccountValidationError
from creator_intelligence_studio.domain.instagram_integration.oauth_broker import generate_transaction_proof
from creator_intelligence_studio.infrastructure.instagram.api_client import InstagramApiError, InstagramApiErrorDetails
from creator_intelligence_studio.infrastructure.instagram.oauth_broker import InMemoryInstagramOAuthBrokerStore, InstagramOAuthBrokerService
from creator_intelligence_studio.domain.instagram_integration.value_objects import (
    READ_ONLY_SCOPES,
    InstagramOAuthAuthorizationResult,
    InstagramOAuthTokenResult,
    build_instagram_credential_reference,
    is_write_scope,
)
from creator_intelligence_studio.domain.analytics.entities import AnalyticsChannel, AnalyticsPlatform
from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricDefinition
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsAggregationType, AnalyticsMetricCategory, AnalyticsPlatformStatus, AnalyticsValueType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.instagram.api_version import DEFAULT_INSTAGRAM_API_VERSION
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import ensure_schema_migrations_table, migration_1, migration_2, migration_3, migration_4, migration_5, migration_6, migration_7, migration_8, migration_9, migration_10, migration_11, migration_12, migration_13, migration_14, migration_15, migration_16, migration_17, migration_18, migration_19, migration_20, migration_21, migration_22, run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import SQLiteCreativePackagingRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_instagram_repository import SQLiteInstagramRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_youtube_repository import SQLiteYouTubeRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser, dispatch
from creator_intelligence_studio.presentation.desktop.view_models.workspace import WorkspaceViewModel
from creator_intelligence_studio.presentation.desktop.views.instagram_integration_view import InstagramIntegrationView
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


class MemoryInstagramCredentialStore:
    def __init__(self) -> None:
        self._bundles: dict[str, object] = {}

    def save(self, reference: str, bundle) -> None:
        self._bundles[reference] = bundle

    def load(self, reference: str):
        return self._bundles.get(reference)

    def delete(self, reference: str) -> None:
        self._bundles.pop(reference, None)


class FakeInstagramOAuthClient:
    def __init__(self) -> None:
        self.begin_calls: list[tuple[str, tuple[str, ...], str | None]] = []
        self.exchange_calls: list[tuple[str, str | None, str, str]] = []
        self.verify_calls: list[tuple[str, tuple[str, ...]]] = []
        self.revoke_calls: list[str] = []
        self.refresh_calls: list[tuple[str, str | None, str]] = []
        self._token_user_ids = {
            "code-a": "ig-a",
            "code-b": "ig-b",
            "code-personal": "ig-personal",
        }

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> InstagramOAuthAuthorizationResult:
        self.begin_calls.append((client_id, scopes, redirect_uri))
        return InstagramOAuthAuthorizationResult(
            authorization_url="https://www.instagram.com/oauth/authorize?stub=1",
            state=state or "state",
            redirect_uri=redirect_uri or "https://example.invalid/callback",
            provider=InstagramAuthProvider.INSTAGRAM_LOGIN,
            code_challenge="challenge",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> InstagramOAuthTokenResult:
        self.exchange_calls.append((client_id, client_secret, code, redirect_uri))
        user_id = self._token_user_ids.get(code, "ig-a")
        return InstagramOAuthTokenResult(
            access_token=f"access-{code}",
            refresh_token=f"refresh-{code}",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            instagram_user_id=user_id,
            expires_at="2026-08-01T00:00:00Z",
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> InstagramOAuthTokenResult:
        self.refresh_calls.append((client_id, client_secret, refresh_token))
        return InstagramOAuthTokenResult(
            access_token="refreshed-token",
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            instagram_user_id="ig-a",
            expires_at="2026-08-01T00:00:00Z",
        )

    def revoke(self, token: str) -> bool:
        self.revoke_calls.append(token)
        return True

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:
        self.verify_calls.append((token, scopes))
        code = token.removeprefix("access-")
        return {
            "instagram_user_id": self._token_user_ids.get(code, "ig-a"),
            "granted_scopes": scopes,
            "missing_scopes": (),
        }


class FakeInstagramResponse:
    def __init__(self, payload: dict[str, object], headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.headers = headers or {}


class FakeInstagramApiClient:
    def __init__(self) -> None:
        self.api_version = DEFAULT_INSTAGRAM_API_VERSION
        self.account_payloads = {
            "ig-a": {
                "id": "ig-a",
                "username": "creator_a",
                "name": "Creator A",
                "biography": "Entertainment creator",
                "website": "https://example.com/a",
                "profile_picture_url": "https://example.com/a.jpg",
                "followers_count": 1200,
                "follows_count": 130,
                "media_count": 3,
                "account_type": "creator",
            },
            "ig-b": {
                "id": "ig-b",
                "username": "creator_b",
                "name": "Creator B",
                "biography": "Music education",
                "website": "https://example.com/b",
                "profile_picture_url": "https://example.com/b.jpg",
                "followers_count": 540,
                "follows_count": 90,
                "media_count": 2,
                "account_type": "business",
            },
            "ig-personal": {
                "id": "ig-personal",
                "username": "personal_account",
                "name": "Personal Account",
                "account_type": "personal",
            },
        }
        self.media_sequences = {
            "ig-a": [
                {
                    "data": [
                        {
                            "id": "shared-media",
                            "caption": "Topic high reach low conversion",
                            "media_type": "reels",
                            "media_product_type": "reels",
                            "media_url": "https://example.com/a/shared.mp4",
                            "thumbnail_url": "https://example.com/a/shared.jpg",
                            "cover_url": "https://example.com/a/shared-cover-v1.jpg",
                            "permalink": "https://instagram.com/p/shared-media",
                            "timestamp": "2026-07-25T12:00:00Z",
                            "shortcode": "sharedmedia",
                            "children_count": 0,
                            "views": 5000,
                            "reach": 4300,
                            "shares": 22,
                            "saves": 4,
                            "likes": 80,
                            "comments": 2,
                            "profile_visits": 12,
                            "follows": 1,
                            "completion_rate": 0.31,
                        },
                        {
                            "id": "carousel-a",
                            "caption": "Carousel educational bridge",
                            "media_type": "carousel_album",
                            "media_product_type": "feed",
                            "media_url": "https://example.com/a/carousel.mp4",
                            "thumbnail_url": "https://example.com/a/carousel.jpg",
                            "cover_url": "https://example.com/a/carousel-cover-v1.jpg",
                            "permalink": "https://instagram.com/p/carousel-a",
                            "timestamp": "2026-07-24T12:00:00Z",
                            "shortcode": "carousela",
                            "children_count": 2,
                            "children": {
                                "data": [
                                    {"id": "child-a-1", "media_type": "image", "media_url": "https://example.com/a/c1.jpg", "thumbnail_url": "https://example.com/a/c1-thumb.jpg"},
                                    {"id": "child-a-2", "media_type": "video", "media_url": "https://example.com/a/c2.mp4", "thumbnail_url": "https://example.com/a/c2-thumb.jpg"},
                                ]
                            },
                            "views": 1500,
                            "reach": 1100,
                            "shares": 10,
                            "saves": 18,
                            "likes": 95,
                            "comments": 8,
                            "profile_visits": 30,
                            "follows": 11,
                            "completion_rate": 0.74,
                        },
                    ],
                    "paging": {"cursors": {"after": "cursor-a-2"}},
                },
                {
                    "data": [
                        {
                            "id": "shared-media",
                            "caption": "Topic high reach low conversion updated",
                            "media_type": "reels",
                            "media_product_type": "reels",
                            "media_url": "https://example.com/a/shared.mp4",
                            "thumbnail_url": "https://example.com/a/shared.jpg",
                            "cover_url": "https://example.com/a/shared-cover-v2.jpg",
                            "permalink": "https://instagram.com/p/shared-media",
                            "timestamp": "2026-07-25T12:00:00Z",
                            "shortcode": "sharedmedia",
                            "children_count": 0,
                            "views": 5400,
                            "reach": 4700,
                            "shares": 25,
                            "saves": 5,
                            "likes": 90,
                            "comments": 2,
                            "profile_visits": 15,
                            "follows": 2,
                            "completion_rate": 0.34,
                        }
                    ],
                    "paging": {"cursors": {"after": None}},
                },
            ],
            "ig-b": [
                {
                    "data": [
                        {
                            "id": "shared-media",
                            "caption": "Music education longform",
                            "media_type": "video",
                            "media_product_type": "feed",
                            "media_url": "https://example.com/b/shared.mp4",
                            "thumbnail_url": "https://example.com/b/shared.jpg",
                            "cover_url": "https://example.com/b/shared-cover.jpg",
                            "permalink": "https://instagram.com/p/shared-media",
                            "timestamp": "2026-07-25T14:00:00Z",
                            "shortcode": "sharedmedia",
                            "children_count": 0,
                            "views": 800,
                            "reach": 620,
                            "shares": 3,
                            "saves": 7,
                            "likes": 55,
                            "comments": 6,
                            "profile_visits": 28,
                            "follows": 13,
                            "completion_rate": 0.82,
                        }
                    ],
                    "paging": {"cursors": {"after": None}},
                }
            ],
            "ig-personal": [{"data": [], "paging": {"cursors": {"after": None}}}],
        }
        self.account_insights = {
            "ig-a": {
                "data": [
                    {"name": "reach", "values": [{"value": 5200, "unit": "count"}]},
                    {"name": "accounts_engaged", "values": [{"value": 180, "unit": "count"}]},
                    {"name": "profile_visits", "values": [{"value": 42, "unit": "count"}]},
                    {"name": "follows", "values": [{"value": 14, "unit": "count"}]},
                ],
                "date_start": "2026-07-01",
                "date_end": "2026-07-07",
                "comparable_window": "day_7",
                "status": "ok",
            },
            "ig-b": {"data": [], "date_start": "2026-07-01", "date_end": "2026-07-07", "comparable_window": "day_7", "status": "empty"},
        }
        self.media_insights = {
            "shared-media": {
                "data": [
                    {"name": "reach", "values": [{"value": 4300, "unit": "count"}]},
                    {"name": "views", "values": [{"value": 5000, "unit": "count"}]},
                    {"name": "shares", "values": [{"value": 22, "unit": "count"}]},
                    {"name": "saves", "values": [{"value": 4, "unit": "count"}]},
                ],
                "date_start": "2026-07-01",
                "date_end": "2026-07-07",
                "comparable_window": "day_7",
                "status": "ok",
            }
        }
        self.account_calls: list[tuple[str, str, tuple[str, ...]]] = []
        self.media_calls: list[tuple[str, str | None, str | None, int]] = []
        self.account_insight_calls: list[tuple[str, str, tuple[str, ...], str]] = []
        self.media_insight_calls: list[tuple[str, str, tuple[str, ...], str]] = []
        self._media_call_count: dict[str, int] = {}
        self.profile_errors: dict[str, InstagramApiErrorDetails] = {}

    def fetch_account(self, *, token: str, instagram_user_id: str, fields: tuple[str, ...]):
        if instagram_user_id in self.profile_errors:
            raise InstagramApiError(self.profile_errors[instagram_user_id])
        self.account_calls.append((token, instagram_user_id, fields))
        return FakeInstagramResponse(self.account_payloads[instagram_user_id], headers={"x-app-usage": "{\"call_count\":1}"})

    def fetch_media(self, *, token: str, instagram_user_id: str, fields: tuple[str, ...], after: str | None = None, before: str | None = None, limit: int = 25):
        self.media_calls.append((instagram_user_id, after, before, limit))
        count = self._media_call_count.get(instagram_user_id, 0)
        self._media_call_count[instagram_user_id] = count + 1
        sequence = self.media_sequences[instagram_user_id]
        payload = sequence[min(count, len(sequence) - 1)]
        return FakeInstagramResponse(payload, headers={"x-app-usage": "{\"call_count\":2}"})

    def fetch_children(self, *, token: str, media_id: str, fields: tuple[str, ...]):
        return FakeInstagramResponse({"data": []})

    def fetch_account_insights(self, *, token: str, instagram_user_id: str, metrics: tuple[str, ...], period):
        self.account_insight_calls.append((token, instagram_user_id, metrics, period.value))
        return FakeInstagramResponse(self.account_insights[instagram_user_id], headers={"x-app-usage": "{\"call_count\":3}"})

    def fetch_media_insights(self, *, token: str, media_id: str, metrics: tuple[str, ...], period):
        self.media_insight_calls.append((token, media_id, metrics, period.value))
        return FakeInstagramResponse(self.media_insights.get(media_id, {"data": [], "status": "empty"}), headers={"x-app-usage": "{\"call_count\":4}"})


def _make_bundle(root: Path, api_client: FakeInstagramApiClient | None = None, oauth_client: FakeInstagramOAuthClient | None = None, oauth_broker: InstagramOAuthBrokerService | None = None):
    settings = make_settings()
    paths = ProjectPaths.from_settings(root, settings)
    paths.ensure_runtime_directories()
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    catalog = bootstrap.build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
    analytics_repository = SQLiteAnalyticsRepository(database)
    creative_packaging_repository = SQLiteCreativePackagingRepository(database)
    instagram_repository = SQLiteInstagramRepository(database)
    service = build_instagram_integration_service(
        settings=settings,
        paths=paths,
        repository=instagram_repository,
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=creative_packaging_repository,
        oauth_client=oauth_client or FakeInstagramOAuthClient(),
        oauth_broker=oauth_broker,
        credential_store=MemoryInstagramCredentialStore(),
        api_client=api_client or FakeInstagramApiClient(),
        logger=logging.getLogger("test"),
    )
    return settings, paths, database, catalog, analytics_repository, creative_packaging_repository, instagram_repository, service


def _make_broker(oauth_client: FakeInstagramOAuthClient) -> InstagramOAuthBrokerService:
    return InstagramOAuthBrokerService(
        client_id="client-id",
        client_secret="client-secret",
        callback_url="https://broker.example.test/oauth/instagram/callback",
        oauth_client=oauth_client,
        store=InMemoryInstagramOAuthBrokerStore(),
        transaction_ttl_seconds=60,
        logger=logging.getLogger("test"),
    )


def _seed_analytics_channel(analytics_repository: SQLiteAnalyticsRepository, *, creator_id: str, channel_id: str) -> None:
    now = datetime(2026, 7, 27, tzinfo=timezone.utc)
    platform = analytics_repository.upsert_platform(
        AnalyticsPlatform(
            id="platform-instagram-reel",
            platform_key="instagram_reel",
            display_name="Instagram Reels",
            status=AnalyticsPlatformStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    analytics_repository.upsert_channel(
        AnalyticsChannel(
            id=channel_id,
            creator_id=creator_id,
            platform_id=platform.id,
            platform_key=platform.platform_key,
            external_channel_id=channel_id,
            channel_name=f"Instagram {creator_id}",
            channel_url=f"https://instagram.com/{creator_id}",
            timezone_name="UTC",
            is_primary=True,
            metadata_json="{}",
            created_at=now,
            updated_at=now,
        )
    )


def _seed_instagram_metric_definitions(analytics_repository: SQLiteAnalyticsRepository) -> None:
    now = datetime(2026, 7, 27, tzinfo=timezone.utc)
    metric_specs = {
        "views": (AnalyticsMetricCategory.ATTENTION, "count"),
        "reach": (AnalyticsMetricCategory.DISCOVERY, "count"),
        "shares": (AnalyticsMetricCategory.INTERACTION, "count"),
        "saves": (AnalyticsMetricCategory.INTERACTION, "count"),
        "likes": (AnalyticsMetricCategory.INTERACTION, "count"),
        "comments": (AnalyticsMetricCategory.INTERACTION, "count"),
        "profile_visits": (AnalyticsMetricCategory.RELATION, "count"),
        "follows": (AnalyticsMetricCategory.CONVERSION, "count"),
        "completion_rate": (AnalyticsMetricCategory.ATTENTION, "ratio"),
        "accounts_engaged": (AnalyticsMetricCategory.RELATION, "count"),
        "plays": (AnalyticsMetricCategory.ATTENTION, "count"),
        "watch_time": (AnalyticsMetricCategory.ATTENTION, "seconds"),
    }
    for key, (category, unit) in metric_specs.items():
        analytics_repository.upsert_metric_definition(
            AnalyticsMetricDefinition(
                id=f"metric-{key}",
                metric_key=key,
                display_name=key.replace("_", " ").title(),
                category=category,
                unit=unit,
                value_type=AnalyticsValueType.NUMERIC,
                aggregation_type=AnalyticsAggregationType.LATEST,
                higher_is_better=None,
                description=f"Instagram metric {key}",
                aliases_json="[]",
                applicability_json='{"platform":"instagram"}',
                created_at=now,
            )
        )


class InstagramIntegrationTests(unittest.TestCase):
    def test_migration_v23_schema_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                self.assertEqual(versions[-1], 37)
                expected = {
                    "instagram_connections",
                    "instagram_accounts",
                    "instagram_remote_media",
                    "instagram_carousel_children",
                    "instagram_caption_versions",
                    "instagram_cover_versions",
                    "instagram_sync_runs",
                    "instagram_sync_items",
                    "instagram_insight_imports",
                    "instagram_insight_values",
                    "instagram_content_links",
                    "instagram_rate_limit_usage",
                    "instagram_sync_schedules",
                }
                self.assertTrue(expected.issubset(tables))
                run_migrations(connection)
                second_pass = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
            self.assertEqual(versions, second_pass)

    def test_upgrade_from_v22_applies_v23_and_preserves_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                ensure_schema_migrations_table(connection)
                for version in range(1, 23):
                    getattr(__import__("creator_intelligence_studio.infrastructure.persistence.migrations", fromlist=[f"migration_{version}"]), f"migration_{version}")(connection)
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (version, f"migration_{version}", "2026-07-27T00:00:00Z"),
                    )
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
            self.assertEqual(versions[-1], 37)

    def test_sync_profile_media_insights_history_and_creator_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            oauth_client = FakeInstagramOAuthClient()
            settings, paths, database, catalog, analytics_repository, creative_packaging_repository, instagram_repository, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")

            connection_a = service.connect_account(creator_id=creator_a.id, client_id="client-a", authorization_code="code-a")
            connection_b = service.connect_account(creator_id=creator_b.id, client_id="client-b", authorization_code="code-b")
            self.assertEqual(connection_a.connection.status, InstagramConnectionStatus.VERIFIED)
            self.assertEqual(connection_b.connection.status, InstagramConnectionStatus.VERIFIED)

            account_a = service.list_accounts(creator_a.id)[0]
            account_b = service.list_accounts(creator_b.id)[0]
            self.assertEqual(account_a.account_type, InstagramProfessionalAccountType.CREATOR)
            self.assertEqual(account_b.account_type, InstagramProfessionalAccountType.BUSINESS)
            _seed_analytics_channel(analytics_repository, creator_id=creator_a.id, channel_id=account_a.id)
            _seed_analytics_channel(analytics_repository, creator_id=creator_b.id, channel_id=account_b.id)
            _seed_instagram_metric_definitions(analytics_repository)

            result_a = service.sync_account(account_id=account_a.id)
            result_b = service.sync_account(account_id=account_b.id)
            self.assertEqual(result_a.run.creator_id, creator_a.id)
            self.assertEqual(result_b.run.creator_id, creator_b.id)

            self.assertEqual(len(service.list_media(account_a.id)), 2)
            self.assertEqual(len(service.list_media(account_b.id)), 1)
            self.assertEqual(instagram_repository.list_remote_media(creator_a.id)[0].creator_id, creator_a.id)
            self.assertEqual(instagram_repository.list_remote_media(creator_b.id)[0].creator_id, creator_b.id)

            self.assertGreaterEqual(len(analytics_repository.list_publications(creator_a.id)), 2)
            self.assertEqual({publication.creator_id for publication in analytics_repository.list_publications(creator_a.id)}, {creator_a.id})
            self.assertEqual({publication.creator_id for publication in analytics_repository.list_publications(creator_b.id)}, {creator_b.id})

            account_insights_a = service.sync_insights(account_id=account_a.id)
            media_insights_a = service.sync_insights(account_id=account_a.id, remote_media_id="shared-media")
            account_insights_b = service.sync_insights(account_id=account_b.id)
            self.assertGreaterEqual(len(account_insights_a.insight_values), 4)
            self.assertGreaterEqual(len(media_insights_a.insight_values), 4)
            self.assertEqual(len(account_insights_b.insight_values), 0)

            sync_runs_a = service.list_sync_runs(creator_a.id)
            sync_runs_b = service.list_sync_runs(creator_b.id)
            self.assertTrue(all(run.creator_id == creator_a.id for run in sync_runs_a))
            self.assertTrue(all(run.creator_id == creator_b.id for run in sync_runs_b))
            self.assertTrue(service.list_rate_limit_usage(connection_a.connection.id))
            self.assertTrue(service.list_rate_limit_usage(connection_b.connection.id))

            result_a_2 = service.sync_account(account_id=account_a.id)
            remote_media = instagram_repository.get_remote_media_by_instagram_id(creator_a.id, "shared-media")
            self.assertIsNotNone(remote_media)
            self.assertEqual(len(service.list_caption_versions(remote_media.id)), 2)
            self.assertEqual(len(service.list_cover_versions(remote_media.id)), 2)
            self.assertEqual(result_a_2.report.next_recommended_action, "incremental_sync")

            link = service.link_content(remote_media_id=remote_media.id, publication_id=analytics_repository.list_publications(creator_a.id)[0].id, confidence_level="high", status="linked")
            self.assertEqual(link.creator_id, creator_a.id)
            self.assertEqual(len(service.list_content_links(creator_b.id)), 0)

            sample_sync_run = sync_runs_a[0]
            export_path = service.export_report(sample_sync_run.id, "json")
            self.assertTrue(export_path.exists())
            self.assertIn("instagram_sync", export_path.name)

    def test_personal_account_rejected_and_scope_allowlist_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            oauth_client = FakeInstagramOAuthClient()
            settings, paths, database, catalog, analytics_repository, _, _, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client)
            creator = catalog.create_creator(display_name="Creator X")
            with self.assertRaises(InstagramAccountValidationError):
                service.connect_account(creator_id=creator.id, client_id="client-x", authorization_code="code-personal")
            self.assertFalse(any(is_write_scope(scope) for scope in READ_ONLY_SCOPES))

    def test_profile_read_creates_canonical_account_and_preserves_creator_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            oauth_client = FakeInstagramOAuthClient()
            broker = _make_broker(oauth_client)
            settings, paths, database, catalog, analytics_repository, _, _, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client, oauth_broker=broker)
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")

            proof_a = generate_transaction_proof()
            start_a = service.start_oauth_transaction(creator_id=creator_a.id, client_id="client-id", transaction_proof=proof_a)
            broker.handle_callback(state=start_a.state, code="code-a")
            pending_a = service.complete_oauth_transaction(creator_id=creator_a.id, transaction_id=start_a.transaction_id, transaction_proof=proof_a)
            before_begin_calls = len(oauth_client.begin_calls)
            before_exchange_calls = len(oauth_client.exchange_calls)
            before_verify_calls = len(oauth_client.verify_calls)
            result_a = service.read_account_profile(pending_a.connection.id)
            expected_ref_a = build_instagram_credential_reference(creator_id=creator_a.id, instagram_user_id="ig-a")

            proof_b = generate_transaction_proof()
            start_b = service.start_oauth_transaction(creator_id=creator_b.id, client_id="client-id", transaction_proof=proof_b)
            broker.handle_callback(state=start_b.state, code="code-b")
            pending_b = service.complete_oauth_transaction(creator_id=creator_b.id, transaction_id=start_b.transaction_id, transaction_proof=proof_b)
            result_b = service.read_account_profile(pending_b.connection.id)
            expected_ref_b = build_instagram_credential_reference(creator_id=creator_b.id, instagram_user_id="ig-b")

            self.assertTrue(result_a.success)
            self.assertTrue(result_b.success)
            self.assertEqual(result_a.connection.status, InstagramConnectionStatus.VERIFIED)
            self.assertEqual(result_b.connection.status, InstagramConnectionStatus.VERIFIED)
            self.assertEqual(result_a.connection.credential_reference, expected_ref_a)
            self.assertEqual(result_b.connection.credential_reference, expected_ref_b)
            self.assertEqual(result_a.connection.credential_reference, pending_a.connection.credential_reference)
            self.assertEqual(result_b.connection.credential_reference, pending_b.connection.credential_reference)
            self.assertEqual(result_a.account.account_type, InstagramProfessionalAccountType.CREATOR)
            self.assertEqual(result_b.account.account_type, InstagramProfessionalAccountType.BUSINESS)
            self.assertEqual(result_a.account.username, "creator_a")
            self.assertEqual(result_b.account.username, "creator_b")
            self.assertEqual(len(service.list_accounts(creator_a.id)), 1)
            self.assertEqual(len(service.list_accounts(creator_b.id)), 1)
            self.assertEqual(service.list_accounts(creator_a.id)[0].creator_id, creator_a.id)
            self.assertEqual(service.list_accounts(creator_b.id)[0].creator_id, creator_b.id)
            self.assertEqual(len(service.list_connections(creator_a.id)), 1)
            self.assertEqual(len(service.list_connections(creator_b.id)), 1)
            self.assertEqual(len(api_client.account_calls), 2)
            self.assertEqual(api_client.account_calls[0][0], "access-code-a")
            self.assertEqual(api_client.account_calls[0][1], "ig-a")
            self.assertEqual(api_client.account_calls[0][2], PROFILE_READ_FIELDS)
            self.assertEqual(api_client.account_calls[1][0], "access-code-b")
            self.assertEqual(api_client.account_calls[1][1], "ig-b")
            self.assertEqual(api_client.account_calls[1][2], PROFILE_READ_FIELDS)
            self.assertEqual(len(oauth_client.begin_calls), before_begin_calls + 1)
            self.assertEqual(len(oauth_client.exchange_calls), before_exchange_calls + 1)
            self.assertEqual(len(oauth_client.verify_calls), before_verify_calls)

    def test_profile_read_preserves_nullable_fields_and_text_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            api_client.account_payloads["ig-a"] = {
                "id": "ig-a",
                "username": "Creator_Emoji",
                "name": "Creator Emoji",
                "biography": "Hola, mundo! ✨ #Creador?",
                "website": None,
                "profile_picture_url": None,
                "followers_count": None,
                "follows_count": None,
                "media_count": None,
                "account_type": "creator",
            }
            oauth_client = FakeInstagramOAuthClient()
            broker = _make_broker(oauth_client)
            settings, paths, database, catalog, analytics_repository, _, _, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client, oauth_broker=broker)
            creator = catalog.create_creator(display_name="Creator Emoji")

            proof = generate_transaction_proof()
            start = service.start_oauth_transaction(creator_id=creator.id, client_id="client-id", transaction_proof=proof)
            broker.handle_callback(state=start.state, code="code-a")
            pending = service.complete_oauth_transaction(creator_id=creator.id, transaction_id=start.transaction_id, transaction_proof=proof)
            result = service.read_account_profile(pending.connection.id)

            self.assertTrue(result.success)
            self.assertEqual(result.account.username, "Creator_Emoji")
            self.assertEqual(result.account.biography, "Hola, mundo! ✨ #Creador?")
            self.assertIsNone(result.account.website)
            self.assertIsNone(result.account.profile_picture_url)
            self.assertIsNone(result.account.followers_count)
            self.assertIsNone(result.account.follows_count)
            self.assertIsNone(result.account.media_count)

    def test_profile_read_reports_sanitized_provider_failures_without_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            oauth_client = FakeInstagramOAuthClient()
            broker = _make_broker(oauth_client)
            settings, paths, database, catalog, analytics_repository, _, _, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client, oauth_broker=broker)
            creator = catalog.create_creator(display_name="Creator Errors")

            proof = generate_transaction_proof()
            start = service.start_oauth_transaction(creator_id=creator.id, client_id="client-id", transaction_proof=proof)
            broker.handle_callback(state=start.state, code="code-a")
            pending = service.complete_oauth_transaction(creator_id=creator.id, transaction_id=start.transaction_id, transaction_proof=proof)

            scenarios = [
                (
                    "auth_expired",
                    InstagramApiErrorDetails(
                        http_status=401,
                        code="190",
                        reason="OAuthException",
                        message="Error validating access token: Session expired.",
                        request_path="ig-a",
                        request_url="https://graph.instagram.com/v25.0/ig-a?fields=id",
                        response_headers={"x-app-usage": "{\"call_count\":90}"},
                    ),
                    IntegrationErrorCategory.AUTHENTICATION_EXPIRED,
                ),
                (
                    "provider_unavailable",
                    InstagramApiErrorDetails(
                        http_status=503,
                        code="2",
                        reason="ServiceUnavailable",
                        message="Service temporarily unavailable.",
                        request_path="ig-a",
                        request_url="https://graph.instagram.com/v25.0/ig-a?fields=id",
                        response_headers={},
                    ),
                    IntegrationErrorCategory.PROVIDER_UNAVAILABLE,
                ),
                (
                    "rate_limited",
                    InstagramApiErrorDetails(
                        http_status=429,
                        code="4",
                        reason="rate limit",
                        message="Too many calls.",
                        request_path="ig-a",
                        request_url="https://graph.instagram.com/v25.0/ig-a?fields=id",
                        response_headers={"x-app-usage": "{\"call_count\":100}"},
                    ),
                    IntegrationErrorCategory.RATE_LIMITED,
                ),
                (
                    "malformed_response",
                    InstagramApiErrorDetails(
                        http_status=400,
                        code=None,
                        reason=None,
                        message="Respuesta invalida del proveedor.",
                        request_path="ig-a",
                        request_url="https://graph.instagram.com/v25.0/ig-a?fields=id",
                        response_headers={},
                    ),
                    IntegrationErrorCategory.INVALID_REQUEST,
                ),
            ]
            for label, error_details, expected_category in scenarios:
                with self.subTest(label=label):
                    api_client.profile_errors["ig-a"] = error_details
                    before_begin_calls = len(oauth_client.begin_calls)
                    before_exchange_calls = len(oauth_client.exchange_calls)
                    before_verify_calls = len(oauth_client.verify_calls)
                    result = service.read_account_profile(pending.connection.id)
                    self.assertFalse(result.success)
                    self.assertIsNone(result.account)
                    self.assertIsNotNone(result.error)
                    self.assertEqual(result.error.category, expected_category)
                    self.assertEqual(result.error.message, error_details.message)
                    expected_user_status = {
                        IntegrationErrorCategory.AUTHENTICATION_EXPIRED: "auth_expired",
                        IntegrationErrorCategory.PROVIDER_UNAVAILABLE: "provider_unavailable",
                        IntegrationErrorCategory.RATE_LIMITED: "quota_exhausted",
                    }.get(expected_category, "needs_attention")
                    self.assertEqual(result.health.user_status.value, expected_user_status)
                    self.assertEqual(len(oauth_client.begin_calls), before_begin_calls)
                    self.assertEqual(len(oauth_client.exchange_calls), before_exchange_calls)
                    self.assertEqual(len(oauth_client.verify_calls), before_verify_calls)
                    api_client.profile_errors.pop("ig-a", None)

    def test_cli_dispatch_and_gui_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            api_client = FakeInstagramApiClient()
            oauth_client = FakeInstagramOAuthClient()
            settings, paths, database, catalog, analytics_repository, _, _, service = _make_bundle(root, api_client=api_client, oauth_client=oauth_client)
            creator = catalog.create_creator(display_name="Creator CLI")
            service.connect_account(creator_id=creator.id, client_id="client-cli", authorization_code="code-a")
            account = service.list_accounts(creator.id)[0]
            _seed_analytics_channel(analytics_repository, creator_id=creator.id, channel_id=account.id)
            _seed_instagram_metric_definitions(analytics_repository)
            service.sync_account(account_id=account.id)

            parser = build_parser()
            args = parser.parse_args(["instagram", "connections", "--creator-id", creator.id, "--json"])
            stdout = io.StringIO()
            stderr = io.StringIO()
            dummy = SimpleNamespace()
            code = dispatch(
                args,
                service=service,
                media_service=dummy,
                audio_service=dummy,
                transcription_service=dummy,
                acoustic_service=dummy,
                visual_service=dummy,
                multimodal_service=dummy,
                clip_service=dummy,
                diagnostic=dummy,
                stdout=stdout,
                stderr=stderr,
                instagram_service=service,
            )
            self.assertEqual(code, 0)
            json.loads(stdout.getvalue())

            if QApplication is None:
                self.skipTest("PySide6 not available")
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication.instance() or QApplication([])
            workspace = SimpleNamespace(
                selected_creator_id=creator.id,
                list_instagram_connections=lambda creator_id: service.list_connections(creator_id),
                list_instagram_accounts=lambda creator_id: service.list_accounts(creator_id),
                list_instagram_media=lambda account_id: service.list_media(account_id),
                list_instagram_content_links=lambda creator_id: service.list_content_links(creator_id),
                list_instagram_insight_imports=lambda creator_id, account_id=None: service.list_insight_imports(creator_id, account_id=account_id),
                list_instagram_insight_values=lambda insight_import_id: service.list_insight_values(insight_import_id),
                list_instagram_sync_runs=lambda creator_id: service.list_sync_runs(creator_id),
                list_instagram_rate_limit_usage=lambda connection_id: service.list_rate_limit_usage(connection_id),
                verify_instagram_connection=lambda connection_id: service.verify_connection(connection_id),
                disconnect_instagram_connection=lambda connection_id: service.disconnect_connection(connection_id),
                revoke_instagram_connection=lambda connection_id: service.revoke_connection(connection_id),
                select_instagram_account=lambda account_id: service.select_account(account_id),
                read_instagram_account_profile=lambda connection_id: service.read_account_profile(connection_id),
                sync_instagram_account=lambda account_id, **kwargs: service.sync_account(account_id=account_id, **kwargs),
                sync_instagram_media=lambda account_id, **kwargs: service.sync_media(account_id=account_id, **kwargs),
                sync_instagram_insights=lambda account_id, **kwargs: service.sync_insights(account_id=account_id, **kwargs),
                sync_instagram_incremental=lambda account_id, **kwargs: service.sync_incremental(account_id=account_id, **kwargs),
                sync_instagram_repair=lambda account_id: service.sync_repair(account_id=account_id),
                export_instagram_sync_report=lambda run_id, format_name="json", destination=None: service.export_report(run_id, format_name, destination=destination),
                interrupt_instagram_sync_run=lambda run_id, reason=None: service.show_sync_run(run_id),
                resume_instagram_sync_run=lambda run_id: service.resume_sync(run_id),
                background_tasks=lambda: [
                    SimpleNamespace(
                        task_id=service.list_sync_runs(creator.id)[0].id,
                        title="Sincronizacion de Instagram",
                        status=service.list_sync_runs(creator.id)[0].status.value,
                        stage_name=service.list_sync_runs(creator.id)[0].sync_type.value,
                        video_title=account.id,
                        action_id=account.id,
                        progress_percent=100.0,
                        message="completed",
                        error=None,
                        cancellable=True,
                        updated_at="2026-07-27T00:00:00Z",
                        payload={"kind": "instagram_sync", "run": service.list_sync_runs(creator.id)[0].to_dict(), "creator_id": creator.id, "account_id": account.id, "sync_type": service.list_sync_runs(creator.id)[0].sync_type.value},
                    )
                ],
            )
            view = InstagramIntegrationView(workspace)
            view.refresh()
            self.assertGreaterEqual(view.connection_table.rowCount(), 1)
            self.assertGreaterEqual(view.account_table.rowCount(), 1)
            task_view = TaskCenterView(workspace)
            task_view.refresh()
            self.assertGreaterEqual(task_view.table.rowCount(), 1)
