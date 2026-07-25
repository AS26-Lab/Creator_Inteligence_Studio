"""Tipos y resultados de analisis de titulos."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TitlePatternType(str, Enum):
    QUESTION = "question"
    STATEMENT = "statement"
    CHALLENGE = "challenge"
    RESULT = "result"
    TRANSFORMATION = "transformation"
    LIST = "list"
    CURIOSITY_GAP = "curiosity_gap"
    CONFLICT = "conflict"
    COMPARISON = "comparison"
    REACTION = "reaction"
    STORY = "story"
    TUTORIAL = "tutorial"
    DIRECT_PROMISE = "direct_promise"
    INCOMPLETE_PROMISE = "incomplete_promise"
    DESCRIPTIVE = "descriptive"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class TitleAnalysisMetric:
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
class TitleAnalysisResult:
    pattern_type: TitlePatternType
    metrics: tuple[TitleAnalysisMetric, ...]
    warnings: tuple[str, ...]
    recommendation_status: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pattern_type": self.pattern_type.value,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "warnings": list(self.warnings),
            "recommendation_status": self.recommendation_status,
            "summary": self.summary,
        }

