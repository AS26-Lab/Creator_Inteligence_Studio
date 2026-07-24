"""Repositorio SQLite para analytics manual y aprendizaje."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from creator_intelligence_studio.domain.analytics.entities import (
    AnalyticsChannel,
    AnalyticsFieldMapping,
    AnalyticsImport,
    AnalyticsImportRow,
    AnalyticsMetricDefinition,
    AnalyticsMetricSnapshot,
    AnalyticsPlatform,
    AnalyticsPublication,
)
from creator_intelligence_studio.domain.analytics.repositories import AnalyticsRepository
from creator_intelligence_studio.domain.analytics.value_objects import (
    AnalyticsAggregationType,
    AnalyticsContentType,
    AnalyticsFieldMappingOrigin,
    AnalyticsImportRowStatus,
    AnalyticsImportStatus,
    AnalyticsMetricCategory,
    AnalyticsPlatformStatus,
    AnalyticsQualityStatus,
    AnalyticsSourceType,
    AnalyticsValueType,
)
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


def _row_to_platform(row: sqlite3.Row) -> AnalyticsPlatform:
    return AnalyticsPlatform(
        id=row["id"],
        platform_key=row["platform_key"],
        display_name=row["display_name"],
        status=AnalyticsPlatformStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_channel(row: sqlite3.Row) -> AnalyticsChannel:
    return AnalyticsChannel(
        id=row["id"],
        creator_id=row["creator_id"],
        platform_id=row["platform_id"],
        platform_key=row["platform_key"],
        external_channel_id=row["external_channel_id"],
        channel_name=row["channel_name"],
        channel_url=row["channel_url"],
        timezone_name=row["timezone_name"],
        is_primary=bool(row["is_primary"]),
        metadata_json=row["metadata_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_publication(row: sqlite3.Row) -> AnalyticsPublication:
    return AnalyticsPublication(
        id=row["id"],
        creator_id=row["creator_id"],
        channel_id=row["channel_id"],
        video_asset_id=row["video_asset_id"],
        external_publication_id=row["external_publication_id"],
        platform=row["platform"],
        content_type=AnalyticsContentType(row["content_type"]),
        title=row["title"],
        description=row["description"],
        published_at=from_iso_z(row["published_at"]) or utc_now(),
        duration_seconds=row["duration_seconds"],
        url=row["url"],
        thumbnail_path=row["thumbnail_path"],
        status=row["status"],
        source_type=AnalyticsSourceType(row["source_type"]),
        source_fingerprint=row["source_fingerprint"],
        dedupe_key=row["dedupe_key"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_metric_definition(row: sqlite3.Row) -> AnalyticsMetricDefinition:
    return AnalyticsMetricDefinition(
        id=row["id"],
        metric_key=row["metric_key"],
        display_name=row["display_name"],
        category=AnalyticsMetricCategory(row["category"]),
        unit=row["unit"],
        value_type=AnalyticsValueType(row["value_type"]),
        aggregation_type=AnalyticsAggregationType(row["aggregation_type"]),
        higher_is_better=bool(row["higher_is_better"]) if row["higher_is_better"] is not None else None,
        description=row["description"],
        aliases_json=row["aliases_json"],
        applicability_json=row["applicability_json"] if "applicability_json" in row.keys() else "[]",
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_metric_snapshot(row: sqlite3.Row) -> AnalyticsMetricSnapshot:
    return AnalyticsMetricSnapshot(
        id=row["id"],
        publication_id=row["publication_id"],
        snapshot_date=row["snapshot_date"],
        captured_at=from_iso_z(row["captured_at"]) or utc_now(),
        metric_key=row["metric_key"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        source_import_id=row["source_import_id"],
        source_row_number=row["source_row_number"],
        is_derived=bool(row["is_derived"]),
        quality_status=AnalyticsQualityStatus(row["quality_status"]),
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        row_fingerprint=row["row_fingerprint"],
        dedupe_key=row["dedupe_key"],
    )


def _row_to_import(row: sqlite3.Row) -> AnalyticsImport:
    return AnalyticsImport(
        id=row["id"],
        creator_id=row["creator_id"],
        channel_id=row["channel_id"],
        platform=row["platform"],
        source_filename=row["source_filename"],
        source_path=row["source_path"],
        source_fingerprint=row["source_fingerprint"],
        source_type=AnalyticsSourceType(row["source_type"]),
        schema_version=row["schema_version"],
        status=AnalyticsImportStatus(row["status"]),
        total_rows=row["total_rows"],
        accepted_rows=row["accepted_rows"],
        rejected_rows=row["rejected_rows"],
        warning_rows=row["warning_rows"],
        duplicate_rows=row["duplicate_rows"],
        source_sheet_name=row["source_sheet_name"],
        timezone_name=row["timezone_name"],
        delimiter=row["delimiter"],
        mapping_json=row["mapping_json"],
        report_path=row["report_path"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_import_row(row: sqlite3.Row) -> AnalyticsImportRow:
    return AnalyticsImportRow(
        id=row["id"],
        import_id=row["import_id"],
        row_number=row["row_number"],
        raw_json=row["raw_json"],
        normalized_json=row["normalized_json"],
        status=AnalyticsImportRowStatus(row["status"]),
        publication_id=row["publication_id"],
        warning_codes_json=row["warning_codes_json"],
        error_codes_json=row["error_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        row_fingerprint=row["row_fingerprint"],
    )


def _row_to_mapping(row: sqlite3.Row) -> AnalyticsFieldMapping:
    return AnalyticsFieldMapping(
        id=row["id"],
        creator_id=row["creator_id"],
        platform=row["platform"],
        mapping_name=row["mapping_name"],
        source_field=row["source_field"],
        target_field=row["target_field"],
        transformation=row["transformation"],
        confidence=row["confidence"],
        mapping_origin=AnalyticsFieldMappingOrigin(row["mapping_origin"]),
        is_active=bool(row["is_active"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLiteAnalyticsRepository(AnalyticsRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_platform(self, platform: AnalyticsPlatform) -> AnalyticsPlatform:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_platforms (id, platform_key, display_name, status, created_at, updated_at)
                VALUES (:id, :platform_key, :display_name, :status, :created_at, :updated_at)
                ON CONFLICT(platform_key) DO UPDATE SET
                    display_name = excluded.display_name,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                platform.to_dict(),
            )
            row = connection.execute("SELECT * FROM analytics_platforms WHERE platform_key = ?", (platform.platform_key,)).fetchone()
        return _row_to_platform(row)

    def list_platforms(self) -> list[AnalyticsPlatform]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM analytics_platforms ORDER BY platform_key ASC").fetchall()
        return [_row_to_platform(row) for row in rows]

    def get_platform_by_key(self, platform_key: str) -> AnalyticsPlatform | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_platforms WHERE platform_key = ?", (platform_key,)).fetchone()
        return _row_to_platform(row) if row else None

    def upsert_channel(self, channel: AnalyticsChannel) -> AnalyticsChannel:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_channels (
                    id, creator_id, platform_id, external_channel_id, channel_name,
                    channel_url, timezone_name, is_primary, metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform_id, :external_channel_id, :channel_name,
                    :channel_url, :timezone_name, :is_primary, :metadata_json, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, platform_id, channel_name) DO UPDATE SET
                    external_channel_id = excluded.external_channel_id,
                    channel_url = excluded.channel_url,
                    timezone_name = excluded.timezone_name,
                    is_primary = excluded.is_primary,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                {
                    **channel.to_dict(),
                    "is_primary": 1 if channel.is_primary else 0,
                },
            )
            row = connection.execute(
                "SELECT c.*, p.platform_key FROM analytics_channels c JOIN analytics_platforms p ON p.id = c.platform_id WHERE c.creator_id = ? AND c.platform_id = ? AND c.channel_name = ?",
                (channel.creator_id, channel.platform_id, channel.channel_name),
            ).fetchone()
        return _row_to_channel(row)

    def list_channels(self, creator_id: str) -> list[AnalyticsChannel]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*, p.platform_key
                FROM analytics_channels c
                JOIN analytics_platforms p ON p.id = c.platform_id
                WHERE c.creator_id = ?
                ORDER BY c.is_primary DESC, c.updated_at DESC
                """,
                (creator_id,),
            ).fetchall()
        return [_row_to_channel(row) for row in rows]

    def get_channel_by_id(self, channel_id: str) -> AnalyticsChannel | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT c.*, p.platform_key FROM analytics_channels c JOIN analytics_platforms p ON p.id = c.platform_id WHERE c.id = ?",
                (channel_id,),
            ).fetchone()
        return _row_to_channel(row) if row else None

    def upsert_publication(self, publication: AnalyticsPublication) -> AnalyticsPublication:
        with self._database.connect() as connection:
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
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    video_asset_id = excluded.video_asset_id,
                    external_publication_id = excluded.external_publication_id,
                    content_type = excluded.content_type,
                    title = excluded.title,
                    description = excluded.description,
                    published_at = excluded.published_at,
                    duration_seconds = excluded.duration_seconds,
                    url = excluded.url,
                    thumbnail_path = excluded.thumbnail_path,
                    status = excluded.status,
                    source_type = excluded.source_type,
                    source_fingerprint = excluded.source_fingerprint,
                    updated_at = excluded.updated_at
                """,
                publication.to_dict() | {"content_type": publication.content_type.value, "source_type": publication.source_type.value},
            )
            row = connection.execute("SELECT * FROM analytics_publications WHERE dedupe_key = ?", (publication.dedupe_key,)).fetchone()
        return _row_to_publication(row)

    def list_publications(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsPublication]:
        filters = filters or {}
        query = ["SELECT * FROM analytics_publications WHERE creator_id = ?"]
        params: list[object] = [creator_id]
        if platform := filters.get("platform"):
            query.append("AND platform = ?")
            params.append(platform)
        if channel_id := filters.get("channel_id"):
            query.append("AND channel_id = ?")
            params.append(channel_id)
        if content_type := filters.get("content_type"):
            query.append("AND content_type = ?")
            params.append(content_type if isinstance(content_type, str) else content_type.value)
        if date_from := filters.get("date_from"):
            query.append("AND published_at >= ?")
            params.append(str(date_from))
        if date_to := filters.get("date_to"):
            query.append("AND published_at <= ?")
            params.append(str(date_to))
        if linked := filters.get("linked"):
            query.append("AND video_asset_id IS NOT NULL" if linked else "AND video_asset_id IS NULL")
        status = filters.get("status")
        if status:
            query.append("AND status = ?")
            params.append(status)
        query.append("ORDER BY published_at DESC, updated_at DESC")
        with self._database.connect() as connection:
            rows = connection.execute(" ".join(query), tuple(params)).fetchall()
        return [_row_to_publication(row) for row in rows]

    def get_publication_by_id(self, publication_id: str) -> AnalyticsPublication | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_publications WHERE id = ?", (publication_id,)).fetchone()
        return _row_to_publication(row) if row else None

    def get_publication_by_dedupe_key(self, dedupe_key: str) -> AnalyticsPublication | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_publications WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
        return _row_to_publication(row) if row else None

    def upsert_metric_definition(self, metric_definition: AnalyticsMetricDefinition) -> AnalyticsMetricDefinition:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_metric_definitions (
                    id, metric_key, display_name, category, unit, value_type,
                    aggregation_type, higher_is_better, description, aliases_json, applicability_json, created_at
                ) VALUES (
                    :id, :metric_key, :display_name, :category, :unit, :value_type,
                    :aggregation_type, :higher_is_better, :description, :aliases_json, :applicability_json, :created_at
                )
                ON CONFLICT(metric_key) DO UPDATE SET
                    display_name = excluded.display_name,
                    category = excluded.category,
                    unit = excluded.unit,
                    value_type = excluded.value_type,
                    aggregation_type = excluded.aggregation_type,
                    higher_is_better = excluded.higher_is_better,
                    description = excluded.description,
                    aliases_json = excluded.aliases_json,
                    applicability_json = excluded.applicability_json
                """,
                metric_definition.to_dict() | {"category": metric_definition.category.value, "value_type": metric_definition.value_type.value, "aggregation_type": metric_definition.aggregation_type.value, "higher_is_better": None if metric_definition.higher_is_better is None else (1 if metric_definition.higher_is_better else 0)},
            )
            row = connection.execute("SELECT * FROM analytics_metric_definitions WHERE metric_key = ?", (metric_definition.metric_key,)).fetchone()
        return _row_to_metric_definition(row)

    def list_metric_definitions(self) -> list[AnalyticsMetricDefinition]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM analytics_metric_definitions ORDER BY metric_key ASC").fetchall()
        return [_row_to_metric_definition(row) for row in rows]

    def get_metric_definition_by_key(self, metric_key: str) -> AnalyticsMetricDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_metric_definitions WHERE metric_key = ?", (metric_key,)).fetchone()
        return _row_to_metric_definition(row) if row else None

    def upsert_metric_snapshot(self, snapshot: AnalyticsMetricSnapshot) -> AnalyticsMetricSnapshot:
        with self._database.connect() as connection:
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
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    is_derived = excluded.is_derived,
                    quality_status = excluded.quality_status,
                    warning_codes_json = excluded.warning_codes_json,
                    row_fingerprint = excluded.row_fingerprint
                """,
                snapshot.to_dict() | {"quality_status": snapshot.quality_status.value, "is_derived": 1 if snapshot.is_derived else 0},
            )
            row = connection.execute("SELECT * FROM analytics_metric_snapshots WHERE dedupe_key = ?", (snapshot.dedupe_key,)).fetchone()
        return _row_to_metric_snapshot(row)

    def list_metric_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM analytics_metric_snapshots WHERE publication_id = ? ORDER BY captured_at ASC, metric_key ASC", (publication_id,)).fetchall()
        return [_row_to_metric_snapshot(row) for row in rows]

    def get_latest_metric_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.*
                FROM analytics_metric_snapshots s
                INNER JOIN (
                    SELECT metric_key, MAX(captured_at) AS max_captured_at
                    FROM analytics_metric_snapshots
                    WHERE publication_id = ?
                    GROUP BY metric_key
                ) latest
                ON latest.metric_key = s.metric_key AND latest.max_captured_at = s.captured_at
                WHERE s.publication_id = ?
                ORDER BY s.metric_key ASC
                """,
                (publication_id, publication_id),
            ).fetchall()
        return [_row_to_metric_snapshot(row) for row in rows]

    def upsert_import(self, import_record: AnalyticsImport) -> AnalyticsImport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_imports (
                    id, creator_id, channel_id, platform, source_filename, source_path,
                    source_fingerprint, source_type, schema_version, status, total_rows,
                    accepted_rows, rejected_rows, warning_rows, duplicate_rows,
                    source_sheet_name, timezone_name, delimiter, mapping_json, report_path,
                    started_at, completed_at, error_code, error_message, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :channel_id, :platform, :source_filename, :source_path,
                    :source_fingerprint, :source_type, :schema_version, :status, :total_rows,
                    :accepted_rows, :rejected_rows, :warning_rows, :duplicate_rows,
                    :source_sheet_name, :timezone_name, :delimiter, :mapping_json, :report_path,
                    :started_at, :completed_at, :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    platform = excluded.platform,
                    source_filename = excluded.source_filename,
                    source_path = excluded.source_path,
                    source_fingerprint = excluded.source_fingerprint,
                    source_type = excluded.source_type,
                    schema_version = excluded.schema_version,
                    status = excluded.status,
                    total_rows = excluded.total_rows,
                    accepted_rows = excluded.accepted_rows,
                    rejected_rows = excluded.rejected_rows,
                    warning_rows = excluded.warning_rows,
                    duplicate_rows = excluded.duplicate_rows,
                    source_sheet_name = excluded.source_sheet_name,
                    timezone_name = excluded.timezone_name,
                    delimiter = excluded.delimiter,
                    mapping_json = excluded.mapping_json,
                    report_path = excluded.report_path,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                import_record.to_dict() | {"source_type": import_record.source_type.value, "status": import_record.status.value},
            )
            row = connection.execute("SELECT * FROM analytics_imports WHERE id = ?", (import_record.id,)).fetchone()
        return _row_to_import(row)

    def get_import_by_id(self, import_id: str) -> AnalyticsImport | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_imports WHERE id = ?", (import_id,)).fetchone()
        return _row_to_import(row) if row else None

    def list_imports(self, creator_id: str) -> list[AnalyticsImport]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM analytics_imports WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,)).fetchall()
        return [_row_to_import(row) for row in rows]

    def get_import_by_fingerprint(self, source_fingerprint: str) -> AnalyticsImport | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_imports WHERE source_fingerprint = ? ORDER BY created_at DESC LIMIT 1", (source_fingerprint,)).fetchone()
        return _row_to_import(row) if row else None

    def upsert_import_row(self, row: AnalyticsImportRow) -> AnalyticsImportRow:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_import_rows (
                    id, import_id, row_number, raw_json, normalized_json, status,
                    publication_id, warning_codes_json, error_codes_json, created_at, row_fingerprint
                ) VALUES (
                    :id, :import_id, :row_number, :raw_json, :normalized_json, :status,
                    :publication_id, :warning_codes_json, :error_codes_json, :created_at, :row_fingerprint
                )
                ON CONFLICT(import_id, row_number, row_fingerprint) DO UPDATE SET
                    raw_json = excluded.raw_json,
                    normalized_json = excluded.normalized_json,
                    status = excluded.status,
                    publication_id = excluded.publication_id,
                    warning_codes_json = excluded.warning_codes_json,
                    error_codes_json = excluded.error_codes_json
                """,
                row.to_dict() | {"status": row.status.value, "created_at": row.created_at.isoformat()},
            )
            row_data = connection.execute("SELECT * FROM analytics_import_rows WHERE id = ?", (row.id,)).fetchone()
        return _row_to_import_row(row_data)

    def list_import_rows(self, import_id: str, *, status: str | None = None) -> list[AnalyticsImportRow]:
        query = "SELECT * FROM analytics_import_rows WHERE import_id = ?"
        params: list[object] = [import_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY row_number ASC"
        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row_to_import_row(row) for row in rows]

    def upsert_field_mapping(self, mapping: AnalyticsFieldMapping) -> AnalyticsFieldMapping:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_field_mappings (
                    id, creator_id, platform, mapping_name, source_field, target_field,
                    transformation, confidence, mapping_origin, is_active, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :platform, :mapping_name, :source_field, :target_field,
                    :transformation, :confidence, :mapping_origin, :is_active, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    mapping_name = excluded.mapping_name,
                    source_field = excluded.source_field,
                    target_field = excluded.target_field,
                    transformation = excluded.transformation,
                    confidence = excluded.confidence,
                    mapping_origin = excluded.mapping_origin,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                mapping.to_dict() | {"mapping_origin": mapping.mapping_origin.value, "is_active": 1 if mapping.is_active else 0},
            )
            row = connection.execute("SELECT * FROM analytics_field_mappings WHERE id = ?", (mapping.id,)).fetchone()
        return _row_to_mapping(row)

    def list_field_mappings(self, *, creator_id: str | None = None, platform: str | None = None, active_only: bool = False) -> list[AnalyticsFieldMapping]:
        query = "SELECT * FROM analytics_field_mappings WHERE 1=1"
        params: list[object] = []
        if creator_id is not None:
            query += " AND (creator_id = ? OR creator_id IS NULL)"
            params.append(creator_id)
        if platform is not None:
            query += " AND platform = ?"
            params.append(platform)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY updated_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row_to_mapping(row) for row in rows]

    def get_field_mapping(self, mapping_id: str) -> AnalyticsFieldMapping | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_field_mappings WHERE id = ?", (mapping_id,)).fetchone()
        return _row_to_mapping(row) if row else None
