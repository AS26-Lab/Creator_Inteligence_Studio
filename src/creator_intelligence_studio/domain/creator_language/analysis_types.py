"""Tipos de analisis y consulta para Creator Language Analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatorLanguageCorpusSelection:
    creator_id: str
    language: str | None = None
    platform: str | None = None
    content_type: str | None = None
    topic: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    approved_examples_only: bool = False


@dataclass(frozen=True, slots=True)
class CreatorLanguageQueryFilters:
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
class CreatorLanguageRetrievalResult:
    item_type: str
    item_id: str
    title: str
    summary: str
    scope: str | None
    platform: str | None
    content_type: str | None
    topic: str | None
    confidence_level: str
    score: float
    evidence_weight: float
    warnings: tuple[str, ...]
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "item_type": self.item_type,
            "item_id": self.item_id,
            "title": self.title,
            "summary": self.summary,
            "scope": self.scope,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "confidence_level": self.confidence_level,
            "score": self.score,
            "evidence_weight": self.evidence_weight,
            "warnings": list(self.warnings),
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class CreatorLanguageProfileComparison:
    creator_id: str
    base_profile_version: int
    compare_profile_version: int
    changed_sections: tuple[str, ...]
    base_summary: dict[str, object]
    compare_summary: dict[str, object]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "base_profile_version": self.base_profile_version,
            "compare_profile_version": self.compare_profile_version,
            "changed_sections": list(self.changed_sections),
            "base_summary": self.base_summary,
            "compare_summary": self.compare_summary,
            "warnings": list(self.warnings),
        }

