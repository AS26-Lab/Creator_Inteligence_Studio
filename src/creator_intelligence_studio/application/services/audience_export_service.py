"""Servicio de exportacion de audiencia."""

from __future__ import annotations

from .audience_model_service import AudienceModelService


class AudienceExportService:
    def __init__(self, service: AudienceModelService) -> None:
        self.service = service

    def export(self, creator_id: str, format_name: str):
        return self.service.export(creator_id, format_name)

