"""Servicio de afinidades de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceAffinityService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def list_affinities(self, creator_id: str):
        return self.service.list_affinities(creator_id)

    def get_affinity(self, affinity_id: str):
        return self.service.get_affinity(affinity_id)

