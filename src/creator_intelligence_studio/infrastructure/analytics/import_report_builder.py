"""Construccion de reportes exportables de importacion analytics."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .models import AnalyticsExportResult, ImportReportSummary


_NUMERIC_STRING = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def _csv_safe_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and stripped[0] in "=+-@" and not _NUMERIC_STRING.fullmatch(stripped):
        return "'" + value
    return value


def build_import_report_json(summary: ImportReportSummary) -> str:
    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def build_import_report_txt(summary: ImportReportSummary) -> str:
    lines = [
        f"Importacion: {summary.import_id}",
        f"Plataforma: {summary.platform}",
        f"Archivo: {summary.source_filename}",
        f"Estado: {summary.status}",
        f"Filas: {summary.total_rows}",
        f"Aceptadas: {summary.accepted_rows}",
        f"Advertencias: {summary.warning_rows}",
        f"Rechazadas: {summary.rejected_rows}",
        f"Duplicadas: {summary.duplicate_rows}",
        f"Publicaciones creadas: {summary.publications_created}",
        f"Publicaciones actualizadas: {summary.publications_updated}",
        f"Snapshots creados: {summary.snapshots_created}",
    ]
    if summary.warnings:
        lines.append("Advertencias:")
        lines.extend(f"- {item}" for item in summary.warnings)
    if summary.errors:
        lines.append("Errores:")
        lines.extend(f"- {item}" for item in summary.errors)
    return "\n".join(lines)


def write_import_report(path: Path, summary: ImportReportSummary, *, format_name: str = "json") -> AnalyticsExportResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        path.write_text(build_import_report_json(summary), encoding="utf-8")
    elif format_name == "txt":
        path.write_text(build_import_report_txt(summary), encoding="utf-8")
    elif format_name == "csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["field", "value"])
            for key, value in summary.to_dict().items():
                rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                writer.writerow([_csv_safe_value(key), _csv_safe_value(rendered)])
    else:
        raise ValueError("Formato de reporte no soportado.")
    return AnalyticsExportResult(format=format_name, path=str(path), row_count=summary.total_rows)
