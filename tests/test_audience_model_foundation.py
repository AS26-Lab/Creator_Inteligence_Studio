from __future__ import annotations

import csv
import logging
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - optional in some environments
    QApplication = None

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsImportService
from creator_intelligence_studio.application.services.audience_model_service import build_audience_model_service
from creator_intelligence_studio.application.services.catalog_service import build_catalog_service
from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricSnapshot, AnalyticsPublication
from creator_intelligence_studio.domain.analytics.metric_definitions import default_metric_definitions
from creator_intelligence_studio.domain.analytics.services import build_metric_snapshot_dedupe_key, build_publication_dedupe_key
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsContentType, AnalyticsQualityStatus, AnalyticsSourceType
from creator_intelligence_studio.domain.audience_model.audience_types import AudienceReviewDecision
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import (
    migration_1,
    migration_2,
    migration_3,
    migration_4,
    migration_5,
    migration_6,
    migration_7,
    migration_8,
    migration_9,
    migration_10,
    migration_11,
    migration_12,
    migration_13,
    migration_14,
    migration_15,
    migration_16,
    migration_17,
    migration_18,
    migration_19,
    migration_20,
    migration_21,
    migration_22,
    ensure_schema_migrations_table,
    run_migrations,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import SQLiteAnalyticsRepository
from creator_intelligence_studio.infrastructure.persistence.sqlite_audience_repository import SQLiteAudienceRepository
from creator_intelligence_studio.presentation.cli.cli import build_parser
from creator_intelligence_studio.presentation.desktop.views.audience_overview_view import AudienceOverviewView
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
        audio_normalization_sample_rate_hz=16000,
        audio_extraction_timeout_seconds=60.0,
        audio_cache_version="v1",
        preferred_audio_language=None,
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    headers = list(dict.fromkeys(key for row in rows for key in row.keys()))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def build_import_row(*, title: str, video_id: str, published_at: str, platform: str, topic: str, format_name: str, views: int, new_viewers: int | None = None, unique_viewers: int | None = None, returning_viewers: int | None = None, search_views: int | None = None, suggested_views: int | None = None, browse_views: int | None = None, shorts_feed_views: int | None = None, external_views: int | None = None, direct_views: int | None = None, watch_time_minutes: int | None = None, average_view_duration_seconds: int | None = None, average_percentage_viewed: float | None = None, completion_rate: float | None = None, likes: int | None = None, comments: int | None = None, shares: int | None = None, saves: int | None = None, subscribers_gained: int | None = None, subscribers_lost: int | None = None, profile_visits: int | None = None, traffic_to_longform: int | None = None, traffic_source: str | None = None, device_share: float | None = None, geography_share: float | None = None, subscription_status_share: float | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "title": title,
        "video_id": video_id,
        "published_at": published_at,
        "duration_seconds": 420,
        "content_type": format_name,
        "views": views,
        "new_viewers": new_viewers,
        "unique_viewers": unique_viewers,
        "returning_viewers": returning_viewers,
        "search_views": search_views,
        "suggested_views": suggested_views,
        "browse_views": browse_views,
        "shorts_feed_views": shorts_feed_views,
        "external_views": external_views,
        "direct_views": direct_views,
        "watch_time_minutes": watch_time_minutes,
        "average_view_duration_seconds": average_view_duration_seconds,
        "average_percentage_viewed": average_percentage_viewed,
        "completion_rate": completion_rate,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "subscribers_gained": subscribers_gained,
        "subscribers_lost": subscribers_lost,
        "profile_visits": profile_visits,
        "traffic_to_longform": traffic_to_longform,
        "traffic_source": traffic_source,
        "topic": topic,
        "format": format_name,
        "platform": platform,
        "device_share": device_share,
        "geography_share": geography_share,
        "subscription_status_share": subscription_status_share,
    }
    return {key: value for key, value in row.items() if value is not None}


def to_utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def seed_publication(
    repository: SQLiteAnalyticsRepository,
    *,
    creator_id: str,
    channel_id: str | None,
    platform: str,
    content_type: AnalyticsContentType,
    title: str,
    external_publication_id: str,
    published_at: str,
    duration_seconds: float,
    source_fingerprint: str,
    metrics: list[tuple[str, float | str | None, str, AnalyticsQualityStatus]] ,
) -> AnalyticsPublication:
    publication = AnalyticsPublication(
        id=external_publication_id,
        creator_id=creator_id,
        channel_id=channel_id,
        video_asset_id=None,
        external_publication_id=external_publication_id,
        platform=platform,
        content_type=content_type,
        title=title,
        description=None,
        published_at=to_utc_datetime(published_at),
        duration_seconds=duration_seconds,
        url=None,
        thumbnail_path=None,
        status="observed",
        source_type=AnalyticsSourceType.MANUAL,
        source_fingerprint=source_fingerprint,
        dedupe_key=build_publication_dedupe_key(
            platform=platform,
            external_publication_id=external_publication_id,
            url="",
            title=title,
            published_at=to_utc_datetime(published_at),
            channel_id=channel_id,
        ),
        created_at=to_utc_datetime(published_at),
        updated_at=to_utc_datetime(published_at),
    )
    captured_at = to_utc_datetime(published_at)
    with repository._database.connect() as connection:  # noqa: SLF001 - test fixture seeding
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO analytics_publications (
                id, creator_id, channel_id, video_asset_id, external_publication_id,
                platform, content_type, title, description, published_at,
                duration_seconds, url, thumbnail_path, status, source_type,
                source_fingerprint, dedupe_key, created_at, updated_at
            ) VALUES (
                :id, :creator_id, :channel_id, :video_asset_id, :external_publication_id,
                :platform, :content_type, :title, :description, :published_at,
                :duration_seconds, :url, :thumbnail_path, :status, :source_type,
                :source_fingerprint, :dedupe_key, :created_at, :updated_at
            )
            """,
            publication.to_dict() | {"content_type": publication.content_type.value, "source_type": publication.source_type.value},
        )
        for index, (metric_key, value, unit, quality_status) in enumerate(metrics, start=1):
            snapshot = AnalyticsMetricSnapshot(
                id=f"{external_publication_id}-{metric_key}",
                publication_id=publication.id,
                snapshot_date=captured_at.date().isoformat(),
                captured_at=captured_at,
                metric_key=metric_key,
                numeric_value=float(value) if isinstance(value, (int, float)) else None,
                text_value=str(value) if isinstance(value, str) else None,
                unit=unit,
                source_import_id=f"manual-{external_publication_id}",
                source_row_number=index,
                is_derived=False,
                quality_status=quality_status,
                warning_codes_json="[]",
                created_at=captured_at,
                row_fingerprint=f"{external_publication_id}:{metric_key}:{value}",
                dedupe_key=build_metric_snapshot_dedupe_key(
                    {
                        "publication_id": publication.id,
                        "metric_key": metric_key,
                        "snapshot_date": captured_at.date().isoformat(),
                        "source_import_id": f"manual-{external_publication_id}",
                        "source_row_number": index,
                        "row_fingerprint": f"{external_publication_id}:{metric_key}:{value}",
                    }
                ),
            )
            connection.execute(
                """
                INSERT INTO analytics_metric_snapshots (
                    id, publication_id, snapshot_date, captured_at, metric_key,
                    numeric_value, text_value, unit, source_import_id, source_row_number,
                    is_derived, quality_status, warning_codes_json, created_at, row_fingerprint, dedupe_key
                ) VALUES (
                    :id, :publication_id, :snapshot_date, :captured_at, :metric_key,
                    :numeric_value, :text_value, :unit, :source_import_id, :source_row_number,
                    :is_derived, :quality_status, :warning_codes_json, :created_at, :row_fingerprint, :dedupe_key
                )
                """,
                snapshot.to_dict() | {"quality_status": snapshot.quality_status.value, "is_derived": 1 if snapshot.is_derived else 0},
            )
    return publication


class AudienceModelFoundationTests(unittest.TestCase):
    def test_migration_v21_to_v22_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            database = build_database(settings, paths)
            with database.connect() as connection:
                for migration in (
                    migration_1,
                    migration_2,
                    migration_3,
                    migration_4,
                    migration_5,
                    migration_6,
                    migration_7,
                    migration_8,
                    migration_9,
                    migration_10,
                    migration_11,
                    migration_12,
                    migration_13,
                    migration_14,
                    migration_15,
                    migration_16,
                    migration_17,
                    migration_18,
                    migration_19,
                    migration_20,
                    migration_21,
                ):
                    migration(connection)
                ensure_schema_migrations_table(connection)
                connection.executemany(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, '2026-07-27T00:00:00Z')",
                    [(version, f"migration_{version}") for version in range(1, 22)],
                )
                run_migrations(connection)
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                run_migrations(connection)
                idempotent_count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
            self.assertEqual(versions[-1], 28)
            self.assertEqual(idempotent_count, 28)
            self.assertIn("audience_profiles", tables)
            self.assertIn("audience_model_runs", tables)

    def test_audience_model_build_for_synthetic_creators(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = make_settings()
            paths = ProjectPaths.from_settings(root, settings)
            paths.ensure_runtime_directories()
            database = build_database(settings, paths)
            with database.connect() as connection:
                run_migrations(connection)
            catalog = build_catalog_service(settings, paths, logger=logging.getLogger("test"), database=database)
            analytics_repository = SQLiteAnalyticsRepository(database)
            analytics_service = AnalyticsImportService(
                settings=settings,
                paths=paths,
                catalog_service=catalog,
                repository=analytics_repository,
                database=database,
                logger=logging.getLogger("test"),
            )
            creator_a = catalog.create_creator(display_name="Creator A")
            creator_b = catalog.create_creator(display_name="Creator B")
            for platform in ("youtube_longform", "youtube_short", "tiktok"):
                analytics_service.create_channel(
                    creator_id=creator_a.id,
                    platform=platform,
                    name=f"{platform} channel",
                    timezone_name="America/Mexico_City",
                    is_primary=platform == "youtube_longform",
                )
            analytics_service.create_channel(
                creator_id=creator_b.id,
                platform="youtube_longform",
                name="longform channel",
                timezone_name="America/Mexico_City",
                is_primary=True,
            )
            audience_service = build_audience_model_service(
                settings=settings,
                paths=paths,
                analytics_service=analytics_service,
                repository=SQLiteAudienceRepository(database),
                database=database,
                logger=logging.getLogger("test"),
            )

            short_publication = seed_publication(
                analytics_repository,
                creator_id=creator_a.id,
                channel_id=None,
                platform="youtube_short",
                content_type=AnalyticsContentType.SHORT_VIDEO,
                title="Short discovery",
                external_publication_id="a_short_1",
                published_at="2026-06-01T12:00:00",
                duration_seconds=32,
                source_fingerprint="seed-a-short-1",
                metrics=[
                    ("views", 10000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("new_viewers", 8000, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 9000, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 500, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 1200, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("shorts_feed_views", 7000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 900, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.65, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 500, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 50, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("shares", 25, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 30, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("profile_visits", 200, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_to_longform", 120, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "shorts_feed", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "entertainment", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "short_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            viral_publication = seed_publication(
                analytics_repository,
                creator_id=creator_a.id,
                channel_id=None,
                platform="youtube_longform",
                content_type=AnalyticsContentType.LONGFORM_VIDEO,
                title="Viral topic",
                external_publication_id="a_long_1",
                published_at="2026-06-07T12:00:00",
                duration_seconds=540,
                source_fingerprint="seed-a-long-1",
                metrics=[
                    ("views", 12000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 8000, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("returning_viewers", 500, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 400, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 7000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("browse_views", 1000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 1500, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("average_view_duration_seconds", 45, "seconds", AnalyticsQualityStatus.ACCEPTED),
                    ("average_percentage_viewed", 0.18, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.14, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 100, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 10, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("shares", 5, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 5, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "suggested", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "viral_topic", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "longform_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            tutorial_publication = seed_publication(
                analytics_repository,
                creator_id=creator_a.id,
                channel_id=None,
                platform="youtube_longform",
                content_type=AnalyticsContentType.LONGFORM_VIDEO,
                title="Tutorial conversion",
                external_publication_id="a_long_2",
                published_at="2026-06-30T12:00:00",
                duration_seconds=720,
                source_fingerprint="seed-a-long-2",
                metrics=[
                    ("views", 1500, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 1200, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("returning_viewers", 600, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 900, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 250, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("browse_views", 200, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 1800, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("average_view_duration_seconds", 220, "seconds", AnalyticsQualityStatus.ACCEPTED),
                    ("average_percentage_viewed", 0.82, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.8, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 250, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 35, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("shares", 15, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 120, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_to_longform", 300, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "search", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "tutorial", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "longform_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            tiktok_publication = seed_publication(
                analytics_repository,
                creator_id=creator_a.id,
                channel_id=None,
                platform="tiktok",
                content_type=AnalyticsContentType.TIKTOK,
                title="Manual TikTok",
                external_publication_id="a_tiktok_1",
                published_at="2026-06-15T12:00:00",
                duration_seconds=24,
                source_fingerprint="seed-a-tiktok-1",
                metrics=[
                    ("views", 7000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("new_viewers", 6500, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 6800, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("external_views", 400, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 700, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.5, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 420, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 22, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("shares", 300, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("profile_visits", 100, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "for_you", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "=DANGEROUS", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "tiktok", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            music_intro = seed_publication(
                analytics_repository,
                creator_id=creator_b.id,
                channel_id=None,
                platform="youtube_longform",
                content_type=AnalyticsContentType.LONGFORM_VIDEO,
                title="Music theory intro",
                external_publication_id="b_long_1",
                published_at="2026-06-01T12:00:00",
                duration_seconds=620,
                source_fingerprint="seed-b-long-1",
                metrics=[
                    ("views", 5000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 3500, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 3500, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 800, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 4200, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("average_view_duration_seconds", 260, "seconds", AnalyticsQualityStatus.ACCEPTED),
                    ("average_percentage_viewed", 0.74, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.71, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 250, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 30, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 120, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "search", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("subscription_status_share", 0.62, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "music theory", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "longform_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            music_follow = seed_publication(
                analytics_repository,
                creator_id=creator_b.id,
                channel_id=None,
                platform="youtube_longform",
                content_type=AnalyticsContentType.LONGFORM_VIDEO,
                title="Music theory follow-up",
                external_publication_id="b_long_2",
                published_at="2026-06-07T12:00:00",
                duration_seconds=620,
                source_fingerprint="seed-b-long-2",
                metrics=[
                    ("views", 4300, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 2900, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("returning_viewers", 1100, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 3200, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 700, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 3600, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("average_view_duration_seconds", 240, "seconds", AnalyticsQualityStatus.ACCEPTED),
                    ("average_percentage_viewed", 0.7, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.68, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 210, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 18, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 90, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "search", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "music theory", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "longform_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )
            music_outlier = seed_publication(
                analytics_repository,
                creator_id=creator_b.id,
                channel_id=None,
                platform="youtube_longform",
                content_type=AnalyticsContentType.LONGFORM_VIDEO,
                title="Outlier lecture",
                external_publication_id="b_long_3",
                published_at="2026-06-30T12:00:00",
                duration_seconds=620,
                source_fingerprint="seed-b-long-3",
                metrics=[
                    ("views", 12000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("unique_viewers", 6000, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("returning_viewers", 900, "viewers", AnalyticsQualityStatus.ACCEPTED),
                    ("search_views", 1000, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("suggested_views", 1500, "views", AnalyticsQualityStatus.ACCEPTED),
                    ("watch_time_minutes", 1800, "minutes", AnalyticsQualityStatus.ACCEPTED),
                    ("average_view_duration_seconds", 85, "seconds", AnalyticsQualityStatus.ACCEPTED),
                    ("average_percentage_viewed", 0.17, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("completion_rate", 0.12, "ratio", AnalyticsQualityStatus.ACCEPTED),
                    ("likes", 1500, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("comments", 5, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("subscribers_gained", 2, "count", AnalyticsQualityStatus.ACCEPTED),
                    ("traffic_source", "suggested", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("topic", "music theory", "text", AnalyticsQualityStatus.ACCEPTED),
                    ("format", "longform_video", "text", AnalyticsQualityStatus.ACCEPTED),
                ],
            )

            result_a = audience_service.build_profile(creator_a.id)
            result_a_cached = audience_service.build_profile(creator_a.id)
            result_b = audience_service.build_profile(creator_b.id)

            self.assertEqual(result_a.run.id, result_a_cached.run.id)
            self.assertIn("shorts_feed_discovery", {segment.name for segment in result_a.segments})
            self.assertIn("longform_loyalty_candidate", {segment.name for segment in result_a.segments})
            self.assertIn("topic_affinity:entertainment", {segment.name for segment in result_a.segments})
            self.assertIn("platform_not_supported", {signal.quality_status for signal in result_a.signals})
            self.assertIn("metric_not_available", {signal.quality_status for signal in result_b.signals})
            self.assertIn("youtube_short", result_a.platform_roles)
            self.assertEqual(result_a.platform_roles["youtube_short"]["role"], "discovery")
            self.assertIn("youtube_longform", result_a.platform_roles)
            self.assertIn(result_b.profile.status.value, {"active", "draft"})
            self.assertIn("music theory", {signal.text_value for signal in result_b.signals if signal.signal_key == "topic"})
            self.assertTrue(any(payload["role"] == "authority" for payload in result_b.content_roles.values()))
            self.assertTrue(any(payload["discovery"] > 0 for payload in result_b.platform_roles.values()))
            self.assertNotEqual(
                {signal.creator_id for signal in result_a.signals},
                {signal.creator_id for signal in result_b.signals},
            )
            self.assertTrue(result_a.journeys)
            self.assertTrue(any("aggregated_only" in journey.evidence_json for journey in result_a.journeys))
            self.assertTrue(result_a.questions)

            summary = audience_service.compare_profiles(creator_a.id, result_a.profile.profile_version, result_a.profile.profile_version)
            self.assertIn("summary_delta", summary)

            exported_csv = audience_service.export(creator_a.id, "csv")
            exported_text = Path(exported_csv).read_text(encoding="utf-8")
            self.assertIn("'=DANGEROUS", exported_text)

            segment = audience_service.create_segment(
                creator_id=creator_a.id,
                name="manual_segment",
                segment_type="creator_defined",
                scope="creator",
                description="Manual review segment.",
            )
            review = audience_service.review_segment(segment.id, AudienceReviewDecision.CONFIRM.value, "Looks correct")
            self.assertEqual(review.decision, AudienceReviewDecision.CONFIRM)
            self.assertEqual(audience_service.get_segment(segment.id).status.value, "reviewed")

    def test_cli_help_and_gui_smoke(self) -> None:
        parser = build_parser()
        self.assertIn("audience", parser.format_help())

        if QApplication is None:
            self.skipTest("PySide6 not available")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication([])
        workspace = SimpleNamespace(
            selected_creator_id="creator-test",
            get_audience_profile=lambda creator_id, profile_version=None: SimpleNamespace(profile_version=1, status=SimpleNamespace(value="active"), confidence_level=SimpleNamespace(value="high")),
            list_audience_signals=lambda creator_id, platform=None: [],
            list_audience_segments=lambda creator_id: [],
            list_audience_affinities=lambda creator_id: [],
            list_audience_journeys=lambda creator_id: [],
            list_audience_profile_history=lambda creator_id: [],
            list_audience_platform_roles=lambda creator_id: {},
            list_audience_content_roles=lambda creator_id: {},
            list_audience_journey_steps=lambda journey_id: [],
            list_analytics_publications=lambda creator_id: [],
            build_audience_model=lambda creator_id, force=False, configuration=None: SimpleNamespace(run=SimpleNamespace(status=SimpleNamespace(value="completed"))),
        )
        view = AudienceOverviewView(workspace)
        view.refresh()
        task_workspace = SimpleNamespace(
            background_tasks=lambda: [
                SimpleNamespace(
                    task_id="audience-task",
                    title="Modelo de audiencia",
                    status="running",
                    stage_name="building_profile",
                    video_title="creator-test",
                    action_id="build",
                    progress_percent=25.0,
                    message="Construyendo",
                    error=None,
                    cancellable=True,
                    updated_at="2026-07-27T00:00:00Z",
                    payload={"kind": "audience_model_build", "creator_id": "creator-test", "force": False, "configuration": {}},
                )
            ],
            export_youtube_sync_report=lambda task_id: None,
            interrupt_background_task=lambda *args, **kwargs: None,
            interrupt_youtube_sync_run=lambda *args, **kwargs: None,
            resume_youtube_sync_run=lambda *args, **kwargs: None,
            cancel_delivery=lambda *args, **kwargs: None,
            retry_delivery=lambda *args, **kwargs: None,
            cancel_analytics_import=lambda *args, **kwargs: None,
            retry_analytics_import=lambda *args, **kwargs: None,
            interrupt_operational_evaluation=lambda *args, **kwargs: None,
            retry_operational_evaluation=lambda *args, **kwargs: None,
            select_video=lambda *args, **kwargs: None,
            cancel_render=lambda *args, **kwargs: None,
            retry_render=lambda *args, **kwargs: None,
            selected_creator_id="creator-test",
            build_audience_model=lambda *args, **kwargs: SimpleNamespace(run=SimpleNamespace(status=SimpleNamespace(value="completed"))),
        )
        task_view = TaskCenterView(task_workspace)
        task_view.refresh()
        self.assertGreaterEqual(task_view.table.rowCount(), 1)
