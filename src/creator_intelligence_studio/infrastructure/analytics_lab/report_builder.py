"""Constructor de reportes para Analytics Lab."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from creator_intelligence_studio.domain.analytics_lab.entities import AnalyticsReportItem, AnalyticsReportRun


def _csv_safe_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and stripped[0] in "=+-@" and not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
        return "'" + value
    return value


def build_report_payload(report_run: AnalyticsReportRun, items: list[AnalyticsReportItem], findings: list[dict[str, object]], *, sections: list[dict[str, object]], warnings: list[str], confidence: list[dict[str, object]], limitations: list[str]) -> dict[str, object]:
    return {
        "report_run": report_run.to_dict(),
        "items": [item.to_dict() for item in items],
        "findings": findings,
        "sections": sections,
        "warnings": warnings,
        "confidence": confidence,
        "limitations": limitations,
    }


def write_report(path: Path, payload: dict[str, object], *, format_name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    if format_name == "txt":
        lines = [payload.get("report_run", {}).get("title", "Analytics Lab Report")]
        for section in payload.get("sections", []):
            lines.append(f"[{section.get('name', 'section')}]")
            lines.append(section.get("body", ""))
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
    if format_name == "csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "title", "body"])
            for section in payload.get("sections", []):
                writer.writerow([
                    _csv_safe_value(section.get("name", "")),
                    _csv_safe_value(section.get("title", "")),
                    _csv_safe_value(section.get("body", "")),
                ])
        return path
    raise ValueError("Formato de reporte no soportado.")

