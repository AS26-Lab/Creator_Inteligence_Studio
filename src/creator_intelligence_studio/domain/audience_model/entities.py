"""Entidades persistidas del modelo de audiencia."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .audience_types import (
    AudienceConfidenceLevel,
    AudienceModelRunStatus,
    AudienceReviewDecision,
    AudienceSignalType,
    AudienceStatus,
)
from .evidence_types import AudienceEvidenceType
from .lifecycle_types import AudienceLifecycleStage
from .segment_types import AudienceSegmentScope, AudienceSegmentType


@dataclass(frozen=True, slots=True)
class AudienceProfile:
    id: str
    creator_id: str
    profile_version: int
    status: AudienceStatus
    summary: str
    evidence_quality: str
    confidence_level: AudienceConfidenceLevel
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_version": self.profile_version,
            "status": self.status.value,
            "summary": self.summary,
            "evidence_quality": self.evidence_quality,
            "confidence_level": self.confidence_level.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceSignal:
    id: str
    creator_id: str
    platform: str
    channel_id: str | None
    publication_id: str | None
    remote_video_id: str | None
    signal_type: AudienceSignalType
    signal_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str | None
    period_start: datetime | None
    period_end: datetime | None
    observed_at: datetime
    source_type: str
    source_id: str | None
    dimensions_json: str
    quality_status: str
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "platform": self.platform,
            "channel_id": self.channel_id,
            "publication_id": self.publication_id,
            "remote_video_id": self.remote_video_id,
            "signal_type": self.signal_type.value,
            "signal_key": self.signal_key,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "period_start": to_iso_z(self.period_start),
            "period_end": to_iso_z(self.period_end),
            "observed_at": to_iso_z(self.observed_at),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "dimensions_json": self.dimensions_json,
            "quality_status": self.quality_status,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceSegmentDefinition:
    id: str
    segment_id: str
    rule_type: str
    field_key: str
    operator: str
    value_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "rule_type": self.rule_type,
            "field_key": self.field_key,
            "operator": self.operator,
            "value_json": self.value_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceSegmentEvidence:
    id: str
    segment_id: str
    signal_id: str | None
    publication_id: str | None
    analytics_finding_id: str | None
    experiment_id: str | None
    evidence_type: AudienceEvidenceType
    supports_segment: bool
    weight: float
    notes: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "signal_id": self.signal_id,
            "publication_id": self.publication_id,
            "analytics_finding_id": self.analytics_finding_id,
            "experiment_id": self.experiment_id,
            "evidence_type": self.evidence_type.value,
            "supports_segment": self.supports_segment,
            "weight": self.weight,
            "notes": self.notes,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceSegment:
    id: str
    creator_id: str
    name: str
    segment_type: AudienceSegmentType
    description: str
    scope: AudienceSegmentScope
    platform: str | None
    content_type: str | None
    topic: str | None
    lifecycle_stage: AudienceLifecycleStage | None
    status: AudienceStatus
    confidence_level: AudienceConfidenceLevel
    confidence_score: float | None
    supporting_signal_count: int
    contradicting_signal_count: int
    first_observed_at: datetime | None
    last_observed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "segment_type": self.segment_type.value,
            "description": self.description,
            "scope": self.scope.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "lifecycle_stage": None if self.lifecycle_stage is None else self.lifecycle_stage.value,
            "status": self.status.value,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "supporting_signal_count": self.supporting_signal_count,
            "contradicting_signal_count": self.contradicting_signal_count,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_observed_at": to_iso_z(self.last_observed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceAffinity:
    id: str
    creator_id: str
    segment_id: str | None
    affinity_type: str
    target_key: str
    target_value: str
    platform: str | None
    content_type: str | None
    score: float | None
    supporting_example_count: int
    contradicting_example_count: int
    confidence_level: AudienceConfidenceLevel
    status: AudienceStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "segment_id": self.segment_id,
            "affinity_type": self.affinity_type,
            "target_key": self.target_key,
            "target_value": self.target_value,
            "platform": self.platform,
            "content_type": self.content_type,
            "score": self.score,
            "supporting_example_count": self.supporting_example_count,
            "contradicting_example_count": self.contradicting_example_count,
            "confidence_level": self.confidence_level.value,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceJourneyStep:
    id: str
    journey_id: str
    step_order: int
    platform: str
    content_type: str | None
    action_type: str
    metric_key: str | None
    observed_value: float | None
    evidence_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "journey_id": self.journey_id,
            "step_order": self.step_order,
            "platform": self.platform,
            "content_type": self.content_type,
            "action_type": self.action_type,
            "metric_key": self.metric_key,
            "observed_value": self.observed_value,
            "evidence_json": self.evidence_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceJourney:
    id: str
    creator_id: str
    name: str
    entry_platform: str | None
    entry_source: str | None
    entry_content_type: str | None
    next_step_type: str | None
    conversion_type: str | None
    status: AudienceStatus
    confidence_level: AudienceConfidenceLevel
    evidence_json: str
    limitations_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "name": self.name,
            "entry_platform": self.entry_platform,
            "entry_source": self.entry_source,
            "entry_content_type": self.entry_content_type,
            "next_step_type": self.next_step_type,
            "conversion_type": self.conversion_type,
            "status": self.status.value,
            "confidence_level": self.confidence_level.value,
            "evidence_json": self.evidence_json,
            "limitations_json": self.limitations_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceProfileSnapshot:
    id: str
    creator_id: str
    profile_version: int
    snapshot_json: str
    source_fingerprint: str
    status: AudienceStatus
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
class AudienceReview:
    id: str
    creator_id: str
    target_type: str
    target_id: str
    decision: AudienceReviewDecision
    previous_value_json: str | None
    new_value_json: str | None
    reason: str
    reviewed_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "decision": self.decision.value,
            "previous_value_json": self.previous_value_json,
            "new_value_json": self.new_value_json,
            "reason": self.reason,
            "reviewed_at": to_iso_z(self.reviewed_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class AudienceModelRun:
    id: str
    creator_id: str
    status: AudienceModelRunStatus
    configuration_json: str
    source_fingerprint: str
    signal_count: int
    segment_count: int
    warning_count: int
    started_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "source_fingerprint": self.source_fingerprint,
            "signal_count": self.signal_count,
            "segment_count": self.segment_count,
            "warning_count": self.warning_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
        }
