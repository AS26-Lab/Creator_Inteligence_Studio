"""Repositorio SQLite para la integracion de Instagram."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.instagram_integration.connection_types import (
    InstagramAccessLevel,
    InstagramAppAccessStatus,
    InstagramConnectionStatus,
    InstagramContentType,
    InstagramLinkMethod,
    InstagramMediaType,
    InstagramProfessionalAccountType,
)
from creator_intelligence_studio.domain.instagram_integration.entities import (
    InstagramAccount,
    InstagramCaptionVersion,
    InstagramCarouselChild,
    InstagramConnection,
    InstagramContentLink,
    InstagramCoverVersion,
    InstagramInsightImport,
    InstagramInsightValue,
    InstagramRateLimitUsage,
    InstagramRemoteMedia,
    InstagramSyncItem,
    InstagramSyncReport,
    InstagramSyncRun,
    InstagramSyncSchedule,
)
from creator_intelligence_studio.domain.instagram_integration.insight_types import InstagramInsightPeriod, InstagramInsightScope
from creator_intelligence_studio.domain.instagram_integration.repositories import InstagramIntegrationRepository
from creator_intelligence_studio.domain.instagram_integration.sync_types import InstagramSyncStatus, InstagramSyncType
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


def _row_to_connection(row: sqlite3.Row) -> InstagramConnection:
    return InstagramConnection(
        id=row["id"],
        creator_id=row["creator_id"],
        provider=row["provider"],
        account_identifier=row["account_identifier"],
        professional_account_type=InstagramProfessionalAccountType(row["professional_account_type"]) if row["professional_account_type"] else None,
        status=InstagramConnectionStatus(row["status"]),
        granted_scopes_json=row["granted_scopes_json"],
        credential_reference=row["credential_reference"],
        api_version=row["api_version"],
        access_level=InstagramAccessLevel(row["access_level"]) if row["access_level"] else None,
        app_access_status=InstagramAppAccessStatus(row["app_access_status"]),
        connected_at=from_iso_z(row["connected_at"]) or utc_now(),
        last_verified_at=from_iso_z(row["last_verified_at"]),
        disconnected_at=from_iso_z(row["disconnected_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_account(row: sqlite3.Row) -> InstagramAccount:
    return InstagramAccount(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        instagram_user_id=row["instagram_user_id"],
        username=row["username"],
        name=row["name"],
        biography=row["biography"],
        website=row["website"],
        profile_picture_url=row["profile_picture_url"],
        followers_count=row["followers_count"],
        follows_count=row["follows_count"],
        media_count=row["media_count"],
        account_type=InstagramProfessionalAccountType(row["account_type"]),
        selected_for_sync=bool(row["selected_for_sync"]),
        last_synced_at=from_iso_z(row["last_synced_at"]),
        remote_fingerprint=row["remote_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_remote_media(row: sqlite3.Row) -> InstagramRemoteMedia:
    return InstagramRemoteMedia(
        id=row["id"],
        creator_id=row["creator_id"],
        account_id=row["account_id"],
        instagram_media_id=row["instagram_media_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        packaging_asset_id=row["packaging_asset_id"],
        media_type=InstagramMediaType(row["media_type"]),
        media_product_type=row["media_product_type"],
        content_type=InstagramContentType(row["content_type"]),
        caption=row["caption"],
        permalink=row["permalink"],
        media_url=row["media_url"],
        thumbnail_url=row["thumbnail_url"],
        cover_url=row["cover_url"],
        timestamp=from_iso_z(row["timestamp"]) or utc_now(),
        shortcode=row["shortcode"],
        children_count=row["children_count"],
        remote_fingerprint=row["remote_fingerprint"],
        first_seen_at=from_iso_z(row["first_seen_at"]) or utc_now(),
        last_seen_at=from_iso_z(row["last_seen_at"]) or utc_now(),
        remote_status=row["remote_status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_child(row: sqlite3.Row) -> InstagramCarouselChild:
    return InstagramCarouselChild(
        id=row["id"],
        remote_media_id=row["remote_media_id"],
        instagram_child_id=row["instagram_child_id"],
        child_order=row["child_order"],
        media_type=InstagramMediaType(row["media_type"]),
        media_url=row["media_url"],
        thumbnail_url=row["thumbnail_url"],
        remote_fingerprint=row["remote_fingerprint"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_caption(row: sqlite3.Row) -> InstagramCaptionVersion:
    return InstagramCaptionVersion(
        id=row["id"],
        remote_media_id=row["remote_media_id"],
        version_number=row["version_number"],
        caption_text=row["caption_text"],
        source_fingerprint=row["source_fingerprint"],
        is_current=bool(row["is_current"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_cover(row: sqlite3.Row) -> InstagramCoverVersion:
    return InstagramCoverVersion(
        id=row["id"],
        remote_media_id=row["remote_media_id"],
        version_number=row["version_number"],
        cover_url=row["cover_url"],
        thumbnail_url=row["thumbnail_url"],
        remote_fingerprint=row["remote_fingerprint"],
        packaging_asset_id=row["packaging_asset_id"],
        is_current=bool(row["is_current"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_sync_run(row: sqlite3.Row) -> InstagramSyncRun:
    return InstagramSyncRun(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        account_id=row["account_id"],
        sync_type=InstagramSyncType(row["sync_type"]),
        status=InstagramSyncStatus(row["status"]),
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


def _row_to_sync_item(row: sqlite3.Row) -> InstagramSyncItem:
    return InstagramSyncItem(
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


def _row_to_insight_import(row: sqlite3.Row) -> InstagramInsightImport:
    return InstagramInsightImport(
        id=row["id"],
        creator_id=row["creator_id"],
        account_id=row["account_id"],
        remote_media_id=row["remote_media_id"],
        sync_run_id=row["sync_run_id"],
        insight_scope=InstagramInsightScope(row["insight_scope"]),
        metric_period=InstagramInsightPeriod(row["metric_period"]) if row["metric_period"] else None,
        date_start=row["date_start"],
        date_end=row["date_end"],
        comparable_window=row["comparable_window"],
        source_fingerprint=row["source_fingerprint"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_insight_value(row: sqlite3.Row) -> InstagramInsightValue:
    return InstagramInsightValue(
        id=row["id"],
        insight_import_id=row["insight_import_id"],
        metric_key=row["metric_key"],
        raw_metric_name=row["raw_metric_name"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        period=row["period"],
        dimensions_json=row["dimensions_json"],
        breakdowns_json=row["breakdowns_json"],
        quality_status=row["quality_status"],
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_link(row: sqlite3.Row) -> InstagramContentLink:
    return InstagramContentLink(
        id=row["id"],
        creator_id=row["creator_id"],
        remote_media_id=row["remote_media_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        packaging_asset_id=row["packaging_asset_id"],
        link_method=InstagramLinkMethod(row["link_method"]),
        confidence_level=row["confidence_level"],
        status=row["status"],
        reviewed_at=from_iso_z(row["reviewed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_rate_limit(row: sqlite3.Row) -> InstagramRateLimitUsage:
    return InstagramRateLimitUsage(
        id=row["id"],
        connection_id=row["connection_id"],
        operation_key=row["operation_key"],
        estimated_usage=row["estimated_usage"],
        request_count=row["request_count"],
        usage_date=row["usage_date"],
        headers_snapshot_json=row["headers_snapshot_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_schedule(row: sqlite3.Row) -> InstagramSyncSchedule:
    return InstagramSyncSchedule(
        id=row["id"],
        creator_id=row["creator_id"],
        connection_id=row["connection_id"],
        account_id=row["account_id"],
        schedule_type=row["schedule_type"],
        enabled=bool(row["enabled"]),
        interval_hours=row["interval_hours"],
        last_run_at=from_iso_z(row["last_run_at"]),
        next_run_at=from_iso_z(row["next_run_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLiteInstagramRepository(InstagramIntegrationRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchall()

    def upsert_connection(self, connection_obj: InstagramConnection) -> InstagramConnection:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_connections (
                    id, creator_id, provider, account_identifier, professional_account_type,
                    status, granted_scopes_json, credential_reference, api_version,
                    access_level, app_access_status, connected_at, last_verified_at,
                    disconnected_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :provider, :account_identifier, :professional_account_type,
                    :status, :granted_scopes_json, :credential_reference, :api_version,
                    :access_level, :app_access_status, :connected_at, :last_verified_at,
                    :disconnected_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    provider = excluded.provider,
                    account_identifier = excluded.account_identifier,
                    professional_account_type = excluded.professional_account_type,
                    status = excluded.status,
                    granted_scopes_json = excluded.granted_scopes_json,
                    credential_reference = excluded.credential_reference,
                    api_version = excluded.api_version,
                    access_level = excluded.access_level,
                    app_access_status = excluded.app_access_status,
                    last_verified_at = excluded.last_verified_at,
                    disconnected_at = excluded.disconnected_at,
                    updated_at = excluded.updated_at
                """,
                connection_obj.to_dict() | {
                    "professional_account_type": None if connection_obj.professional_account_type is None else connection_obj.professional_account_type.value,
                    "status": connection_obj.status.value,
                    "access_level": None if connection_obj.access_level is None else connection_obj.access_level.value,
                    "app_access_status": connection_obj.app_access_status.value,
                },
            )
        row = self._fetch_one("SELECT * FROM instagram_connections WHERE id = ?", (connection_obj.id,))
        return _row_to_connection(row)

    def get_connection(self, connection_id: str) -> InstagramConnection | None:
        row = self._fetch_one("SELECT * FROM instagram_connections WHERE id = ?", (connection_id,))
        return _row_to_connection(row) if row else None

    def list_connections(self, creator_id: str) -> list[InstagramConnection]:
        rows = self._fetch_all("SELECT * FROM instagram_connections WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_connection(row) for row in rows]

    def upsert_account(self, account: InstagramAccount) -> InstagramAccount:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_accounts (
                    id, creator_id, connection_id, instagram_user_id, username, name,
                    biography, website, profile_picture_url, followers_count, follows_count,
                    media_count, account_type, selected_for_sync, last_synced_at,
                    remote_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :instagram_user_id, :username, :name,
                    :biography, :website, :profile_picture_url, :followers_count, :follows_count,
                    :media_count, :account_type, :selected_for_sync, :last_synced_at,
                    :remote_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, instagram_user_id) DO UPDATE SET
                    connection_id = excluded.connection_id,
                    username = excluded.username,
                    name = excluded.name,
                    biography = excluded.biography,
                    website = excluded.website,
                    profile_picture_url = excluded.profile_picture_url,
                    followers_count = excluded.followers_count,
                    follows_count = excluded.follows_count,
                    media_count = excluded.media_count,
                    account_type = excluded.account_type,
                    selected_for_sync = excluded.selected_for_sync,
                    last_synced_at = excluded.last_synced_at,
                    remote_fingerprint = excluded.remote_fingerprint,
                    updated_at = excluded.updated_at
                """,
                account.to_dict() | {"account_type": account.account_type.value, "selected_for_sync": 1 if account.selected_for_sync else 0},
            )
        row = self._fetch_one("SELECT * FROM instagram_accounts WHERE creator_id = ? AND instagram_user_id = ?", (account.creator_id, account.instagram_user_id))
        return _row_to_account(row)

    def get_account(self, account_id: str) -> InstagramAccount | None:
        row = self._fetch_one("SELECT * FROM instagram_accounts WHERE id = ?", (account_id,))
        return _row_to_account(row) if row else None

    def get_account_by_instagram_user_id(self, creator_id: str, instagram_user_id: str) -> InstagramAccount | None:
        row = self._fetch_one("SELECT * FROM instagram_accounts WHERE creator_id = ? AND instagram_user_id = ?", (creator_id, instagram_user_id))
        return _row_to_account(row) if row else None

    def list_accounts(self, creator_id: str, *, connection_id: str | None = None) -> list[InstagramAccount]:
        query = "SELECT * FROM instagram_accounts WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY selected_for_sync DESC, updated_at DESC"
        return [_row_to_account(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_remote_media(self, media: InstagramRemoteMedia) -> InstagramRemoteMedia:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_remote_media (
                    id, creator_id, account_id, instagram_media_id, publication_id,
                    video_asset_id, packaging_asset_id, media_type, media_product_type,
                    content_type, caption, permalink, media_url, thumbnail_url, cover_url,
                    timestamp, shortcode, children_count, remote_fingerprint, first_seen_at,
                    last_seen_at, remote_status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :account_id, :instagram_media_id, :publication_id,
                    :video_asset_id, :packaging_asset_id, :media_type, :media_product_type,
                    :content_type, :caption, :permalink, :media_url, :thumbnail_url, :cover_url,
                    :timestamp, :shortcode, :children_count, :remote_fingerprint, :first_seen_at,
                    :last_seen_at, :remote_status, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, instagram_media_id) DO UPDATE SET
                    account_id = excluded.account_id,
                    publication_id = excluded.publication_id,
                    video_asset_id = excluded.video_asset_id,
                    packaging_asset_id = excluded.packaging_asset_id,
                    media_type = excluded.media_type,
                    media_product_type = excluded.media_product_type,
                    content_type = excluded.content_type,
                    caption = excluded.caption,
                    permalink = excluded.permalink,
                    media_url = excluded.media_url,
                    thumbnail_url = excluded.thumbnail_url,
                    cover_url = excluded.cover_url,
                    timestamp = excluded.timestamp,
                    shortcode = excluded.shortcode,
                    children_count = excluded.children_count,
                    remote_fingerprint = excluded.remote_fingerprint,
                    last_seen_at = excluded.last_seen_at,
                    remote_status = excluded.remote_status,
                    updated_at = excluded.updated_at
                """,
                media.to_dict() | {"media_type": media.media_type.value, "content_type": media.content_type.value},
            )
        row = self._fetch_one("SELECT * FROM instagram_remote_media WHERE creator_id = ? AND instagram_media_id = ?", (media.creator_id, media.instagram_media_id))
        return _row_to_remote_media(row)

    def get_remote_media(self, remote_media_id: str) -> InstagramRemoteMedia | None:
        row = self._fetch_one("SELECT * FROM instagram_remote_media WHERE id = ?", (remote_media_id,))
        return _row_to_remote_media(row) if row else None

    def get_remote_media_by_instagram_id(self, creator_id: str, instagram_media_id: str) -> InstagramRemoteMedia | None:
        row = self._fetch_one("SELECT * FROM instagram_remote_media WHERE creator_id = ? AND instagram_media_id = ?", (creator_id, instagram_media_id))
        return _row_to_remote_media(row) if row else None

    def list_remote_media(self, creator_id: str, *, account_id: str | None = None) -> list[InstagramRemoteMedia]:
        query = "SELECT * FROM instagram_remote_media WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        query += " ORDER BY timestamp DESC, last_seen_at DESC"
        return [_row_to_remote_media(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_carousel_child(self, child: InstagramCarouselChild) -> InstagramCarouselChild:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_carousel_children (
                    id, remote_media_id, instagram_child_id, child_order, media_type,
                    media_url, thumbnail_url, remote_fingerprint, created_at, updated_at
                ) VALUES (
                    :id, :remote_media_id, :instagram_child_id, :child_order, :media_type,
                    :media_url, :thumbnail_url, :remote_fingerprint, :created_at, :updated_at
                )
                ON CONFLICT(remote_media_id, instagram_child_id) DO UPDATE SET
                    child_order = excluded.child_order,
                    media_type = excluded.media_type,
                    media_url = excluded.media_url,
                    thumbnail_url = excluded.thumbnail_url,
                    remote_fingerprint = excluded.remote_fingerprint,
                    updated_at = excluded.updated_at
                """,
                child.to_dict() | {"media_type": child.media_type.value},
            )
        row = self._fetch_one("SELECT * FROM instagram_carousel_children WHERE remote_media_id = ? AND instagram_child_id = ?", (child.remote_media_id, child.instagram_child_id))
        return _row_to_child(row)

    def list_carousel_children(self, remote_media_id: str) -> list[InstagramCarouselChild]:
        rows = self._fetch_all("SELECT * FROM instagram_carousel_children WHERE remote_media_id = ? ORDER BY child_order ASC", (remote_media_id,))
        return [_row_to_child(row) for row in rows]

    def upsert_caption_version(self, caption: InstagramCaptionVersion) -> InstagramCaptionVersion:
        with self._database.connect() as connection:
            if caption.is_current:
                connection.execute("UPDATE instagram_caption_versions SET is_current = 0 WHERE remote_media_id = ?", (caption.remote_media_id,))
            connection.execute(
                """
                INSERT INTO instagram_caption_versions (
                    id, remote_media_id, version_number, caption_text, source_fingerprint,
                    is_current, observed_at, created_at
                ) VALUES (
                    :id, :remote_media_id, :version_number, :caption_text, :source_fingerprint,
                    :is_current, :observed_at, :created_at
                )
                ON CONFLICT(remote_media_id, version_number) DO UPDATE SET
                    caption_text = excluded.caption_text,
                    source_fingerprint = excluded.source_fingerprint,
                    is_current = excluded.is_current,
                    observed_at = excluded.observed_at
                """,
                caption.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM instagram_caption_versions WHERE remote_media_id = ? AND version_number = ?", (caption.remote_media_id, caption.version_number))
        return _row_to_caption(row)

    def list_caption_versions(self, remote_media_id: str) -> list[InstagramCaptionVersion]:
        rows = self._fetch_all("SELECT * FROM instagram_caption_versions WHERE remote_media_id = ? ORDER BY version_number ASC", (remote_media_id,))
        return [_row_to_caption(row) for row in rows]

    def upsert_cover_version(self, cover: InstagramCoverVersion) -> InstagramCoverVersion:
        with self._database.connect() as connection:
            if cover.is_current:
                connection.execute("UPDATE instagram_cover_versions SET is_current = 0 WHERE remote_media_id = ?", (cover.remote_media_id,))
            connection.execute(
                """
                INSERT INTO instagram_cover_versions (
                    id, remote_media_id, version_number, cover_url, thumbnail_url,
                    remote_fingerprint, packaging_asset_id, is_current, observed_at, created_at
                ) VALUES (
                    :id, :remote_media_id, :version_number, :cover_url, :thumbnail_url,
                    :remote_fingerprint, :packaging_asset_id, :is_current, :observed_at, :created_at
                )
                ON CONFLICT(remote_media_id, version_number) DO UPDATE SET
                    cover_url = excluded.cover_url,
                    thumbnail_url = excluded.thumbnail_url,
                    remote_fingerprint = excluded.remote_fingerprint,
                    packaging_asset_id = excluded.packaging_asset_id,
                    is_current = excluded.is_current,
                    observed_at = excluded.observed_at
                """,
                cover.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM instagram_cover_versions WHERE remote_media_id = ? AND version_number = ?", (cover.remote_media_id, cover.version_number))
        return _row_to_cover(row)

    def list_cover_versions(self, remote_media_id: str) -> list[InstagramCoverVersion]:
        rows = self._fetch_all("SELECT * FROM instagram_cover_versions WHERE remote_media_id = ? ORDER BY version_number ASC", (remote_media_id,))
        return [_row_to_cover(row) for row in rows]

    def upsert_sync_run(self, run: InstagramSyncRun) -> InstagramSyncRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_sync_runs (
                    id, creator_id, connection_id, account_id, sync_type, status,
                    configuration_json, cursor_json, discovered_count, imported_count,
                    updated_count, unchanged_count, skipped_count, warning_count,
                    error_count, estimated_usage, started_at, completed_at, error_code,
                    error_message, created_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :account_id, :sync_type, :status,
                    :configuration_json, :cursor_json, :discovered_count, :imported_count,
                    :updated_count, :unchanged_count, :skipped_count, :warning_count,
                    :error_count, :estimated_usage, :started_at, :completed_at, :error_code,
                    :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    account_id = excluded.account_id,
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
        row = self._fetch_one("SELECT * FROM instagram_sync_runs WHERE id = ?", (run.id,))
        return _row_to_sync_run(row)

    def get_sync_run(self, run_id: str) -> InstagramSyncRun | None:
        row = self._fetch_one("SELECT * FROM instagram_sync_runs WHERE id = ?", (run_id,))
        return _row_to_sync_run(row) if row else None

    def list_sync_runs(self, creator_id: str) -> list[InstagramSyncRun]:
        rows = self._fetch_all("SELECT * FROM instagram_sync_runs WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_sync_run(row) for row in rows]

    def get_latest_sync_run(self, creator_id: str, *, connection_id: str | None = None) -> InstagramSyncRun | None:
        query = "SELECT * FROM instagram_sync_runs WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY created_at DESC LIMIT 1"
        row = self._fetch_one(query, tuple(params))
        return _row_to_sync_run(row) if row else None

    def upsert_sync_item(self, item: InstagramSyncItem) -> InstagramSyncItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_sync_items (
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
        row = self._fetch_one("SELECT * FROM instagram_sync_items WHERE sync_run_id = ? AND remote_type = ? AND remote_id = ? AND action = ?", (item.sync_run_id, item.remote_type, item.remote_id, item.action))
        return _row_to_sync_item(row)

    def list_sync_items(self, sync_run_id: str) -> list[InstagramSyncItem]:
        rows = self._fetch_all("SELECT * FROM instagram_sync_items WHERE sync_run_id = ? ORDER BY created_at ASC", (sync_run_id,))
        return [_row_to_sync_item(row) for row in rows]

    def upsert_insight_import(self, insight_import: InstagramInsightImport) -> InstagramInsightImport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_insight_imports (
                    id, creator_id, account_id, remote_media_id, sync_run_id,
                    insight_scope, metric_period, date_start, date_end, comparable_window,
                    source_fingerprint, status, created_at
                ) VALUES (
                    :id, :creator_id, :account_id, :remote_media_id, :sync_run_id,
                    :insight_scope, :metric_period, :date_start, :date_end, :comparable_window,
                    :source_fingerprint, :status, :created_at
                )
                ON CONFLICT(source_fingerprint) DO UPDATE SET
                    status = excluded.status
                """,
                insight_import.to_dict() | {"insight_scope": insight_import.insight_scope.value, "metric_period": None if insight_import.metric_period is None else insight_import.metric_period.value},
            )
        row = self._fetch_one("SELECT * FROM instagram_insight_imports WHERE source_fingerprint = ?", (insight_import.source_fingerprint,))
        return _row_to_insight_import(row)

    def get_insight_import(self, insight_import_id: str) -> InstagramInsightImport | None:
        row = self._fetch_one("SELECT * FROM instagram_insight_imports WHERE id = ?", (insight_import_id,))
        return _row_to_insight_import(row) if row else None

    def list_insight_imports(self, creator_id: str, *, account_id: str | None = None) -> list[InstagramInsightImport]:
        query = "SELECT * FROM instagram_insight_imports WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        query += " ORDER BY created_at DESC"
        return [_row_to_insight_import(row) for row in self._fetch_all(query, tuple(params))]

    def upsert_insight_value(self, insight_value: InstagramInsightValue) -> InstagramInsightValue:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_insight_values (
                    id, insight_import_id, metric_key, raw_metric_name, numeric_value,
                    text_value, unit, period, dimensions_json, breakdowns_json,
                    quality_status, warning_codes_json, created_at
                ) VALUES (
                    :id, :insight_import_id, :metric_key, :raw_metric_name, :numeric_value,
                    :text_value, :unit, :period, :dimensions_json, :breakdowns_json,
                    :quality_status, :warning_codes_json, :created_at
                )
                ON CONFLICT(insight_import_id, metric_key, dimensions_json, raw_metric_name) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    period = excluded.period,
                    breakdowns_json = excluded.breakdowns_json,
                    quality_status = excluded.quality_status,
                    warning_codes_json = excluded.warning_codes_json
                """,
                insight_value.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM instagram_insight_values WHERE insight_import_id = ? AND metric_key = ? AND dimensions_json = ? AND raw_metric_name = ?", (insight_value.insight_import_id, insight_value.metric_key, insight_value.dimensions_json, insight_value.raw_metric_name))
        return _row_to_insight_value(row)

    def list_insight_values(self, insight_import_id: str) -> list[InstagramInsightValue]:
        rows = self._fetch_all("SELECT * FROM instagram_insight_values WHERE insight_import_id = ? ORDER BY created_at ASC", (insight_import_id,))
        return [_row_to_insight_value(row) for row in rows]

    def upsert_content_link(self, link: InstagramContentLink) -> InstagramContentLink:
        with self._database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM instagram_content_links
                WHERE creator_id = ?
                  AND remote_media_id = ?
                  AND IFNULL(publication_id, '') = IFNULL(?, '')
                  AND IFNULL(video_asset_id, '') = IFNULL(?, '')
                  AND IFNULL(packaging_asset_id, '') = IFNULL(?, '')
                """,
                (link.creator_id, link.remote_media_id, link.publication_id, link.video_asset_id, link.packaging_asset_id),
            ).fetchone()
            payload = link.to_dict() | {"link_method": link.link_method.value}
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO instagram_content_links (
                        id, creator_id, remote_media_id, publication_id, video_asset_id,
                        packaging_asset_id, link_method, confidence_level, status, reviewed_at,
                        created_at, updated_at
                    ) VALUES (
                        :id, :creator_id, :remote_media_id, :publication_id, :video_asset_id,
                        :packaging_asset_id, :link_method, :confidence_level, :status, :reviewed_at,
                        :created_at, :updated_at
                    )
                    """,
                    payload,
                )
            else:
                connection.execute(
                    """
                    UPDATE instagram_content_links
                    SET link_method = :link_method,
                        confidence_level = :confidence_level,
                        status = :status,
                        reviewed_at = :reviewed_at,
                        updated_at = :updated_at
                    WHERE id = :id
                    """,
                    payload,
                )
        row = self._fetch_one("SELECT * FROM instagram_content_links WHERE creator_id = ? AND remote_media_id = ? AND IFNULL(publication_id, '') = IFNULL(?, '') AND IFNULL(video_asset_id, '') = IFNULL(?, '') AND IFNULL(packaging_asset_id, '') = IFNULL(?, '')", (link.creator_id, link.remote_media_id, link.publication_id, link.video_asset_id, link.packaging_asset_id))
        return _row_to_link(row)

    def get_content_link(self, link_id: str) -> InstagramContentLink | None:
        row = self._fetch_one("SELECT * FROM instagram_content_links WHERE id = ?", (link_id,))
        return _row_to_link(row) if row else None

    def list_content_links(self, creator_id: str) -> list[InstagramContentLink]:
        rows = self._fetch_all("SELECT * FROM instagram_content_links WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_link(row) for row in rows]

    def upsert_rate_limit_usage(self, usage: InstagramRateLimitUsage) -> InstagramRateLimitUsage:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_rate_limit_usage (
                    id, connection_id, operation_key, estimated_usage,
                    request_count, usage_date, headers_snapshot_json, created_at
                ) VALUES (
                    :id, :connection_id, :operation_key, :estimated_usage,
                    :request_count, :usage_date, :headers_snapshot_json, :created_at
                )
                ON CONFLICT(connection_id, operation_key, usage_date) DO UPDATE SET
                    estimated_usage = excluded.estimated_usage,
                    request_count = request_count + excluded.request_count,
                    headers_snapshot_json = excluded.headers_snapshot_json
                """,
                usage.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM instagram_rate_limit_usage WHERE connection_id = ? AND operation_key = ? AND usage_date = ?", (usage.connection_id, usage.operation_key, usage.usage_date))
        return _row_to_rate_limit(row)

    def list_rate_limit_usage(self, connection_id: str) -> list[InstagramRateLimitUsage]:
        rows = self._fetch_all("SELECT * FROM instagram_rate_limit_usage WHERE connection_id = ? ORDER BY usage_date DESC, created_at DESC", (connection_id,))
        return [_row_to_rate_limit(row) for row in rows]

    def upsert_sync_schedule(self, schedule: InstagramSyncSchedule) -> InstagramSyncSchedule:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instagram_sync_schedules (
                    id, creator_id, connection_id, account_id, schedule_type, enabled,
                    interval_hours, last_run_at, next_run_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :connection_id, :account_id, :schedule_type, :enabled,
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
        row = self._fetch_one("SELECT * FROM instagram_sync_schedules WHERE id = ?", (schedule.id,))
        return _row_to_schedule(row)

    def list_sync_schedules(self, creator_id: str, *, connection_id: str | None = None) -> list[InstagramSyncSchedule]:
        query = "SELECT * FROM instagram_sync_schedules WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if connection_id is not None:
            query += " AND connection_id = ?"
            params.append(connection_id)
        query += " ORDER BY created_at DESC"
        return [_row_to_schedule(row) for row in self._fetch_all(query, tuple(params))]
