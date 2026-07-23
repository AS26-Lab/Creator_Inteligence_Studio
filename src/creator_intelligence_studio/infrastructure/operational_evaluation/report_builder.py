"""Construccion de reportes de evaluacion operativa."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from creator_intelligence_studio.domain.operational_evaluation.entities import OperationalEvaluationReport


def build_json_report(report: OperationalEvaluationReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True, default=str)


def build_csv_report(report: OperationalEvaluationReport) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "stage_index",
            "stage_name",
            "status",
            "duration_seconds",
            "cache_status",
            "retry_count",
            "warning_code",
            "warning_message",
            "error_code",
            "error_message",
        ],
    )
    writer.writeheader()
    for stage in report.stages:
        writer.writerow(
            {
                "stage_index": stage.stage_index,
                "stage_name": stage.stage_name,
                "status": stage.status.value,
                "duration_seconds": stage.duration_seconds,
                "cache_status": stage.cache_status.value,
                "retry_count": stage.retry_count,
                "warning_code": stage.warning_code,
                "warning_message": stage.warning_message,
                "error_code": stage.error_code,
                "error_message": stage.error_message,
            }
        )
    return buffer.getvalue()


def build_txt_report(report: OperationalEvaluationReport) -> str:
    lines = [
        f"Scenario: {report.scenario.id}",
        f"Run: {report.run.id}",
        f"Status: {report.run.status.value}",
        f"Final result: {report.run.final_result.value}",
        f"Total duration: {report.run.total_duration_seconds}",
        f"Stages: {len(report.stages)}",
        f"Assertions passed: {report.run.assertion_pass_count}",
        f"Assertions failed: {report.run.assertion_fail_count}",
        f"Cache hits: {report.run.cache_hit_count}",
        f"Cache misses: {report.run.cache_miss_count}",
    ]
    for stage in report.stages:
        lines.append(
            f"- {stage.stage_index}. {stage.stage_name}: {stage.status.value} ({stage.duration_seconds}) [{stage.cache_status.value}]"
        )
    return "\n".join(lines) + "\n"


def write_report(path: Path, report: OperationalEvaluationReport, format_name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    format_name = format_name.lower()
    if format_name == "json":
        payload = build_json_report(report)
    elif format_name == "csv":
        payload = build_csv_report(report)
    else:
        payload = build_txt_report(report)
    path.write_text(payload, encoding="utf-8")
    return path
