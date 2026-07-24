"""Wrapper de evaluacion de experimentos."""

from __future__ import annotations

from creator_intelligence_studio.application.services.experiment_service import ExperimentService


class ExperimentEvaluationService:
    def __init__(self, experiment_service: ExperimentService) -> None:
        self.experiment_service = experiment_service

    def list_experiments(self, creator_id: str):
        return self.experiment_service.list_experiments(creator_id)

    def evaluate_experiment(self, experiment_id: str):
        return self.experiment_service.evaluate_experiment(experiment_id)

    def get_evaluation(self, evaluation_id: str):
        return self.experiment_service.get_evaluation(evaluation_id)

    def list_evaluations(self, experiment_id: str):
        return self.experiment_service.list_evaluations(experiment_id)

    def get_evaluation_detail(self, evaluation_id: str):
        return self.experiment_service.get_evaluation_detail(evaluation_id)

    def generate_report(self, experiment_id: str, evaluation_id: str | None = None):
        return self.experiment_service.generate_report(experiment_id, evaluation_id)

    def list_reports(self, creator_id: str):
        return self.experiment_service.list_reports(creator_id)

    def get_report(self, report_id: str):
        return self.experiment_service.get_report(report_id)

    def get_report_detail(self, report_id: str):
        return self.experiment_service.get_report_detail(report_id)

    def export_report(self, report_id: str, format_name: str):
        return self.experiment_service.export_report(report_id, format_name)

