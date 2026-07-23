"""Valores y estados para evaluacion operativa."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OperationalEvaluationRunStatus(str, Enum):
    QUEUED = "queued"
    PREPARING_SCENARIO = "preparing_scenario"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class OperationalEvaluationStageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    SKIPPED = "skipped"
    CACHED = "cached"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class OperationalEvaluationFinalResult(str, Enum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    INCONCLUSIVE = "inconclusive"


class OperationalEvaluationCacheStatus(str, Enum):
    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class OperationalEvaluationAssertionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class OperationalEvaluationProgress:
    """Progreso aproximado de una evaluacion."""

    stage_name: str
    stage_index: int
    stage_count: int
    ratio: float
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage_name": self.stage_name,
            "stage_index": self.stage_index,
            "stage_count": self.stage_count,
            "ratio": self.ratio,
            "message": self.message,
        }
