"""Modelos auxiliares para importacion y analitica normalizada."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceTable:
    path: Path
    source_type: str
    source_fingerprint: str
    source_filename: str
    size_bytes: int
    delimiter: str | None = None
    sheet_name: str | None = None
    headers: tuple[str, ...] = ()
    rows: tuple[dict[str, object], ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "source_type": self.source_type,
            "source_fingerprint": self.source_fingerprint,
            "source_filename": self.source_filename,
            "size_bytes": self.size_bytes,
            "delimiter": self.delimiter,
            "sheet_name": self.sheet_name,
            "headers": list(self.headers),
            "rows": [dict(row) for row in self.rows],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class SchemaFieldSuggestion:
    source_field: str
    target_field: str
    confidence: float
    transformation: str = "identity"
    origin: str = "auto"
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SchemaDetectionResult:
    path: Path
    source_type: str
    source_fingerprint: str
    source_filename: str
    delimiter: str | None
    sheet_name: str | None
    headers: tuple[str, ...]
    suggestions: tuple[SchemaFieldSuggestion, ...]
    ambiguous_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "source_type": self.source_type,
            "source_fingerprint": self.source_fingerprint,
            "source_filename": self.source_filename,
            "delimiter": self.delimiter,
            "sheet_name": self.sheet_name,
            "headers": list(self.headers),
            "suggestions": [
                {
                    "source_field": item.source_field,
                    "target_field": item.target_field,
                    "confidence": item.confidence,
                    "transformation": item.transformation,
                    "origin": item.origin,
                    "warning_codes": list(item.warning_codes),
                }
                for item in self.suggestions
            ],
            "ambiguous_fields": list(self.ambiguous_fields),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True, slots=True)
class NormalizedMetricValue:
    metric_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedRow:
    row_number: int
    raw_json: dict[str, object]
    normalized_json: dict[str, object]
    publication_key: str | None
    publication_payload: dict[str, object] | None
    metric_values: tuple[NormalizedMetricValue, ...]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    status: str = "accepted"


@dataclass(frozen=True, slots=True)
class RowValidationIssue:
    row_number: int
    status: str
    warning_codes: tuple[str, ...] = ()
    error_codes: tuple[str, ...] = ()
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ImportValidationResult:
    rows: tuple[RowValidationIssue, ...]
    accepted_rows: int
    rejected_rows: int
    warning_rows: int
    duplicate_rows: int


@dataclass(frozen=True, slots=True)
class ImportReportSummary:
    import_id: str
    creator_id: str
    platform: str
    channel_id: str | None
    source_filename: str
    source_fingerprint: str
    source_type: str
    status: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    warning_rows: int
    duplicate_rows: int
    publications_created: int
    publications_updated: int
    snapshots_created: int
    metric_unknown_rows: int
    duration_seconds: float | None
    mapping_name: str | None
    report_path: str | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    examples: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "import_id": self.import_id,
            "creator_id": self.creator_id,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "source_filename": self.source_filename,
            "source_fingerprint": self.source_fingerprint,
            "source_type": self.source_type,
            "status": self.status,
            "total_rows": self.total_rows,
            "accepted_rows": self.accepted_rows,
            "rejected_rows": self.rejected_rows,
            "warning_rows": self.warning_rows,
            "duplicate_rows": self.duplicate_rows,
            "publications_created": self.publications_created,
            "publications_updated": self.publications_updated,
            "snapshots_created": self.snapshots_created,
            "metric_unknown_rows": self.metric_unknown_rows,
            "duration_seconds": self.duration_seconds,
            "mapping_name": self.mapping_name,
            "report_path": self.report_path,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "examples": list(self.examples),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsExportResult:
    format: str
    path: str
    row_count: int
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "path": self.path,
            "row_count": self.row_count,
            "created_at": self.created_at.isoformat(),
        }
