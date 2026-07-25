"""Repositorio SQLite para la integracion YouTube de solo lectura."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from creator_intelligence_studio.domain.youtube_integration.connection_types import (
    YouTubeConnectionStatus,
    YouTubeLinkMethod,
    YouTubeRemoteContentType,
)
from creator_intelligence_studio.domain.youtube_integration.entities import (
    YouTubeChannel,
    YouTubeConnection,
    YouTubeContentLink,
    YouTubeMetricImport,
    YouTubeMetricValue,
    YouTubeQuotaUsage,
    YouTubeRemoteVideo,
    YouTubeSyncItem,
    YouTubeSyncReport,
    YouTubeSyncRun,
    YouTubeSyncSchedule,
    YouTubeVideoThumbnail,
)
from creator_intelligence_studio.domain.youtube_integration.metric_types import YouTubeMetricAvailability, YouTubeMetricScope
from creator_intelligence_studio.domain.youtube_integration.repositories import YouTubeIntegrationRepository
from creator_intelligence_studio.domain.youtube_integration.sync_types import YouTubeSyncStatus, YouTubeSyncType
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _row_to_connection(row: sqlite3.Row) -> YouTubeConnection:
    return YouTubeConnection(
        id=row["id"],
        creator_id=row["creator_id"],
        google_account_identifier=row["google_account_identifier"],
        status=YouTubeConnectionStatus(row["status"]),
        granted_scopes_json=row["granted_scopes_json"],
        credential_reference=row["credential_reference"],
        connected_at=from_iso_z(row["connected_at"]) or utc_now(),
        last_verified_at=from_iso_z(row["last_verified_at"]),
        disconnected_at=from_iso_z(row["disconnected_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_channel(row: sqlite3.Row) -> YouTubeChannel:
    return YouTubeChannel(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        youtube_channel_id=row["youtube_channel_id"],
        title=row["title"],
        description=row["description"],
        custom_url=row["custom_url"],
        country=row["country"],
        published_at=from_iso_z(row["published_at"]),
        thumbnail_url=row["thumbnail_url"],
        subscriber_count=row["subscriber_count"],
        video_count=row["video_count"],
        view_count=row["view_count"],
        hidden_subscriber_count=bool(row["hidden_subscriber_count"]),
        selected_for_sync=bool(row["selected_for_sync"]),
        last_synced_at=from_iso_z(row["last_synced_at"]),
        remote_fingerprint=row["remote_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_remote_video(row: sqlite3.Row) -> YouTubeRemoteVideo:
    return YouTubeRemoteVideo(
        id=row["id"],
        creator_id=row["creator_id"],
        channel_id=row["channel_id"],
        youtube_video_id=row["youtube_video_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        content_type=YouTubeRemoteContentType(row["content_type"]),
        title=row["title"],
        description=row["description"],
        published_at=from_iso_z(row["published_at"]) or utc_now(),
        duration_seconds=row["duration_seconds"],
        privacy_status=row["privacy_status"],
        live_broadcast_content=row["live_broadcast_content"],
        default_language=row["default_language"],
        default_audio_language=row["default_audio_language"],
        category_id=row["category_id"],
        tags_json=row["tags_json"],
        thumbnail_metadata_json=row["thumbnail_metadata_json"],
        remote_fingerprint=row["remote_fingerprint"],
        first_seen_at=from_iso_z(row["first_seen_at"]) or utc_now(),
        last_seen_at=from_iso_z(row["last_seen_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_thumbnail(row: sqlite3.Row) -> YouTubeVideoThumbnail:
    return YouTubeVideoThumbnail(
        id=row["id"],
        remote_video_id=row["remote_video_id"],
        thumbnail_type=row["thumbnail_type"],
        remote_url=row["remote_url"],
        width=row["width"],
        height=row["height"],
        local_cache_path=row["local_cache_path"],
        remote_fingerprint=row["remote_fingerprint"],
        imported_at=from_iso_z(row["imported_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_sync_run(row: sqlite3.Row) -> YouTubeSyncRun:
    return YouTubeSyncRun(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        channel_id=row["channel_id"],
        sync_type=YouTubeSyncType(row["sync_type"]),
        status=YouTubeSyncStatus(row["status"]),
        configuration_json=row["configuration_json"],
        cursor_json=row["cursor_json"],
        discovered_count=row["discovered_count"],
        imported_count=row["imported_count"],
        updated_count=row["updated_count"],
        skipped_count=row["skipped_count"],
        warning_count=row["warning_count"],
        error_count=row["error_count"],
        quota_cost_estimate=row["quota_cost_estimate"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_sync_item(row: sqlite3.Row) -> YouTubeSyncItem:
    return YouTubeSyncItem(
        id=row["id"],
        sync_run_id=row["sync_run_id"],
        remote_type=row["remote_type"],
        remote_id=row["remote_id"],
        local_type=row["local_type"],
        local_id=row["local_id"],
        action=row["action"],
        status=row["status"],
        warnings_json=row["warnings_json"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric_import(row: sqlite3.Row) -> YouTubeMetricImport:
    return YouTubeMetricImport(
        id=row["id"],
        creator_id=row["creator_id"],
        channel_id=row["channel_id"],
        remote_video_id=row["remote_video_id"],
        sync_run_id=row["sync_run_id"],
        metric_scope=row["metric_scope"],
        date_start=row["date_start"],
        date_end=row["date_end"],
        comparable_window=row["comparable_window"],
        source_fingerprint=row["source_fingerprint"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric_value(row: sqlite3.Row) -> YouTubeMetricValue:
    return YouTubeMetricValue(
        id=row["id"],
        metric_import_id=row["metric_import_id"],
        metric_key=row["metric_key"],
        raw_metric_name=row["raw_metric_name"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        dimensions_json=row["dimensions_json"],
        quality_status=row["quality_status"],
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_link(row: sqlite3.Row) -> YouTubeContentLink:
    return YouTubeContentLink(
        id=row["id"],
        creator_id=row["creator_id"],
        remote_video_id=row["remote_video_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        link_method=YouTubeLinkMethod(row["link_method"]),
        confidence_level=row["confidence_level"],
        status=row["status"],
        reviewed_at=from_iso_z(row["reviewed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_quota(row: sqlite3.Row) -> YouTubeQuotaUsage:
    return YouTubeQuotaUsage(
        id=row["id"],
        connection_id=row["connection_id"],
        operation_key=row["operation_key"],
        estimated_cost=row["estimated_cost"],
        request_count=row["request_count"],
        usage_date=row["usage_date"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_schedule(row: sqlite3.Row) -> YouTubeSyncSchedule:
    return YouTubeSyncSchedule(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        channel_id=row["channel_id"],
        schedule_type=row["schedule_type"],
        enabled=bool(row["enabled"]),
        interval_hours=row["interval_hours"],
        last_run_at=from_iso_z(row["last_run_at"]),
        next_run_at=from_iso_z(row["next_run_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLiteYouTubeRepository(YouTubeIntegrationRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchall()

    def upsert_connection(self, connection_obj: YouTubeConnection) -> YouTubeConnection:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_connections (
                    id, creator_id, google_account_identifier, status, granted_scopes_json,
                    credential_reference, connected_at, last_verified_at, disconnected_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :google_account_identifier, :status, :granted_scopes_json,
                    :credential_reference, :connected_at, :last_verified_at, :disconnected_at,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    google_account_identifier = excluded.google_account_identifier,
                    status = excluded.status,
                    granted_scopes_json = excluded.granted_scopes_json,
                    credential_reference = excluded.credential_reference,
                    connected_at = excluded.connected_at,
                    last_verified_at = excluded.last_verified_at,
                    disconnected_at = excluded.disconnected_at,
                    updated_at = excluded.updated_at
                """,
                connection_obj.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM youtube_connections WHERE id = ?", (connection_obj.id,))
        return _row_to_connection(row)

    def get_connection(self, connection_id: str) -> YouTubeConnection | None:
        row = self._fetch_one("SELECT * FROM youtube_connections WHERE id = ?", (connection_id,))
        return _row_to_connection(row) if row else None

    def list_connections(self, creator_id: str) -> list[YouTubeConnection]:
        rows = self._fetch_all("SELECT * FROM youtube_connections WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_connection(row) for row in rows]

    def upsert_channel(self, channel: YouTubeChannel) -> YouTubeChannel:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_channels (
                    id, creator_id, connection_id, youtube_channel_id, title, description,
                    custom_url, country, published_at, thumbnail_url, subscriber_count,
                    video_count, view_count, hidden_subscriber_count, selected_for_sync,
                    last_synced_at, remote_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :youtube_channel_id, :title, :description,
                    :custom_url, :country, :published_at, :thumbnail_url, :subscriber_count,
                    :video_count, :view_count, :hidden_subscriber_count, :selected_for_sync,
                    :last_synced_at, :remote_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, youtube_channel_id) DO UPDATE SET
                    connection_id = excluded.connection_id,
                    title = excluded.title,
                    description = excluded.description,
                    custom_url = excluded.custom_url,
                    country = excluded.country,
                    published_at = excluded.published_at,
                    thumbnail_url = excluded.thumbnail_url,
                    subscriber_count = excluded.subscriber_count,
                    video_count = excluded.video_count,
                    view_count = excluded.view_count,
                    hidden_subscriber_count = excluded.hidden_subscriber_count,
                    selected_for_sync = excluded.selected_for_sync,
                    last_synced_at = excluded.last_synced_at,
                    remote_fingerprint = excluded.remote_fingerprint,
                    updated_at = excluded.updated_at
                """,
                channel.to_dict() | {"hidden_subscriber_count": 1 if channel.hidden_subscriber_count else 0, "selected_for_sync": 1 if channel.selected_for_sync else 0},
            )
        row = self._fetch_one("SELECT * FROM youtube_channels WHERE creator_id = ? AND youtube_channel_id = ?", (channel.creator_id, channel.youtube_channel_id))
        return _row_to_channel(row)

    def get_channel(self, channel_id: str) -> YouTubeChannel | None:
        row = self._fetch_one("SELECT * FROM youtube_channels WHERE id = ?", (channel_id,))
        return _row_to_channel(row) if row else None

    def get_channel_by_youtube_id(self, creator_id: str, youtube_channel_id: str) -> YouTubeChannel | None:
        row = self._fetch_one("SELECT * FROM youtube_channels WHERE creator_id = ? AND youtube_channel_id = ?", (creator_id, youtube_channel_id))
        return _row_to_channel(row) if row else None

    def list_channels(self, creator_id: str) -> list[YouTubeChannel]:
        rows = self._fetch_all("SELECT * FROM youtube_channels WHERE creator_id = ? ORDER BY selected_for_sync DESC, updated_at DESC", (creator_id,))
        return [_row_to_channel(row) for row in rows]

    def upsert_remote_video(self, video: YouTubeRemoteVideo) -> YouTubeRemoteVideo:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_remote_videos (
                    id, creator_id, channel_id, youtube_video_id, publication_id, video_asset_id,
                    content_type, title, description, published_at, duration_seconds, privacy_status,
                    live_broadcast_content, default_language, default_audio_language, category_id,
                    tags_json, thumbnail_metadata_json, remote_fingerprint, first_seen_at, last_seen_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :channel_id, :youtube_video_id, :publication_id, :video_asset_id,
                    :content_type, :title, :description, :published_at, :duration_seconds, :privacy_status,
                    :live_broadcast_content, :default_language, :default_audio_language, :category_id,
                    :tags_json, :thumbnail_metadata_json, :remote_fingerprint, :first_seen_at, :last_seen_at,
                    :created_at, :updated_at
                )
                ON CONFLICT(creator_id, youtube_video_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    publication_id = excluded.publication_id,
                    video_asset_id = excluded.video_asset_id,
                    content_type = excluded.content_type,
                    title = excluded.title,
                    description = excluded.description,
                    published_at = excluded.published_at,
                    duration_seconds = excluded.duration_seconds,
                    privacy_status = excluded.privacy_status,
                    live_broadcast_content = excluded.live_broadcast_content,
                    default_language = excluded.default_language,
                    default_audio_language = excluded.default_audio_language,
                    category_id = excluded.category_id,
                    tags_json = excluded.tags_json,
                    thumbnail_metadata_json = excluded.thumbnail_metadata_json,
                    remote_fingerprint = excluded.remote_fingerprint,
                    last_seen_at = excluded.last_seen_at,
                    updated_at = excluded.updated_at
                """,
                video.to_dict() | {"content_type": video.content_type.value},
            )
        row = self._fetch_one("SELECT * FROM youtube_remote_videos WHERE creator_id = ? AND youtube_video_id = ?", (video.creator_id, video.youtube_video_id))
        return _row_to_remote_video(row)

    def get_remote_video(self, remote_video_id: str) -> YouTubeRemoteVideo | None:
        row = self._fetch_one("SELECT * FROM youtube_remote_videos WHERE id = ?", (remote_video_id,))
        return _row_to_remote_video(row) if row else None

    def get_remote_video_by_youtube_id(self, creator_id: str, youtube_video_id: str) -> YouTubeRemoteVideo | None:
        row = self._fetch_one("SELECT * FROM youtube_remote_videos WHERE creator_id = ? AND youtube_video_id = ?", (creator_id, youtube_video_id))
        return _row_to_remote_video(row) if row else None

    def list_remote_videos(self, channel_id: str) -> list[YouTubeRemoteVideo]:
        rows = self._fetch_all("SELECT * FROM youtube_remote_videos WHERE channel_id = ? ORDER BY published_at DESC, last_seen_at DESC", (channel_id,))
        return [_row_to_remote_video(row) for row in rows]

    def upsert_video_thumbnail(self, thumbnail: YouTubeVideoThumbnail) -> YouTubeVideoThumbnail:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_video_thumbnails (
                    id, remote_video_id, thumbnail_type, remote_url, width, height,
                    local_cache_path, remote_fingerprint, imported_at, created_at
                ) VALUES (
                    :id, :remote_video_id, :thumbnail_type, :remote_url, :width, :height,
                    :local_cache_path, :remote_fingerprint, :imported_at, :created_at
                )
                ON CONFLICT(remote_video_id, thumbnail_type, remote_fingerprint) DO UPDATE SET
                    remote_url = excluded.remote_url,
                    width = excluded.width,
                    height = excluded.height,
                    local_cache_path = excluded.local_cache_path,
                    imported_at = excluded.imported_at
                """,
                thumbnail.to_dict(),
            )
        row = self._fetch_one(
            "SELECT * FROM youtube_video_thumbnails WHERE remote_video_id = ? AND thumbnail_type = ? AND remote_fingerprint = ?",
            (thumbnail.remote_video_id, thumbnail.thumbnail_type, thumbnail.remote_fingerprint),
        )
        return _row_to_thumbnail(row)

    def list_video_thumbnails(self, remote_video_id: str) -> list[YouTubeVideoThumbnail]:
        rows = self._fetch_all("SELECT * FROM youtube_video_thumbnails WHERE remote_video_id = ? ORDER BY created_at ASC", (remote_video_id,))
        return [_row_to_thumbnail(row) for row in rows]

    def upsert_sync_run(self, run: YouTubeSyncRun) -> YouTubeSyncRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_sync_runs (
                    id, creator_id, connection_id, channel_id, sync_type, status,
                    configuration_json, cursor_json, discovered_count, imported_count,
                    updated_count, skipped_count, warning_count, error_count,
                    quota_cost_estimate, started_at, completed_at, error_code, error_message, created_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :channel_id, :sync_type, :status,
                    :configuration_json, :cursor_json, :discovered_count, :imported_count,
                    :updated_count, :skipped_count, :warning_count, :error_count,
                    :quota_cost_estimate, :started_at, :completed_at, :error_code, :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    sync_type = excluded.sync_type,
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    cursor_json = excluded.cursor_json,
                    discovered_count = excluded.discovered_count,
                    imported_count = excluded.imported_count,
                    updated_count = excluded.updated_count,
                    skipped_count = excluded.skipped_count,
                    warning_count = excluded.warning_count,
                    error_count = excluded.error_count,
                    quota_cost_estimate = excluded.quota_cost_estimate,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                run.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM youtube_sync_runs WHERE id = ?", (run.id,))
        return _row_to_sync_run(row)

    def get_sync_run(self, run_id: str) -> YouTubeSyncRun | None:
        row = self._fetch_one("SELECT * FROM youtube_sync_runs WHERE id = ?", (run_id,))
        return _row_to_sync_run(row) if row else None

    def list_sync_runs(self, creator_id: str, *, channel_id: str | None = None) -> list[YouTubeSyncRun]:
        query = "SELECT * FROM youtube_sync_runs WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if channel_id is not None:
            query += " AND channel_id = ?"
            params.append(channel_id)
        query += " ORDER BY created_at DESC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_sync_run(row) for row in rows]

    def upsert_sync_item(self, item: YouTubeSyncItem) -> YouTubeSyncItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_sync_items (
                    id, sync_run_id, remote_type, remote_id, local_type, local_id, action,
                    status, warnings_json, error_code, error_message, created_at
                ) VALUES (
                    :id, :sync_run_id, :remote_type, :remote_id, :local_type, :local_id, :action,
                    :status, :warnings_json, :error_code, :error_message, :created_at
                )
                ON CONFLICT(sync_run_id, remote_type, remote_id, action) DO UPDATE SET
                    local_type = excluded.local_type,
                    local_id = excluded.local_id,
                    status = excluded.status,
                    warnings_json = excluded.warnings_json,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                item.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM youtube_sync_items WHERE sync_run_id = ? AND remote_type = ? AND remote_id = ? AND action = ?", (item.sync_run_id, item.remote_type, item.remote_id, item.action))
        return _row_to_sync_item(row)

    def list_sync_items(self, sync_run_id: str) -> list[YouTubeSyncItem]:
        rows = self._fetch_all("SELECT * FROM youtube_sync_items WHERE sync_run_id = ? ORDER BY created_at ASC", (sync_run_id,))
        return [_row_to_sync_item(row) for row in rows]

    def upsert_metric_import(self, metric_import: YouTubeMetricImport) -> YouTubeMetricImport:
        with self._database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM youtube_metric_imports
                WHERE source_fingerprint = ?
                  AND metric_scope = ?
                  AND date_start = ?
                  AND date_end = ?
                  AND IFNULL(channel_id, '') = IFNULL(?, '')
                  AND IFNULL(remote_video_id, '') = IFNULL(?, '')
                """,
                (
                    metric_import.source_fingerprint,
                    metric_import.metric_scope,
                    metric_import.date_start,
                    metric_import.date_end,
                    metric_import.channel_id,
                    metric_import.remote_video_id,
                ),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO youtube_metric_imports (
                        id, creator_id, channel_id, remote_video_id, sync_run_id, metric_scope,
                        date_start, date_end, comparable_window, source_fingerprint, status, created_at
                    ) VALUES (
                        :id, :creator_id, :channel_id, :remote_video_id, :sync_run_id, :metric_scope,
                        :date_start, :date_end, :comparable_window, :source_fingerprint, :status, :created_at
                    )
                    """,
                    metric_import.to_dict(),
                )
            else:
                connection.execute(
                    """
                    UPDATE youtube_metric_imports
                    SET creator_id = :creator_id,
                        channel_id = :channel_id,
                        remote_video_id = :remote_video_id,
                        sync_run_id = :sync_run_id,
                        metric_scope = :metric_scope,
                        date_start = :date_start,
                        date_end = :date_end,
                        comparable_window = :comparable_window,
                        status = :status
                    WHERE id = :id
                    """,
                    metric_import.to_dict(),
                )
        row = self._fetch_one(
            "SELECT * FROM youtube_metric_imports WHERE source_fingerprint = ? AND metric_scope = ? AND date_start = ? AND date_end = ? AND IFNULL(channel_id, '') = IFNULL(?, '') AND IFNULL(remote_video_id, '') = IFNULL(?, '')",
            (metric_import.source_fingerprint, metric_import.metric_scope, metric_import.date_start, metric_import.date_end, metric_import.channel_id, metric_import.remote_video_id),
        )
        return _row_to_metric_import(row)

    def get_metric_import(self, metric_import_id: str) -> YouTubeMetricImport | None:
        row = self._fetch_one("SELECT * FROM youtube_metric_imports WHERE id = ?", (metric_import_id,))
        return _row_to_metric_import(row) if row else None

    def list_metric_imports(self, creator_id: str, *, channel_id: str | None = None) -> list[YouTubeMetricImport]:
        query = "SELECT * FROM youtube_metric_imports WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if channel_id is not None:
            query += " AND channel_id = ?"
            params.append(channel_id)
        query += " ORDER BY created_at DESC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_metric_import(row) for row in rows]

    def upsert_metric_value(self, metric_value: YouTubeMetricValue) -> YouTubeMetricValue:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_metric_values (
                    id, metric_import_id, metric_key, raw_metric_name, numeric_value, text_value,
                    unit, dimensions_json, quality_status, warning_codes_json, created_at
                ) VALUES (
                    :id, :metric_import_id, :metric_key, :raw_metric_name, :numeric_value, :text_value,
                    :unit, :dimensions_json, :quality_status, :warning_codes_json, :created_at
                )
                ON CONFLICT(metric_import_id, metric_key, dimensions_json, raw_metric_name) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    quality_status = excluded.quality_status,
                    warning_codes_json = excluded.warning_codes_json
                """,
                metric_value.to_dict(),
            )
        row = self._fetch_one(
            "SELECT * FROM youtube_metric_values WHERE metric_import_id = ? AND metric_key = ? AND dimensions_json = ? AND raw_metric_name = ?",
            (metric_value.metric_import_id, metric_value.metric_key, metric_value.dimensions_json, metric_value.raw_metric_name),
        )
        return _row_to_metric_value(row)

    def list_metric_values(self, metric_import_id: str) -> list[YouTubeMetricValue]:
        rows = self._fetch_all("SELECT * FROM youtube_metric_values WHERE metric_import_id = ? ORDER BY created_at ASC", (metric_import_id,))
        return [_row_to_metric_value(row) for row in rows]

    def upsert_content_link(self, link: YouTubeContentLink) -> YouTubeContentLink:
        payload = link.to_dict() | {"link_method": link.link_method.value}
        with self._database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM youtube_content_links
                WHERE creator_id = ?
                  AND remote_video_id = ?
                  AND IFNULL(publication_id, '') = IFNULL(?, '')
                  AND IFNULL(video_asset_id, '') = IFNULL(?, '')
                """,
                (link.creator_id, link.remote_video_id, link.publication_id, link.video_asset_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO youtube_content_links (
                        id, creator_id, remote_video_id, publication_id, video_asset_id,
                        link_method, confidence_level, status, reviewed_at, created_at, updated_at
                    ) VALUES (
                        :id, :creator_id, :remote_video_id, :publication_id, :video_asset_id,
                        :link_method, :confidence_level, :status, :reviewed_at, :created_at, :updated_at
                    )
                    """,
                    payload,
                )
            else:
                connection.execute(
                    """
                    UPDATE youtube_content_links
                    SET link_method = :link_method,
                        confidence_level = :confidence_level,
                        status = :status,
                        reviewed_at = :reviewed_at,
                        updated_at = :updated_at
                    WHERE id = :id
                    """,
                    payload,
                )
        row = self._fetch_one(
            "SELECT * FROM youtube_content_links WHERE creator_id = ? AND remote_video_id = ? AND IFNULL(publication_id, '') = IFNULL(?, '') AND IFNULL(video_asset_id, '') = IFNULL(?, '')",
            (link.creator_id, link.remote_video_id, link.publication_id, link.video_asset_id),
        )
        return _row_to_link(row)

    def get_content_link(self, link_id: str) -> YouTubeContentLink | None:
        row = self._fetch_one("SELECT * FROM youtube_content_links WHERE id = ?", (link_id,))
        return _row_to_link(row) if row else None

    def list_content_links(self, creator_id: str) -> list[YouTubeContentLink]:
        rows = self._fetch_all("SELECT * FROM youtube_content_links WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_link(row) for row in rows]

    def upsert_quota_usage(self, quota: YouTubeQuotaUsage) -> YouTubeQuotaUsage:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_quota_usage (
                    id, connection_id, operation_key, estimated_cost, request_count, usage_date, created_at
                ) VALUES (
                    :id, :connection_id, :operation_key, :estimated_cost, :request_count, :usage_date, :created_at
                )
                ON CONFLICT(connection_id, operation_key, usage_date) DO UPDATE SET
                    estimated_cost = estimated_cost + excluded.estimated_cost,
                    request_count = request_count + excluded.request_count
                """,
                quota.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM youtube_quota_usage WHERE connection_id = ? AND operation_key = ? AND usage_date = ?", (quota.connection_id, quota.operation_key, quota.usage_date))
        return _row_to_quota(row)

    def list_quota_usage(self, connection_id: str) -> list[YouTubeQuotaUsage]:
        rows = self._fetch_all("SELECT * FROM youtube_quota_usage WHERE connection_id = ? ORDER BY usage_date DESC, created_at DESC", (connection_id,))
        return [_row_to_quota(row) for row in rows]

    def upsert_sync_schedule(self, schedule: YouTubeSyncSchedule) -> YouTubeSyncSchedule:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_sync_schedules (
                    id, creator_id, connection_id, channel_id, schedule_type, enabled,
                    interval_hours, last_run_at, next_run_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :channel_id, :schedule_type, :enabled,
                    :interval_hours, :last_run_at, :next_run_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    enabled = excluded.enabled,
                    interval_hours = excluded.interval_hours,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    updated_at = excluded.updated_at
                """,
                schedule.to_dict() | {"enabled": 1 if schedule.enabled else 0},
            )
        row = self._fetch_one("SELECT * FROM youtube_sync_schedules WHERE id = ?", (schedule.id,))
        return _row_to_schedule(row)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[YouTubeSyncSchedule]:
        query = "SELECT * FROM youtube_sync_schedules WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY created_at DESC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_schedule(row) for row in rows]
