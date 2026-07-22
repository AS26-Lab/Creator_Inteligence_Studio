"""Entidades de creador."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.shared.dates import to_iso_z


class CreatorStatus(str, Enum):
    """Estado del creador."""

    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Creator:
    """Representa un creador del sistema."""

    id: str
    display_name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    status: CreatorStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "slug": self.slug,
            "description": self.description,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
            "status": self.status.value,
        }

