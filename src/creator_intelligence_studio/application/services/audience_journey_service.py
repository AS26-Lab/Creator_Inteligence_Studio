"""Servicio de journeys de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceJourneyService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def list_journeys(self, creator_id: str):
        return self.service.list_journeys(creator_id)

    def get_journey(self, journey_id: str):
        return self.service.get_journey(journey_id)

    def review_journey(self, *args, **kwargs):
        return self.service.review_journey(*args, **kwargs)

