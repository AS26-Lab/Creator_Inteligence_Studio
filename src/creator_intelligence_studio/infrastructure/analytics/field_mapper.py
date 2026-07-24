"""Mapeo reutilizable de columnas de analytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.analytics.entities import AnalyticsFieldMapping
from creator_intelligence_studio.domain.analytics.value_objects import AnalyticsFieldMappingOrigin


@dataclass(frozen=True, slots=True)
class FieldMappingPlan:
    mapping_name: str
    platform: str
    creator_id: str | None
    mappings: tuple[AnalyticsFieldMapping, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "mapping_name": self.mapping_name,
            "platform": self.platform,
            "creator_id": self.creator_id,
            "mappings": [mapping.to_dict() for mapping in self.mappings],
        }


def build_field_mapping(
    *,
    mapping_name: str,
    platform: str,
    creator_id: str | None,
    source_field: str,
    target_field: str,
    transformation: str = "identity",
    confidence: float = 1.0,
    origin: AnalyticsFieldMappingOrigin = AnalyticsFieldMappingOrigin.AUTO,
    is_active: bool = True,
    mapping_id: str,
) -> AnalyticsFieldMapping:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return AnalyticsFieldMapping(
        id=mapping_id,
        creator_id=creator_id,
        platform=platform,
        mapping_name=mapping_name,
        source_field=source_field,
        target_field=target_field,
        transformation=transformation,
        confidence=confidence,
        mapping_origin=origin,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
