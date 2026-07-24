"""Reglas y utilidades para Analytics Lab."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime

from .cohort_definitions import AnalyticsSystemCohortPreset, SYSTEM_COHORT_PRESETS
from .value_objects import AnalyticsConfidenceLevel, AnalyticsComparisonStatus


def build_analytics_lab_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def confidence_from_sample(sample_size: int, comparable: bool = True) -> AnalyticsConfidenceLevel:
    if not comparable or sample_size < 4:
        return AnalyticsConfidenceLevel.LOW
    if sample_size < 10:
        return AnalyticsConfidenceLevel.MEDIUM
    return AnalyticsConfidenceLevel.HIGH


def comparison_status_from_sample(sample_size: int, comparable: bool, outlier_dominated: bool = False) -> AnalyticsComparisonStatus:
    if not comparable:
        return AnalyticsComparisonStatus.INCOMPARABLE
    if sample_size <= 0:
        return AnalyticsComparisonStatus.NO_DATA
    if sample_size < 4:
        return AnalyticsComparisonStatus.INSUFFICIENT_SAMPLE
    if outlier_dominated:
        return AnalyticsComparisonStatus.OUTLIER_DOMINATED
    return AnalyticsComparisonStatus.COMPARABLE


def system_cohort_payloads() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "name": preset.name,
            "description": preset.description,
            "filters": dict(preset.filters),
        }
        for preset in SYSTEM_COHORT_PRESETS
    )

