"""Tipos de evidencia del creador."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import CreatorEvidenceType


@dataclass(frozen=True, slots=True)
class CreatorEvidenceLink:
    source_type: str
    source_id: str | None
    publication_id: str | None
    video_asset_id: str | None
    transcript_segment_id: str | None
    start_seconds: float | None
    end_seconds: float | None
    quoted_text: str | None
    evidence_type: CreatorEvidenceType
    supports_trait: bool
    weight: float
    notes: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "transcript_segment_id": self.transcript_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "quoted_text": self.quoted_text,
            "evidence_type": self.evidence_type.value,
            "supports_trait": self.supports_trait,
            "weight": self.weight,
            "notes": self.notes,
            "created_at": to_iso_z(self.created_at),
        }

