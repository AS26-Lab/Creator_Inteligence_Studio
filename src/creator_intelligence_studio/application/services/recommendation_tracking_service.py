"""Wrapper de recomendacion manual."""

from __future__ import annotations

from creator_intelligence_studio.application.services.experiment_service import ExperimentService


class RecommendationTrackingService:
    def __init__(self, experiment_service: ExperimentService) -> None:
        self.experiment_service = experiment_service

    def list_recommendations(self, creator_id: str):
        return self.experiment_service.list_recommendations(creator_id)

    def get_recommendation(self, recommendation_id: str):
        return self.experiment_service.get_recommendation(recommendation_id)

    def create_recommendation(self, **kwargs):
        return self.experiment_service.create_recommendation(**kwargs)

    def decide_recommendation(self, recommendation_id: str, *, decision: str, reason: str, modified_value_json: str | None = None):
        return self.experiment_service.decide_recommendation(
            recommendation_id,
            decision=decision,
            reason=reason,
            modified_value_json=modified_value_json,
        )

