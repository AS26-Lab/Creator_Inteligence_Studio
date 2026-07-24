"""Entidades persistidas para analytics manual y aprendizaje."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
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


@dataclass(frozen=True, slots=True)
class AnalyticsPlatform:
    id: str
    platform_key: str
    display_name: str
    status: AnalyticsPlatformStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "platform_key": self.platform_key,
            "display_name": self.display_name,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsChannel:
    id: str
    creator_id: str
    platform_id: str
    platform_key: str
    external_channel_id: str | None
    channel_name: str
    channel_url: str | None
    timezone_name: str
    is_primary: bool
    metadata_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform_id": self.platform_id,
            "platform_key": self.platform_key,
            "external_channel_id": self.external_channel_id,
            "channel_name": self.channel_name,
            "channel_url": self.channel_url,
            "timezone_name": self.timezone_name,
            "is_primary": self.is_primary,
            "metadata_json": self.metadata_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsPublication:
    id: str
    creator_id: str
    channel_id: str | None
    video_asset_id: str | None
    external_publication_id: str | None
    platform: str
    content_type: AnalyticsContentType
    title: str
    description: str | None
    published_at: datetime
    duration_seconds: float | None
    url: str | None
    thumbnail_path: str | None
    status: str
    source_type: AnalyticsSourceType
    source_fingerprint: str
    dedupe_key: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "channel_id": self.channel_id,
            "video_asset_id": self.video_asset_id,
            "external_publication_id": self.external_publication_id,
            "platform": self.platform,
            "content_type": self.content_type.value,
            "title": self.title,
            "description": self.description,
            "published_at": to_iso_z(self.published_at),
            "duration_seconds": self.duration_seconds,
            "url": self.url,
            "thumbnail_path": self.thumbnail_path,
            "status": self.status,
            "source_type": self.source_type.value,
            "source_fingerprint": self.source_fingerprint,
            "dedupe_key": self.dedupe_key,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsMetricDefinition:
    id: str
    metric_key: str
    display_name: str
    category: AnalyticsMetricCategory
    unit: str
    value_type: AnalyticsValueType
    aggregation_type: AnalyticsAggregationType
    higher_is_better: bool | None
    description: str
    aliases_json: str
    applicability_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "metric_key": self.metric_key,
            "display_name": self.display_name,
            "category": self.category.value,
            "unit": self.unit,
            "value_type": self.value_type.value,
            "aggregation_type": self.aggregation_type.value,
            "higher_is_better": self.higher_is_better,
            "description": self.description,
            "aliases_json": self.aliases_json,
            "applicability_json": self.applicability_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsMetricSnapshot:
    id: str
    publication_id: str
    snapshot_date: str
    captured_at: datetime
    metric_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    source_import_id: str
    source_row_number: int | None
    is_derived: bool
    quality_status: AnalyticsQualityStatus
    warning_codes_json: str
    created_at: datetime
    row_fingerprint: str
    dedupe_key: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "publication_id": self.publication_id,
            "snapshot_date": self.snapshot_date,
            "captured_at": to_iso_z(self.captured_at),
            "metric_key": self.metric_key,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "source_import_id": self.source_import_id,
            "source_row_number": self.source_row_number,
            "is_derived": self.is_derived,
            "quality_status": self.quality_status.value,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
            "row_fingerprint": self.row_fingerprint,
            "dedupe_key": self.dedupe_key,
        }


@dataclass(frozen=True, slots=True)
class AnalyticsImport:
    id: str
    creator_id: str
    channel_id: str | None
    platform: str
    source_filename: str
    source_path: str | None
    source_fingerprint: str
    source_type: AnalyticsSourceType
    schema_version: str
    status: AnalyticsImportStatus
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    warning_rows: int
    duplicate_rows: int
    source_sheet_name: str | None
    timezone_name: str | None
    delimiter: str | None
    mapping_json: str
    report_path: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "channel_id": self.channel_id,
            "platform": self.platform,
            "source_filename": self.source_filename,
            "source_path": self.source_path,
            "source_fingerprint": self.source_fingerprint,
            "source_type": self.source_type.value,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "total_rows": self.total_rows,
            "accepted_rows": self.accepted_rows,
            "rejected_rows": self.rejected_rows,
            "warning_rows": self.warning_rows,
            "duplicate_rows": self.duplicate_rows,
            "source_sheet_name": self.source_sheet_name,
            "timezone_name": self.timezone_name,
            "delimiter": self.delimiter,
            "mapping_json": self.mapping_json,
            "report_path": self.report_path,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsImportRow:
    id: str
    import_id: str
    row_number: int
    raw_json: str
    normalized_json: str | None
    status: AnalyticsImportRowStatus
    publication_id: str | None
    warning_codes_json: str
    error_codes_json: str
    created_at: datetime
    row_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "import_id": self.import_id,
            "row_number": self.row_number,
            "raw_json": self.raw_json,
            "normalized_json": self.normalized_json,
            "status": self.status.value,
            "publication_id": self.publication_id,
            "warning_codes_json": self.warning_codes_json,
            "error_codes_json": self.error_codes_json,
            "created_at": to_iso_z(self.created_at),
            "row_fingerprint": self.row_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class AnalyticsFieldMapping:
    id: str
    creator_id: str | None
    platform: str
    mapping_name: str
    source_field: str
    target_field: str
    transformation: str
    confidence: float
    mapping_origin: AnalyticsFieldMappingOrigin
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform,
            "mapping_name": self.mapping_name,
            "source_field": self.source_field,
            "target_field": self.target_field,
            "transformation": self.transformation,
            "confidence": self.confidence,
            "mapping_origin": self.mapping_origin.value,
            "is_active": self.is_active,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }
