"""Orquestador de bajo nivel para evaluacion operativa."""

from __future__ import annotations

from creator_intelligence_studio.application.services.operational_evaluation_service import (
    OperationalEvaluationComparisonReport,
    OperationalEvaluationService,
)


class OperationalEvaluationPipelineOrchestrator:
    """Envoltorio estable sobre el servicio de aplicacion."""

    def __init__(self, service: OperationalEvaluationService) -> None:
        self._service = service

    def run(self, scenario_id: str, *, force: bool = False, progress_callback=None):
        return self._service.run_scenario(scenario_id, force=force, progress_callback=progress_callback)

    def cancel(self, run_id: str) -> bool:
        return self._service.cancel(run_id)

    def retry_stage(self, run_id: str, stage_name: str):
        return self._service.retry_stage(run_id, stage_name)

    def clean(self, run_id: str, *, dry_run: bool = False):
        return self._service.clean(run_id, dry_run=dry_run)

    def compare_runs(self, baseline_run_id: str, candidate_run_id: str) -> OperationalEvaluationComparisonReport:
        return self._service.compare_runs(baseline_run_id, candidate_run_id)
