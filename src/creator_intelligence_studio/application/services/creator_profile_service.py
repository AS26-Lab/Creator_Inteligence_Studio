"""Servicio fino para perfil del creador."""

from __future__ import annotations

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorProfileService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def get_creator_profile(self, creator_id: str):
        return self.service.get_creator_profile(creator_id)

    def update_creator_profile(self, **kwargs):
        return self.service.update_creator_profile(**kwargs)

    def create_profile_snapshot(self, creator_id: str):
        return self.service.create_profile_snapshot(creator_id)

    def list_profile_snapshots(self, creator_id: str):
        return self.service.list_profile_snapshots(creator_id)

    def compare_profile_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str):
        return self.service.compare_profile_snapshots(creator_id, base_snapshot_id, compare_snapshot_id)

    def get_profile_detail(self, creator_id: str):
        return self.service.get_profile_detail(creator_id)

