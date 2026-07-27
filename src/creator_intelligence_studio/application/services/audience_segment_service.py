"""Servicio de segmentos de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceSegmentService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def list_segments(self, creator_id: str):
        return self.service.list_segments(creator_id)

    def create_segment(self, **kwargs):
        return self.service.create_segment(**kwargs)

    def review_segment(self, *args, **kwargs):
        return self.service.review_segment(*args, **kwargs)

    def archive_segment(self, segment_id: str):
        return self.service.archive_segment(segment_id)

    def get_segment(self, segment_id: str):
        return self.service.get_segment(segment_id)

