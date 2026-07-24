"""Wrapper de ejecuciones reales."""

from __future__ import annotations

from creator_intelligence_studio.application.services.experiment_service import ExperimentService


class ExecutionTrackingService:
    def __init__(self, experiment_service: ExperimentService) -> None:
        self.experiment_service = experiment_service

    def list_executions(self, creator_id: str):
        return self.experiment_service.list_executions(creator_id)

    def record_execution(self, **kwargs):
        return self.experiment_service.record_execution(**kwargs)

