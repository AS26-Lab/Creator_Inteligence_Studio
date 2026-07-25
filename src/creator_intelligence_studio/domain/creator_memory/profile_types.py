"""Tipos auxiliares del perfil del creador."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import CreatorObjectiveStatus, CreatorObjectiveType


@dataclass(frozen=True, slots=True)
class CreatorObjectiveEntry:
    objective_type: CreatorObjectiveType
    priority: int
    platform: str | None
    period: str | None
    notes: str | None
    status: CreatorObjectiveStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "objective_type": self.objective_type.value,
            "priority": self.priority,
            "platform": self.platform,
            "period": self.period,
            "notes": self.notes,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class CreatorProfileSummary:
    creator_id: str
    display_name: str
    profile_version: int
    status: str
    primary_language: str | None
    default_tone: str | None
    default_formality: str | None
    objective_count: int
    trait_count: int
    example_count: int
    vocabulary_count: int
    rule_count: int
    limit_count: int
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "display_name": self.display_name,
            "profile_version": self.profile_version,
            "status": self.status,
            "primary_language": self.primary_language,
            "default_tone": self.default_tone,
            "default_formality": self.default_formality,
            "objective_count": self.objective_count,
            "trait_count": self.trait_count,
            "example_count": self.example_count,
            "vocabulary_count": self.vocabulary_count,
            "rule_count": self.rule_count,
            "limit_count": self.limit_count,
            "updated_at": to_iso_z(self.updated_at),
        }

