"""Controlled Creator Voice workflow application boundary."""

from __future__ import annotations

import json
import logging
from hashlib import sha256
from typing import Any

from creator_intelligence_studio.application.services.creator_voice_evidence_service import CreatorVoiceEvidenceService
from creator_intelligence_studio.application.services.creator_voice_guidance_service import CreatorVoiceGuidanceService
from creator_intelligence_studio.application.services.creator_voice_profile_service import CreatorVoiceProfileService
from creator_intelligence_studio.domain.creator_voice import (
    CreatorVoiceGuidanceBundle,
    CreatorVoiceGuidanceState,
    CreatorVoiceProfile,
    CreatorVoiceProfileStatus,
    CreatorVoiceWorkflowApplicationBundle,
    CreatorVoiceWorkflowApplicationRequest,
    CreatorVoiceWorkflowApplicationState,
    CreatorVoiceWorkflowApplicationVersion,
)
from creator_intelligence_studio.shared.dates import utc_now


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _stable_id(*parts: object) -> str:
    return sha256(_json_dumps(parts).encode("utf-8")).hexdigest()


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _language_key(value: str | None) -> str | None:
    normalized = _normalize_text(value).replace("_", "-").lower()
    return normalized or None
class CreatorVoiceWorkflowApplicationService:
    APPLICATION_VERSION = CreatorVoiceWorkflowApplicationVersion.V1
    DEFAULT_ALLOWED_WORKFLOWS = ("production_preparation",)

    def __init__(
        self,
        *,
        evidence_service: CreatorVoiceEvidenceService,
        profile_service: CreatorVoiceProfileService,
        guidance_service: CreatorVoiceGuidanceService,
        allowed_application_workflows: tuple[str, ...] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.evidence_service = evidence_service
        self.profile_service = profile_service
        self.guidance_service = guidance_service
        self.allowed_application_workflows = tuple(allowed_application_workflows or self.DEFAULT_ALLOWED_WORKFLOWS)
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_voice_workflow_application")

    def _normalize_request(self, request: CreatorVoiceWorkflowApplicationRequest | dict[str, object]) -> CreatorVoiceWorkflowApplicationRequest:
        if isinstance(request, CreatorVoiceWorkflowApplicationRequest):
            normalized = request
        elif isinstance(request, dict):
            normalized = CreatorVoiceWorkflowApplicationRequest(**request)
        else:
            raise TypeError("request must be a CreatorVoiceWorkflowApplicationRequest or dict.")
        creator_id = _normalize_text(normalized.creator_id)
        workflow_type = _normalize_text(normalized.workflow_type)
        if not creator_id:
            raise ValueError("creator_id is required.")
        if not workflow_type:
            raise ValueError("workflow_type is required.")
        return CreatorVoiceWorkflowApplicationRequest(
            creator_id=creator_id,
            project_id=_normalize_text(normalized.project_id) or None,
            workflow_type=workflow_type,
            language=_language_key(normalized.language),
            current_user_instruction=_normalize_text(normalized.current_user_instruction) or None,
            project_instruction=_normalize_text(normalized.project_instruction) or None,
            enabled=bool(normalized.enabled),
            apply_enabled=bool(normalized.apply_enabled),
            max_items=max(0, int(normalized.max_items)),
            max_characters=max(0, int(normalized.max_characters)),
            include_historical_versions=bool(normalized.include_historical_versions),
            include_creator_global_when_project_scope=bool(normalized.include_creator_global_when_project_scope),
            include_creator_global_when_workflow_scope=bool(normalized.include_creator_global_when_workflow_scope),
        )

    def _snapshot_request(self, request: CreatorVoiceWorkflowApplicationRequest) -> dict[str, object]:
        return {
            "creator_id": request.creator_id,
            "project_id": request.project_id,
            "workflow_type": request.workflow_type,
            "language": request.language,
            "include_historical_versions": request.include_historical_versions,
            "include_creator_global_when_project_scope": request.include_creator_global_when_project_scope,
            "include_creator_global_when_workflow_scope": request.include_creator_global_when_workflow_scope,
            "max_items": 24,
            "max_items_per_source": 3,
            "max_items_per_type": 8,
        }

    def _build_profile(self, request: CreatorVoiceWorkflowApplicationRequest) -> tuple[object | None, CreatorVoiceProfile | None]:
        snapshot = self.evidence_service.build_snapshot(self._snapshot_request(request))
        profile = self.profile_service.build_profile(snapshot)
        return snapshot, profile

    def _build_guidance(
        self,
        *,
        request: CreatorVoiceWorkflowApplicationRequest,
        profile: CreatorVoiceProfile | None,
    ) -> CreatorVoiceGuidanceBundle | None:
        if profile is None:
            return None
        payload = self.guidance_service.build_guidance(
            {
                "creator_id": request.creator_id,
                "project_id": request.project_id,
                "workflow_type": request.workflow_type,
                "language": request.language,
                "current_user_instruction": request.current_user_instruction,
                "project_instruction": request.project_instruction,
                "profile": profile,
                "enabled": True,
                "max_items": request.max_items,
                "max_characters": request.max_characters,
            }
        )
        return payload

    def build_application(self, request: CreatorVoiceWorkflowApplicationRequest | dict[str, object]) -> CreatorVoiceWorkflowApplicationBundle:
        normalized_request = self._normalize_request(request)
        if not normalized_request.enabled:
            return self._empty_bundle(
                normalized_request,
                application_state=CreatorVoiceWorkflowApplicationState.DISABLED,
                warnings=("voice_application_disabled",),
                profile=None,
                guidance_bundle=None,
            )

        snapshot, profile = self._build_profile(normalized_request)
        if profile is None:
            return self._empty_bundle(
                normalized_request,
                application_state=CreatorVoiceWorkflowApplicationState.MISSING_PROFILE,
                warnings=("profile_missing",),
                profile=None,
                guidance_bundle=None,
            )

        guidance_bundle = self._build_guidance(request=normalized_request, profile=profile)
        if guidance_bundle is None:
            return self._empty_bundle(
                normalized_request,
                application_state=CreatorVoiceWorkflowApplicationState.MISSING_PROFILE,
                warnings=("guidance_missing",),
                profile=profile,
                guidance_bundle=None,
            )

        allowed_for_application = normalized_request.workflow_type in self.allowed_application_workflows
        guidance_available = bool(guidance_bundle.guidance_items)
        applied = bool(normalized_request.apply_enabled and allowed_for_application and guidance_available and guidance_bundle.guidance_state == CreatorVoiceGuidanceState.READY)
        application_state = CreatorVoiceWorkflowApplicationState.APPLIED if applied else CreatorVoiceWorkflowApplicationState.SHADOW
        rendered_guidance = guidance_bundle.rendered_guidance if guidance_bundle is not None else ""
        warnings = list(guidance_bundle.warnings)
        if not allowed_for_application:
            warnings.append("workflow_shadow_only")
        if normalized_request.apply_enabled and not applied:
            warnings.append("voice_guidance_not_applied")
        if not guidance_available:
            warnings.append("no_consumable_voice_guidance")
        if profile.status == CreatorVoiceProfileStatus.PARTIAL:
            warnings.append("partial_profile")

        request_trace = {
            "enabled": normalized_request.enabled,
            "apply_enabled": normalized_request.apply_enabled,
            "allowed_for_application": allowed_for_application,
            "applied": applied,
            "profile_status": profile.status.value,
            "profile_confidence": profile.confidence_summary.value,
            "profile_fingerprint": profile.fingerprint,
            "guidance_state": guidance_bundle.guidance_state.value,
            "guidance_bundle_fingerprint": guidance_bundle.bundle_fingerprint,
            "guidance_item_ids": [item.id for item in guidance_bundle.guidance_items],
            "omitted_item_ids": [item.id for item in guidance_bundle.omitted_items],
            "conflict_ids": [item.id for item in guidance_bundle.conflicts],
            "snapshot_fingerprint": getattr(snapshot, "content_fingerprint", None),
        }
        bundle_fingerprint = _stable_id(
            {
                "application_version": self.APPLICATION_VERSION.value,
                "profile_fingerprint": profile.fingerprint,
                "guidance_bundle_fingerprint": guidance_bundle.bundle_fingerprint,
                "creator_id": normalized_request.creator_id,
                "project_id": normalized_request.project_id,
                "workflow_type": normalized_request.workflow_type,
                "language": normalized_request.language,
                "enabled": normalized_request.enabled,
                "apply_enabled": normalized_request.apply_enabled,
                "allowed_for_application": allowed_for_application,
                "applied": applied,
                "guidance_item_ids": [item.id for item in guidance_bundle.guidance_items],
                "omitted_item_ids": [item.id for item in guidance_bundle.omitted_items],
            }
        )
        return CreatorVoiceWorkflowApplicationBundle(
            creator_id=normalized_request.creator_id,
            project_id=normalized_request.project_id,
            workflow_type=normalized_request.workflow_type,
            language=normalized_request.language,
            application_version=self.APPLICATION_VERSION,
            profile_fingerprint=profile.fingerprint,
            profile_version=profile.profile_version,
            profile_status=profile.status,
            guidance_state=guidance_bundle.guidance_state,
            application_state=application_state,
            voice_guidance_shadow=True,
            voice_guidance_applied=applied,
            guidance_bundle=guidance_bundle,
            rendered_guidance=rendered_guidance,
            guidance_bundle_fingerprint=guidance_bundle.bundle_fingerprint,
            applied_guidance_item_ids=tuple(item.id for item in guidance_bundle.guidance_items) if applied else (),
            omitted_guidance_item_ids=tuple(item.id for item in guidance_bundle.omitted_items),
            warnings=tuple(dict.fromkeys(warnings)),
            request_trace=request_trace,
            bundle_fingerprint=bundle_fingerprint,
            created_at=utc_now(),
        )

    def _empty_bundle(
        self,
        request: CreatorVoiceWorkflowApplicationRequest,
        *,
        application_state: CreatorVoiceWorkflowApplicationState,
        warnings: tuple[str, ...],
        profile: CreatorVoiceProfile | None,
        guidance_bundle: CreatorVoiceGuidanceBundle | None,
    ) -> CreatorVoiceWorkflowApplicationBundle:
        profile_fingerprint = profile.fingerprint if profile else None
        guidance_bundle_fingerprint = guidance_bundle.bundle_fingerprint if guidance_bundle else None
        bundle_fingerprint = _stable_id(
            {
                "application_version": self.APPLICATION_VERSION.value,
                "profile_fingerprint": profile_fingerprint,
                "guidance_bundle_fingerprint": guidance_bundle_fingerprint,
                "creator_id": request.creator_id,
                "project_id": request.project_id,
                "workflow_type": request.workflow_type,
                "language": request.language,
                "enabled": request.enabled,
                "apply_enabled": request.apply_enabled,
                "application_state": application_state.value,
            }
        )
        return CreatorVoiceWorkflowApplicationBundle(
            creator_id=request.creator_id,
            project_id=request.project_id,
            workflow_type=request.workflow_type,
            language=request.language,
            application_version=self.APPLICATION_VERSION,
            profile_fingerprint=profile_fingerprint,
            profile_version=profile.profile_version if profile else None,
            profile_status=profile.status if profile else None,
            guidance_state=guidance_bundle.guidance_state if guidance_bundle else None,
            application_state=application_state,
            voice_guidance_shadow=False,
            voice_guidance_applied=False,
            guidance_bundle=guidance_bundle,
            rendered_guidance=guidance_bundle.rendered_guidance if guidance_bundle else "",
            guidance_bundle_fingerprint=guidance_bundle_fingerprint,
            applied_guidance_item_ids=(),
            omitted_guidance_item_ids=tuple(item.id for item in guidance_bundle.omitted_items) if guidance_bundle else (),
            warnings=warnings,
            request_trace={
                "enabled": request.enabled,
                "apply_enabled": request.apply_enabled,
                "application_state": application_state.value,
                "profile_status": profile.status.value if profile else None,
                "profile_fingerprint": profile_fingerprint,
                "guidance_bundle_fingerprint": guidance_bundle_fingerprint,
            },
            bundle_fingerprint=bundle_fingerprint,
            created_at=utc_now(),
        )

    def diagnostics(self, request: CreatorVoiceWorkflowApplicationRequest | dict[str, object], *, debug: bool = False) -> dict[str, object]:
        bundle = self.build_application(request)
        payload = bundle.to_dict()
        if not debug:
            payload["request_trace"] = dict(payload["request_trace"])
        return {
            "bundle": payload,
            "summary": {
                "creator_id": bundle.creator_id,
                "project_id": bundle.project_id,
                "workflow_type": bundle.workflow_type,
                "language": bundle.language,
                "application_state": bundle.application_state.value,
                "voice_guidance_shadow": bundle.voice_guidance_shadow,
                "voice_guidance_applied": bundle.voice_guidance_applied,
                "guidance_item_count": 0 if bundle.guidance_bundle is None else len(bundle.guidance_bundle.guidance_items),
                "omitted_count": 0 if bundle.guidance_bundle is None else len(bundle.guidance_bundle.omitted_items),
                "conflict_count": 0 if bundle.guidance_bundle is None else len(bundle.guidance_bundle.conflicts),
                "bundle_fingerprint": bundle.bundle_fingerprint,
            },
        }


def build_creator_voice_workflow_application_service(
    *,
    evidence_service: CreatorVoiceEvidenceService,
    profile_service: CreatorVoiceProfileService,
    guidance_service: CreatorVoiceGuidanceService,
    allowed_application_workflows: tuple[str, ...] | None = None,
    logger: logging.Logger | None = None,
) -> CreatorVoiceWorkflowApplicationService:
    return CreatorVoiceWorkflowApplicationService(
        evidence_service=evidence_service,
        profile_service=profile_service,
        guidance_service=guidance_service,
        allowed_application_workflows=allowed_application_workflows,
        logger=logger,
    )
