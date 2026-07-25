"""Servicio fino para traits del creador."""

from __future__ import annotations

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorTraitService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def list_traits(self, creator_id: str, filters: dict[str, object] | None = None):
        return self.service.list_traits(creator_id, filters=filters)

    def create_trait(self, **kwargs):
        return self.service.create_trait(**kwargs)

    def update_trait(self, trait_id: str, **changes):
        return self.service.update_trait(trait_id, **changes)

    def archive_trait(self, trait_id: str):
        return self.service.archive_trait(trait_id)

    def add_trait_evidence(self, **kwargs):
        return self.service.add_trait_evidence(**kwargs)

    def list_trait_evidence(self, trait_id: str):
        return self.service.list_trait_evidence(trait_id)

