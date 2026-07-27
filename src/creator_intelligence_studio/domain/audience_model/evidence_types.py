"""Tipos de evidencia del modelo de audiencia."""

from __future__ import annotations

from enum import Enum


class AudienceEvidenceType(str, Enum):
    METRIC = "metric"
    PUBLICATION = "publication"
    ANALYTICS_FINDING = "analytics_finding"
    EXPERIMENT = "experiment"
    SNAPSHOT = "snapshot"
    REVIEW = "review"
    QUALITY = "quality"
    CONTRADICTION = "contradiction"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"

