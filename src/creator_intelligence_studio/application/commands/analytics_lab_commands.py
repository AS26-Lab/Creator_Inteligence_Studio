"""Comandos de aplicacion para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListAnalyticsCohortsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateAnalyticsCohortCommand:
    creator_id: str
    name: str
    description: str
    platform: str | None = None
    content_type: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    duration_min_seconds: float | None = None
    duration_max_seconds: float | None = None
    topic: str | None = None
    format: str | None = None
    language: str | None = None
    channel_id: str | None = None
    linked: bool | None = None


@dataclass(frozen=True, slots=True)
class ShowAnalyticsCohortCommand:
    cohort_id: str


@dataclass(frozen=True, slots=True)
class AnalyzeAnalyticsCohortCommand:
    cohort_id: str


@dataclass(frozen=True, slots=True)
class CompareAnalyticsPublicationCommand:
    publication_id: str
    cohort_id: str


@dataclass(frozen=True, slots=True)
class ShowAnalyticsAnalysisCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ListAnalyticsFindingsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowAnalyticsFindingCommand:
    finding_id: str


@dataclass(frozen=True, slots=True)
class ConfirmAnalyticsFindingCommand:
    finding_id: str


@dataclass(frozen=True, slots=True)
class RejectAnalyticsFindingCommand:
    finding_id: str


@dataclass(frozen=True, slots=True)
class GenerateAnalyticsWeeklyReportCommand:
    creator_id: str
    period_start: str
    period_end: str


@dataclass(frozen=True, slots=True)
class ListAnalyticsReportsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowAnalyticsReportCommand:
    report_id: str


@dataclass(frozen=True, slots=True)
class ExportAnalyticsReportCommand:
    report_id: str
    format: str

