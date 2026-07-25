"""Servicio fino de consultas de memoria."""

from __future__ import annotations

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorMemoryQueryService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def retrieve_creator_context(self, creator_id: str, query_filters):
        return self.service.retrieve_creator_context(creator_id, query_filters)

    def list_feedback(self, creator_id: str):
        return self.service.list_feedback(creator_id)

    def record_memory_feedback(self, **kwargs):
        return self.service.record_memory_feedback(**kwargs)

    def get_profile_detail(self, creator_id: str):
        return self.service.get_profile_detail(creator_id)

