"""Contratos de persistencia para Analytics Lab."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    AnalyticsAnalysisRun,
    AnalyticsCohortDefinition,
    AnalyticsComparisonResult,
    AnalyticsFinding,
    AnalyticsReportItem,
    AnalyticsReportRun,
)


class AnalyticsLabRepository(ABC):
    @abstractmethod
    def upsert_cohort(self, cohort: AnalyticsCohortDefinition) -> AnalyticsCohortDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_cohort_by_id(self, cohort_id: str) -> AnalyticsCohortDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def get_cohort_by_name(self, creator_id: str, name: str) -> AnalyticsCohortDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_cohorts(self, creator_id: str, *, active_only: bool = False) -> list[AnalyticsCohortDefinition]:
        raise NotImplementedError

    @abstractmethod
    def upsert_analysis_run(self, run: AnalyticsAnalysisRun) -> AnalyticsAnalysisRun:
        raise NotImplementedError

    @abstractmethod
    def get_analysis_run_by_id(self, run_id: str) -> AnalyticsAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_analysis_run_by_fingerprint(self, source_fingerprint: str, run_type: str) -> AnalyticsAnalysisRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_analysis_runs(self, creator_id: str, *, run_type: str | None = None) -> list[AnalyticsAnalysisRun]:
        raise NotImplementedError

    @abstractmethod
    def upsert_comparison_results(self, analysis_run_id: str, results: list[AnalyticsComparisonResult]) -> list[AnalyticsComparisonResult]:
        raise NotImplementedError

    @abstractmethod
    def list_comparison_results(self, analysis_run_id: str) -> list[AnalyticsComparisonResult]:
        raise NotImplementedError

    @abstractmethod
    def upsert_finding(self, finding: AnalyticsFinding) -> AnalyticsFinding:
        raise NotImplementedError

    @abstractmethod
    def list_findings(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsFinding]:
        raise NotImplementedError

    @abstractmethod
    def get_finding_by_id(self, finding_id: str) -> AnalyticsFinding | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_report_run(self, report_run: AnalyticsReportRun) -> AnalyticsReportRun:
        raise NotImplementedError

    @abstractmethod
    def get_report_run_by_id(self, report_id: str) -> AnalyticsReportRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_report_run_by_fingerprint(self, source_fingerprint: str, report_type: str) -> AnalyticsReportRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_report_runs(self, creator_id: str) -> list[AnalyticsReportRun]:
        raise NotImplementedError

    @abstractmethod
    def upsert_report_items(self, report_run_id: str, items: list[AnalyticsReportItem]) -> list[AnalyticsReportItem]:
        raise NotImplementedError

    @abstractmethod
    def list_report_items(self, report_run_id: str) -> list[AnalyticsReportItem]:
        raise NotImplementedError

