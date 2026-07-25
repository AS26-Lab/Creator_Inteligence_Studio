"""Tipos auxiliares de consulta y versionado de memoria."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z


@dataclass(frozen=True, slots=True)
class CreatorMemoryQueryFilters:
    creator_id: str
    query: str | None = None
    platform: str | None = None
    content_type: str | None = None
    topic: str | None = None
    trait_type: str | None = None
    example_type: str | None = None
    approval_status: str | None = None
    confidence_level: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class CreatorMemoryRetrievalResult:
    item_type: str
    item_id: str
    title: str
    summary: str | None
    platform: str | None
    content_type: str | None
    topic: str | None
    scope: str | None
    status: str
    confidence_level: str | None
    approval_status: str | None
    evidence_weight: float
    recency_score: float
    match_score: float
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "item_type": self.item_type,
            "item_id": self.item_id,
            "title": self.title,
            "summary": self.summary,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "scope": self.scope,
            "status": self.status,
            "confidence_level": self.confidence_level,
            "approval_status": self.approval_status,
            "evidence_weight": self.evidence_weight,
            "recency_score": self.recency_score,
            "match_score": self.match_score,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorProfileSnapshotComparison:
    creator_id: str
    base_snapshot_id: str
    compare_snapshot_id: str
    base_version: int
    compare_version: int
    changed_fields: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "base_snapshot_id": self.base_snapshot_id,
            "compare_snapshot_id": self.compare_snapshot_id,
            "base_version": self.base_version,
            "compare_version": self.compare_version,
            "changed_fields": list(self.changed_fields),
            "summary": self.summary,
        }
