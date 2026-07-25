"""Entidades persistidas para Creator Memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    CreatorExampleApprovalStatus,
    CreatorExampleType,
    CreatorFeedbackType,
    CreatorLimitSeverity,
    CreatorLimitStatus,
    CreatorLimitType,
    CreatorMemoryConfidenceLevel,
    CreatorMemoryScope,
    CreatorObjectiveStatus,
    CreatorProfileStatus,
    CreatorRuleReviewDecision,
    CreatorRuleStatus,
    CreatorSnapshotStatus,
    CreatorTraitStatus,
    CreatorTraitType,
    CreatorVocabularyStatus,
    CreatorVocabularyType,
    CreatorEvidenceType,
)


@dataclass(frozen=True, slots=True)
class CreatorProfile:
    id: str
    creator_id: str
    display_name: str
    profile_version: int
    status: CreatorProfileStatus
    summary: str | None
    primary_language: str | None
    secondary_languages_json: str
    default_tone: str | None
    default_formality: str | None
    objectives_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "display_name": self.display_name,
            "profile_version": self.profile_version,
            "status": self.status.value,
            "summary": self.summary,
            "primary_language": self.primary_language,
            "secondary_languages_json": self.secondary_languages_json,
            "default_tone": self.default_tone,
            "default_formality": self.default_formality,
            "objectives_json": self.objectives_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorTrait:
    id: str
    creator_id: str
    trait_type: CreatorTraitType
    trait_key: str
    display_name: str
    description: str | None
    value_json: str
    scope: CreatorMemoryScope
    platform: str | None
    content_type: str | None
    topic: str | None
    confidence_level: CreatorMemoryConfidenceLevel
    confidence_score: float | None
    status: CreatorTraitStatus
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "trait_type": self.trait_type.value,
            "trait_key": self.trait_key,
            "display_name": self.display_name,
            "description": self.description,
            "value_json": self.value_json,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "status": self.status.value,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_observed_at": to_iso_z(self.last_observed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorTraitEvidence:
    id: str
    trait_id: str
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
            "id": self.id,
            "trait_id": self.trait_id,
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


@dataclass(frozen=True, slots=True)
class CreatorExample:
    id: str
    creator_id: str
    example_type: CreatorExampleType
    category: str
    platform: str | None
    content_type: str | None
    topic: str | None
    title: str
    text_content: str | None
    source_type: str
    source_id: str | None
    publication_id: str | None
    video_asset_id: str | None
    start_seconds: float | None
    end_seconds: float | None
    representativeness: float | None
    approval_status: CreatorExampleApprovalStatus
    approval_reason: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "example_type": self.example_type.value,
            "category": self.category,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "title": self.title,
            "text_content": self.text_content,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "representativeness": self.representativeness,
            "approval_status": self.approval_status.value,
            "approval_reason": self.approval_reason,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorVocabulary:
    id: str
    creator_id: str
    term: str
    normalized_term: str
    vocabulary_type: CreatorVocabularyType
    meaning: str | None
    usage_notes: str | None
    platform: str | None
    content_type: str | None
    frequency_count: int
    confidence_level: CreatorMemoryConfidenceLevel
    status: CreatorVocabularyStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "term": self.term,
            "normalized_term": self.normalized_term,
            "vocabulary_type": self.vocabulary_type.value,
            "meaning": self.meaning,
            "usage_notes": self.usage_notes,
            "platform": self.platform,
            "content_type": self.content_type,
            "frequency_count": self.frequency_count,
            "confidence_level": self.confidence_level.value,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorStyleRule:
    id: str
    creator_id: str
    rule_type: CreatorStyleRuleType
    scope: CreatorMemoryScope
    platform: str | None
    content_type: str | None
    topic: str | None
    statement: str
    rationale: str | None
    status: CreatorRuleStatus
    confidence_level: CreatorMemoryConfidenceLevel
    supporting_example_count: int
    contradicting_example_count: int
    first_observed_at: datetime | None
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "rule_type": self.rule_type.value,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "statement": self.statement,
            "rationale": self.rationale,
            "status": self.status.value,
            "confidence_level": self.confidence_level.value,
            "supporting_example_count": self.supporting_example_count,
            "contradicting_example_count": self.contradicting_example_count,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_reviewed_at": to_iso_z(self.last_reviewed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorStyleRuleReview:
    id: str
    rule_id: str
    decision: CreatorRuleReviewDecision
    previous_statement: str | None
    new_statement: str | None
    reason: str
    reviewed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "decision": self.decision.value,
            "previous_statement": self.previous_statement,
            "new_statement": self.new_statement,
            "reason": self.reason,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLimit:
    id: str
    creator_id: str
    limit_type: CreatorLimitType
    category: str
    statement: str
    severity: CreatorLimitSeverity
    scope: CreatorMemoryScope
    platform: str | None
    status: CreatorLimitStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "limit_type": self.limit_type.value,
            "category": self.category,
            "statement": self.statement,
            "severity": self.severity.value,
            "scope": self.scope.value,
            "platform": self.platform,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorProfileSnapshot:
    id: str
    creator_id: str
    profile_version: int
    snapshot_json: str
    source_fingerprint: str
    status: CreatorSnapshotStatus
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_version": self.profile_version,
            "snapshot_json": self.snapshot_json,
            "source_fingerprint": self.source_fingerprint,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorMemoryFeedback:
    id: str
    creator_id: str
    target_type: str
    target_id: str
    feedback_type: CreatorFeedbackType
    reason: str
    corrected_value_json: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "feedback_type": self.feedback_type.value,
            "reason": self.reason,
            "corrected_value_json": self.corrected_value_json,
            "created_at": to_iso_z(self.created_at),
        }

