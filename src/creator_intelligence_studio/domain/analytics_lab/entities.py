"""Entidades persistidas para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    AnalyticsAnalysisRunStatus,
    AnalyticsConfidenceLevel,
    AnalyticsComparisonStatus,
    AnalyticsFindingStatus,
    AnalyticsFindingType,
    AnalyticsLabRunType,
    AnalyticsReportStatus,
)


@dataclass(frozen=True, slots=True)
class AnalyticsCohortDefinition:
    id: str
    creator_id: str
    name: str
    description: str
    platform: str | None
    content_type: str | None
    date_from: str | None
    date_to: str | None
    duration_min_seconds: float | None
    duration_max_seconds: float | None
    topic: str | None
    format: str | None
    language: str | None
    filters_json: str
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "description": self.description,
            "platform": self.platform,
            "content_type": self.content_type,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "duration_min_seconds": self.duration_min_seconds,
            "duration_max_seconds": self.duration_max_seconds,
            "topic": self.topic,
            "format": self.format,
            "language": self.language,
            "filters_json": self.filters_json,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsAnalysisRun:
    id: str
    creator_id: str
    run_type: AnalyticsLabRunType
    cohort_id: str | None
    status: AnalyticsAnalysisRunStatus
    configuration_json: str
    source_fingerprint: str
    publication_count: int
    metric_count: int
    warning_count: int
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "run_type": self.run_type.value,
            "cohort_id": self.cohort_id,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "source_fingerprint": self.source_fingerprint,
            "publication_count": self.publication_count,
            "metric_count": self.metric_count,
            "warning_count": self.warning_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsComparisonResult:
    id: str
    analysis_run_id: str
    publication_id: str | None
    cohort_id: str
    metric_key: str
    observed_value: float | None
    cohort_count: int
    cohort_min: float | None
    cohort_max: float | None
    cohort_mean: float | None
    cohort_median: float | None
    percentile: float | None
    lower_quartile: float | None
    upper_quartile: float | None
    robust_z_score: float | None
    comparison_status: AnalyticsComparisonStatus
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "publication_id": self.publication_id,
            "cohort_id": self.cohort_id,
            "metric_key": self.metric_key,
            "observed_value": self.observed_value,
            "cohort_count": self.cohort_count,
            "cohort_min": self.cohort_min,
            "cohort_max": self.cohort_max,
            "cohort_mean": self.cohort_mean,
            "cohort_median": self.cohort_median,
            "percentile": self.percentile,
            "lower_quartile": self.lower_quartile,
            "upper_quartile": self.upper_quartile,
            "robust_z_score": self.robust_z_score,
            "comparison_status": self.comparison_status.value,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsFinding:
    id: str
    analysis_run_id: str
    creator_id: str
    publication_id: str | None
    cohort_id: str | None
    finding_type: AnalyticsFindingType
    category: str
    title: str
    summary: str
    evidence_json: str
    confidence_level: AnalyticsConfidenceLevel
    confidence_score: float | None
    sample_size: int
    contradiction_count: int
    status: AnalyticsFindingStatus
    is_confirmed: bool
    confirmed_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "creator_id": self.creator_id,
            "publication_id": self.publication_id,
            "cohort_id": self.cohort_id,
            "finding_type": self.finding_type.value,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "evidence_json": self.evidence_json,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "sample_size": self.sample_size,
            "contradiction_count": self.contradiction_count,
            "status": self.status.value,
            "is_confirmed": self.is_confirmed,
            "confirmed_at": to_iso_z(self.confirmed_at),
            "rejected_at": to_iso_z(self.rejected_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsReportRun:
    id: str
    creator_id: str
    report_type: str
    period_start: str
    period_end: str
    status: AnalyticsReportStatus
    title: str
    summary: str
    configuration_json: str
    source_fingerprint: str
    finding_count: int
    warning_count: int
    output_json_path: str | None
    output_txt_path: str | None
    output_csv_path: str | None
    created_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "report_type": self.report_type,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "status": self.status.value,
            "title": self.title,
            "summary": self.summary,
            "configuration_json": self.configuration_json,
            "source_fingerprint": self.source_fingerprint,
            "finding_count": self.finding_count,
            "warning_count": self.warning_count,
            "output_json_path": self.output_json_path,
            "output_txt_path": self.output_txt_path,
            "output_csv_path": self.output_csv_path,
            "created_at": to_iso_z(self.created_at),
            "completed_at": to_iso_z(self.completed_at),
        }


@dataclass(frozen=True, slots=True)
class AnalyticsReportItem:
    id: str
    report_run_id: str
    item_index: int
    section: str
    finding_id: str | None
    item_type: str
    title: str
    body: str
    evidence_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "report_run_id": self.report_run_id,
            "item_index": self.item_index,
            "section": self.section,
            "finding_id": self.finding_id,
            "item_type": self.item_type,
            "title": self.title,
            "body": self.body,
            "evidence_json": self.evidence_json,
            "created_at": to_iso_z(self.created_at),
        }

