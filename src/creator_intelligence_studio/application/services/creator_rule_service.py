"""Servicio fino para reglas de estilo del creador."""

from __future__ import annotations

from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService


class CreatorRuleService:
    def __init__(self, service: CreatorMemoryService) -> None:
        self.service = service

    def list_style_rules(self, creator_id: str, filters: dict[str, object] | None = None):
        return self.service.list_style_rules(creator_id, filters=filters)

    def create_style_rule(self, **kwargs):
        return self.service.create_style_rule(**kwargs)

    def review_style_rule(self, rule_id: str, **kwargs):
        return self.service.review_style_rule(rule_id, **kwargs)

    def list_limits(self, creator_id: str):
        return self.service.list_limits(creator_id)

    def create_limit(self, **kwargs):
        return self.service.create_limit(**kwargs)

    def update_limit(self, limit_id: str, **kwargs):
        return self.service.update_limit(limit_id, **kwargs)

