"""Wrapper de memoria de aprendizaje."""

from __future__ import annotations

from creator_intelligence_studio.application.services.experiment_service import ExperimentService


class LearningMemoryService:
    def __init__(self, experiment_service: ExperimentService) -> None:
        self.experiment_service = experiment_service

    def list_learnings(self, creator_id: str):
        return self.experiment_service.list_learnings(creator_id)

    def get_learning(self, learning_id: str):
        return self.experiment_service.get_learning(learning_id)

    def confirm_learning(self, learning_id: str):
        return self.experiment_service.confirm_learning(learning_id)

    def reject_learning(self, learning_id: str):
        return self.experiment_service.reject_learning(learning_id)

    def needs_more_data(self, learning_id: str):
        return self.experiment_service.needs_more_data(learning_id)

    def deprecate_learning(self, learning_id: str):
        return self.experiment_service.deprecate_learning(learning_id)

    def edit_learning_statement(self, learning_id: str, statement: str, reason: str):
        return self.experiment_service.edit_learning_statement(learning_id, statement, reason)

    def list_learning_reviews(self, learning_id: str):
        return self.experiment_service.list_learning_reviews(learning_id)

