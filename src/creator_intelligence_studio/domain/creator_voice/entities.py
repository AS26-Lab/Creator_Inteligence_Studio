"""Persisted Creator Voice evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from creator_intelligence_studio.domain.creator_corpus.value_objects import CorpusAuthorshipClass

from .value_objects import (
    CreatorVoiceEvidenceQuality,
    CreatorVoiceEvidenceSourceKind,
    CreatorVoiceEvidenceType,
    CreatorVoiceScopeMode,
    CreatorVoiceSelectionPolicyVersion,
)


def _serialize(value: Any) -> object:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class CreatorVoiceEvidenceItem:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    document_id: str | None
    version_id: str | None
    segment_id: str | None
    authorship_class: CorpusAuthorshipClass | None
    evidence_type: CreatorVoiceEvidenceType
    text_reference: str | None
    language: str | None
    source_kind: CreatorVoiceEvidenceSourceKind
    confidence_state: str | None
    voice_learning_eligible: bool
    quality_flags: tuple[str, ...]
    provenance: str
    content_hash: str
    created_at: datetime
    evidence_quality: CreatorVoiceEvidenceQuality
    evidence_weight: float
    qualification_reason: str
    source_identity: str
    source_scope: CreatorVoiceScopeMode

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "segment_id": self.segment_id,
            "authorship_class": self.authorship_class.value if self.authorship_class else None,
            "evidence_type": self.evidence_type.value,
            "language": self.language,
            "source_kind": self.source_kind.value,
            "confidence_state": self.confidence_state,
            "voice_learning_eligible": self.voice_learning_eligible,
            "quality_flags": list(self.quality_flags),
            "provenance": self.provenance,
            "content_hash": self.content_hash,
            "created_at": to_iso_z(self.created_at),
            "evidence_quality": self.evidence_quality.value,
            "evidence_weight": self.evidence_weight,
            "qualification_reason": self.qualification_reason,
            "source_identity": self.source_identity,
            "source_scope": self.source_scope.value,
        }

    def to_public_dict(self, *, include_reference: bool = False) -> dict[str, object]:
        payload = self.to_dict()
        if include_reference:
            payload["text_reference"] = self.text_reference
        return payload


@dataclass(frozen=True, slots=True)
class CreatorVoiceEvidenceExclusion:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    document_id: str | None
    version_id: str | None
    segment_id: str | None
    evidence_type: CreatorVoiceEvidenceType | None
    source_kind: CreatorVoiceEvidenceSourceKind
    language: str | None
    reason: str
    quality_flags: tuple[str, ...]
    source_identity: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "segment_id": self.segment_id,
            "evidence_type": self.evidence_type.value if self.evidence_type else None,
            "source_kind": self.source_kind.value,
            "language": self.language,
            "reason": self.reason,
            "quality_flags": list(self.quality_flags),
            "source_identity": self.source_identity,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceEvidenceSnapshot:
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    language: str | None
    policy_version: CreatorVoiceSelectionPolicyVersion
    source_scope: CreatorVoiceScopeMode
    generated_at: datetime
    evidence_items: tuple[CreatorVoiceEvidenceItem, ...]
    excluded_candidates: tuple[CreatorVoiceEvidenceExclusion, ...]
    evidence_count: int
    category_counts: dict[str, int]
    quality_counts: dict[str, int]
    excluded_counts: dict[str, int]
    language_distribution: dict[str, int]
    project_distribution: dict[str, int]
    workflow_distribution: dict[str, int]
    total_estimated_words: int
    total_estimated_characters: int
    content_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "policy_version": self.policy_version.value,
            "source_scope": self.source_scope.value,
            "generated_at": to_iso_z(self.generated_at),
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "excluded_candidates": [item.to_dict() for item in self.excluded_candidates],
            "evidence_count": self.evidence_count,
            "category_counts": dict(self.category_counts),
            "quality_counts": dict(self.quality_counts),
            "excluded_counts": dict(self.excluded_counts),
            "language_distribution": dict(self.language_distribution),
            "project_distribution": dict(self.project_distribution),
            "workflow_distribution": dict(self.workflow_distribution),
            "total_estimated_words": self.total_estimated_words,
            "total_estimated_characters": self.total_estimated_characters,
            "content_fingerprint": self.content_fingerprint,
        }

    def to_debug_dict(self) -> dict[str, object]:
        payload = self.to_dict()
        payload["evidence_items"] = [item.to_public_dict(include_reference=True) for item in self.evidence_items]
        return payload

