"""Persisted entities for creator feedback and learning signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    CreatorFeedbackEventSource,
    CreatorFeedbackEventType,
    CreatorFeedbackExplicitness,
    CreatorFeedbackScope,
    CreatorLearningSignalConfidence,
    CreatorLearningSignalPolarity,
    CreatorLearningSignalStatus,
    CreatorLearningSignalType,
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
class CreatorFeedbackEvent:
    id: str
    dedupe_key: str
    creator_id: str
    project_id: str | None
    workflow_type: str
    artifact_type: str
    artifact_id: str
    source_version_id: str | None
    result_version_id: str | None
    ai_execution_id: str | None
    event_type: CreatorFeedbackEventType
    event_source: CreatorFeedbackEventSource
    signal_explicitness: CreatorFeedbackExplicitness
    created_at: datetime
    metadata_json: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "dedupe_key": self.dedupe_key,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "source_version_id": self.source_version_id,
            "result_version_id": self.result_version_id,
            "ai_execution_id": self.ai_execution_id,
            "event_type": self.event_type.value,
            "event_source": self.event_source.value,
            "signal_explicitness": self.signal_explicitness.value,
            "created_at": to_iso_z(self.created_at),
            "metadata_json": self.metadata_json,
        }


@dataclass(frozen=True, slots=True)
class CreatorLearningSignal:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    scope: CreatorFeedbackScope
    signal_type: CreatorLearningSignalType
    signal_value: str
    polarity: CreatorLearningSignalPolarity
    strength: float
    confidence: CreatorLearningSignalConfidence
    evidence_count: int
    supporting_event_count: int
    contradicting_event_count: int
    status: CreatorLearningSignalStatus
    first_observed_at: datetime
    last_observed_at: datetime
    algorithm_version: str
    metadata_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "scope": self.scope.value,
            "signal_type": self.signal_type.value,
            "signal_value": self.signal_value,
            "polarity": self.polarity.value,
            "strength": self.strength,
            "confidence": self.confidence.value,
            "evidence_count": self.evidence_count,
            "supporting_event_count": self.supporting_event_count,
            "contradicting_event_count": self.contradicting_event_count,
            "status": self.status.value,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_observed_at": to_iso_z(self.last_observed_at),
            "algorithm_version": self.algorithm_version,
            "metadata_json": self.metadata_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLearningSignalEvidence:
    id: str
    signal_id: str
    feedback_event_id: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "feedback_event_id": self.feedback_event_id,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorLearningSnapshot:
    creator_id: str
    generated_at: datetime
    feedback_event_count: int
    active_signal_count: int
    candidate_signal_count: int
    dismissed_signal_count: int
    orphan_evidence_count: int
    signals: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "generated_at": to_iso_z(self.generated_at),
            "feedback_event_count": self.feedback_event_count,
            "active_signal_count": self.active_signal_count,
            "candidate_signal_count": self.candidate_signal_count,
            "dismissed_signal_count": self.dismissed_signal_count,
            "orphan_evidence_count": self.orphan_evidence_count,
            "signals": [_serialize(signal) for signal in self.signals],
        }

