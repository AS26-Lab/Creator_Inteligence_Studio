"""Cronometraje sencillo de etapas de evaluacion."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class StageTiming:
    started_at: float
    completed_at: float
    duration_seconds: float


class StageTimer:
    """Calcula tiempos aproximados sin depender de relojes externos."""

    def __init__(self) -> None:
        self._started_at = perf_counter()

    def finish(self) -> StageTiming:
        completed_at = perf_counter()
        return StageTiming(
            started_at=self._started_at,
            completed_at=completed_at,
            duration_seconds=max(0.0, completed_at - self._started_at),
        )
