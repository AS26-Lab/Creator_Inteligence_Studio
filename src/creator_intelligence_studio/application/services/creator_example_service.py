"""Servicio fino para ejemplos del creador."""

from __future__ import annotations

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorExampleService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def list_examples(self, creator_id: str, filters: dict[str, object] | None = None):
        return self.service.list_examples(creator_id, filters=filters)

    def create_example(self, **kwargs):
        return self.service.create_example(**kwargs)

    def review_example(self, example_id: str, **kwargs):
        return self.service.review_example(example_id, **kwargs)

