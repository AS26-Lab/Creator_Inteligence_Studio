"""Servicio de perfiles de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceProfileService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def build_profile(self, creator_id: str, *, force: bool = False, configuration: dict[str, object] | None = None):
        return self.service.build_profile(creator_id, force=force, configuration=configuration)

    def get_profile(self, creator_id: str, profile_version: int | None = None):
        return self.service.get_profile(creator_id, profile_version=profile_version)

    def get_profile_history(self, creator_id: str):
        return self.service.get_profile_history(creator_id)

    def compare_profiles(self, creator_id: str, base_version: int, compare_version: int):
        return self.service.compare_profiles(creator_id, base_version, compare_version)

