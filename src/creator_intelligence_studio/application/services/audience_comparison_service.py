"""Servicio de comparacion de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceComparisonService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def compare_profiles(self, creator_id: str, base_version: int, compare_version: int):
        return self.service.compare_profiles(creator_id, base_version, compare_version)

