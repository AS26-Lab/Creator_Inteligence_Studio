"""Tipos y resultados de analisis de miniaturas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThumbnailReviewStatus(str, Enum):
    READY_TO_USE = "ready_to_use"
    READY_WITH_MINOR_CHANGES = "ready_with_minor_changes"
    NEEDS_REVISION = "needs_revision"
    OFF_BRAND = "off_brand"
    MISLEADING = "misleading"
    TECHNICALLY_WEAK = "technically_weak"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    NOT_RECOMMENDED = "not_recommended"


@dataclass(frozen=True, slots=True)
class ThumbnailAnalysisMetric:
    metric_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    confidence_level: str
    warning_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_key": self.metric_key,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "confidence_level": self.confidence_level,
            "warning_codes": list(self.warning_codes),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailAnalysisResult:
    dimensions: tuple[int, int] | None
    metrics: tuple[ThumbnailAnalysisMetric, ...]
    warnings: tuple[str, ...]
    recommendation_status: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "dimensions": list(self.dimensions) if self.dimensions else None,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "warnings": list(self.warnings),
            "recommendation_status": self.recommendation_status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ThumbnailReviewResult:
    status: ThumbnailReviewStatus
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    keep: tuple[str, ...]
    change: tuple[str, ...]
    risks: tuple[str, ...]
    revision_instructions: str
    confidence_level: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "keep": list(self.keep),
            "change": list(self.change),
            "risks": list(self.risks),
            "revision_instructions": self.revision_instructions,
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }

