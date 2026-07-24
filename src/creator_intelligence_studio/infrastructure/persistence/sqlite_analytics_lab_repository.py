"""Repositorio SQLite para Analytics Lab."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace

from creator_intelligence_studio.domain.analytics_lab.entities import (
    AnalyticsAnalysisRun,
    AnalyticsCohortDefinition,
    AnalyticsComparisonResult,
    AnalyticsFinding,
    AnalyticsReportItem,
    AnalyticsReportRun,
)
from creator_intelligence_studio.domain.analytics_lab.repositories import AnalyticsLabRepository
from creator_intelligence_studio.domain.analytics_lab.value_objects import (
    AnalyticsAnalysisRunStatus,
    AnalyticsConfidenceLevel,
    AnalyticsComparisonStatus,
    AnalyticsFindingStatus,
    AnalyticsFindingType,
    AnalyticsLabRunType,
    AnalyticsReportStatus,
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


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _row_to_cohort(row: sqlite3.Row) -> AnalyticsCohortDefinition:
    return AnalyticsCohortDefinition(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        description=row["description"],
        platform=row["platform"],
        content_type=row["content_type"],
        date_from=row["date_from"],
        date_to=row["date_to"],
        duration_min_seconds=row["duration_min_seconds"],
        duration_max_seconds=row["duration_max_seconds"],
        topic=row["topic"],
        format=row["format"],
        language=row["language"],
        filters_json=row["filters_json"],
        is_system=bool(row["is_system"]),
        is_active=bool(row["is_active"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_analysis_run(row: sqlite3.Row) -> AnalyticsAnalysisRun:
    return AnalyticsAnalysisRun(
        id=row["id"],
        creator_id=row["creator_id"],
        run_type=AnalyticsLabRunType(row["run_type"]),
        cohort_id=row["cohort_id"],
        status=AnalyticsAnalysisRunStatus(row["status"]),
        configuration_json=row["configuration_json"],
        source_fingerprint=row["source_fingerprint"],
        publication_count=row["publication_count"],
        metric_count=row["metric_count"],
        warning_count=row["warning_count"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_comparison(row: sqlite3.Row) -> AnalyticsComparisonResult:
    return AnalyticsComparisonResult(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        publication_id=row["publication_id"],
        cohort_id=row["cohort_id"],
        metric_key=row["metric_key"],
        observed_value=row["observed_value"],
        cohort_count=row["cohort_count"],
        cohort_min=row["cohort_min"],
        cohort_max=row["cohort_max"],
        cohort_mean=row["cohort_mean"],
        cohort_median=row["cohort_median"],
        percentile=row["percentile"],
        lower_quartile=row["lower_quartile"],
        upper_quartile=row["upper_quartile"],
        robust_z_score=row["robust_z_score"],
        comparison_status=AnalyticsComparisonStatus(row["comparison_status"]),
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_finding(row: sqlite3.Row) -> AnalyticsFinding:
    return AnalyticsFinding(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        creator_id=row["creator_id"],
        publication_id=row["publication_id"],
        cohort_id=row["cohort_id"],
        finding_type=AnalyticsFindingType(row["finding_type"]),
        category=row["category"],
        title=row["title"],
        summary=row["summary"],
        evidence_json=row["evidence_json"],
        confidence_level=AnalyticsConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        sample_size=row["sample_size"],
        contradiction_count=row["contradiction_count"],
        status=AnalyticsFindingStatus(row["status"]),
        is_confirmed=bool(row["is_confirmed"]),
        confirmed_at=from_iso_z(row["confirmed_at"]),
        rejected_at=from_iso_z(row["rejected_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_report(row: sqlite3.Row) -> AnalyticsReportRun:
    return AnalyticsReportRun(
        id=row["id"],
        creator_id=row["creator_id"],
        report_type=row["report_type"],
        period_start=row["period_start"],
        period_end=row["period_end"],
        status=AnalyticsReportStatus(row["status"]),
        title=row["title"],
        summary=row["summary"],
        configuration_json=row["configuration_json"],
        source_fingerprint=row["source_fingerprint"],
        finding_count=row["finding_count"],
        warning_count=row["warning_count"],
        output_json_path=row["output_json_path"],
        output_txt_path=row["output_txt_path"],
        output_csv_path=row["output_csv_path"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
    )


def _row_to_report_item(row: sqlite3.Row) -> AnalyticsReportItem:
    return AnalyticsReportItem(
        id=row["id"],
        report_run_id=row["report_run_id"],
        item_index=row["item_index"],
        section=row["section"],
        finding_id=row["finding_id"],
        item_type=row["item_type"],
        title=row["title"],
        body=row["body"],
        evidence_json=row["evidence_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteAnalyticsLabRepository(AnalyticsLabRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_cohort(self, cohort: AnalyticsCohortDefinition) -> AnalyticsCohortDefinition:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_cohort_definitions (
                    id, creator_id, name, description, platform, content_type, date_from, date_to,
                    duration_min_seconds, duration_max_seconds, topic, format, language,
                    filters_json, is_system, is_active, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :name, :description, :platform, :content_type, :date_from, :date_to,
                    :duration_min_seconds, :duration_max_seconds, :topic, :format, :language,
                    :filters_json, :is_system, :is_active, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, name) DO UPDATE SET
                    description = excluded.description,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    date_from = excluded.date_from,
                    date_to = excluded.date_to,
                    duration_min_seconds = excluded.duration_min_seconds,
                    duration_max_seconds = excluded.duration_max_seconds,
                    topic = excluded.topic,
                    format = excluded.format,
                    language = excluded.language,
                    filters_json = excluded.filters_json,
                    is_system = excluded.is_system,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                {
                    **cohort.to_dict(),
                    "is_system": 1 if cohort.is_system else 0,
                    "is_active": 1 if cohort.is_active else 0,
                },
            )
            row = connection.execute(
                "SELECT * FROM analytics_cohort_definitions WHERE creator_id = ? AND name = ?",
                (cohort.creator_id, cohort.name),
            ).fetchone()
        return _row_to_cohort(row)

    def get_cohort_by_id(self, cohort_id: str) -> AnalyticsCohortDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_cohort_definitions WHERE id = ?", (cohort_id,)).fetchone()
        return _row_to_cohort(row) if row else None

    def get_cohort_by_name(self, creator_id: str, name: str) -> AnalyticsCohortDefinition | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analytics_cohort_definitions WHERE creator_id = ? AND name = ?",
                (creator_id, name),
            ).fetchone()
        return _row_to_cohort(row) if row else None

    def list_cohorts(self, creator_id: str, *, active_only: bool = False) -> list[AnalyticsCohortDefinition]:
        query = "SELECT * FROM analytics_cohort_definitions WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY is_system DESC, updated_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row_to_cohort(row) for row in rows]

    def upsert_analysis_run(self, run: AnalyticsAnalysisRun) -> AnalyticsAnalysisRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_analysis_runs (
                    id, creator_id, run_type, cohort_id, status, configuration_json, source_fingerprint,
                    publication_count, metric_count, warning_count, started_at, completed_at,
                    error_code, error_message, created_at
                ) VALUES (
                    :id, :creator_id, :run_type, :cohort_id, :status, :configuration_json, :source_fingerprint,
                    :publication_count, :metric_count, :warning_count, :started_at, :completed_at,
                    :error_code, :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    publication_count = excluded.publication_count,
                    metric_count = excluded.metric_count,
                    warning_count = excluded.warning_count,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                {
                    **run.to_dict(),
                    "status": run.status.value,
                    "run_type": run.run_type.value,
                    "started_at": run.started_at.isoformat(),
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "created_at": run.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM analytics_analysis_runs WHERE id = ?", (run.id,)).fetchone()
        return _row_to_analysis_run(row)

    def get_analysis_run_by_id(self, run_id: str) -> AnalyticsAnalysisRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_analysis_runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_analysis_run(row) if row else None

    def get_analysis_run_by_fingerprint(self, source_fingerprint: str, run_type: str) -> AnalyticsAnalysisRun | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analytics_analysis_runs WHERE source_fingerprint = ? AND run_type = ? ORDER BY created_at DESC LIMIT 1",
                (source_fingerprint, run_type),
            ).fetchone()
        return _row_to_analysis_run(row) if row else None

    def list_analysis_runs(self, creator_id: str, *, run_type: str | None = None) -> list[AnalyticsAnalysisRun]:
        query = "SELECT * FROM analytics_analysis_runs WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if run_type:
            query += " AND run_type = ?"
            params.append(run_type)
        query += " ORDER BY created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row_to_analysis_run(row) for row in rows]

    def upsert_comparison_results(self, analysis_run_id: str, results: list[AnalyticsComparisonResult]) -> list[AnalyticsComparisonResult]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM analytics_comparison_results WHERE analysis_run_id = ?", (analysis_run_id,))
            for result in results:
                connection.execute(
                    """
                    INSERT INTO analytics_comparison_results (
                        id, analysis_run_id, publication_id, cohort_id, metric_key, observed_value,
                        cohort_count, cohort_min, cohort_max, cohort_mean, cohort_median, percentile,
                        lower_quartile, upper_quartile, robust_z_score, comparison_status,
                        warning_codes_json, created_at
                    ) VALUES (
                        :id, :analysis_run_id, :publication_id, :cohort_id, :metric_key, :observed_value,
                        :cohort_count, :cohort_min, :cohort_max, :cohort_mean, :cohort_median, :percentile,
                        :lower_quartile, :upper_quartile, :robust_z_score, :comparison_status,
                        :warning_codes_json, :created_at
                    )
                    """,
                    {
                        **result.to_dict(),
                        "comparison_status": result.comparison_status.value,
                        "created_at": result.created_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM analytics_comparison_results WHERE analysis_run_id = ? ORDER BY publication_id, metric_key",
                (analysis_run_id,),
            ).fetchall()
        return [_row_to_comparison(row) for row in rows]

    def list_comparison_results(self, analysis_run_id: str) -> list[AnalyticsComparisonResult]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analytics_comparison_results WHERE analysis_run_id = ? ORDER BY publication_id, metric_key",
                (analysis_run_id,),
            ).fetchall()
        return [_row_to_comparison(row) for row in rows]

    def upsert_finding(self, finding: AnalyticsFinding) -> AnalyticsFinding:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_findings (
                    id, analysis_run_id, creator_id, publication_id, cohort_id, finding_type, category,
                    title, summary, evidence_json, confidence_level, confidence_score, sample_size,
                    contradiction_count, status, is_confirmed, confirmed_at, rejected_at, created_at, updated_at
                ) VALUES (
                    :id, :analysis_run_id, :creator_id, :publication_id, :cohort_id, :finding_type, :category,
                    :title, :summary, :evidence_json, :confidence_level, :confidence_score, :sample_size,
                    :contradiction_count, :status, :is_confirmed, :confirmed_at, :rejected_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    finding_type = excluded.finding_type,
                    category = excluded.category,
                    title = excluded.title,
                    summary = excluded.summary,
                    evidence_json = excluded.evidence_json,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    sample_size = excluded.sample_size,
                    contradiction_count = excluded.contradiction_count,
                    status = excluded.status,
                    is_confirmed = excluded.is_confirmed,
                    confirmed_at = excluded.confirmed_at,
                    rejected_at = excluded.rejected_at,
                    updated_at = excluded.updated_at
                """,
                {
                    **finding.to_dict(),
                    "finding_type": finding.finding_type.value,
                    "confidence_level": finding.confidence_level.value,
                    "status": finding.status.value,
                    "is_confirmed": 1 if finding.is_confirmed else 0,
                    "created_at": finding.created_at.isoformat(),
                    "updated_at": finding.updated_at.isoformat(),
                    "confirmed_at": finding.confirmed_at.isoformat() if finding.confirmed_at else None,
                    "rejected_at": finding.rejected_at.isoformat() if finding.rejected_at else None,
                },
            )
            row = connection.execute("SELECT * FROM analytics_findings WHERE id = ?", (finding.id,)).fetchone()
        return _row_to_finding(row)

    def list_findings(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsFinding]:
        filters = filters or {}
        query = "SELECT * FROM analytics_findings WHERE creator_id = ?"
        params: list[object] = [creator_id]
        for key in ("analysis_run_id", "publication_id", "cohort_id", "status", "finding_type"):
            if key in filters and filters[key] is not None:
                query += f" AND {key} = ?"
                value = filters[key]
                if hasattr(value, "value"):
                    value = value.value
                params.append(value)
        query += " ORDER BY created_at DESC"
        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [_row_to_finding(row) for row in rows]

    def get_finding_by_id(self, finding_id: str) -> AnalyticsFinding | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_findings WHERE id = ?", (finding_id,)).fetchone()
        return _row_to_finding(row) if row else None

    def upsert_report_run(self, report_run: AnalyticsReportRun) -> AnalyticsReportRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO analytics_report_runs (
                    id, creator_id, report_type, period_start, period_end, status, title, summary,
                    configuration_json, source_fingerprint, finding_count, warning_count,
                    output_json_path, output_txt_path, output_csv_path, created_at, completed_at
                ) VALUES (
                    :id, :creator_id, :report_type, :period_start, :period_end, :status, :title, :summary,
                    :configuration_json, :source_fingerprint, :finding_count, :warning_count,
                    :output_json_path, :output_txt_path, :output_csv_path, :created_at, :completed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    title = excluded.title,
                    summary = excluded.summary,
                    configuration_json = excluded.configuration_json,
                    source_fingerprint = excluded.source_fingerprint,
                    finding_count = excluded.finding_count,
                    warning_count = excluded.warning_count,
                    output_json_path = excluded.output_json_path,
                    output_txt_path = excluded.output_txt_path,
                    output_csv_path = excluded.output_csv_path,
                    completed_at = excluded.completed_at
                """,
                {
                    **report_run.to_dict(),
                    "status": report_run.status.value,
                    "created_at": report_run.created_at.isoformat(),
                    "completed_at": report_run.completed_at.isoformat() if report_run.completed_at else None,
                },
            )
            row = connection.execute("SELECT * FROM analytics_report_runs WHERE id = ?", (report_run.id,)).fetchone()
        return _row_to_report(row)

    def get_report_run_by_id(self, report_id: str) -> AnalyticsReportRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM analytics_report_runs WHERE id = ?", (report_id,)).fetchone()
        return _row_to_report(row) if row else None

    def get_report_run_by_fingerprint(self, source_fingerprint: str, report_type: str) -> AnalyticsReportRun | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM analytics_report_runs WHERE source_fingerprint = ? AND report_type = ? ORDER BY created_at DESC LIMIT 1",
                (source_fingerprint, report_type),
            ).fetchone()
        return _row_to_report(row) if row else None

    def list_report_runs(self, creator_id: str) -> list[AnalyticsReportRun]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analytics_report_runs WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [_row_to_report(row) for row in rows]

    def upsert_report_items(self, report_run_id: str, items: list[AnalyticsReportItem]) -> list[AnalyticsReportItem]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM analytics_report_items WHERE report_run_id = ?", (report_run_id,))
            for item in items:
                connection.execute(
                    """
                    INSERT INTO analytics_report_items (
                        id, report_run_id, item_index, section, finding_id, item_type, title, body,
                        evidence_json, created_at
                    ) VALUES (
                        :id, :report_run_id, :item_index, :section, :finding_id, :item_type, :title, :body,
                        :evidence_json, :created_at
                    )
                    """,
                    {
                        **item.to_dict(),
                        "created_at": item.created_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM analytics_report_items WHERE report_run_id = ? ORDER BY item_index ASC",
                (report_run_id,),
            ).fetchall()
        return [_row_to_report_item(row) for row in rows]

    def list_report_items(self, report_run_id: str) -> list[AnalyticsReportItem]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analytics_report_items WHERE report_run_id = ? ORDER BY item_index ASC",
                (report_run_id,),
            ).fetchall()
        return [_row_to_report_item(row) for row in rows]

