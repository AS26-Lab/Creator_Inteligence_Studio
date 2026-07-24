"""Construccion de reportes reproducibles de experiments."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path


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


def build_report_payload(report, evaluation, report_items, *, sections, warnings, confidence, limitations) -> dict[str, object]:
    return {
        "report": report.to_dict(),
        "evaluation": None if evaluation is None else evaluation.to_dict(),
        "items": [item.to_dict() for item in report_items],
        "sections": sections,
        "warnings": list(warnings),
        "confidence": list(confidence),
        "limitations": list(limitations),
    }


def write_report(path: Path, payload: dict[str, object], *, format_name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if format_name == "json":
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    if format_name == "txt":
        lines = []
        report = payload.get("report", {})
        lines.append(str(report.get("title", "Reporte")))
        lines.append(str(report.get("summary", "")))
        for section in payload.get("sections", []):
            lines.append("")
            lines.append(str(section.get("name", "")))
            lines.append(str(section.get("body", "")))
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
    raise ValueError("Formato no soportado.")

