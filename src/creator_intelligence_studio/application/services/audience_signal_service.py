"""Servicio de señales de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceSignalService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def normalize_signals(self, creator_id: str):
        return self.service.normalize_signals(creator_id)

    def list_signals(self, creator_id: str, *, platform: str | None = None):
        return self.service.list_signals(creator_id, platform=platform)

    def get_signal(self, signal_id: str):
        return self.service.get_signal(signal_id)

