"""Persisted entities for creator preference synthesis and confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    CreatorPreferenceCandidateStatus,
    CreatorPreferenceConfidence,
    CreatorPreferenceScope,
    CreatorPreferenceType,
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
class CreatorPreferenceCandidate:
    id: str
    candidate_key: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    scope: CreatorPreferenceScope
    preference_type: CreatorPreferenceType
    proposed_value: str
    evidence_count: int
    supporting_signal_count: int
    conflicting_signal_count: int
    confidence: CreatorPreferenceConfidence
    status: CreatorPreferenceCandidateStatus
    dismissed_evidence_count: int
    source_signal_ids_json: str
    explanation_json: str
    algorithm_version: str
    first_observed_at: datetime
    last_observed_at: datetime
    confirmed_preference_id: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "candidate_key": self.candidate_key,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "scope": self.scope.value,
            "preference_type": self.preference_type.value,
            "proposed_value": self.proposed_value,
            "evidence_count": self.evidence_count,
            "supporting_signal_count": self.supporting_signal_count,
            "conflicting_signal_count": self.conflicting_signal_count,
            "confidence": self.confidence.value,
            "status": self.status.value,
            "dismissed_evidence_count": self.dismissed_evidence_count,
            "source_signal_ids_json": self.source_signal_ids_json,
            "explanation_json": self.explanation_json,
            "algorithm_version": self.algorithm_version,
            "first_observed_at": to_iso_z(self.first_observed_at),
            "last_observed_at": to_iso_z(self.last_observed_at),
            "confirmed_preference_id": self.confirmed_preference_id,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorConfirmedPreference:
    id: str
    preference_key: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    scope: CreatorPreferenceScope
    preference_type: CreatorPreferenceType
    value_json: str
    source_candidate_id: str | None
    confirmed_by: str
    confirmed_at: datetime
    active: bool
    provenance_json: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "preference_key": self.preference_key,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "scope": self.scope.value,
            "preference_type": self.preference_type.value,
            "value_json": self.value_json,
            "source_candidate_id": self.source_candidate_id,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": to_iso_z(self.confirmed_at),
            "active": self.active,
            "provenance_json": self.provenance_json,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorPreferenceCandidateEvidence:
    id: str
    candidate_id: str
    learning_signal_id: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "learning_signal_id": self.learning_signal_id,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorPreferenceSnapshot:
    creator_id: str
    generated_at: datetime
    candidate_count: int
    active_candidate_count: int
    confirmed_count: int
    active_confirmed_count: int
    dismissed_candidate_count: int
    conflict_count: int
    candidates: tuple[dict[str, object], ...]
    confirmed_preferences: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "generated_at": to_iso_z(self.generated_at),
            "candidate_count": self.candidate_count,
            "active_candidate_count": self.active_candidate_count,
            "confirmed_count": self.confirmed_count,
            "active_confirmed_count": self.active_confirmed_count,
            "dismissed_candidate_count": self.dismissed_candidate_count,
            "conflict_count": self.conflict_count,
            "candidates": [_serialize(candidate) for candidate in self.candidates],
            "confirmed_preferences": [_serialize(preference) for preference in self.confirmed_preferences],
        }
