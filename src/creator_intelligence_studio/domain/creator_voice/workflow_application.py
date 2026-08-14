"""Canonical Creator Voice workflow application contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .guidance import CreatorVoiceGuidanceBundle, CreatorVoiceGuidanceState
from .profile import CreatorVoiceProfileStatus, CreatorVoiceProfileVersion


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


class CreatorVoiceWorkflowApplicationVersion(str, Enum):
    V1 = "creator-voice-workflow-application-v1"


class CreatorVoiceWorkflowApplicationState(str, Enum):
    DISABLED = "disabled"
    MISSING_PROFILE = "missing_profile"
    INSUFFICIENT_PROFILE = "insufficient_profile"
    SHADOW = "shadow"
    APPLIED = "applied"


@dataclass(frozen=True, slots=True)
class CreatorVoiceWorkflowApplicationRequest:
    creator_id: str
    workflow_type: str
    project_id: str | None = None
    language: str | None = None
    current_user_instruction: str | None = None
    project_instruction: str | None = None
    enabled: bool = True
    apply_enabled: bool = False
    max_items: int = 4
    max_characters: int = 480
    include_historical_versions: bool = False
    include_creator_global_when_project_scope: bool = True
    include_creator_global_when_workflow_scope: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "current_user_instruction": self.current_user_instruction,
            "project_instruction": self.project_instruction,
            "enabled": self.enabled,
            "apply_enabled": self.apply_enabled,
            "max_items": self.max_items,
            "max_characters": self.max_characters,
            "include_historical_versions": self.include_historical_versions,
            "include_creator_global_when_project_scope": self.include_creator_global_when_project_scope,
            "include_creator_global_when_workflow_scope": self.include_creator_global_when_workflow_scope,
        }


@dataclass(frozen=True, slots=True)
class CreatorVoiceWorkflowApplicationBundle:
    creator_id: str
    project_id: str | None
    workflow_type: str
    language: str | None
    application_version: CreatorVoiceWorkflowApplicationVersion
    profile_fingerprint: str | None
    profile_version: CreatorVoiceProfileVersion | None
    profile_status: CreatorVoiceProfileStatus | None
    guidance_state: CreatorVoiceGuidanceState | None
    application_state: CreatorVoiceWorkflowApplicationState
    voice_guidance_shadow: bool
    voice_guidance_applied: bool
    guidance_bundle: CreatorVoiceGuidanceBundle | None
    rendered_guidance: str
    guidance_bundle_fingerprint: str | None
    applied_guidance_item_ids: tuple[str, ...]
    omitted_guidance_item_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    request_trace: dict[str, object]
    bundle_fingerprint: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "application_version": self.application_version.value,
            "profile_fingerprint": self.profile_fingerprint,
            "profile_version": self.profile_version.value if self.profile_version else None,
            "profile_status": self.profile_status.value if self.profile_status else None,
            "guidance_state": self.guidance_state.value if self.guidance_state else None,
            "application_state": self.application_state.value,
            "voice_guidance_shadow": self.voice_guidance_shadow,
            "voice_guidance_applied": self.voice_guidance_applied,
            "guidance_bundle": None if self.guidance_bundle is None else self.guidance_bundle.to_dict(),
            "rendered_guidance": self.rendered_guidance,
            "guidance_bundle_fingerprint": self.guidance_bundle_fingerprint,
            "applied_guidance_item_ids": list(self.applied_guidance_item_ids),
            "omitted_guidance_item_ids": list(self.omitted_guidance_item_ids),
            "warnings": list(self.warnings),
            "request_trace": _serialize(self.request_trace),
            "bundle_fingerprint": self.bundle_fingerprint,
            "created_at": to_iso_z(self.created_at),
        }
