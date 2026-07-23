"""Comandos para evaluacion operativa."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunOperationalEvaluationCommand:
    scenario_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowOperationalEvaluationCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class StageOperationalEvaluationCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class RetryOperationalEvaluationStageCommand:
    run_id: str
    stage_name: str


@dataclass(frozen=True, slots=True)
class CancelOperationalEvaluationCommand:
    run_id: str


@dataclass(frozen=True, slots=True)
class ExportOperationalEvaluationCommand:
    run_id: str
    format: str


@dataclass(frozen=True, slots=True)
class CleanOperationalEvaluationCommand:
    run_id: str
    dry_run: bool = False
