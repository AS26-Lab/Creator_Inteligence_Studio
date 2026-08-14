"""Persisted-free Creator Voice profile contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import CreatorVoiceScopeMode


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


class CreatorVoiceProfileVersion(str, Enum):
    V1 = "creator-voice-profile-v1"


class CreatorVoiceProfileStatus(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PARTIAL = "partial"
    READY = "ready"


class CreatorVoiceFeatureStatus(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PARTIAL = "partial"
    READY = "ready"


class CreatorVoiceConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class CreatorVoiceFeature:
    id: str
    feature_key: str
    section_key: str
    title: str
    value: object
    unit: str | None
    status: CreatorVoiceFeatureStatus
    confidence: CreatorVoiceConfidenceLevel
    evidence_item_count: int
    independent_source_count: int
    weighted_evidence_count: float
    evidence_weight_sum: float
    evidence_basis: dict[str, object]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "feature_key": self.feature_key,
            "section_key": self.section_key,
            "title": self.title,
            "value": _serialize(self.value),
            "unit": self.unit,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "evidence_item_count": self.evidence_item_count,
            "independent_source_count": self.independent_source_count,
            "weighted_evidence_count": self.weighted_evidence_count,
            "evidence_weight_sum": self.evidence_weight_sum,
            "evidence_basis": _serialize(self.evidence_basis),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceProfileSection:
    id: str
    section_key: str
    title: str
    summary: str
    status: CreatorVoiceProfileStatus
    confidence: CreatorVoiceConfidenceLevel
    features: tuple[CreatorVoiceFeature, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "section_key": self.section_key,
            "title": self.title,
            "summary": self.summary,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "features": [feature.to_dict() for feature in self.features],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceStructuredPreference:
    id: str
    preference_key: str
    preference_type: str
    scope: CreatorVoiceScopeMode
    project_id: str | None
    workflow_type: str | None
    value: dict[str, object]
    rendered_text: str
    observed_pattern: str | None
    conflict: bool
    warning: str | None
    evidence_basis: dict[str, object]
    confirmed_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "preference_key": self.preference_key,
            "preference_type": self.preference_type,
            "scope": self.scope.value,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "value": _serialize(self.value),
            "rendered_text": self.rendered_text,
            "observed_pattern": self.observed_pattern,
            "conflict": self.conflict,
            "warning": self.warning,
            "evidence_basis": _serialize(self.evidence_basis),
            "confirmed_at": to_iso_z(self.confirmed_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceProfile:
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    language: str | None
    profile_version: CreatorVoiceProfileVersion
    feature_algorithm_version: str
    evidence_snapshot_fingerprint: str
    generated_at: datetime
    evidence_count: int
    confidence_summary: CreatorVoiceConfidenceLevel
    status: CreatorVoiceProfileStatus
    sections: tuple[CreatorVoiceProfileSection, ...]
    structured_preferences: tuple[CreatorVoiceStructuredPreference, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    summary: str
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "profile_version": self.profile_version.value,
            "feature_algorithm_version": self.feature_algorithm_version,
            "evidence_snapshot_fingerprint": self.evidence_snapshot_fingerprint,
            "generated_at": to_iso_z(self.generated_at),
            "evidence_count": self.evidence_count,
            "confidence_summary": self.confidence_summary.value,
            "status": self.status.value,
            "sections": [section.to_dict() for section in self.sections],
            "structured_preferences": [item.to_dict() for item in self.structured_preferences],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "summary": self.summary,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceProfileComparison:
    creator_id: str
    base_profile_fingerprint: str
    compare_profile_fingerprint: str
    changed_sections: tuple[str, ...]
    changed_features: tuple[str, ...]
    summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "base_profile_fingerprint": self.base_profile_fingerprint,
            "compare_profile_fingerprint": self.compare_profile_fingerprint,
            "changed_sections": list(self.changed_sections),
            "changed_features": list(self.changed_features),
            "summary": self.summary,
        }

