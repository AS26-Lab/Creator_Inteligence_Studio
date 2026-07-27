"""Repositorio SQLite para la integracion de solo lectura con TikTok."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.tiktok_integration.connection_types import TikTokAccessLevel, TikTokConnectionStatus, TikTokLinkMethod, TikTokRemoteStatus
from creator_intelligence_studio.domain.tiktok_integration.entities import (
    TikTokConnection,
    TikTokContentLink,
    TikTokCoverVersion,
    TikTokMetricImport,
    TikTokMetricValue,
    TikTokProfile,
    TikTokRateLimitUsage,
    TikTokRemoteVideo,
    TikTokSyncItem,
    TikTokSyncReport,
    TikTokSyncRun,
    TikTokSyncSchedule,
    TikTokVideoTextVersion,
)
from creator_intelligence_studio.domain.tiktok_integration.metric_types import TikTokMetricScope, TikTokMetricSourceType, TikTokMetricStatus
from creator_intelligence_studio.domain.tiktok_integration.repositories import TikTokIntegrationRepository
from creator_intelligence_studio.domain.tiktok_integration.sync_types import TikTokSyncStatus, TikTokSyncType
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


def _row_to_connection(row: sqlite3.Row) -> TikTokConnection:
    return TikTokConnection(
        id=row["id"],
        creator_id=row["creator_id"],
        status=TikTokConnectionStatus(row["status"]),
        open_id=row["open_id"],
        union_id=row["union_id"],
        account_identifier=row["account_identifier"],
        granted_scopes_json=row["granted_scopes_json"],
        credential_reference=row["credential_reference"],
        api_version=row["api_version"],
        access_level=TikTokAccessLevel(row["access_level"]) if row["access_level"] else None,
        connected_at=from_iso_z(row["connected_at"]) or utc_now(),
        last_verified_at=from_iso_z(row["last_verified_at"]),
        disconnected_at=from_iso_z(row["disconnected_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_profile(row: sqlite3.Row) -> TikTokProfile:
    return TikTokProfile(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        open_id=row["open_id"],
        union_id=row["union_id"],
        display_name=row["display_name"],
        username=row["username"],
        avatar_url=row["avatar_url"],
        bio_description=row["bio_description"],
        profile_deep_link=row["profile_deep_link"],
        profile_web_link=row["profile_web_link"],
        is_verified=None if row["is_verified"] is None else bool(row["is_verified"]),
        follower_count=row["follower_count"],
        following_count=row["following_count"],
        likes_count=row["likes_count"],
        video_count=row["video_count"],
        selected_for_sync=bool(row["selected_for_sync"]),
        last_synced_at=from_iso_z(row["last_synced_at"]),
        remote_fingerprint=row["remote_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_remote_video(row: sqlite3.Row) -> TikTokRemoteVideo:
    return TikTokRemoteVideo(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_id=row["profile_id"],
        tiktok_video_id=row["tiktok_video_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        packaging_asset_id=row["packaging_asset_id"],
        title=row["title"],
        video_description=row["video_description"],
        create_time=from_iso_z(row["create_time"]) or utc_now(),
        duration_seconds=row["duration_seconds"],
        width=row["width"],
        height=row["height"],
        share_url=row["share_url"],
        embed_link=row["embed_link"],
        cover_image_url=row["cover_image_url"],
        like_count=row["like_count"],
        comment_count=row["comment_count"],
        share_count=row["share_count"],
        view_count=row["view_count"],
        remote_fingerprint=row["remote_fingerprint"],
        first_seen_at=from_iso_z(row["first_seen_at"]) or utc_now(),
        last_seen_at=from_iso_z(row["last_seen_at"]) or utc_now(),
        remote_status=TikTokRemoteStatus(row["remote_status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_text_version(row: sqlite3.Row) -> TikTokVideoTextVersion:
    return TikTokVideoTextVersion(
        id=row["id"],
        remote_video_id=row["remote_video_id"],
        version_number=row["version_number"],
        title_text=row["title_text"],
        description_text=row["description_text"],
        source_fingerprint=row["source_fingerprint"],
        is_current=bool(row["is_current"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_cover_version(row: sqlite3.Row) -> TikTokCoverVersion:
    return TikTokCoverVersion(
        id=row["id"],
        remote_video_id=row["remote_video_id"],
        version_number=row["version_number"],
        cover_image_url=row["cover_image_url"],
        remote_fingerprint=row["remote_fingerprint"],
        packaging_asset_id=row["packaging_asset_id"],
        is_current=bool(row["is_current"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_sync_run(row: sqlite3.Row) -> TikTokSyncRun:
    return TikTokSyncRun(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        profile_id=row["profile_id"],
        sync_type=TikTokSyncType(row["sync_type"]),
        status=TikTokSyncStatus(row["status"]),
        configuration_json=row["configuration_json"],
        cursor_json=row["cursor_json"],
        discovered_count=row["discovered_count"],
        imported_count=row["imported_count"],
        updated_count=row["updated_count"],
        unchanged_count=row["unchanged_count"],
        skipped_count=row["skipped_count"],
        warning_count=row["warning_count"],
        error_count=row["error_count"],
        estimated_usage=row["estimated_usage"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_sync_item(row: sqlite3.Row) -> TikTokSyncItem:
    return TikTokSyncItem(
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


def _row_to_metric_import(row: sqlite3.Row) -> TikTokMetricImport:
    return TikTokMetricImport(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_id=row["profile_id"],
        remote_video_id=row["remote_video_id"],
        sync_run_id=row["sync_run_id"],
        metric_scope=TikTokMetricScope(row["metric_scope"]),
        source_type=TikTokMetricSourceType(row["source_type"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        period_start=row["period_start"],
        period_end=row["period_end"],
        comparable_window=row["comparable_window"],
        source_fingerprint=row["source_fingerprint"],
        status=TikTokMetricStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric_value(row: sqlite3.Row) -> TikTokMetricValue:
    return TikTokMetricValue(
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


def _row_to_link(row: sqlite3.Row) -> TikTokContentLink:
    return TikTokContentLink(
        id=row["id"],
        creator_id=row["creator_id"],
        remote_video_id=row["remote_video_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        packaging_asset_id=row["packaging_asset_id"],
        link_method=TikTokLinkMethod(row["link_method"]),
        confidence_level=row["confidence_level"],
        status=row["status"],
        reviewed_at=from_iso_z(row["reviewed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_rate_limit(row: sqlite3.Row) -> TikTokRateLimitUsage:
    return TikTokRateLimitUsage(
        id=row["id"],
        connection_id=row["connection_id"],
        operation_key=row["operation_key"],
        endpoint=row["endpoint"],
        request_count=row["request_count"],
        estimated_usage=row["estimated_usage"],
        window_started_at=from_iso_z(row["window_started_at"]),
        response_headers_json=row["response_headers_json"],
        usage_date=row["usage_date"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_schedule(row: sqlite3.Row) -> TikTokSyncSchedule:
    return TikTokSyncSchedule(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        profile_id=row["profile_id"],
        schedule_type=row["schedule_type"],
        enabled=bool(row["enabled"]),
        interval_hours=row["interval_hours"],
        last_run_at=from_iso_z(row["last_run_at"]),
        next_run_at=from_iso_z(row["next_run_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLiteTikTokRepository(TikTokIntegrationRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchall()

    def upsert_connection(self, connection_obj: TikTokConnection) -> TikTokConnection:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_connections (
                    id, creator_id, status, open_id, union_id, account_identifier,
                    granted_scopes_json, credential_reference, api_version, access_level,
                    connected_at, last_verified_at, disconnected_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :status, :open_id, :union_id, :account_identifier,
                    :granted_scopes_json, :credential_reference, :api_version, :access_level,
                    :connected_at, :last_verified_at, :disconnected_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    open_id = excluded.open_id,
                    union_id = excluded.union_id,
                    account_identifier = excluded.account_identifier,
                    granted_scopes_json = excluded.granted_scopes_json,
                    credential_reference = excluded.credential_reference,
                    api_version = excluded.api_version,
                    access_level = excluded.access_level,
                    connected_at = excluded.connected_at,
                    last_verified_at = excluded.last_verified_at,
                    disconnected_at = excluded.disconnected_at,
                    updated_at = excluded.updated_at
                """,
                connection_obj.to_dict() | {"status": connection_obj.status.value, "access_level": None if connection_obj.access_level is None else connection_obj.access_level.value},
            )
        row = self._fetch_one("SELECT * FROM tiktok_connections WHERE id = ?", (connection_obj.id,))
        return _row_to_connection(row)

    def get_connection(self, connection_id: str) -> TikTokConnection | None:
        row = self._fetch_one("SELECT * FROM tiktok_connections WHERE id = ?", (connection_id,))
        return _row_to_connection(row) if row else None

    def list_connections(self, creator_id: str) -> list[TikTokConnection]:
        rows = self._fetch_all("SELECT * FROM tiktok_connections WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_connection(row) for row in rows]

    def upsert_profile(self, profile: TikTokProfile) -> TikTokProfile:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_profiles (
                    id, creator_id, connection_id, open_id, union_id, display_name, username,
                    avatar_url, bio_description, profile_deep_link, profile_web_link, is_verified,
                    follower_count, following_count, likes_count, video_count, selected_for_sync,
                    last_synced_at, remote_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :open_id, :union_id, :display_name, :username,
                    :avatar_url, :bio_description, :profile_deep_link, :profile_web_link, :is_verified,
                    :follower_count, :following_count, :likes_count, :video_count, :selected_for_sync,
                    :last_synced_at, :remote_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, open_id) DO UPDATE SET
                    connection_id = excluded.connection_id,
                    union_id = excluded.union_id,
                    display_name = excluded.display_name,
                    username = excluded.username,
                    avatar_url = excluded.avatar_url,
                    bio_description = excluded.bio_description,
                    profile_deep_link = excluded.profile_deep_link,
                    profile_web_link = excluded.profile_web_link,
                    is_verified = excluded.is_verified,
                    follower_count = excluded.follower_count,
                    following_count = excluded.following_count,
                    likes_count = excluded.likes_count,
                    video_count = excluded.video_count,
                    selected_for_sync = excluded.selected_for_sync,
                    last_synced_at = excluded.last_synced_at,
                    remote_fingerprint = excluded.remote_fingerprint,
                    updated_at = excluded.updated_at
                """,
                profile.to_dict() | {"is_verified": None if profile.is_verified is None else (1 if profile.is_verified else 0), "selected_for_sync": 1 if profile.selected_for_sync else 0},
            )
        row = self._fetch_one("SELECT * FROM tiktok_profiles WHERE creator_id = ? AND open_id = ?", (profile.creator_id, profile.open_id))
        return _row_to_profile(row)

    def get_profile(self, profile_id: str) -> TikTokProfile | None:
        row = self._fetch_one("SELECT * FROM tiktok_profiles WHERE id = ?", (profile_id,))
        return _row_to_profile(row) if row else None

    def get_profile_by_open_id(self, creator_id: str, open_id: str) -> TikTokProfile | None:
        row = self._fetch_one("SELECT * FROM tiktok_profiles WHERE creator_id = ? AND open_id = ?", (creator_id, open_id))
        return _row_to_profile(row) if row else None

    def list_profiles(self, creator_id: str, *, connection_id: str | None = None) -> list[TikTokProfile]:
        query = "SELECT * FROM tiktok_profiles WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY selected_for_sync DESC, updated_at DESC"
        return [_row_to_profile(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_remote_video(self, video: TikTokRemoteVideo) -> TikTokRemoteVideo:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_remote_videos (
                    id, creator_id, profile_id, tiktok_video_id, publication_id, video_asset_id,
                    packaging_asset_id, title, video_description, create_time, duration_seconds,
                    width, height, share_url, embed_link, cover_image_url, like_count,
                    comment_count, share_count, view_count, remote_fingerprint, first_seen_at,
                    last_seen_at, remote_status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :profile_id, :tiktok_video_id, :publication_id, :video_asset_id,
                    :packaging_asset_id, :title, :video_description, :create_time, :duration_seconds,
                    :width, :height, :share_url, :embed_link, :cover_image_url, :like_count,
                    :comment_count, :share_count, :view_count, :remote_fingerprint, :first_seen_at,
                    :last_seen_at, :remote_status, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, tiktok_video_id) DO UPDATE SET
                    profile_id = excluded.profile_id,
                    publication_id = excluded.publication_id,
                    video_asset_id = excluded.video_asset_id,
                    packaging_asset_id = excluded.packaging_asset_id,
                    title = excluded.title,
                    video_description = excluded.video_description,
                    create_time = excluded.create_time,
                    duration_seconds = excluded.duration_seconds,
                    width = excluded.width,
                    height = excluded.height,
                    share_url = excluded.share_url,
                    embed_link = excluded.embed_link,
                    cover_image_url = excluded.cover_image_url,
                    like_count = excluded.like_count,
                    comment_count = excluded.comment_count,
                    share_count = excluded.share_count,
                    view_count = excluded.view_count,
                    remote_fingerprint = excluded.remote_fingerprint,
                    last_seen_at = excluded.last_seen_at,
                    remote_status = excluded.remote_status,
                    updated_at = excluded.updated_at
                """,
                video.to_dict() | {"remote_status": video.remote_status.value},
            )
        row = self._fetch_one("SELECT * FROM tiktok_remote_videos WHERE creator_id = ? AND tiktok_video_id = ?", (video.creator_id, video.tiktok_video_id))
        return _row_to_remote_video(row)

    def get_remote_video(self, remote_video_id: str) -> TikTokRemoteVideo | None:
        row = self._fetch_one("SELECT * FROM tiktok_remote_videos WHERE id = ?", (remote_video_id,))
        return _row_to_remote_video(row) if row else None

    def get_remote_video_by_tiktok_id(self, creator_id: str, tiktok_video_id: str) -> TikTokRemoteVideo | None:
        row = self._fetch_one("SELECT * FROM tiktok_remote_videos WHERE creator_id = ? AND tiktok_video_id = ?", (creator_id, tiktok_video_id))
        return _row_to_remote_video(row) if row else None

    def list_remote_videos(self, creator_id: str, *, profile_id: str | None = None) -> list[TikTokRemoteVideo]:
        query = "SELECT * FROM tiktok_remote_videos WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if profile_id is not None:
            query += " AND profile_id = ?"
            params.append(profile_id)
        query += " ORDER BY create_time DESC, last_seen_at DESC"
        return [_row_to_remote_video(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_video_text_version(self, version: TikTokVideoTextVersion) -> TikTokVideoTextVersion:
        with self._database.connect() as connection:
            if version.is_current:
                connection.execute("UPDATE tiktok_video_text_versions SET is_current = 0 WHERE remote_video_id = ?", (version.remote_video_id,))
            connection.execute(
                """
                INSERT INTO tiktok_video_text_versions (
                    id, remote_video_id, version_number, title_text, description_text,
                    source_fingerprint, is_current, observed_at, created_at
                ) VALUES (
                    :id, :remote_video_id, :version_number, :title_text, :description_text,
                    :source_fingerprint, :is_current, :observed_at, :created_at
                )
                ON CONFLICT(remote_video_id, version_number) DO UPDATE SET
                    title_text = excluded.title_text,
                    description_text = excluded.description_text,
                    source_fingerprint = excluded.source_fingerprint,
                    is_current = excluded.is_current,
                    observed_at = excluded.observed_at
                """,
                version.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM tiktok_video_text_versions WHERE remote_video_id = ? AND version_number = ?", (version.remote_video_id, version.version_number))
        return _row_to_text_version(row)

    def list_video_text_versions(self, remote_video_id: str) -> list[TikTokVideoTextVersion]:
        rows = self._fetch_all("SELECT * FROM tiktok_video_text_versions WHERE remote_video_id = ? ORDER BY version_number ASC", (remote_video_id,))
        return [_row_to_text_version(row) for row in rows]

    def upsert_cover_version(self, version: TikTokCoverVersion) -> TikTokCoverVersion:
        with self._database.connect() as connection:
            if version.is_current:
                connection.execute("UPDATE tiktok_cover_versions SET is_current = 0 WHERE remote_video_id = ?", (version.remote_video_id,))
            connection.execute(
                """
                INSERT INTO tiktok_cover_versions (
                    id, remote_video_id, version_number, cover_image_url, remote_fingerprint,
                    packaging_asset_id, is_current, observed_at, created_at
                ) VALUES (
                    :id, :remote_video_id, :version_number, :cover_image_url, :remote_fingerprint,
                    :packaging_asset_id, :is_current, :observed_at, :created_at
                )
                ON CONFLICT(remote_video_id, version_number) DO UPDATE SET
                    cover_image_url = excluded.cover_image_url,
                    remote_fingerprint = excluded.remote_fingerprint,
                    packaging_asset_id = excluded.packaging_asset_id,
                    is_current = excluded.is_current,
                    observed_at = excluded.observed_at
                """,
                version.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM tiktok_cover_versions WHERE remote_video_id = ? AND version_number = ?", (version.remote_video_id, version.version_number))
        return _row_to_cover_version(row)

    def list_cover_versions(self, remote_video_id: str) -> list[TikTokCoverVersion]:
        rows = self._fetch_all("SELECT * FROM tiktok_cover_versions WHERE remote_video_id = ? ORDER BY version_number ASC", (remote_video_id,))
        return [_row_to_cover_version(row) for row in rows]

    def upsert_sync_run(self, run: TikTokSyncRun) -> TikTokSyncRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_sync_runs (
                    id, creator_id, connection_id, profile_id, sync_type, status,
                    configuration_json, cursor_json, discovered_count, imported_count,
                    updated_count, unchanged_count, skipped_count, warning_count,
                    error_count, estimated_usage, started_at, completed_at, error_code,
                    error_message, created_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :profile_id, :sync_type, :status,
                    :configuration_json, :cursor_json, :discovered_count, :imported_count,
                    :updated_count, :unchanged_count, :skipped_count, :warning_count,
                    :error_count, :estimated_usage, :started_at, :completed_at, :error_code,
                    :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    profile_id = excluded.profile_id,
                    sync_type = excluded.sync_type,
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    cursor_json = excluded.cursor_json,
                    discovered_count = excluded.discovered_count,
                    imported_count = excluded.imported_count,
                    updated_count = excluded.updated_count,
                    unchanged_count = excluded.unchanged_count,
                    skipped_count = excluded.skipped_count,
                    warning_count = excluded.warning_count,
                    error_count = excluded.error_count,
                    estimated_usage = excluded.estimated_usage,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                run.to_dict() | {"sync_type": run.sync_type.value, "status": run.status.value},
            )
        row = self._fetch_one("SELECT * FROM tiktok_sync_runs WHERE id = ?", (run.id,))
        return _row_to_sync_run(row)

    def get_sync_run(self, run_id: str) -> TikTokSyncRun | None:
        row = self._fetch_one("SELECT * FROM tiktok_sync_runs WHERE id = ?", (run_id,))
        return _row_to_sync_run(row) if row else None

    def list_sync_runs(self, creator_id: str) -> list[TikTokSyncRun]:
        rows = self._fetch_all("SELECT * FROM tiktok_sync_runs WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_sync_run(row) for row in rows]

    def get_latest_sync_run(self, creator_id: str, *, connection_id: str | None = None) -> TikTokSyncRun | None:
        query = "SELECT * FROM tiktok_sync_runs WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY created_at DESC LIMIT 1"
        row = self._fetch_one(query, tuple(params))
        return _row_to_sync_run(row) if row else None

    def upsert_sync_item(self, item: TikTokSyncItem) -> TikTokSyncItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_sync_items (
                    id, sync_run_id, remote_type, remote_id, local_type, local_id,
                    action, status, warnings_json, error_code, error_message, created_at
                ) VALUES (
                    :id, :sync_run_id, :remote_type, :remote_id, :local_type, :local_id,
                    :action, :status, :warnings_json, :error_code, :error_message, :created_at
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
        row = self._fetch_one("SELECT * FROM tiktok_sync_items WHERE sync_run_id = ? AND remote_type = ? AND remote_id = ? AND action = ?", (item.sync_run_id, item.remote_type, item.remote_id, item.action))
        return _row_to_sync_item(row)

    def list_sync_items(self, sync_run_id: str) -> list[TikTokSyncItem]:
        rows = self._fetch_all("SELECT * FROM tiktok_sync_items WHERE sync_run_id = ? ORDER BY created_at ASC", (sync_run_id,))
        return [_row_to_sync_item(row) for row in rows]

    def upsert_metric_import(self, metric_import: TikTokMetricImport) -> TikTokMetricImport:
        with self._database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM tiktok_metric_imports
                WHERE source_fingerprint = ?
                  AND metric_scope = ?
                  AND source_type = ?
                  AND IFNULL(profile_id, '') = IFNULL(?, '')
                  AND IFNULL(remote_video_id, '') = IFNULL(?, '')
                """,
                (
                    metric_import.source_fingerprint,
                    metric_import.metric_scope.value,
                    metric_import.source_type.value,
                    metric_import.profile_id,
                    metric_import.remote_video_id,
                ),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO tiktok_metric_imports (
                        id, creator_id, profile_id, remote_video_id, sync_run_id, metric_scope,
                        source_type, observed_at, period_start, period_end, comparable_window,
                        source_fingerprint, status, created_at
                    ) VALUES (
                        :id, :creator_id, :profile_id, :remote_video_id, :sync_run_id, :metric_scope,
                        :source_type, :observed_at, :period_start, :period_end, :comparable_window,
                        :source_fingerprint, :status, :created_at
                    )
                    """,
                    metric_import.to_dict(),
                )
            else:
                connection.execute(
                    """
                    UPDATE tiktok_metric_imports
                    SET creator_id = :creator_id,
                        profile_id = :profile_id,
                        remote_video_id = :remote_video_id,
                        sync_run_id = :sync_run_id,
                        metric_scope = :metric_scope,
                        source_type = :source_type,
                        observed_at = :observed_at,
                        period_start = :period_start,
                        period_end = :period_end,
                        comparable_window = :comparable_window,
                        status = :status
                    WHERE id = :id
                    """,
                    metric_import.to_dict(),
                )
        row = self._fetch_one(
            "SELECT * FROM tiktok_metric_imports WHERE source_fingerprint = ? AND metric_scope = ? AND source_type = ? AND IFNULL(profile_id, '') = IFNULL(?, '') AND IFNULL(remote_video_id, '') = IFNULL(?, '')",
            (
                metric_import.source_fingerprint,
                metric_import.metric_scope.value,
                metric_import.source_type.value,
                metric_import.profile_id,
                metric_import.remote_video_id,
            ),
        )
        return _row_to_metric_import(row)

    def get_metric_import(self, metric_import_id: str) -> TikTokMetricImport | None:
        row = self._fetch_one("SELECT * FROM tiktok_metric_imports WHERE id = ?", (metric_import_id,))
        return _row_to_metric_import(row) if row else None

    def list_metric_imports(self, creator_id: str, *, profile_id: str | None = None) -> list[TikTokMetricImport]:
        query = "SELECT * FROM tiktok_metric_imports WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if profile_id is not None:
            query += " AND profile_id = ?"
            params.append(profile_id)
        query += " ORDER BY created_at DESC"
        return [_row_to_metric_import(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_metric_value(self, metric_value: TikTokMetricValue) -> TikTokMetricValue:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_metric_values (
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
        row = self._fetch_one("SELECT * FROM tiktok_metric_values WHERE metric_import_id = ? AND metric_key = ? AND dimensions_json = ? AND raw_metric_name = ?", (metric_value.metric_import_id, metric_value.metric_key, metric_value.dimensions_json, metric_value.raw_metric_name))
        return _row_to_metric_value(row)

    def list_metric_values(self, metric_import_id: str) -> list[TikTokMetricValue]:
        return [_row_to_metric_value(row) for row in self._fetch_all("SELECT * FROM tiktok_metric_values WHERE metric_import_id = ? ORDER BY created_at ASC", (metric_import_id,))]

    def upsert_content_link(self, link: TikTokContentLink) -> TikTokContentLink:
        payload = link.to_dict() | {"link_method": link.link_method.value}
        with self._database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM tiktok_content_links
                WHERE creator_id = ?
                  AND remote_video_id = ?
                  AND IFNULL(publication_id, '') = IFNULL(?, '')
                  AND IFNULL(video_asset_id, '') = IFNULL(?, '')
                  AND IFNULL(packaging_asset_id, '') = IFNULL(?, '')
                """,
                (link.creator_id, link.remote_video_id, link.publication_id, link.video_asset_id, link.packaging_asset_id),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO tiktok_content_links (
                        id, creator_id, remote_video_id, publication_id, video_asset_id,
                        packaging_asset_id, link_method, confidence_level, status, reviewed_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :creator_id, :remote_video_id, :publication_id, :video_asset_id,
                        :packaging_asset_id, :link_method, :confidence_level, :status, :reviewed_at,
                        :created_at, :updated_at
                    )
                    """,
                    payload,
                )
            else:
                connection.execute(
                    """
                    UPDATE tiktok_content_links
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
            "SELECT * FROM tiktok_content_links WHERE creator_id = ? AND remote_video_id = ? AND IFNULL(publication_id, '') = IFNULL(?, '') AND IFNULL(video_asset_id, '') = IFNULL(?, '') AND IFNULL(packaging_asset_id, '') = IFNULL(?, '')",
            (link.creator_id, link.remote_video_id, link.publication_id, link.video_asset_id, link.packaging_asset_id),
        )
        return _row_to_link(row)

    def get_content_link(self, link_id: str) -> TikTokContentLink | None:
        row = self._fetch_one("SELECT * FROM tiktok_content_links WHERE id = ?", (link_id,))
        return _row_to_link(row) if row else None

    def list_content_links(self, creator_id: str) -> list[TikTokContentLink]:
        return [_row_to_link(row) for row in self._fetch_all("SELECT * FROM tiktok_content_links WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))]

    def upsert_rate_limit_usage(self, usage: TikTokRateLimitUsage) -> TikTokRateLimitUsage:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_rate_limit_usage (
                    id, connection_id, operation_key, endpoint, request_count,
                    estimated_usage, window_started_at, response_headers_json, usage_date, created_at
                ) VALUES (
                    :id, :connection_id, :operation_key, :endpoint, :request_count,
                    :estimated_usage, :window_started_at, :response_headers_json, :usage_date, :created_at
                )
                ON CONFLICT(connection_id, operation_key, usage_date) DO UPDATE SET
                    endpoint = excluded.endpoint,
                    request_count = request_count + excluded.request_count,
                    estimated_usage = excluded.estimated_usage,
                    window_started_at = excluded.window_started_at,
                    response_headers_json = excluded.response_headers_json
                """,
                usage.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM tiktok_rate_limit_usage WHERE connection_id = ? AND operation_key = ? AND usage_date = ?", (usage.connection_id, usage.operation_key, usage.usage_date))
        return _row_to_rate_limit(row)

    def list_rate_limit_usage(self, connection_id: str) -> list[TikTokRateLimitUsage]:
        return [_row_to_rate_limit(row) for row in self._fetch_all("SELECT * FROM tiktok_rate_limit_usage WHERE connection_id = ? ORDER BY usage_date DESC, created_at DESC", (connection_id,))]

    def upsert_sync_schedule(self, schedule: TikTokSyncSchedule) -> TikTokSyncSchedule:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO tiktok_sync_schedules (
                    id, creator_id, connection_id, profile_id, schedule_type, enabled,
                    interval_hours, last_run_at, next_run_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :profile_id, :schedule_type, :enabled,
                    :interval_hours, :last_run_at, :next_run_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    enabled = excluded.enabled,
                    interval_hours = excluded.interval_hours,
                    last_run_at = excluded.last_run_at,
                    next_run_at = excluded.next_run_at,
                    updated_at = excluded.updated_at
                """,
                schedule.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM tiktok_sync_schedules WHERE id = ?", (schedule.id,))
        return _row_to_schedule(row)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[TikTokSyncSchedule]:
        query = "SELECT * FROM tiktok_sync_schedules WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY created_at DESC"
        return [_row_to_schedule(row) for row in self._fetch_all(query, tuple(params))]

