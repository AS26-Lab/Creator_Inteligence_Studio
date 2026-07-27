"""Servicio de revision humana de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceReviewService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def list_reviews(self, creator_id: str, *, target_type: str | None = None):
        return self.service.list_reviews(creator_id, target_type=target_type)

    def review_segment(self, *args, **kwargs):
        return self.service.review_segment(*args, **kwargs)

    def review_journey(self, *args, **kwargs):
        return self.service.review_journey(*args, **kwargs)

