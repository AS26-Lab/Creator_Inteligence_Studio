"""Servicio de aplicacion para la foundation de analytics manual."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.domain.analytics.errors import AnalyticsImportError
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
from creator_intelligence_studio.domain.analytics.metric_definitions import default_metric_definitions
from creator_intelligence_studio.domain.analytics.repositories import AnalyticsRepository
from creator_intelligence_studio.domain.analytics.services import (
    build_import_fingerprint,
    build_metric_snapshot_dedupe_key,
    build_publication_dedupe_key,
    build_row_fingerprint,
    normalize_content_type,
    normalize_key,
    normalize_platform_key,
    normalize_text,
    normalize_url,
    platform_defaults,
)
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
    PLATFORM_PRESETS,
)
from creator_intelligence_studio.infrastructure.analytics.csv_importer import load_csv_table
from creator_intelligence_studio.infrastructure.analytics.date_normalizer import normalize_date
from creator_intelligence_studio.infrastructure.analytics.excel_importer import load_xlsx_table
from creator_intelligence_studio.infrastructure.analytics.field_mapper import (
    FieldMappingPlan,
    build_field_mapping,
)
from creator_intelligence_studio.infrastructure.analytics.import_report_builder import (
    build_import_report_json,
    build_import_report_txt,
    write_import_report,
)
from creator_intelligence_studio.infrastructure.analytics.import_validator import validate_row
from creator_intelligence_studio.infrastructure.analytics.metric_normalizer import normalize_metric_value
from creator_intelligence_studio.infrastructure.analytics.models import (
    AnalyticsExportResult,
    ImportReportSummary,
    NormalizedMetricValue,
    NormalizedRow,
    RowValidationIssue,
    SchemaDetectionResult,
)
from creator_intelligence_studio.infrastructure.analytics.schema_detector import detect_schema
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import (
    SQLiteAnalyticsRepository,
)
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc_iso_now() -> str:
    return utc_now().isoformat()


def _csv_safe_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] in "=+-@" and not (stripped.startswith("-") and stripped[1:].replace(".", "", 1).isdigit()):
        if not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
            return "'" + value
    return value


def _mapping_plan_payload(plan: FieldMappingPlan) -> dict[str, object]:
    return {
        "mapping_name": plan.mapping_name,
        "platform": plan.platform,
        "creator_id": plan.creator_id,
        "mappings": [
            {
                "source_field": mapping.source_field,
                "target_field": mapping.target_field,
                "transformation": mapping.transformation,
                "confidence": mapping.confidence,
                "mapping_origin": mapping.mapping_origin.value,
                "is_active": mapping.is_active,
            }
            for mapping in plan.mappings
        ],
    }


@dataclass(frozen=True, slots=True)
class AnalyticsImportResult:
    import_record: AnalyticsImport
    summary: ImportReportSummary
    report_json: str
    report_txt: str
    report: AnalyticsExportResult
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    reused: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "import_record": self.import_record.to_dict(),
            "summary": self.summary.to_dict(),
            "report_json": self.report_json,
            "report_txt": self.report_txt,
            "report": self.report.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "reused": self.reused,
        }


class AnalyticsImportService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        catalog_service: CatalogService,
        repository: AnalyticsRepository,
        database: SQLiteDatabase,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.catalog_service = catalog_service
        self.repository = repository
        self.database = database
        self.logger = logger or logging.getLogger("creator_intelligence_studio.analytics")
        self._output_root = self.paths.data_directory / "analytics"
        self._ensure_seed_data()

    def _ensure_seed_data(self) -> None:
        now = utc_now()
        for preset in PLATFORM_PRESETS:
            platform = AnalyticsPlatform(
                id=str(uuid4()),
                platform_key=preset.platform_key,
                display_name=preset.display_name,
                status=AnalyticsPlatformStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            existing = self.repository.get_platform_by_key(platform.platform_key)
            if existing is None:
                self.repository.upsert_platform(platform)
        for spec in default_metric_definitions():
            self.repository.upsert_metric_definition(
                AnalyticsMetricDefinition(
                    id=str(uuid4()),
                    metric_key=spec.metric_key,
                    display_name=spec.display_name,
                    category=spec.category,
                    unit=spec.unit,
                    value_type=spec.value_type,
                    aggregation_type=spec.aggregation_type,
                    higher_is_better=spec.higher_is_better,
                    description=spec.description,
                    aliases_json=_json_dumps(spec.aliases),
                    applicability_json=_json_dumps(spec.applicability),
                    created_at=now,
                )
            )

    def _resolve_platform(self, platform_key: str | None) -> AnalyticsPlatform:
        if platform_key:
            normalized = normalize_platform_key(platform_key)
            existing = self.repository.get_platform_by_key(normalized)
            if existing is not None:
                return existing
        preset = next((item for item in PLATFORM_PRESETS if item.platform_key == (platform_key or "")), None)
        if preset is None:
            preset = next(item for item in PLATFORM_PRESETS if item.platform_key == "manual_other")
        platform = AnalyticsPlatform(
            id=str(uuid4()),
            platform_key=preset.platform_key,
            display_name=preset.display_name,
            status=AnalyticsPlatformStatus.ACTIVE,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_platform(platform)

    def list_platforms(self) -> list[AnalyticsPlatform]:
        return self.repository.list_platforms()

    def list_channels(self, creator_id: str) -> list[AnalyticsChannel]:
        return self.repository.list_channels(creator_id)

    def create_channel(
        self,
        *,
        creator_id: str,
        platform: str,
        name: str,
        external_channel_id: str | None = None,
        channel_url: str | None = None,
        timezone_name: str | None = None,
        is_primary: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> AnalyticsChannel:
        platform_row = self._resolve_platform(platform)
        channel = AnalyticsChannel(
            id=str(uuid4()),
            creator_id=creator_id,
            platform_id=platform_row.id,
            platform_key=platform_row.platform_key,
            external_channel_id=normalize_text(external_channel_id),
            channel_name=normalize_text(name) or "Canal",
            channel_url=normalize_url(channel_url),
            timezone_name=timezone_name or "UTC",
            is_primary=is_primary,
            metadata_json=_json_dumps(metadata or {}),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_channel(channel)

    def list_imports(self, creator_id: str) -> list[AnalyticsImport]:
        return self.repository.list_imports(creator_id)

    def get_import(self, import_id: str) -> AnalyticsImport | None:
        return self.repository.get_import_by_id(import_id)

    def get_import_rows(self, import_id: str, status: str | None = None) -> list[AnalyticsImportRow]:
        return self.repository.list_import_rows(import_id, status=status)

    def cancel_import(self, import_id: str) -> AnalyticsImport | None:
        import_record = self.repository.get_import_by_id(import_id)
        if import_record is None:
            return None
        updated = replace(
            import_record,
            status=AnalyticsImportStatus.INTERRUPTED,
            completed_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_import(updated)

    def retry_import(self, import_id: str) -> AnalyticsImport | None:
        import_record = self.repository.get_import_by_id(import_id)
        if import_record is None:
            return None
        updated = replace(
            import_record,
            status=AnalyticsImportStatus.QUEUED,
            started_at=utc_now(),
            completed_at=None,
            error_code=None,
            error_message=None,
            updated_at=utc_now(),
        )
        return self.repository.upsert_import(updated)

    def get_import_report_path(self, import_id: str) -> Path | None:
        import_record = self.repository.get_import_by_id(import_id)
        if import_record is None or import_record.report_path is None:
            return None
        return Path(import_record.report_path)

    def list_publications(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsPublication]:
        return self.repository.list_publications(creator_id, filters=filters)

    def get_publication(self, publication_id: str) -> AnalyticsPublication | None:
        return self.repository.get_publication_by_id(publication_id)

    def list_metric_snapshots(self, publication_id: str) -> list[AnalyticsMetricSnapshot]:
        return self.repository.list_metric_snapshots(publication_id)

    def get_latest_metrics(self, publication_id: str) -> dict[str, AnalyticsMetricSnapshot]:
        return {item.metric_key: item for item in self.repository.get_latest_metric_snapshots(publication_id)}

    def list_mappings(self, creator_id: str) -> list[AnalyticsFieldMapping]:
        return self.repository.list_field_mappings(creator_id=creator_id)

    def save_mapping(
        self,
        *,
        creator_id: str | None,
        platform: str,
        mapping_name: str,
        source_field: str,
        target_field: str,
        transformation: str = "identity",
        confidence: float = 1.0,
        active: bool = True,
        origin: AnalyticsFieldMappingOrigin = AnalyticsFieldMappingOrigin.MANUAL,
    ) -> AnalyticsFieldMapping:
        mapping = build_field_mapping(
            mapping_name=mapping_name,
            platform=platform,
            creator_id=creator_id,
            source_field=source_field,
            target_field=target_field,
            transformation=transformation,
            confidence=confidence,
            origin=origin,
            is_active=active,
            mapping_id=str(uuid4()),
        )
        return self.repository.upsert_field_mapping(mapping)

    def detect_schema(self, path: Path, *, sheet_name: str | None = None) -> SchemaDetectionResult:
        return detect_schema(path, sheet_name=sheet_name, max_bytes=25_000_000)

    def inspect_file(self, path: Path, *, sheet_name: str | None = None):
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            return load_xlsx_table(path, sheet_name=sheet_name, max_bytes=25_000_000)
        return load_csv_table(path, max_bytes=25_000_000)

    def _current_mapping_plan(self, *, creator_id: str, platform: str, mapping_name: str | None = None) -> FieldMappingPlan:
        mappings = self.repository.list_field_mappings(creator_id=creator_id, platform=platform, active_only=True)
        if mapping_name:
            mappings = [item for item in mappings if item.mapping_name == mapping_name]
        return FieldMappingPlan(
            mapping_name=mapping_name or "auto",
            platform=platform,
            creator_id=creator_id,
            mappings=tuple(mappings),
        )

    def _normalize_row(
        self,
        *,
        row_number: int,
        raw_row: dict[str, object],
        headers: tuple[str, ...],
        mapping_plan: FieldMappingPlan,
        platform: str,
        channel: AnalyticsChannel | None,
    ) -> NormalizedRow:
        mapping_by_source = {mapping.source_field: mapping for mapping in mapping_plan.mappings}
        publication_payload: dict[str, object] = {}
        metric_values: list[NormalizedMetricValue] = []
        warnings: list[str] = []
        errors: list[str] = []
        normalized_payload: dict[str, object] = {}
        for header in headers:
            raw_value = raw_row.get(header)
            mapping = mapping_by_source.get(header)
            target = mapping.target_field if mapping else normalize_key(header)
            normalized_payload[target] = raw_value
            if target in {
                "title",
                "description",
                "external_publication_id",
                "published_at",
                "duration_seconds",
                "url",
                "thumbnail_path",
                "platform",
                "content_type",
                "status",
                "source_type",
                "video_asset_id",
            }:
                publication_payload[target] = raw_value
                continue
            definition = self.repository.get_metric_definition_by_key(target)
            if definition is None:
                warnings.append("unknown_metric")
                continue
            normalized = normalize_metric_value(raw_value, target_unit=definition.unit)
            metric_values.append(
                NormalizedMetricValue(
                    metric_key=definition.metric_key,
                    numeric_value=normalized.numeric_value,
                    text_value=normalized.text_value,
                    unit=normalized.unit,
                    warnings=normalized.warning_codes,
                    errors=normalized.error_codes,
                )
            )
            warnings.extend(normalized.warning_codes)
            errors.extend(normalized.error_codes)
        publication_payload.setdefault("platform", platform)
        publication_payload.setdefault("content_type", AnalyticsContentType.OTHER.value)
        publication_payload.setdefault("status", "observed")
        title = normalize_text(str(publication_payload.get("title") or "")) or ""
        published_at_result = normalize_date(
            publication_payload.get("published_at"),
            timezone_name=channel.timezone_name if channel else "UTC",
        )
        if published_at_result.inferred_timezone:
            warnings.extend(published_at_result.warning_codes)
        publication_payload["published_at"] = published_at_result.value.isoformat() if published_at_result.value else None
        content_type = normalize_content_type(str(publication_payload.get("content_type") or "other"))
        publication_payload["content_type"] = content_type.value
        publication_payload["title"] = title
        if not title:
            errors.append("missing_required_field")
        publication_payload["url"] = normalize_url(str(publication_payload.get("url") or "")) if publication_payload.get("url") else None
        return NormalizedRow(
            row_number=row_number,
            raw_json=raw_row,
            normalized_json=normalized_payload,
            publication_key=None,
            publication_payload=publication_payload,
            metric_values=tuple(metric_values),
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
        )

    def import_csv(
        self,
        *,
        creator_id: str,
        file: Path,
        channel_id: str | None = None,
        platform: str | None = None,
        mapping_name: str | None = None,
        delimiter: str | None = None,
    ) -> AnalyticsImportResult:
        table = load_csv_table(file, max_bytes=25_000_000, delimiter=delimiter)
        return self._import_table(creator_id=creator_id, table=table, channel_id=channel_id, platform=platform, mapping_name=mapping_name)

    def import_excel(
        self,
        *,
        creator_id: str,
        file: Path,
        channel_id: str | None = None,
        platform: str | None = None,
        sheet_name: str | None = None,
        mapping_name: str | None = None,
    ) -> AnalyticsImportResult:
        table = load_xlsx_table(file, sheet_name=sheet_name, max_bytes=25_000_000)
        return self._import_table(creator_id=creator_id, table=table, channel_id=channel_id, platform=platform, mapping_name=mapping_name)

    def _import_table(
        self,
        *,
        creator_id: str,
        table,
        channel_id: str | None,
        platform: str | None,
        mapping_name: str | None,
    ) -> AnalyticsImportResult:
        channel = self.repository.get_channel_by_id(channel_id) if channel_id else None
        platform_row = self._resolve_platform(platform or (channel.platform_key if channel else None))
        mapping_plan = self._current_mapping_plan(creator_id=creator_id, platform=platform_row.platform_key, mapping_name=mapping_name)
        if not mapping_plan.mappings:
            schema = detect_schema(table.path, sheet_name=table.sheet_name, max_bytes=25_000_000)
            auto_mappings = tuple(
                build_field_mapping(
                    mapping_name="auto",
                    platform=platform_row.platform_key,
                    creator_id=creator_id,
                    source_field=suggestion.source_field,
                    target_field=suggestion.target_field,
                    transformation=suggestion.transformation,
                    confidence=suggestion.confidence,
                    origin=AnalyticsFieldMappingOrigin.AUTO,
                    is_active=True,
                    mapping_id=str(uuid4()),
                )
                for suggestion in schema.suggestions
            )
            if auto_mappings:
                mapping_plan = FieldMappingPlan(
                    mapping_name="auto",
                    platform=platform_row.platform_key,
                    creator_id=creator_id,
                    mappings=auto_mappings,
                )
        mapping_json = _json_dumps(_mapping_plan_payload(mapping_plan))
        source_fingerprint = build_import_fingerprint(
            table.path.read_bytes(),
            mapping_json=mapping_json,
            platform=platform_row.platform_key,
        )
        existing_import = self.repository.get_import_by_fingerprint(source_fingerprint)
        if existing_import is not None and existing_import.mapping_json == mapping_json:
            summary = ImportReportSummary(
                import_id=existing_import.id,
                creator_id=creator_id,
                platform=platform_row.platform_key,
                channel_id=channel_id,
                source_filename=table.source_filename,
                source_fingerprint=source_fingerprint,
                source_type=table.source_type,
                status=existing_import.status.value,
                total_rows=existing_import.total_rows,
                accepted_rows=existing_import.accepted_rows,
                rejected_rows=existing_import.rejected_rows,
                warning_rows=existing_import.warning_rows,
                duplicate_rows=existing_import.duplicate_rows,
                publications_created=0,
                publications_updated=0,
                snapshots_created=0,
                metric_unknown_rows=0,
                duration_seconds=None,
                mapping_name=mapping_name,
                report_path=existing_import.report_path,
                warnings=("reused_import",),
                errors=(),
                examples=(),
            )
            report = AnalyticsExportResult(format="json", path=existing_import.report_path or "", row_count=existing_import.total_rows)
            return AnalyticsImportResult(existing_import, summary, build_import_report_json(summary), build_import_report_txt(summary), report, summary.warnings, summary.errors, True)
        now = utc_now()
        import_record = AnalyticsImport(
            id=str(uuid4()),
            creator_id=creator_id,
            channel_id=channel_id,
            platform=platform_row.platform_key,
            source_filename=table.source_filename,
            source_path=str(table.path),
            source_fingerprint=source_fingerprint,
            source_type=AnalyticsSourceType(table.source_type),
            schema_version="v15",
            status=AnalyticsImportStatus.RUNNING,
            total_rows=len(table.rows),
            accepted_rows=0,
            rejected_rows=0,
            warning_rows=0,
            duplicate_rows=0,
            source_sheet_name=table.sheet_name,
            timezone_name=channel.timezone_name if channel else "UTC",
            delimiter=table.delimiter,
            mapping_json=mapping_json,
            report_path=None,
            started_at=now,
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self.repository.upsert_import(import_record)
        seen_snapshots: set[str] = set()
        summary_examples: list[dict[str, object]] = []
        import_rows: list[AnalyticsImportRow] = []
        publications_created = 0
        publications_updated = 0
        snapshots_created = 0
        metric_unknown_rows = 0
        summary_warning_set: set[str] = set()
        summary_error_set: set[str] = set()
        try:
            for index, raw_row in enumerate(table.rows, start=1):
                normalized = self._normalize_row(
                    row_number=index,
                    raw_row=raw_row,
                    headers=table.headers,
                    mapping_plan=mapping_plan,
                    platform=platform_row.platform_key,
                    channel=channel,
                )
                validation = validate_row(
                    publication_payload=normalized.publication_payload,
                    content_type=normalize_content_type(str(normalized.publication_payload.get("content_type") if normalized.publication_payload else None)),
                    published_at=normalize_date(normalized.publication_payload.get("published_at") if normalized.publication_payload else None).value if normalized.publication_payload else None,
                    warnings=list(normalized.warnings),
                    errors=list(normalized.errors),
                )
                summary_warning_set.update(validation.warning_codes)
                summary_error_set.update(validation.error_codes)
                row_fingerprint = build_row_fingerprint(normalized.normalized_json | {"row_number": index})
                publication = None
                if validation.status != AnalyticsImportRowStatus.REJECTED and normalized.publication_payload is not None:
                    dedupe_key = build_publication_dedupe_key(
                        platform=platform_row.platform_key,
                        external_publication_id=str(normalized.publication_payload.get("external_publication_id") or ""),
                        url=str(normalized.publication_payload.get("url") or ""),
                        title=str(normalized.publication_payload.get("title") or ""),
                        published_at=normalize_date(normalized.publication_payload.get("published_at")).value,
                        channel_id=channel.id if channel else None,
                    )
                    publication = self.repository.get_publication_by_dedupe_key(dedupe_key)
                    if publication is None:
                        publication = self.repository.upsert_publication(
                            AnalyticsPublication(
                                id=str(uuid4()),
                                creator_id=creator_id,
                                channel_id=channel.id if channel else None,
                                video_asset_id=normalized.publication_payload.get("video_asset_id"),
                                external_publication_id=normalize_text(str(normalized.publication_payload.get("external_publication_id") or "")),
                                platform=platform_row.platform_key,
                                content_type=normalize_content_type(str(normalized.publication_payload.get("content_type") or "other")),
                                title=str(normalized.publication_payload.get("title") or ""),
                                description=normalize_text(str(normalized.publication_payload.get("description") or "")),
                                published_at=normalize_date(normalized.publication_payload.get("published_at")).value or utc_now(),
                                duration_seconds=float(normalized.publication_payload.get("duration_seconds")) if normalized.publication_payload.get("duration_seconds") not in (None, "") else None,
                                url=normalize_url(str(normalized.publication_payload.get("url") or "")),
                                thumbnail_path=normalize_text(str(normalized.publication_payload.get("thumbnail_path") or "")),
                                status="observed",
                                source_type=AnalyticsSourceType(table.source_type),
                                source_fingerprint=source_fingerprint,
                                dedupe_key=dedupe_key,
                                created_at=utc_now(),
                                updated_at=utc_now(),
                            )
                        )
                        publications_created += 1
                    else:
                        publications_updated += 1
                    for metric in normalized.metric_values:
                        if metric.numeric_value is None and metric.text_value is None:
                            continue
                        snapshot_dedupe_key = build_metric_snapshot_dedupe_key(
                            {
                                "publication_id": publication.id,
                                "snapshot_date": publication.published_at.date().isoformat(),
                                "captured_at": publication.updated_at.isoformat(),
                                "metric_key": metric.metric_key,
                                "numeric_value": metric.numeric_value,
                                "text_value": metric.text_value,
                                "unit": metric.unit,
                                "source_import_id": import_record.id,
                                "source_row_number": index,
                            }
                        )
                        if snapshot_dedupe_key in seen_snapshots:
                            validation = replace(validation, status=AnalyticsImportRowStatus.DUPLICATE)
                            continue
                        seen_snapshots.add(snapshot_dedupe_key)
                        self.repository.upsert_metric_snapshot(
                            AnalyticsMetricSnapshot(
                                id=str(uuid4()),
                                publication_id=publication.id,
                                snapshot_date=publication.published_at.date().isoformat(),
                                captured_at=utc_now(),
                                metric_key=metric.metric_key,
                                numeric_value=metric.numeric_value,
                                text_value=metric.text_value,
                                unit=metric.unit,
                                source_import_id=import_record.id,
                                source_row_number=index,
                                is_derived=False,
                                quality_status=AnalyticsQualityStatus(validation.status.value),
                                warning_codes_json=_json_dumps(metric.warnings),
                                created_at=utc_now(),
                                row_fingerprint=row_fingerprint,
                                dedupe_key=snapshot_dedupe_key,
                            )
                        )
                        snapshots_created += 1
                row_record = AnalyticsImportRow(
                    id=str(uuid4()),
                    import_id=import_record.id,
                    row_number=index,
                    raw_json=_json_dumps(raw_row),
                    normalized_json=_json_dumps(normalized.normalized_json),
                    status=validation.status,
                    publication_id=publication.id if publication else None,
                    warning_codes_json=_json_dumps(validation.warning_codes),
                    error_codes_json=_json_dumps(validation.error_codes),
                    created_at=utc_now(),
                    row_fingerprint=row_fingerprint,
                )
                self.repository.upsert_import_row(row_record)
                import_rows.append(row_record)
                if validation.status == AnalyticsImportRowStatus.ACCEPTED:
                    import_record = replace(import_record, accepted_rows=import_record.accepted_rows + 1)
                elif validation.status == AnalyticsImportRowStatus.ACCEPTED_WITH_WARNINGS:
                    import_record = replace(import_record, accepted_rows=import_record.accepted_rows + 1, warning_rows=import_record.warning_rows + 1)
                elif validation.status == AnalyticsImportRowStatus.REJECTED:
                    import_record = replace(import_record, rejected_rows=import_record.rejected_rows + 1)
                elif validation.status == AnalyticsImportRowStatus.DUPLICATE:
                    import_record = replace(import_record, duplicate_rows=import_record.duplicate_rows + 1)
                if validation.warning_codes:
                    metric_unknown_rows += int("unknown_metric" in validation.warning_codes)
                if len(summary_examples) < 5 and (validation.warning_codes or validation.error_codes):
                    summary_examples.append(
                        {
                            "row_number": index,
                            "warnings": list(validation.warning_codes),
                            "errors": list(validation.error_codes),
                        }
                    )
        except Exception as exc:
            failed = replace(
                import_record,
                status=AnalyticsImportStatus.FAILED,
                completed_at=utc_now(),
                error_code=type(exc).__name__,
                error_message=str(exc),
                updated_at=utc_now(),
            )
            self.repository.upsert_import(failed)
            raise AnalyticsImportError(f"La importacion de analytics fallo: {exc}") from exc
        final_status = AnalyticsImportStatus.COMPLETED_WITH_WARNINGS if import_record.warning_rows or import_record.rejected_rows or import_record.duplicate_rows else AnalyticsImportStatus.COMPLETED
        completed = replace(
            import_record,
            status=final_status,
            completed_at=utc_now(),
            updated_at=utc_now(),
            report_path=str(self._output_root / f"{import_record.id}.json"),
            accepted_rows=import_record.accepted_rows,
            rejected_rows=import_record.rejected_rows,
            warning_rows=import_record.warning_rows,
            duplicate_rows=import_record.duplicate_rows,
        )
        self.repository.upsert_import(completed)
        summary = ImportReportSummary(
            import_id=completed.id,
            creator_id=creator_id,
            platform=platform_row.platform_key,
            channel_id=channel_id,
            source_filename=table.source_filename,
            source_fingerprint=source_fingerprint,
            source_type=table.source_type,
            status=completed.status.value,
            total_rows=len(table.rows),
            accepted_rows=completed.accepted_rows,
            rejected_rows=completed.rejected_rows,
            warning_rows=completed.warning_rows,
            duplicate_rows=completed.duplicate_rows,
            publications_created=publications_created,
            publications_updated=publications_updated,
            snapshots_created=snapshots_created,
            metric_unknown_rows=metric_unknown_rows,
            duration_seconds=None,
            mapping_name=mapping_name or "auto",
            report_path=completed.report_path,
            warnings=tuple(sorted(summary_warning_set)),
            errors=tuple(sorted(summary_error_set)),
            examples=tuple(summary_examples),
        )
        report_path = self._output_root / f"{completed.id}.json"
        report = write_import_report(report_path, summary, format_name="json")
        return AnalyticsImportResult(
            import_record=completed,
            summary=summary,
            report_json=build_import_report_json(summary),
            report_txt=build_import_report_txt(summary),
            report=report,
            warnings=summary.warnings,
            errors=summary.errors,
            reused=False,
        )


class AnalyticsQueryService:
    def __init__(self, import_service: AnalyticsImportService) -> None:
        self.import_service = import_service

    def list_platforms(self):
        return self.import_service.list_platforms()

    def list_channels(self, creator_id: str):
        return self.import_service.list_channels(creator_id)

    def list_publications(self, creator_id: str, *, filters: dict[str, object] | None = None):
        return self.import_service.list_publications(creator_id, filters=filters)

    def get_publication(self, publication_id: str):
        return self.import_service.get_publication(publication_id)

    def list_publication_snapshots(self, publication_id: str):
        return self.import_service.list_metric_snapshots(publication_id)

    def get_latest_metrics(self, publication_id: str):
        return self.import_service.get_latest_metrics(publication_id)

    def list_imports(self, creator_id: str):
        return self.import_service.list_imports(creator_id)

    def get_import(self, import_id: str):
        return self.import_service.get_import(import_id)

    def get_import_rows(self, import_id: str, status: str | None = None):
        return self.import_service.get_import_rows(import_id, status=status)

    def export_normalized_data(self, *, creator_id: str, format_name: str = "json") -> AnalyticsExportResult:
        path = self.import_service.paths.data_directory / "analytics" / f"export_{creator_id}.{format_name}"
        publications = self.list_publications(creator_id)
        rows: list[dict[str, object]] = []
        payload = {
            "creator_id": creator_id,
            "publications": [publication.to_dict() for publication in publications],
            "latest_metrics": {},
        }
        for publication in publications:
            latest_metrics = self.get_latest_metrics(publication.id)
            payload["latest_metrics"][publication.id] = {
                key: metric.to_dict() for key, metric in latest_metrics.items()
            }
            for metric_key, metric in latest_metrics.items():
                rows.append(
                    {
                        "publication_id": publication.id,
                        "title": publication.title,
                        "platform": publication.platform,
                        "content_type": publication.content_type.value,
                        "published_at": publication.published_at.isoformat(),
                        "metric_key": metric_key,
                        "snapshot_date": metric.snapshot_date,
                        "captured_at": metric.captured_at.isoformat(),
                        "numeric_value": metric.numeric_value,
                        "text_value": metric.text_value,
                        "unit": metric.unit,
                        "quality_status": metric.quality_status.value,
                    }
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif format_name == "csv":
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                headers = ["publication_id", "title", "platform", "content_type", "published_at", "metric_key", "snapshot_date", "captured_at", "numeric_value", "text_value", "unit", "quality_status"]
                writer.writerow(headers)
                for row in rows:
                    writer.writerow([_csv_safe_value(row.get(column, "")) for column in headers])
        else:
            raise ValueError("Formato no soportado.")
        return AnalyticsExportResult(format=format_name, path=str(path), row_count=len(rows) if format_name == "csv" else len(payload["publications"]))


def build_analytics_services(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    catalog_service: CatalogService,
    repository: AnalyticsRepository,
    database: SQLiteDatabase,
    logger: logging.Logger | None = None,
) -> tuple[AnalyticsImportService, AnalyticsQueryService]:
    import_service = AnalyticsImportService(
        settings=settings,
        paths=paths,
        catalog_service=catalog_service,
        repository=repository,
        database=database,
        logger=logger,
    )
    return import_service, AnalyticsQueryService(import_service)
