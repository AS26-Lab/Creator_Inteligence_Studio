"""Canonical Creator Voice guidance contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .profile import CreatorVoiceConfidenceLevel, CreatorVoiceProfileStatus, CreatorVoiceProfileVersion
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


class CreatorVoiceGuidanceVersion(str, Enum):
    V1 = "creator-voice-guidance-v1"


class CreatorVoiceGuidanceState(str, Enum):
    DISABLED = "disabled"
    MISSING_PROFILE = "missing_profile"
    INSUFFICIENT_PROFILE = "insufficient_profile"
    PARTIAL = "partial"
    READY = "ready"


class CreatorVoiceGuidanceCategory(str, Enum):
    LENGTH = "length"
    SENTENCE_STRUCTURE = "sentence_structure"
    FORMATTING = "formatting"
    INTERACTION_STYLE = "interaction_style"
    PUNCTUATION = "punctuation"
    SPOKEN = "spoken"


class CreatorVoiceGuidanceOmissionReason(str, Enum):
    DISABLED = "disabled"
    MISSING_PROFILE = "missing_profile"
    INSUFFICIENT_PROFILE = "insufficient_profile"
    LOW_CONFIDENCE = "low_confidence"
    TOO_LITTLE_SIGNAL = "too_little_signal"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    WRONG_SCOPE = "wrong_scope"
    WRONG_LANGUAGE = "wrong_language"
    PREFERENCE_OVERRIDE = "preference_override"
    USER_OVERRIDE = "user_override"
    PROJECT_OVERRIDE = "project_override"
    PROFILE_CONFLICT = "profile_conflict"
    TOO_MUCH_GUIDANCE = "too_much_guidance"
    PRIVACY_FILTERED = "privacy_filtered"


@dataclass(frozen=True, slots=True)
class CreatorVoiceGuidanceRequest:
    creator_id: str
    workflow_type: str
    project_id: str | None = None
    language: str | None = None
    current_user_instruction: str | None = None
    project_instruction: str | None = None
    profile: object | None = None
    enabled: bool = True
    max_items: int = 4
    max_characters: int = 480

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "current_user_instruction": self.current_user_instruction,
            "project_instruction": self.project_instruction,
            "profile": None if self.profile is None else _serialize(self.profile),
            "enabled": self.enabled,
            "max_items": self.max_items,
            "max_characters": self.max_characters,
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceGuidanceItem:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str
    language: str | None
    category: CreatorVoiceGuidanceCategory
    guidance_key: str
    source_feature_id: str
    source_feature_key: str
    source_feature_title: str
    scope: CreatorVoiceScopeMode
    profile_status: CreatorVoiceProfileStatus
    profile_version: CreatorVoiceProfileVersion
    confidence: CreatorVoiceConfidenceLevel
    feature_status: str
    evidence_item_count: int
    independent_source_count: int
    source_feature_ids: tuple[str, ...]
    source_feature_value: object
    source_feature_basis: dict[str, object]
    guidance_text: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "category": self.category.value,
            "guidance_key": self.guidance_key,
            "source_feature_id": self.source_feature_id,
            "source_feature_key": self.source_feature_key,
            "source_feature_title": self.source_feature_title,
            "scope": self.scope.value,
            "profile_status": self.profile_status.value,
            "profile_version": self.profile_version.value,
            "confidence": self.confidence.value,
            "feature_status": self.feature_status,
            "evidence_item_count": self.evidence_item_count,
            "independent_source_count": self.independent_source_count,
            "source_feature_ids": list(self.source_feature_ids),
            "source_feature_value": _serialize(self.source_feature_value),
            "source_feature_basis": _serialize(self.source_feature_basis),
            "guidance_text": self.guidance_text,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceGuidanceOmission:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str
    language: str | None
    category: CreatorVoiceGuidanceCategory | None
    guidance_key: str | None
    source_feature_id: str | None
    source_feature_key: str | None
    reason: CreatorVoiceGuidanceOmissionReason
    detail: str
    scope: CreatorVoiceScopeMode | None
    confidence: CreatorVoiceConfidenceLevel | None
    profile_status: CreatorVoiceProfileStatus | None
    evidence_item_count: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "category": self.category.value if self.category else None,
            "guidance_key": self.guidance_key,
            "source_feature_id": self.source_feature_id,
            "source_feature_key": self.source_feature_key,
            "reason": self.reason.value,
            "detail": self.detail,
            "scope": self.scope.value if self.scope else None,
            "confidence": self.confidence.value if self.confidence else None,
            "profile_status": self.profile_status.value if self.profile_status else None,
            "evidence_item_count": self.evidence_item_count,
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceGuidanceConflict:
    id: str
    creator_id: str
    project_id: str | None
    workflow_type: str
    language: str | None
    override_type: str
    guidance_key: str
    source_feature_id: str | None
    source_feature_key: str | None
    blocker_text: str
    scope: CreatorVoiceScopeMode | None
    request_scope: str
    profile_status: CreatorVoiceProfileStatus | None
    profile_confidence: CreatorVoiceConfidenceLevel | None
    reason: str
    evidence_item_count: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "override_type": self.override_type,
            "guidance_key": self.guidance_key,
            "source_feature_id": self.source_feature_id,
            "source_feature_key": self.source_feature_key,
            "blocker_text": self.blocker_text,
            "scope": self.scope.value if self.scope else None,
            "request_scope": self.request_scope,
            "profile_status": self.profile_status.value if self.profile_status else None,
            "profile_confidence": self.profile_confidence.value if self.profile_confidence else None,
            "reason": self.reason,
            "evidence_item_count": self.evidence_item_count,
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceGuidanceBundle:
    creator_id: str
    project_id: str | None
    workflow_type: str
    language: str | None
    guidance_version: CreatorVoiceGuidanceVersion
    profile_fingerprint: str | None
    profile_version: CreatorVoiceProfileVersion | None
    profile_status: CreatorVoiceProfileStatus | None
    guidance_state: CreatorVoiceGuidanceState
    guidance_items: tuple[CreatorVoiceGuidanceItem, ...]
    omitted_items: tuple[CreatorVoiceGuidanceOmission, ...]
    conflicts: tuple[CreatorVoiceGuidanceConflict, ...]
    warnings: tuple[str, ...]
    budget_requested: dict[str, int]
    budget_used: dict[str, int]
    rendered_guidance: str
    request_trace: dict[str, object]
    bundle_fingerprint: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "guidance_version": self.guidance_version.value,
            "profile_fingerprint": self.profile_fingerprint,
            "profile_version": self.profile_version.value if self.profile_version else None,
            "profile_status": self.profile_status.value if self.profile_status else None,
            "guidance_state": self.guidance_state.value,
            "guidance_items": [item.to_dict() for item in self.guidance_items],
            "omitted_items": [item.to_dict() for item in self.omitted_items],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "warnings": list(self.warnings),
            "budget_requested": dict(self.budget_requested),
            "budget_used": dict(self.budget_used),
            "rendered_guidance": self.rendered_guidance,
            "request_trace": _serialize(self.request_trace),
            "bundle_fingerprint": self.bundle_fingerprint,
            "created_at": to_iso_z(self.created_at),
        }
