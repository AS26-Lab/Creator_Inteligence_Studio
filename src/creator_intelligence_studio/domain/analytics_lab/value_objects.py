"""Valores y estados para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AnalyticsAnalysisRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class AnalyticsReportStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class AnalyticsComparisonStatus(str, Enum):
    COMPARABLE = "comparable"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    INCOMPARABLE = "incomparable"
    NO_DATA = "no_data"
    OUTLIER_DOMINATED = "outlier_dominated"


class AnalyticsFindingType(str, Enum):
    FACT = "fact"
    COMPARISON = "comparison"
    ANOMALY = "anomaly"
    PATTERN = "pattern"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    DATA_QUALITY_WARNING = "data_quality_warning"


class AnalyticsFindingStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"
    NOT_USEFUL = "not_useful"


class AnalyticsConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalyticsLabRunType(str, Enum):
    COHORT_ANALYSIS = "cohort_analysis"
    PUBLICATION_COMPARISON = "publication_comparison"
    WEEKLY_REPORT = "weekly_report"


@dataclass(frozen=True, slots=True)
class AnalyticsLabSampleStrength:
    sample_size: int
    comparison_status: AnalyticsComparisonStatus
    confidence_level: AnalyticsConfidenceLevel
    warning_codes: tuple[str, ...]

