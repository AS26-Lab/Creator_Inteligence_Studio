"""Normalizacion de valores metricos para analytics."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricNormalizationResult:
    numeric_value: float | None
    text_value: str | None
    unit: str
    warning_codes: tuple[str, ...]
    error_codes: tuple[str, ...]


def _to_float(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "")
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) in {1, 2, 3} and len(parts) > 1:
            cleaned = ".".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = cleaned.replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def normalize_metric_value(raw_value, *, target_unit: str, source_unit: str | None = None) -> MetricNormalizationResult:
    warnings: list[str] = []
    errors: list[str] = []
    if raw_value is None:
        return MetricNormalizationResult(None, None, target_unit, tuple(), tuple())
    if isinstance(raw_value, bool):
        raw_value = int(raw_value)
    if isinstance(raw_value, (int, float)):
        numeric = float(raw_value)
    else:
        text = str(raw_value).strip()
        if not text:
            return MetricNormalizationResult(None, None, target_unit, tuple(), tuple())
        if target_unit == "text":
            return MetricNormalizationResult(None, text, target_unit, tuple(), tuple())
        numeric = _to_float(text)
        if numeric is None:
            return MetricNormalizationResult(None, text, target_unit, tuple(), ("invalid_number",))
        if text.endswith("%") and target_unit == "percent":
            if numeric > 1.0:
                numeric /= 100.0
            warnings.append("percentage_normalized")
        elif target_unit == "percent":
            if 0.0 <= numeric <= 1.0:
                pass
            elif 0.0 <= numeric <= 100.0:
                numeric /= 100.0
                warnings.append("percentage_normalized")
            else:
                warnings.append("percentage_out_of_range")
        elif target_unit == "ratio":
            if numeric > 1.0:
                if numeric <= 100.0:
                    numeric /= 100.0
                    warnings.append("percentage_normalized")
                else:
                    warnings.append("ambiguous_unit")
        elif target_unit in {"minutes", "seconds", "count"} and numeric < 0:
            warnings.append("negative_value")
    if source_unit and source_unit != target_unit:
        warnings.append("ambiguous_unit")
    return MetricNormalizationResult(numeric if target_unit != "text" else None, None if target_unit != "text" else str(raw_value).strip(), target_unit, tuple(dict.fromkeys(warnings)), tuple(errors))
