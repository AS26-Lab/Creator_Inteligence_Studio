"""Entidades de proyecto."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from creator_intelligence_studio.shared.dates import to_iso_z


class ProjectType(str, Enum):
    """Tipo de proyecto."""

    LONG_FORM = "long_form"
    SHORT_FORM = "short_form"
    MIXED = "mixed"
    RESEARCH = "research"


class ProjectStatus(str, Enum):
    """Estado del proyecto."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class Project:
    """Representa un proyecto de un creador."""

    id: str
    creator_id: str
    name: str
    description: str | None
    project_type: ProjectType
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type.value,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }

