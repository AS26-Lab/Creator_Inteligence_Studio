"""Servicio determinista para Script Outline and Production Preparation Foundation."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import NAMESPACE_URL, uuid4, uuid5

from creator_intelligence_studio.application.services.content_brief_service import ContentBriefService
from creator_intelligence_studio.application.services.creator_context_assembly_service import CreatorContextAssemblyService
from creator_intelligence_studio.application.services.creator_context_policy import (
    CreatorContextPolicyRegistry,
    build_default_creator_context_policy_registry,
)
from creator_intelligence_studio.application.services.creator_preference_application_service import (
    CreatorPreferenceApplicationBundle,
    CreatorPreferenceApplicationService,
)
from creator_intelligence_studio.application.services.creator_voice_workflow_application_service import (
    CreatorVoiceWorkflowApplicationBundle,
    CreatorVoiceWorkflowApplicationService,
)
from creator_intelligence_studio.domain.content_briefs import (
    BriefRecord,
    BriefStatus,
    ClaimVerificationStatus,
    CopyingRiskLevel,
    RightsStatus,
)
from creator_intelligence_studio.domain.production_preparation import (
    ApprovalGateType,
    AssetType,
    BeatType,
    ContinuityType,
    DependencyType,
    EquipmentType,
    LifecycleStatus,
    LocationType,
    MilestoneType,
    OutlineSectionType,
    ParticipantType,
    PlatformAdaptationType,
    ProductionPreparationConflictError,
    ProductionPreparationNotFoundError,
    ProductionPreparationStateError,
    ProductionPreparationValidationError,
    ProductionRecord,
    ProductionRequestStatus,
    ReadinessStatus,
    RecordingBlockType,
    RiskType,
    ScriptOutlineStatus,
    ScriptOutlineType,
    SegmentType,
    ShotType,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import to_iso_z, utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_loads(payload: str | None, fallback: object) -> object:
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return fallback if value is None else value
    except json.JSONDecodeError:
        return fallback


def _now() -> str:
    return to_iso_z(utc_now()) or ""


def _stable_id(*parts: str) -> str:
    return str(uuid5(NAMESPACE_URL, "::".join(parts)))


def _safe_list(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_csv_value(value: object) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def build_production_fingerprint(payload: object) -> str:
    return _stable_id("production-fingerprint", _json_dumps(payload))


def _enum_value(enum_cls, value: Any, default: Any):
    try:
        if isinstance(value, enum_cls):
            return value
    except TypeError:
        pass
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except Exception:
        return default


def _row_to_entity(row: dict[str, Any] | None, *, enum_fields: dict[str, Any] | None = None) -> ProductionRecord | None:
    if row is None:
        return None
    payload = dict(row)
    for field, enum_cls in (enum_fields or {}).items():
        if field in payload:
            payload[field] = _enum_value(enum_cls, payload[field], payload[field])
    return ProductionRecord(**payload)


class ProductionPreparationService:
    ENGINE_VERSION = "v30"

    def __init__(
        self,
        *,
        settings: AppSettings | None,
        paths: ProjectPaths,
        repository,
        brief_service: ContentBriefService | None = None,
        planning_service: Any | None = None,
        recommendation_service: Any | None = None,
        experiment_service: Any | None = None,
        content_library_service: Any | None = None,
        creator_memory_service: Any | None = None,
        creator_language_service: Any | None = None,
        creator_context_assembly_service: CreatorContextAssemblyService | None = None,
        creator_preference_application_service: CreatorPreferenceApplicationService | None = None,
        creator_voice_workflow_application_service: CreatorVoiceWorkflowApplicationService | None = None,
        creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
        audience_service: Any | None = None,
        platform_service: Any | None = None,
        packaging_service: Any | None = None,
        preferences: dict[str, object] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.brief_service = brief_service
        self.planning_service = planning_service
        self.recommendation_service = recommendation_service
        self.experiment_service = experiment_service
        self.content_library_service = content_library_service
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.creator_context_assembly_service = creator_context_assembly_service
        self.creator_preference_application_service = creator_preference_application_service
        self.creator_voice_workflow_application_service = creator_voice_workflow_application_service
        self.creator_context_policy_registry = creator_context_policy_registry or build_default_creator_context_policy_registry()
        self.audience_service = audience_service
        self.platform_service = platform_service
        self.packaging_service = packaging_service
        self.creator_feedback_service = None
        self.preferences = {
            "default_outline_type": ScriptOutlineType.UNKNOWN.value,
            "default_platform": [],
            "default_content_type": [],
            "require_human_review": True,
            "allow_automatic_approval": False,
            "allow_ready_for_recording_without_all_gates": False,
            "require_verified_claims": True,
            "require_rights_clearance": True,
            "require_participant_releases": True,
            "require_location_permissions": True,
            "require_continuity_review": True,
            "require_equipment_backup": True,
            "require_measurement_plan": True,
            "maximum_copying_risk": CopyingRiskLevel.HIGH.value,
            "default_target_duration_seconds": 180,
            "default_words_per_minute": 130,
            "max_sections_per_outline": 10,
            "max_beats_per_outline": 20,
            "max_segments_per_outline": 20,
            "max_scenes_per_outline": 20,
            "max_shots_per_scene": 6,
            "max_recording_blocks": 8,
            "recording_order_optimization_enabled": True,
            "automatic_script_generation": False,
            "automatic_media_generation": False,
            "automatic_recording": False,
            "automatic_editing": False,
            "automatic_publication": False,
            "production_cache_hours": 24,
            "report_default_format": "json",
        } | (preferences or {})
        self.logger = logger or logging.getLogger("creator_intelligence_studio.production_preparation")
        self._reports_root = self.paths.data_directory / "production" / "reports"
        self._snapshots_root = self.paths.data_directory / "production" / "snapshots"
        self._reports_root.mkdir(parents=True, exist_ok=True)
        self._snapshots_root.mkdir(parents=True, exist_ok=True)
        self._list_accessors: dict[str, tuple[str, str, dict[str, Any] | None]] = {
            "list_sections": ("outline_sections", "script_outline_id", {"required": None}),
            "list_beats": ("outline_beats", "script_outline_id", {"required": None}),
            "list_segments": ("outline_segments", "script_outline_id", {"required": None}),
            "list_talking_point_links": ("outline_talking_point_links", "script_outline_id", {"required": None}),
            "list_claim_links": ("outline_claim_links", "script_outline_id", {"verification_required": None}),
            "list_proof_requirements": ("outline_proof_requirements", "script_outline_id", {"readiness_status": None}),
            "list_scenes": ("production_scene_plans", "script_outline_id", {"required": None}),
            "list_shots": ("production_shot_items", "script_outline_id", {"required": None}),
            "list_shot_groups": ("production_shot_groups", "script_outline_id", {"status": None}),
            "list_shot_group_items": ("production_shot_group_items", "shot_group_id", None),
            "list_recording_blocks": ("production_recording_blocks", "script_outline_id", {"status": None}),
            "list_recording_block_items": ("production_recording_block_items", "recording_block_id", None),
            "list_visual_cues": ("production_visual_cues", "script_outline_id", {"required": None}),
            "list_audio_cues": ("production_audio_cues", "script_outline_id", {"required": None}),
            "list_on_screen_text": ("production_on_screen_text", "script_outline_id", {"required": None}),
            "list_broll_requirements": ("production_broll_requirements", "script_outline_id", {"readiness_status": None}),
            "list_graphic_requirements": ("production_graphic_requirements", "script_outline_id", {"readiness_status": None}),
            "list_screen_recordings": ("production_screen_recordings", "script_outline_id", {"readiness_status": None}),
            "list_participants": ("production_participant_requirements", "script_outline_id", {"release_status": None}),
            "list_locations": ("production_location_requirements", "script_outline_id", {"permission_status": None}),
            "list_props": ("production_prop_requirements", "script_outline_id", {"rights_status": None}),
            "list_wardrobe": ("production_wardrobe_requirements", "script_outline_id", {"rights_or_brand_status": None}),
            "list_equipment": ("production_equipment_requirements", "script_outline_id", {"availability_status": None}),
            "list_continuity": ("production_continuity_rules", "script_outline_id", {"blocking": None}),
            "list_variants": ("production_platform_variants", "script_outline_id", {"status": None}),
            "list_reusable_segments": ("production_reusable_segments", "script_outline_id", {"status": None}),
            "list_dependencies": ("production_dependencies", "script_outline_id", {"blocking": None}),
            "list_milestones": ("production_milestones", "script_outline_id", {"status": None}),
            "list_checklists": ("production_checklists", "script_outline_id", {"status": None}),
            "list_checklist_items": ("production_checklist_items", "production_checklist_id", {"status": None}),
            "list_gates": ("production_approval_gates", "script_outline_id", {"status": None}),
            "list_risks": ("production_risks", "script_outline_id", {"severity": None}),
            "list_reviews": ("production_reviews", "script_outline_id", {"decision": None}),
            "list_snapshots": ("production_snapshots", "script_outline_id", None),
            "list_reports": ("production_reports", "script_outline_id", None),
        }

    def _build_creator_voice_application_bundle(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str,
        language: str | None,
        current_user_instruction: str | None,
        project_instruction: str | None,
        apply_requested: bool,
    ) -> CreatorVoiceWorkflowApplicationBundle | None:
        if self.creator_voice_workflow_application_service is None:
            return None
        return self.creator_voice_workflow_application_service.build_application(
            {
                "creator_id": creator_id,
                "project_id": project_id,
                "workflow_type": workflow_type,
                "language": language,
                "current_user_instruction": current_user_instruction,
                "project_instruction": project_instruction,
                "enabled": True,
                "apply_enabled": apply_requested,
            }
        )

    def _upsert(self, table: str, payload: dict[str, Any], conflict_columns: tuple[str, ...] = ("id",)) -> dict[str, Any]:
        return self.repository.upsert_record(table, payload, conflict_columns=conflict_columns)

    def _fetch(self, table: str, *, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        return self.repository.fetch_record(table, where=where, params=params)

    def _fetch_many(
        self,
        table: str,
        *,
        where: str = "",
        params: tuple[Any, ...] = (),
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.fetch_records(table, where=where, params=params, order_by=order_by, limit=limit)

    def _entity(self, table: str, *, where: str, params: tuple[Any, ...], enum_fields: dict[str, Any] | None = None) -> ProductionRecord | None:
        return _row_to_entity(self._fetch(table, where=where, params=params), enum_fields=enum_fields)

    def _entities(self, table: str, *, where: str, params: tuple[Any, ...], order_by: str | None = None, enum_fields: dict[str, Any] | None = None) -> list[ProductionRecord]:
        return [_row_to_entity(row, enum_fields=enum_fields) for row in self._fetch_many(table, where=where, params=params, order_by=order_by)]

    def _safe_call(self, service: Any | None, method_names: tuple[str, ...], *args, **kwargs):
        if service is None:
            return None
        for method_name in method_names:
            method = getattr(service, method_name, None)
            if callable(method):
                try:
                    return method(*args, **kwargs)
                except Exception:
                    continue
        return None

    def _safe_payload(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "to_dict"):
            return dict(value.to_dict())
        if isinstance(value, dict):
            return dict(value)
        payload = {}
        for key in dir(value):
            if key.startswith("_"):
                continue
            item = getattr(value, key)
            if callable(item):
                continue
            payload[key] = item
        return payload

    def _validate_creator(self, creator_id: str) -> None:
        if not creator_id:
            raise ProductionPreparationValidationError("Se requiere creator_id.")

    def _load_brief(self, creator_id: str, brief_id: str) -> BriefRecord:
        if self.brief_service is None:
            raise ProductionPreparationValidationError("No hay servicio de Content Briefs.")
        brief = self.brief_service.get_brief(brief_id)
        if brief is None:
            raise ProductionPreparationNotFoundError("El brief no existe.")
        if str(brief.creator_id) != creator_id:
            raise ProductionPreparationValidationError("No se permite cross-creator leakage.")
        return brief

    def _load_brief_context_payload(self, brief: BriefRecord) -> dict[str, object]:
        return {
            "brief": brief.to_dict(),
            "objective": brief.primary_objective,
            "audience": brief.audience_summary,
            "promise": brief.content_promise,
            "message": brief.core_message,
            "claims": [claim.to_dict() for claim in self.brief_service.list_claims(brief.id)] if self.brief_service else [],
            "rights": [right.to_dict() for right in self.brief_service.list_rights(brief.id)] if self.brief_service else [],
            "assets": [asset.to_dict() for asset in self.brief_service.list_assets(brief.id)] if self.brief_service else [],
            "requirements": [req.to_dict() for req in self.brief_service.list_requirements(brief.id)] if self.brief_service else [],
            "gates": [gate.to_dict() for gate in self.brief_service.list_gates(brief.id)] if self.brief_service else [],
            "readiness": self.brief_service.calculate_readiness(brief.id) if self.brief_service else {},
        }

    def create_context_snapshot(
        self,
        creator_id: str,
        *,
        content_brief_id: str,
        brief_version: int,
        strategic_plan_id: str | None = None,
        roadmap_item_id: str | None = None,
        recommendation_candidate_id: str | None = None,
        experiment_id: str | None = None,
        internal_content_id: str | None = None,
        created_at: str | None = None,
        preferences: dict[str, object] | None = None,
        constraints: list[dict[str, object]] | None = None,
        resources: list[dict[str, object]] | None = None,
        missing_data: list[str] | None = None,
        stale_data: list[str] | None = None,
        contradictions: list[dict[str, object]] | None = None,
        use_creator_context: bool = True,
    ) -> ProductionRecord:
        self._validate_creator(creator_id)
        brief = self._load_brief(creator_id, content_brief_id)
        created_at = created_at or _now()
        context_policy = self.creator_context_policy_registry.get_by_workflow("production_preparation")
        creator_memory_snapshot_id = self._snapshot_identifier(self.creator_memory_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots", "list_snapshots"), creator_id)
        creator_language_snapshot_id = self._snapshot_identifier(self.creator_language_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots", "list_snapshots"), creator_id)
        audience_snapshot_id = self._snapshot_identifier(self.audience_service, ("build_profile", "get_profile", "list_profiles"), creator_id)
        platform_snapshot_id = self._snapshot_identifier(self.platform_service, ("list_reports", "list_integrations", "list_connections"), creator_id)
        packaging_snapshot_id = self._snapshot_identifier(self.packaging_service, ("list_concepts", "list_versions", "list_reports"), creator_id)
        script_request_text = " | ".join(
            part
            for part in (
                brief.title,
                brief.primary_objective,
                brief.audience_summary,
                brief.content_promise,
                brief.core_message,
                )
            if part
        ) or "Production preparation context"
        creator_voice_application_bundle = self._build_creator_voice_application_bundle(
            creator_id=creator_id,
            project_id=getattr(brief, "project_id", None),
            workflow_type="production_preparation",
            language=getattr(brief, "language", None),
            current_user_instruction=None,
            project_instruction=None,
            apply_requested=bool(self.preferences.get("creator_voice_guidance_enabled", False)),
        )
        payload = {
            "creator_id": creator_id,
            "context_version": self.ENGINE_VERSION,
            "content_brief_id": content_brief_id,
            "brief_version": brief_version,
            "strategic_plan_id": strategic_plan_id,
            "roadmap_item_id": roadmap_item_id,
            "recommendation_candidate_id": recommendation_candidate_id,
            "experiment_id": experiment_id,
            "internal_content_id": internal_content_id,
            "creator_memory_snapshot_id": creator_memory_snapshot_id,
            "creator_language_snapshot_id": creator_language_snapshot_id,
            "audience_snapshot_id": audience_snapshot_id,
            "platform_snapshot_id": platform_snapshot_id,
            "packaging_snapshot_id": packaging_snapshot_id,
            "created_at": created_at,
        }
        creator_context_bundle = None
        creator_context_package: dict[str, object] = {}
        creator_context_prompt: str | None = None
        creator_preference_application_bundle: CreatorPreferenceApplicationBundle | None = None
        creator_context_usage: dict[str, object] = {
            "enabled": False,
            "policy_id": None if context_policy is None else context_policy.policy_id,
            "grounding_mode": None if context_policy is None else context_policy.grounding_mode.value,
            "item_count": 0,
            "estimated_tokens": 0,
            "estimated_characters": 0,
            "truncated": False,
            "preference_item_count": 0,
            "preference_omitted_count": 0,
            "preference_conflict_count": 0,
            "voice_guidance_shadow": bool(creator_voice_application_bundle and creator_voice_application_bundle.voice_guidance_shadow),
            "voice_guidance_applied": bool(creator_voice_application_bundle and creator_voice_application_bundle.voice_guidance_applied),
            "voice_guidance_item_count": 0 if creator_voice_application_bundle is None or creator_voice_application_bundle.guidance_bundle is None else len(creator_voice_application_bundle.guidance_bundle.guidance_items),
            "voice_guidance_omitted_count": 0 if creator_voice_application_bundle is None or creator_voice_application_bundle.guidance_bundle is None else len(creator_voice_application_bundle.guidance_bundle.omitted_items),
        }
        if use_creator_context and self.creator_context_assembly_service is not None and context_policy is not None and context_policy.is_context_allowed():
            creator_context_request = context_policy.build_request(
                creator_id=creator_id,
                user_request=script_request_text,
                query_text=script_request_text,
            )
            creator_context_bundle = self.creator_context_assembly_service.assemble(creator_context_request)
            creator_context_package = self.creator_context_assembly_service.build_context_package(creator_context_bundle)
            creator_context_prompt = self.creator_context_assembly_service.render_prompt(creator_context_bundle)
            creator_context_usage = {
                "enabled": True,
                "policy_id": context_policy.policy_id,
                "grounding_mode": context_policy.grounding_mode.value,
                "item_count": len(creator_context_bundle.items),
                "estimated_tokens": creator_context_bundle.total_estimated_tokens,
                "estimated_characters": creator_context_bundle.total_estimated_characters,
                "truncated": creator_context_bundle.truncated,
            }
        if self.creator_preference_application_service is not None:
            creator_preference_application_bundle = self.creator_preference_application_service.build_application_bundle(
                creator_id=creator_id,
                workflow_type="production_preparation",
                project_id=getattr(brief, "project_id", None),
                current_user_instruction=script_request_text,
                project_instruction=str(getattr(brief, "title", "") or getattr(brief, "primary_objective", "") or ""),
                primary_artifact_metadata={
                    "brief_id": brief.id,
                    "brief_version": brief_version,
                    "content_brief_id": content_brief_id,
                    "brief_title": getattr(brief, "title", None),
                    "brief_project_id": getattr(brief, "project_id", None),
                },
                corpus_context_present=bool(creator_context_bundle and creator_context_bundle.items),
                corpus_context_item_count=0 if creator_context_bundle is None else len(creator_context_bundle.items),
            )
            if creator_preference_application_bundle.rendered_context:
                creator_context_prompt = (
                    creator_preference_application_bundle.rendered_context
                    + ("\n\n" + creator_context_prompt if creator_context_prompt else "")
                ).strip()
            creator_context_package = {
                **creator_context_package,
                "confirmed_preference_context": creator_preference_application_bundle.to_dict(),
                "confirmed_preference_prompt": creator_preference_application_bundle.rendered_context,
            }
            creator_context_usage = {
                **creator_context_usage,
                "preference_item_count": len(creator_preference_application_bundle.applied_preferences),
                "preference_omitted_count": creator_preference_application_bundle.preferences_omitted_count,
                "preference_conflict_count": creator_preference_application_bundle.conflict_count,
            }
        if creator_voice_application_bundle is not None:
            creator_context_package = {
                **creator_context_package,
                "creator_voice_application_context": creator_voice_application_bundle.to_dict(),
            }
            creator_context_usage = {
                **creator_context_usage,
                "voice_guidance_shadow": creator_voice_application_bundle.voice_guidance_shadow,
                "voice_guidance_applied": creator_voice_application_bundle.voice_guidance_applied,
                "voice_guidance_item_count": 0 if creator_voice_application_bundle.guidance_bundle is None else len(creator_voice_application_bundle.guidance_bundle.guidance_items),
                "voice_guidance_omitted_count": 0 if creator_voice_application_bundle.guidance_bundle is None else len(creator_voice_application_bundle.guidance_bundle.omitted_items),
            }
            if creator_voice_application_bundle.voice_guidance_applied and creator_voice_application_bundle.rendered_guidance:
                creator_context_prompt = (
                    creator_context_prompt + "\n\n" + creator_voice_application_bundle.rendered_guidance
                    if creator_context_prompt
                    else creator_voice_application_bundle.rendered_guidance
                ).strip()
        context_details = {
            "creator_context_enabled": bool(creator_context_usage["enabled"]),
            "creator_context_policy_id": creator_context_usage["policy_id"],
            "creator_context_grounding_mode": creator_context_usage["grounding_mode"],
            "creator_context_usage": creator_context_usage,
            "creator_context_bundle": creator_context_bundle.to_dict() if creator_context_bundle else None,
            "creator_context_package": creator_context_package,
            "creator_context_prompt": creator_context_prompt,
            "confirmed_preference_application": None if creator_preference_application_bundle is None else creator_preference_application_bundle.to_dict(),
            "creator_voice_application_bundle": None if creator_voice_application_bundle is None else creator_voice_application_bundle.to_dict(),
        }
        payload["source_fingerprint"] = build_production_fingerprint(
            {
                "creator_id": creator_id,
                "brief": brief.to_dict(),
                "preferences": dict(preferences or self.preferences),
                "constraints": constraints or [],
                "resources": resources or [],
                "missing_data": missing_data or [],
                "stale_data": stale_data or [],
                "contradictions": contradictions or [],
                "brief_context": self._load_brief_context_payload(brief),
                "creator_context_usage": creator_context_usage,
            }
        )
        payload["context_json"] = _json_dumps(
            {
                "brief": brief.to_dict(),
                "brief_context": self._load_brief_context_payload(brief),
                "preferences": dict(preferences or self.preferences),
                "constraints": constraints or [],
                "resources": resources or [],
                "missing_data": missing_data or [],
                "stale_data": stale_data or [],
                "contradictions": contradictions or [],
                "creator_context_usage": creator_context_usage,
                **context_details,
            }
        )
        payload["id"] = _stable_id("production-context", creator_id, content_brief_id, str(brief_version), payload["source_fingerprint"])
        existing = self._fetch("production_context_snapshots", where="creator_id = ? AND source_fingerprint = ?", params=(creator_id, payload["source_fingerprint"]))
        if existing:
            return _row_to_entity(existing)
        return _row_to_entity(self._upsert("production_context_snapshots", payload))

    def _snapshot_identifier(self, service: Any | None, method_names: tuple[str, ...], creator_id: str) -> str | None:
        if service is None:
            return None
        result = self._safe_call(service, method_names, creator_id)
        if result is None:
            return None
        if isinstance(result, list):
            if not result:
                return None
            first = result[0]
            return str(getattr(first, "id", None) or (first.get("id") if isinstance(first, dict) else None))
        if hasattr(result, "id"):
            return str(result.id)
        if isinstance(result, dict):
            return str(result.get("id")) if result.get("id") is not None else None
        return str(result)

    def _allowed_brief_status(self, brief: BriefRecord) -> bool:
        status = str(getattr(brief, "status", "") or "")
        return status in {
            BriefStatus.APPROVED.value,
            BriefStatus.READY_FOR_PREPRODUCTION.value,
            BriefStatus.PREPRODUCTION_IN_PROGRESS.value,
            BriefStatus.READY_FOR_PRODUCTION.value,
        }

    def _outline_type_for_brief(self, brief: BriefRecord) -> ScriptOutlineType:
        brief_type = str(getattr(brief, "brief_type", "") or "")
        if brief_type in {"short_video_brief"}:
            return ScriptOutlineType.SHORT_VIDEO_OUTLINE
        if brief_type in {"longform_video_brief"}:
            return ScriptOutlineType.LONGFORM_VIDEO_OUTLINE
        if brief_type in {"livestream_brief"}:
            return ScriptOutlineType.LIVESTREAM_OUTLINE
        if brief_type in {"podcast_brief", "audio_brief"}:
            return ScriptOutlineType.PODCAST_OUTLINE
        if brief_type in {"carousel_brief"}:
            return ScriptOutlineType.CAROUSEL_OUTLINE
        if brief_type in {"story_brief"}:
            return ScriptOutlineType.STORY_OUTLINE
        if brief_type in {"image_post_brief"}:
            return ScriptOutlineType.IMAGE_POST_OUTLINE
        if brief_type in {"article_brief", "newsletter_brief"}:
            return ScriptOutlineType.ARTICLE_OUTLINE
        if brief_type in {"community_post_brief"}:
            return ScriptOutlineType.COMMUNITY_POST_OUTLINE
        if brief_type in {"repurpose_brief"}:
            return ScriptOutlineType.REPURPOSE_OUTLINE
        if brief_type in {"experiment_brief"}:
            return ScriptOutlineType.EXPERIMENT_OUTLINE
        if brief_type in {"series_episode_brief"}:
            return ScriptOutlineType.TUTORIAL_OUTLINE
        return ScriptOutlineType.UNKNOWN

    def create_request(
        self,
        *,
        creator_id: str,
        content_brief_id: str,
        request_type: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        constraints_json: str | None = None,
        preferences_json: str | None = None,
        status: str | None = None,
        requested_at: str | None = None,
    ) -> ProductionRecord:
        brief = self._load_brief(creator_id, content_brief_id)
        requested_at = requested_at or _now()
        payload = {
            "id": _stable_id("production-request", creator_id, content_brief_id, request_type or "outline"),
            "creator_id": creator_id,
            "content_brief_id": content_brief_id,
            "request_type": request_type or "brief_to_outline",
            "platform_scope_json": platform_scope_json or getattr(brief, "platform_scope_json", "[]"),
            "content_type_scope_json": content_type_scope_json or getattr(brief, "content_type_scope_json", "[]"),
            "constraints_json": constraints_json or _json_dumps([]),
            "preferences_json": preferences_json or _json_dumps(self.preferences),
            "status": status or ProductionRequestStatus.QUEUED.value,
            "requested_at": requested_at,
            "created_at": requested_at,
            "updated_at": requested_at,
        }
        existing = self._fetch(
            "script_outline_requests",
            where="creator_id = ? AND content_brief_id = ? AND request_type = ?",
            params=(creator_id, content_brief_id, payload["request_type"]),
        )
        if existing:
            return _row_to_entity(existing)
        return _row_to_entity(self._upsert("script_outline_requests", payload))

    def list_requests(self, creator_id: str) -> list[ProductionRecord]:
        return self._entities("script_outline_requests", where="creator_id = ?", params=(creator_id,), order_by="updated_at DESC")

    def get_request(self, request_id: str) -> ProductionRecord | None:
        return self._entity("script_outline_requests", where="id = ?", params=(request_id,))

    def list_context_snapshots(self, creator_id: str) -> list[ProductionRecord]:
        return self._entities("production_context_snapshots", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def get_context_snapshot(self, snapshot_id: str) -> ProductionRecord | None:
        return self._entity("production_context_snapshots", where="id = ?", params=(snapshot_id,))

    def _segment_templates_for_outline(self, outline_type: ScriptOutlineType) -> list[dict[str, Any]]:
        if outline_type == ScriptOutlineType.SHORT_VIDEO_OUTLINE:
            return [
                {"section": OutlineSectionType.OPENING, "beat": BeatType.ATTENTION, "segment": SegmentType.SPOKEN_DIRECTION, "title": "Opening", "purpose": "Establecer el arranque", "text": "Abrir con el conflicto principal."},
                {"section": OutlineSectionType.HOOK, "beat": BeatType.PROMISE, "segment": SegmentType.SPOKEN_DIRECTION, "title": "Hook", "purpose": "Promesa inmediata", "text": "Mostrar la apuesta del contenido."},
                {"section": OutlineSectionType.SETUP, "beat": BeatType.CONTEXT, "segment": SegmentType.DEMONSTRATION, "title": "Setup", "purpose": "Contexto breve", "text": "Situar el reto o problema."},
                {"section": OutlineSectionType.EXPLANATION, "beat": BeatType.CONFLICT, "segment": SegmentType.EXAMPLE, "title": "Challenge", "purpose": "Desarrollo del reto", "text": "Mostrar una respuesta o intento."},
                {"section": OutlineSectionType.ESCALATION, "beat": BeatType.ESCALATION, "segment": SegmentType.B_ROLL, "title": "Escalation", "purpose": "Subir tension", "text": "Aumentar intensidad o dificultad."},
                {"section": OutlineSectionType.SOLUTION, "beat": BeatType.PAYOFF, "segment": SegmentType.RECAP, "title": "Payoff", "purpose": "Resolucion", "text": "Cerrar con el resultado o aprendizaje."},
                {"section": OutlineSectionType.CLOSING, "beat": BeatType.SUMMARY, "segment": SegmentType.CTA_DIRECTION, "title": "Closing", "purpose": "Cierre", "text": "Indicar la accion siguiente."},
            ]
        if outline_type in {ScriptOutlineType.LONGFORM_VIDEO_OUTLINE, ScriptOutlineType.TUTORIAL_OUTLINE, ScriptOutlineType.CASE_STUDY_OUTLINE}:
            return [
                {"section": OutlineSectionType.OPENING, "beat": BeatType.ATTENTION, "segment": SegmentType.SPOKEN_DIRECTION, "title": "Opening", "purpose": "Establecer la necesidad", "text": "Abrir con el problema y la promesa."},
                {"section": OutlineSectionType.HOOK, "beat": BeatType.PROMISE, "segment": SegmentType.SPOKEN_DIRECTION, "title": "Hook", "purpose": "Promesa verificable", "text": "Poner el beneficio central."},
                {"section": OutlineSectionType.CONTEXT, "beat": BeatType.CONTEXT, "segment": SegmentType.VISUAL_EXPLANATION, "title": "Context", "purpose": "Contexto y audiencia", "text": "Explicar por que importa."},
                {"section": OutlineSectionType.PROBLEM, "beat": BeatType.CONFLICT, "segment": SegmentType.EXAMPLE, "title": "Problem", "purpose": "Error o friccion", "text": "Mostrar la situacion a corregir."},
                {"section": OutlineSectionType.EXPLANATION, "beat": BeatType.EXPLANATION, "segment": SegmentType.DEMONSTRATION, "title": "Explanation", "purpose": "Desarrollo central", "text": "Desglosar la idea o tecnica."},
                {"section": OutlineSectionType.DEMONSTRATION, "beat": BeatType.PROOF, "segment": SegmentType.SCREEN_RECORDING, "title": "Proof", "purpose": "Evidencia", "text": "Mostrar una prueba o ejemplo."},
                {"section": OutlineSectionType.APPLICATION, "beat": BeatType.EXAMPLE, "segment": SegmentType.EXERCISE, "title": "Application", "purpose": "Aplicacion", "text": "Indicar como usarlo."},
                {"section": OutlineSectionType.RECAP, "beat": BeatType.SUMMARY, "segment": SegmentType.RECAP, "title": "Recap", "purpose": "Resumen", "text": "Recapitular hallazgos."},
                {"section": OutlineSectionType.CLOSING, "beat": BeatType.ACTION_DIRECTION, "segment": SegmentType.CTA_DIRECTION, "title": "Closing", "purpose": "Siguiente paso", "text": "Cerrar con una instruccion."},
            ]
        return [
            {"section": OutlineSectionType.OPENING, "beat": BeatType.ATTENTION, "segment": SegmentType.SPOKEN_DIRECTION, "title": "Opening", "purpose": "Abrir la pieza", "text": "Introduccion trazable."},
            {"section": OutlineSectionType.CONTEXT, "beat": BeatType.CONTEXT, "segment": SegmentType.VISUAL_EXPLANATION, "title": "Context", "purpose": "Contexto", "text": "Situar al espectador."},
            {"section": OutlineSectionType.EXPLANATION, "beat": BeatType.EXPLANATION, "segment": SegmentType.DEMONSTRATION, "title": "Core", "purpose": "Nucleo", "text": "Desarrollar el contenido."},
            {"section": OutlineSectionType.CLOSING, "beat": BeatType.SUMMARY, "segment": SegmentType.CTA_DIRECTION, "title": "Closing", "purpose": "Cierre", "text": "Definir accion o salida."},
        ]

    def _outline_payload_from_request(self, request: ProductionRecord, brief: BriefRecord, context_snapshot: ProductionRecord) -> dict[str, Any]:
        outline_type = self._outline_type_for_brief(brief)
        template = self._segment_templates_for_outline(outline_type)
        platform_scope = _safe_list(_json_loads(str(request.platform_scope_json or getattr(brief, "platform_scope_json", "[]")), []))
        content_type_scope = _safe_list(_json_loads(str(request.content_type_scope_json or getattr(brief, "content_type_scope_json", "[]")), []))
        target_duration = int(self.preferences.get("default_target_duration_seconds", 180))
        return {
            "id": _stable_id("script-outline", request.id, str(getattr(brief, "version", 1))),
            "creator_id": brief.creator_id,
            "script_outline_request_id": request.id,
            "content_brief_id": brief.id,
            "production_context_snapshot_id": context_snapshot.id,
            "parent_outline_id": None,
            "version": 1,
            "title": f"{brief.title} outline",
            "outline_type": outline_type,
            "status": ScriptOutlineStatus.NEEDS_REVIEW.value,
            "primary_platform": platform_scope[0] if platform_scope else None,
            "platform_scope_json": _json_dumps(platform_scope),
            "content_type": content_type_scope[0] if content_type_scope else getattr(brief, "brief_type", ScriptOutlineType.UNKNOWN.value),
            "target_duration_seconds": target_duration,
            "target_word_range_json": _json_dumps([int(target_duration * 1.8), int(target_duration * 2.4)]),
            "target_segment_count": len(template),
            "primary_objective": str(getattr(brief, "primary_objective", "unknown")),
            "audience_summary": str(getattr(brief, "audience_summary", "Audience")),
            "content_promise": str(getattr(brief, "content_promise", "Promise")),
            "core_message": str(getattr(brief, "core_message", "Message")),
            "narrative_structure": outline_type.value,
            "pacing_direction": "fast" if outline_type == ScriptOutlineType.SHORT_VIDEO_OUTLINE else "balanced",
            "confidence_level": str(getattr(brief, "confidence_level", "medium")),
            "copying_risk": getattr(brief, "copying_risk", CopyingRiskLevel.UNKNOWN),
            "readiness_status": ReadinessStatus.NEEDS_REVIEW.value,
            "created_at": _now(),
            "updated_at": _now(),
        }

    def _build_components(self, outline: ProductionRecord, brief: BriefRecord) -> dict[str, list[dict[str, Any]]]:
        template = self._segment_templates_for_outline(outline.outline_type)
        talking_points = self.brief_service.list_talking_points(brief.id) if self.brief_service else []
        claims = self.brief_service.list_claims(brief.id) if self.brief_service else []
        rights = self.brief_service.list_rights(brief.id) if self.brief_service else []
        assets = self.brief_service.list_assets(brief.id) if self.brief_service else []
        requirements = self.brief_service.list_requirements(brief.id) if self.brief_service else []
        variants = _safe_list(_json_loads(str(outline.platform_scope_json or "[]"), []))
        sections: list[dict[str, Any]] = []
        beats: list[dict[str, Any]] = []
        segments: list[dict[str, Any]] = []
        talking_links: list[dict[str, Any]] = []
        claim_links: list[dict[str, Any]] = []
        proofs: list[dict[str, Any]] = []
        scenes: list[dict[str, Any]] = []
        shots: list[dict[str, Any]] = []
        shot_groups: list[dict[str, Any]] = []
        recording_blocks: list[dict[str, Any]] = []
        recording_block_items: list[dict[str, Any]] = []
        visual_cues: list[dict[str, Any]] = []
        audio_cues: list[dict[str, Any]] = []
        on_screen_text: list[dict[str, Any]] = []
        brolls: list[dict[str, Any]] = []
        graphics: list[dict[str, Any]] = []
        screen_recordings: list[dict[str, Any]] = []
        participants: list[dict[str, Any]] = []
        locations: list[dict[str, Any]] = []
        props: list[dict[str, Any]] = []
        wardrobe: list[dict[str, Any]] = []
        equipment: list[dict[str, Any]] = []
        continuity: list[dict[str, Any]] = []
        platform_variants: list[dict[str, Any]] = []
        reusable_segments: list[dict[str, Any]] = []
        dependencies: list[dict[str, Any]] = []
        milestones: list[dict[str, Any]] = []
        checklists = [
            {
                "id": _stable_id("production-checklist", outline.id),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "checklist_type": "final_recording_readiness",
                "title": "Final recording readiness",
                "status": "open",
                "created_at": _now(),
                "updated_at": _now(),
            }
        ]
        checklist_items: list[dict[str, Any]] = []
        gates: list[dict[str, Any]] = []
        risks: list[dict[str, Any]] = []
        for index, item in enumerate(template, start=1):
            section_id = _stable_id("production-section", outline.id, str(index))
            beat_id = _stable_id("production-beat", outline.id, str(index))
            segment_id = _stable_id("production-segment", outline.id, str(index))
            sections.append({
                "id": section_id,
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "section_type": item["section"].value,
                "sequence_order": index,
                "title": item["title"],
                "purpose": item["purpose"],
                "description": item["text"],
                "required": True,
                "target_duration_seconds": max(10, int(outline.target_duration_seconds or 0) // max(1, len(template))),
                "target_word_range_json": _json_dumps([40, 120]),
                "status": "ready",
                "source_fingerprint": _stable_id("production-section-fingerprint", outline.id, str(index)),
                "created_at": _now(),
                "updated_at": _now(),
            })
            beats.append({
                "id": beat_id,
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_section_id": section_id,
                "sequence_order": index,
                "beat_type": item["beat"].value,
                "title": item["title"],
                "purpose": item["purpose"],
                "description": item["text"],
                "audience_state_before": "curious",
                "audience_state_after": "informed",
                "required": True,
                "estimated_duration_seconds": max(5, int(outline.target_duration_seconds or 0) // max(1, len(template) * 2)),
                "status": "ready",
                "created_at": _now(),
                "updated_at": _now(),
            })
            claim = claims[min(index - 1, max(0, len(claims) - 1))] if claims else None
            talking = talking_points[min(index - 1, max(0, len(talking_points) - 1))] if talking_points else None
            segments.append({
                "id": segment_id,
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_section_id": section_id,
                "outline_beat_id": beat_id,
                "sequence_order": index,
                "segment_type": item["segment"].value,
                "title": item["title"],
                "purpose": item["purpose"],
                "content_direction": item["text"],
                "transition_in": "from previous" if index > 1 else None,
                "transition_out": "to next" if index < len(template) else None,
                "required": True,
                "estimated_duration_seconds": max(5, int(outline.target_duration_seconds or 0) // max(1, len(template))),
                "reusable": index != 1,
                "status": "ready",
                "created_at": _now(),
                "updated_at": _now(),
            })
            if talking is not None:
                talking_links.append({
                    "id": _stable_id("production-talk-link", outline.id, str(index)),
                    "creator_id": outline.creator_id,
                    "script_outline_id": outline.id,
                    "outline_segment_id": segment_id,
                    "brief_talking_point_id": getattr(talking, "id", talking.get("id") if isinstance(talking, dict) else None),
                    "sequence_order": index,
                    "required": True,
                    "created_at": _now(),
                })
            if claim is not None:
                claim_links.append({
                    "id": _stable_id("production-claim-link", outline.id, str(index)),
                    "creator_id": outline.creator_id,
                    "script_outline_id": outline.id,
                    "outline_segment_id": segment_id,
                    "brief_claim_id": getattr(claim, "id", claim.get("id") if isinstance(claim, dict) else None),
                    "usage_type": "supporting",
                    "verification_required": getattr(claim, "verification_status", ClaimVerificationStatus.NOT_REQUIRED).value if hasattr(getattr(claim, "verification_status", None), "value") else "not_required",
                    "created_at": _now(),
                })
                proofs.append({
                    "id": _stable_id("production-proof", outline.id, str(index)),
                    "creator_id": outline.creator_id,
                    "script_outline_id": outline.id,
                    "outline_segment_id": segment_id,
                    "proof_type": "source citation",
                    "description": f"Proof for {getattr(claim, 'claim_text', 'claim')}",
                    "source_type": "claim",
                    "source_id": getattr(claim, "id", claim.get("id") if isinstance(claim, dict) else None),
                    "required": True,
                    "readiness_status": "pending",
                    "created_at": _now(),
                    "updated_at": _now(),
                })
            scene_id = _stable_id("production-scene", outline.id, str(index))
            scenes.append({
                "id": scene_id,
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_number": index,
                "title": item["title"],
                "purpose": item["purpose"],
                "description": item["text"],
                "location_requirement_id": None,
                "continuity_group": f"group-{index}",
                "estimated_duration_seconds": max(5, int(outline.target_duration_seconds or 0) // max(1, len(template))),
                "priority_level": index,
                "required": True,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            shot_id = _stable_id("production-shot", outline.id, str(index))
            shots.append({
                "id": shot_id,
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "scene_plan_id": scene_id,
                "outline_segment_id": segment_id,
                "shot_number": index,
                "shot_type": ShotType.TALKING_HEAD.value if index == 1 else ShotType.DEMONSTRATION.value,
                "framing": "medium",
                "angle": "eye_level",
                "movement": "static",
                "title": item["title"],
                "description": item["text"],
                "purpose": item["purpose"],
                "visual_cue": "subject action",
                "audio_cue": "spoken direction",
                "on_screen_text_direction": "label",
                "estimated_recording_seconds": 10,
                "estimated_final_seconds": 8,
                "required": True,
                "priority_level": index,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            shot_groups.append({
                "id": _stable_id("production-shot-group", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "name": f"Group {index}",
                "grouping_type": "location",
                "location_id": None,
                "participant_scope_json": _json_dumps([]),
                "equipment_scope_json": _json_dumps([]),
                "continuity_scope_json": _json_dumps([]),
                "sequence_order": index,
                "rationale": "Grouped for efficiency",
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            recording_blocks.append({
                "id": _stable_id("production-recording-block", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "name": f"Block {index}",
                "block_type": RecordingBlockType.PRIMARY_TALKING_HEAD.value if index == 1 else RecordingBlockType.DEMONSTRATION.value,
                "sequence_order": index,
                "location_id": None,
                "participant_scope_json": _json_dumps([]),
                "equipment_scope_json": _json_dumps([]),
                "estimated_duration_minutes": 10,
                "setup_duration_minutes": 5,
                "teardown_duration_minutes": 5,
                "status": "planned",
                "rationale": "Production efficiency",
                "created_at": _now(),
                "updated_at": _now(),
            })
            recording_block_items.append({
                "id": _stable_id("production-recording-block-item", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "recording_block_id": _stable_id("production-recording-block", outline.id, str(index)),
                "scene_plan_id": scene_id,
                "shot_item_id": shot_id,
                "sequence_order": index,
                "created_at": _now(),
            })
            visual_cues.append({
                "id": _stable_id("production-visual-cue", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "shot_item_id": shot_id,
                "cue_type": "subject_action",
                "description": item["text"],
                "timing_direction": "during segment",
                "reference_id": None,
                "copying_risk": CopyingRiskLevel.UNKNOWN.value,
                "rights_status": RightsStatus.UNKNOWN.value,
                "required": True,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            audio_cues.append({
                "id": _stable_id("production-audio-cue", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "shot_item_id": shot_id,
                "cue_type": "spoken direction",
                "description": item["text"],
                "timing_direction": "during segment",
                "source_type": "outline",
                "source_id": segment_id,
                "rights_status": RightsStatus.UNKNOWN.value,
                "required": True,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            on_screen_text.append({
                "id": _stable_id("production-text", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "shot_item_id": shot_id,
                "text_type": "text_direction",
                "text_direction": item["text"],
                "exact_text": None,
                "exact_text_approved": False,
                "character_limit": 60,
                "safe_area_notes": "manual review",
                "platform_scope_json": outline.platform_scope_json,
                "required": False,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            brolls.append({
                "id": _stable_id("production-broll", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "title": f"B-roll {index}",
                "description": item["text"],
                "purpose": "supporting visual",
                "source_type": "new_recording",
                "existing_asset_id": None,
                "rights_status": RightsStatus.UNKNOWN.value,
                "required": False,
                "readiness_status": "pending",
                "created_at": _now(),
                "updated_at": _now(),
            })
            graphics.append({
                "id": _stable_id("production-graphic", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "graphic_type": "chart",
                "title": f"Graphic {index}",
                "description": item["text"],
                "data_source_id": None,
                "existing_asset_id": None,
                "rights_status": RightsStatus.UNKNOWN.value,
                "required": False,
                "readiness_status": "pending",
                "created_at": _now(),
                "updated_at": _now(),
            })
            screen_recordings.append({
                "id": _stable_id("production-screen", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "scene_plan_id": scene_id,
                "title": f"Screen recording {index}",
                "description": item["text"],
                "application_name": None,
                "account_scope": None,
                "privacy_notes": "manual review",
                "data_redaction_required": True,
                "required": False,
                "readiness_status": "pending",
                "created_at": _now(),
                "updated_at": _now(),
            })
            participants.append({
                "id": _stable_id("production-participant", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "participant_type": ParticipantType.CREATOR.value,
                "display_name": "Creator",
                "role": "creator",
                "required": True,
                "permission_status": "approved",
                "release_required": False,
                "release_status": "not_required",
                "availability_status": "available",
                "notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            locations.append({
                "id": _stable_id("production-location", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "location_type": LocationType.STUDIO.value,
                "name": "Local production space",
                "description": "Primary recording location",
                "required": True,
                "permission_required": False,
                "permission_status": "approved",
                "availability_status": "available",
                "sound_constraints_json": _json_dumps([]),
                "light_constraints_json": _json_dumps([]),
                "privacy_constraints_json": _json_dumps([]),
                "notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            props.append({
                "id": _stable_id("production-prop", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "title": f"Prop {index}",
                "description": item["text"],
                "required": False,
                "source_type": "existing",
                "existing_asset_id": None,
                "availability_status": "available",
                "rights_status": RightsStatus.UNKNOWN.value,
                "notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            wardrobe.append({
                "id": _stable_id("production-wardrobe", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "participant_requirement_id": None,
                "title": f"Wardrobe {index}",
                "description": "Neutral wardrobe",
                "required": False,
                "availability_status": "available",
                "rights_or_brand_status": "ok",
                "continuity_notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            equipment.append({
                "id": _stable_id("production-equipment", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "equipment_type": EquipmentType.CAMERA.value,
                "title": "Camera",
                "description": "Primary camera",
                "required": True,
                "availability_status": "available",
                "assigned_item": "primary",
                "backup_required": True,
                "backup_status": "recommended",
                "notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            continuity.append({
                "id": _stable_id("production-continuity", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "continuity_type": ContinuityType.NARRATIVE.value,
                "scope_type": "segment",
                "scope_id": segment_id,
                "description": "Keep sequence and terminology consistent",
                "severity": "medium",
                "blocking": False,
                "validation_status": "pending",
                "notes": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            for platform in variants or [None]:
                platform_variants.append({
                    "id": _stable_id("production-variant", outline.id, str(index), str(platform or "default")),
                    "creator_id": outline.creator_id,
                    "script_outline_id": outline.id,
                    "platform": platform or (outline.primary_platform or "unknown"),
                    "content_type": str(outline.content_type or "unknown"),
                    "source_outline_segment_id": segment_id,
                    "variant_type": PlatformAdaptationType.CUSTOM.value,
                    "duration_target": 60 if outline.outline_type == ScriptOutlineType.SHORT_VIDEO_OUTLINE else outline.target_duration_seconds,
                    "aspect_ratio": "9:16" if platform in {"tiktok", "instagram"} else "16:9",
                    "hook_adjustment": "platform native hook",
                    "structure_adjustment_json": _json_dumps({}),
                    "on_screen_text_adjustment_json": _json_dumps({}),
                    "caption_direction": "manual",
                    "packaging_direction_json": _json_dumps({}),
                    "measurement_plan_json": _json_dumps({}),
                    "limitations_json": _json_dumps([]),
                    "status": "planned",
                    "created_at": _now(),
                    "updated_at": _now(),
                })
            reusable_segments.append({
                "id": _stable_id("production-reusable", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "outline_segment_id": segment_id,
                "reuse_type": "reusable_with_edit" if index > 1 else "not_reusable",
                "target_platforms_json": _json_dumps(platforms := (variants or [outline.primary_platform or "unknown"])),
                "target_content_types_json": _json_dumps([outline.content_type]),
                "reuse_constraints_json": _json_dumps([]),
                "adaptation_required": index > 1,
                "rights_status": RightsStatus.UNKNOWN.value,
                "status": "planned",
                "created_at": _now(),
                "updated_at": _now(),
            })
            dependencies.append({
                "id": _stable_id("production-dependency", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "dependency_type": DependencyType.BRIEF_APPROVAL.value,
                "source_type": "brief",
                "source_id": brief.id,
                "target_type": "outline_segment",
                "target_id": segment_id,
                "description": "Depends on approved brief",
                "blocking": True,
                "status": "open",
                "due_date": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            milestones.append({
                "id": _stable_id("production-milestone", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "milestone_type": MilestoneType.OUTLINE_APPROVED.value if index == 1 else MilestoneType.SCENES_APPROVED.value,
                "title": item["title"],
                "description": item["purpose"],
                "target_date": None,
                "status": "pending",
                "completed_at": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            checklist_items.append({
                "id": _stable_id("production-checklist-item", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "production_checklist_id": checklists[0]["id"],
                "sequence_order": index,
                "item_type": "production",
                "title": item["title"],
                "description": item["text"],
                "required": True,
                "blocking": index == 1,
                "status": "open",
                "evidence_reference": None,
                "completed_at": None,
                "completed_by": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            gates.append({
                "id": _stable_id("production-gate", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "gate_type": ApprovalGateType.OUTLINE_APPROVAL.value if index == 1 else ApprovalGateType.FINAL_RECORDING_READINESS.value,
                "sequence_order": index,
                "required": True,
                "status": "pending",
                "approver": None,
                "approved_at": None,
                "rejection_reason": None,
                "created_at": _now(),
                "updated_at": _now(),
            })
            risks.append({
                "id": _stable_id("production-risk", outline.id, str(index)),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "risk_type": RiskType.COPYING.value if index == 1 else RiskType.OPERATIONAL.value,
                "severity": "high" if getattr(brief, "copying_risk", CopyingRiskLevel.UNKNOWN) in {CopyingRiskLevel.HIGH, CopyingRiskLevel.PROHIBITED} else "medium",
                "likelihood": None,
                "impact": None,
                "description": item["text"],
                "mitigation": "human review",
                "blocking": bool(index == 1 and getattr(brief, "copying_risk", CopyingRiskLevel.UNKNOWN) in {CopyingRiskLevel.HIGH, CopyingRiskLevel.PROHIBITED}),
                "owner": None,
                "review_at": None,
                "created_at": _now(),
            })
        if rights and any(str(getattr(right, "status", "")) in {RightsStatus.DENIED.value, RightsStatus.BLOCKED.value, RightsStatus.RESTRICTED.value} for right in rights):
            gates.append({
                "id": _stable_id("production-gate-rights", outline.id),
                "creator_id": outline.creator_id,
                "script_outline_id": outline.id,
                "gate_type": ApprovalGateType.RIGHTS_APPROVAL.value,
                "sequence_order": len(gates) + 1,
                "required": True,
                "status": "blocked",
                "approver": None,
                "approved_at": None,
                "rejection_reason": "rights_block",
                "created_at": _now(),
                "updated_at": _now(),
            })
        return {
            "outline_sections": sections,
            "outline_beats": beats,
            "outline_segments": segments,
            "outline_talking_point_links": talking_links,
            "outline_claim_links": claim_links,
            "outline_proof_requirements": proofs,
            "production_scene_plans": scenes,
            "production_shot_items": shots,
            "production_shot_groups": shot_groups,
            "production_shot_group_items": [],
            "production_recording_blocks": recording_blocks,
            "production_recording_block_items": recording_block_items,
            "production_visual_cues": visual_cues,
            "production_audio_cues": audio_cues,
            "production_on_screen_text": on_screen_text,
            "production_broll_requirements": brolls,
            "production_graphic_requirements": graphics,
            "production_screen_recordings": screen_recordings,
            "production_participant_requirements": participants,
            "production_location_requirements": locations,
            "production_prop_requirements": props,
            "production_wardrobe_requirements": wardrobe,
            "production_equipment_requirements": equipment,
            "production_continuity_rules": continuity,
            "production_platform_variants": platform_variants,
            "production_reusable_segments": reusable_segments,
            "production_dependencies": dependencies,
            "production_milestones": milestones,
            "production_checklists": checklists,
            "production_checklist_items": checklist_items,
            "production_approval_gates": gates,
            "production_risks": risks,
        }

    def _store_related(self, outline: ProductionRecord, payloads: dict[str, list[dict[str, Any]]]) -> None:
        tables_without_updated_at = {
            "production_context_snapshots",
            "production_participant_requirements",
            "production_location_requirements",
            "production_prop_requirements",
            "production_risks",
            "production_reviews",
            "production_snapshots",
            "outline_talking_point_links",
            "outline_claim_links",
            "production_shot_group_items",
            "production_recording_block_items",
        }
        tables_without_outline_id = {
            "production_shot_group_items",
            "production_recording_block_items",
            "production_checklist_items",
        }

        def store(table: str, items: list[dict[str, Any]], *, conflict_columns: tuple[str, ...] = ("id",)) -> None:
            for index, item in enumerate(items):
                record = dict(item)
                record.setdefault("creator_id", outline.creator_id)
                if table not in tables_without_outline_id:
                    record.setdefault("script_outline_id", outline.id)
                record.setdefault("created_at", _now())
                if table not in tables_without_updated_at:
                    record.setdefault("updated_at", record["created_at"])
                self._upsert(table, record, conflict_columns=conflict_columns)

        store("outline_sections", payloads["outline_sections"])
        store("outline_beats", payloads["outline_beats"])
        store("outline_segments", payloads["outline_segments"])
        store("outline_talking_point_links", payloads["outline_talking_point_links"])
        store("outline_claim_links", payloads["outline_claim_links"])
        store("outline_proof_requirements", payloads["outline_proof_requirements"])
        store("production_scene_plans", payloads["production_scene_plans"])
        store("production_shot_items", payloads["production_shot_items"])
        store("production_shot_groups", payloads["production_shot_groups"])
        store("production_recording_blocks", payloads["production_recording_blocks"])
        store("production_recording_block_items", payloads["production_recording_block_items"])
        store("production_visual_cues", payloads["production_visual_cues"])
        store("production_audio_cues", payloads["production_audio_cues"])
        store("production_on_screen_text", payloads["production_on_screen_text"])
        store("production_broll_requirements", payloads["production_broll_requirements"])
        store("production_graphic_requirements", payloads["production_graphic_requirements"])
        store("production_screen_recordings", payloads["production_screen_recordings"])
        store("production_participant_requirements", payloads["production_participant_requirements"])
        store("production_location_requirements", payloads["production_location_requirements"])
        store("production_prop_requirements", payloads["production_prop_requirements"])
        store("production_wardrobe_requirements", payloads["production_wardrobe_requirements"])
        store("production_equipment_requirements", payloads["production_equipment_requirements"])
        store("production_continuity_rules", payloads["production_continuity_rules"])
        store("production_platform_variants", payloads["production_platform_variants"])
        store("production_reusable_segments", payloads["production_reusable_segments"])
        store("production_dependencies", payloads["production_dependencies"])
        store("production_milestones", payloads["production_milestones"])
        store("production_checklists", payloads["production_checklists"])
        store("production_checklist_items", payloads["production_checklist_items"])
        store("production_approval_gates", payloads["production_approval_gates"])
        store("production_risks", payloads["production_risks"])

    def generate_outline(
        self,
        *,
        request_id: str | None = None,
        creator_id: str | None = None,
        brief_id: str | None = None,
        request_type: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        constraints_json: str | None = None,
        preferences_json: str | None = None,
    ) -> ProductionRecord:
        if request_id is None:
            if creator_id is None or brief_id is None:
                raise ProductionPreparationValidationError("Se requiere request_id o creator_id/brief_id.")
            request = self.create_request(
                creator_id=creator_id,
                content_brief_id=brief_id,
                request_type=request_type,
                platform_scope_json=platform_scope_json,
                content_type_scope_json=content_type_scope_json,
                constraints_json=constraints_json,
                preferences_json=preferences_json,
            )
        else:
            request = self.get_request(request_id)
            if request is None:
                raise ProductionPreparationNotFoundError("La solicitud no existe.")
        brief = self._load_brief(request.creator_id, request.content_brief_id)
        if not self._allowed_brief_status(brief):
            self._upsert("script_outline_requests", {**request.to_dict(), "status": ProductionRequestStatus.COMPLETED_WITH_WARNINGS.value, "updated_at": _now()})
            raise ProductionPreparationStateError("El brief no esta listo para generar un outline.")
        context_snapshot = self.create_context_snapshot(
            brief.creator_id,
            content_brief_id=brief.id,
            brief_version=int(getattr(brief, "version", 1) or 1),
            strategic_plan_id=getattr(brief, "strategic_plan_id", None),
            roadmap_item_id=getattr(brief, "roadmap_item_id", None),
            recommendation_candidate_id=getattr(brief, "recommendation_candidate_id", None),
            experiment_id=getattr(brief, "experiment_id", None),
            internal_content_id=getattr(brief, "internal_content_id", None),
            preferences=_safe_dict(_json_loads(request.preferences_json, {})) or None,
            constraints=_safe_list(_json_loads(request.constraints_json, [])),
        )
        existing = self._fetch("script_outlines", where="script_outline_request_id = ?", params=(request.id,))
        if existing:
            outline = _row_to_entity(existing, enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})
        else:
            outline = _row_to_entity(self._upsert("script_outlines", self._outline_payload_from_request(request, brief, context_snapshot)), enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})
        payloads = self._build_components(outline, brief)
        self._store_related(outline, payloads)
        readiness = self.calculate_readiness(outline.id)
        self._upsert("script_outlines", {**outline.to_dict(), "readiness_status": readiness["status"].value if hasattr(readiness["status"], "value") else str(readiness["status"]), "updated_at": _now()})
        self._upsert("script_outline_requests", {**request.to_dict(), "status": ProductionRequestStatus.COMPLETED_WITH_WARNINGS.value if readiness["warnings"] else ProductionRequestStatus.COMPLETED.value, "updated_at": _now()})
        return self.get_outline(outline.id) or outline

    def list_outlines(self, creator_id: str) -> list[ProductionRecord]:
        return self._entities(
            "script_outlines",
            where="creator_id = ?",
            params=(creator_id,),
            order_by="updated_at DESC",
            enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )

    def get_outline(self, outline_id: str) -> ProductionRecord | None:
        return self._entity(
            "script_outlines",
            where="id = ?",
            params=(outline_id,),
            enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )

    def _current_outline(self, creator_id: str) -> ProductionRecord | None:
        outlines = self.list_outlines(creator_id)
        return next((outline for outline in outlines if outline.status == ScriptOutlineStatus.APPROVED), outlines[0] if outlines else None)

    def review_outline(self, outline_id: str, *, decision: str, reason: str, reviewer: str | None = None) -> ProductionRecord:
        outline = self.get_outline(outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        mapping = {
            "approve": ScriptOutlineStatus.APPROVED,
            "reject": ScriptOutlineStatus.CANCELLED,
            "defer": ScriptOutlineStatus.NEEDS_REVIEW,
            "needs_information": ScriptOutlineStatus.NEEDS_INFORMATION,
            "request_changes": ScriptOutlineStatus.NEEDS_REVIEW,
            "reduce_scope": ScriptOutlineStatus.NEEDS_REVIEW,
            "change_structure": ScriptOutlineStatus.NEEDS_REVIEW,
            "change_duration": ScriptOutlineStatus.NEEDS_REVIEW,
            "change_platform": ScriptOutlineStatus.NEEDS_REVIEW,
            "change_scene": ScriptOutlineStatus.NEEDS_REVIEW,
            "remove_claim": ScriptOutlineStatus.NEEDS_REVIEW,
            "request_proof": ScriptOutlineStatus.NEEDS_REVIEW,
            "replace_reference": ScriptOutlineStatus.NEEDS_REVIEW,
            "request_rights": ScriptOutlineStatus.NEEDS_REVIEW,
            "request_participant_release": ScriptOutlineStatus.NEEDS_REVIEW,
            "request_location_permission": ScriptOutlineStatus.NEEDS_REVIEW,
            "change_recording_order": ScriptOutlineStatus.NEEDS_REVIEW,
            "approve_scene_planning": ScriptOutlineStatus.READY_FOR_SCENE_PLANNING,
            "approve_recording_preparation": ScriptOutlineStatus.READY_FOR_RECORDING_PREPARATION,
            "approve_recording_readiness": ScriptOutlineStatus.READY_FOR_RECORDING,
            "block": ScriptOutlineStatus.BLOCKED,
            "supersede": ScriptOutlineStatus.SUPERSEDED,
            "archive": ScriptOutlineStatus.ARCHIVED,
        }
        new_status = mapping.get(decision, ScriptOutlineStatus.NEEDS_REVIEW)
        self._upsert("script_outlines", {**outline.to_dict(), "status": new_status.value, "updated_at": _now()})
        review = {
            "id": _stable_id("production-review", outline_id, decision, reason, reviewer or ""),
            "creator_id": outline.creator_id,
            "script_outline_id": outline_id,
            "review_type": "outline_review",
            "decision": decision,
            "previous_status": outline.status.value if hasattr(outline.status, "value") else str(outline.status),
            "new_status": new_status.value,
            "reason": reason,
            "reviewer": reviewer,
            "reviewed_at": _now(),
            "created_at": _now(),
        }
        self._upsert("production_reviews", review)
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None:
            feedback_kwargs = {
                "creator_id": outline.creator_id,
                "workflow_type": "production_preparation",
                "artifact_type": "script_outline",
                "artifact_id": outline.id,
                "project_id": None,
                "metadata": {
                    "decision": decision,
                    "reason": reason,
                    "reviewer": reviewer,
                    "review_type": "outline_review",
                    "previous_status": outline.status.value if hasattr(outline.status, "value") else str(outline.status),
                    "new_status": new_status.value,
                },
            }
            if decision == "approve" or decision in {"approve_scene_planning", "approve_recording_preparation", "approve_recording_readiness"}:
                feedback_service.record_acceptance(**feedback_kwargs)
            elif decision == "reject":
                feedback_service.record_rejection(**feedback_kwargs)
            elif decision == "supersede":
                feedback_service.record_supersession(**feedback_kwargs)
        return self.get_outline(outline_id) or outline

    def version_outline(self, outline_id: str, *, reason: str = "versioned_outline") -> ProductionRecord:
        outline = self.get_outline(outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        version = int(outline.version or 1) + 1
        brief = self._load_brief(outline.creator_id, outline.content_brief_id)
        context = self.create_context_snapshot(outline.creator_id, content_brief_id=brief.id, brief_version=int(getattr(brief, "version", 1) or 1))
        payload = outline.to_dict()
        payload.update(
            {
                "id": _stable_id("production-outline-version", outline.id, str(version), reason),
                "parent_outline_id": outline.id,
                "script_outline_request_id": None,
                "version": version,
                "production_context_snapshot_id": context.id,
                "status": ScriptOutlineStatus.DRAFT.value,
                "readiness_status": ReadinessStatus.NEEDS_REVIEW.value,
                "updated_at": _now(),
            }
        )
        return _row_to_entity(self._upsert("script_outlines", payload), enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})

    def supersede_outline(self, outline_id: str, *, replacement_id: str | None = None, reason: str) -> ProductionRecord:
        outline = self.get_outline(outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        if replacement_id:
            replacement = self.get_outline(replacement_id)
            if replacement is None:
                raise ProductionPreparationNotFoundError("El replacement outline no existe.")
            self._upsert("script_outlines", {**outline.to_dict(), "status": ScriptOutlineStatus.SUPERSEDED.value, "updated_at": _now()})
            return replacement
        self._upsert("script_outlines", {**outline.to_dict(), "status": ScriptOutlineStatus.SUPERSEDED.value, "updated_at": _now()})
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None:
            feedback_service.record_supersession(
                creator_id=outline.creator_id,
                workflow_type="production_preparation",
                artifact_type="script_outline",
                artifact_id=outline.id,
                project_id=None,
                metadata={
                    "reason": reason,
                    "replacement_id": replacement_id,
                    "previous_status": outline.status.value if hasattr(outline.status, "value") else str(outline.status),
                    "new_status": ScriptOutlineStatus.SUPERSEDED.value,
                },
            )
        children = self._entities(
            "script_outlines",
            where="creator_id = ? AND parent_outline_id = ?",
            params=(outline.creator_id, outline.id),
            order_by="CAST(version AS INTEGER) DESC, updated_at DESC",
            enum_fields={"status": ScriptOutlineStatus, "outline_type": ScriptOutlineType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )
        if children:
            return children[0]
        return self.version_outline(outline_id, reason=reason)

    def calculate_readiness(self, outline_id: str) -> dict[str, object]:
        outline = self.get_outline(outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        claims = self.list_claim_links(outline.id)
        rights = self.list_dependencies(outline.id)
        participants = self.list_participants(outline.id)
        locations = self.list_locations(outline.id)
        equipment = self.list_equipment(outline.id)
        continuity = self.list_continuity(outline.id)
        gates = self.list_gates(outline.id)
        blockers: list[str] = []
        warnings: list[str] = []
        if outline.copying_risk in {CopyingRiskLevel.HIGH, CopyingRiskLevel.PROHIBITED}:
            blockers.append("copying_risk")
        if any(str(getattr(claim, "verification_required", "not_required")) == "blocked" for claim in claims):
            blockers.append("claim_blocked")
        if any(str(getattr(dep, "blocking", False)) in {"True", "true", "1"} for dep in rights if str(getattr(dep, "dependency_type", "")) in {DependencyType.RIGHTS_APPROVAL.value, DependencyType.PARTICIPANT_RELEASE.value, DependencyType.LOCATION_PERMISSION.value}):
            blockers.append("dependencies")
        if any(str(getattr(participant, "release_status", "")) in {"pending", "blocked"} and bool(getattr(participant, "release_required", False)) for participant in participants):
            blockers.append("participants")
        if any(str(getattr(location, "permission_status", "")) in {"pending", "blocked"} and bool(getattr(location, "permission_required", False)) for location in locations):
            blockers.append("locations")
        if any(str(getattr(item, "availability_status", "")) in {"missing", "unavailable"} and bool(getattr(item, "required", False)) for item in equipment):
            blockers.append("equipment")
        if any(bool(getattr(rule, "blocking", False)) for rule in continuity):
            warnings.append("continuity")
        if any(str(getattr(gate, "status", "")) in {"pending", "rejected", "blocked"} and bool(getattr(gate, "required", False)) for gate in gates):
            warnings.append("gates_pending")
        score = 100 - len(blockers) * 30 - len(warnings) * 8
        score = max(0, min(100, score))
        if blockers:
            status = ReadinessStatus.BLOCKED
        elif score >= 80 and not warnings:
            status = ReadinessStatus.READY_FOR_RECORDING_PREPARATION
        elif score >= 60:
            status = ReadinessStatus.CONDITIONALLY_READY
        elif warnings:
            status = ReadinessStatus.NEEDS_REVIEW
        else:
            status = ReadinessStatus.NEEDS_INFORMATION
        return {
            "status": status,
            "score": score,
            "breakdown": {
                "claims": len(claims),
                "rights": len(rights),
                "participants": len(participants),
                "locations": len(locations),
                "equipment": len(equipment),
                "continuity": len(continuity),
                "gates": len(gates),
            },
            "blockers": blockers,
            "warnings": warnings,
            "missing_data": [],
            "critical_requirements": [gate.to_dict() for gate in gates if getattr(gate, "required", False)],
            "recommended_next_action": "human_review",
        }

    def create_snapshot(self, outline_id: str, *, snapshot_type: str = "draft_outline") -> ProductionRecord:
        outline = self.get_outline(outline_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        payload = {
            "id": _stable_id("production-snapshot", outline_id, snapshot_type, str(outline.version)),
            "creator_id": outline.creator_id,
            "script_outline_id": outline.id,
            "snapshot_type": snapshot_type,
            "outline_version": outline.version,
            "source_fingerprint": _stable_id("production-snapshot-fingerprint", outline.id, snapshot_type, str(outline.version)),
            "snapshot_json": _json_dumps({"outline": outline.to_dict(), "snapshot_type": snapshot_type}),
            "created_at": _now(),
        }
        existing = self._fetch("production_snapshots", where="source_fingerprint = ?", params=(payload["source_fingerprint"],))
        if existing:
            return _row_to_entity(existing)
        return _row_to_entity(self._upsert("production_snapshots", payload))

    def compare_snapshots(self, left_id: str, right_id: str) -> dict[str, object]:
        left = self._entity("production_snapshots", where="id = ?", params=(left_id,))
        right = self._entity("production_snapshots", where="id = ?", params=(right_id,))
        if left is None or right is None:
            raise ProductionPreparationNotFoundError("Uno de los snapshots no existe.")
        return {"left": left.to_dict(), "right": right.to_dict(), "differences": {"left_version": getattr(left, "outline_version", None), "right_version": getattr(right, "outline_version", None)}}

    def build_report(
        self,
        *,
        creator_id: str,
        outline_id: str | None,
        report_type: str,
    ) -> ProductionRecord:
        outline = self.get_outline(outline_id) if outline_id else self._current_outline(creator_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("No hay outline disponible.")
        brief = self._load_brief(creator_id, outline.content_brief_id)
        report = {
            "id": _stable_id("production-report", creator_id, outline.id, report_type, str(uuid4())),
            "creator_id": creator_id,
            "script_outline_id": outline.id,
            "report_type": report_type,
            "source_fingerprint": _stable_id("production-report-fingerprint", outline.id, report_type, str(outline.version)),
            "report_json": _json_dumps({
                "creator": creator_id,
                "outline": outline.to_dict(),
                "brief": brief.to_dict(),
                "sections": [item.to_dict() for item in self.list_sections(outline.id)],
                "beats": [item.to_dict() for item in self.list_beats(outline.id)],
                "segments": [item.to_dict() for item in self.list_segments(outline.id)],
                "scenes": [item.to_dict() for item in self.list_scenes(outline.id)],
                "shots": [item.to_dict() for item in self.list_shots(outline.id)],
                "readiness": self.calculate_readiness(outline.id),
            }),
            "created_at": _now(),
        }
        existing = self._fetch("production_reports", where="source_fingerprint = ?", params=(report["source_fingerprint"],))
        if existing:
            return _row_to_entity(existing)
        return _row_to_entity(self._upsert("production_reports", report))

    def export_report(self, report_id: str, report_format: str) -> Path:
        report = self._entity("production_reports", where="id = ?", params=(report_id,))
        if report is None:
            raise ProductionPreparationNotFoundError("El reporte no existe.")
        output_path = self._reports_root / f"{report_id}.{report_format}"
        payload = _json_loads(str(report.report_json), {})
        if report_format == "json":
            output_path.write_text(_json_dumps(payload), encoding="utf-8")
        elif report_format == "txt":
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
        else:
            rows = payload.get("sections") or payload.get("shots") or []
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                if rows:
                    header = list(rows[0].keys())
                    writer.writerow([_safe_csv_value(item) for item in header])
                    for row in rows:
                        writer.writerow([_safe_csv_value(row.get(column)) for column in header])
        return output_path

    def build_overview(self, creator_id: str) -> dict[str, object]:
        outlines = self.list_outlines(creator_id)
        active = next((outline for outline in outlines if outline.status == ScriptOutlineStatus.APPROVED), outlines[0] if outlines else None)
        return {
            "creator_id": creator_id,
            "total_outlines": len(outlines),
            "needs_review": sum(1 for outline in outlines if outline.status == ScriptOutlineStatus.NEEDS_REVIEW),
            "blocked": sum(1 for outline in outlines if outline.status == ScriptOutlineStatus.BLOCKED),
            "ready_for_scene_planning": sum(1 for outline in outlines if outline.status == ScriptOutlineStatus.READY_FOR_SCENE_PLANNING),
            "ready_for_recording_preparation": sum(1 for outline in outlines if outline.status == ScriptOutlineStatus.READY_FOR_RECORDING_PREPARATION),
            "ready_for_recording": sum(1 for outline in outlines if outline.status == ScriptOutlineStatus.READY_FOR_RECORDING),
            "claims_blocked": sum(1 for outline in outlines if self.calculate_readiness(outline.id)["status"] == ReadinessStatus.BLOCKED),
            "rights_blocked": sum(1 for outline in outlines if any(str(dep.dependency_type) in {DependencyType.RIGHTS_APPROVAL.value, DependencyType.LOCATION_PERMISSION.value, DependencyType.PARTICIPANT_RELEASE.value} for dep in self.list_dependencies(outline.id))),
            "participants_pending": sum(1 for outline in outlines if any(str(part.release_status) in {"pending", "blocked"} for part in self.list_participants(outline.id))),
            "locations_pending": sum(1 for outline in outlines if any(str(loc.permission_status) in {"pending", "blocked"} for loc in self.list_locations(outline.id))),
            "equipment_missing": sum(1 for outline in outlines if any(str(eq.availability_status) in {"missing", "unavailable"} for eq in self.list_equipment(outline.id))),
            "continuity_warnings": sum(1 for outline in outlines if any(bool(rule.blocking) for rule in self.list_continuity(outline.id))),
            "gates_pending": sum(1 for outline in outlines if any(gate.status == "pending" for gate in self.list_gates(outline.id))),
            "next_review": None,
            "active_outline": None if active is None else active.to_dict(),
        }

    def list_tasks(self, creator_id: str) -> list[ProductionRecord]:
        outlines = self.list_outlines(creator_id)
        tasks: list[ProductionRecord] = []
        for outline in outlines:
            tasks.append(
                ProductionRecord(
                    id=outline.id,
                    task_id=outline.id,
                    creator_id=creator_id,
                    title=f"Production outline {getattr(outline, 'title', outline.id)}",
                    stage_name=str(outline.status),
                    status="running" if outline.status in {ScriptOutlineStatus.ASSEMBLING, ScriptOutlineStatus.SCENE_PLANNING, ScriptOutlineStatus.RECORDING_PREPARATION} else "pending",
                    progress_percent=50.0 if outline.status == ScriptOutlineStatus.NEEDS_REVIEW else 100.0 if outline.status == ScriptOutlineStatus.APPROVED else 0.0,
                    message="Outline traced",
                    error=None,
                    updated_at=getattr(outline, "updated_at", _now()),
                    payload={"kind": "production_run", "outline_id": outline.id, "brief_id": outline.content_brief_id},
                )
            )
        return tasks

    def cancel_run(self, run_id: str) -> ProductionRecord:
        outline = self.get_outline(run_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        return self.review_outline(outline.id, decision="reject", reason="cancelled")

    def resume_run(self, run_id: str) -> ProductionRecord:
        outline = self.get_outline(run_id)
        if outline is None:
            raise ProductionPreparationNotFoundError("El outline no existe.")
        return self.review_outline(outline.id, decision="approve", reason="resume")

    def __getattr__(self, name: str):
        if name in self._list_accessors:
            table, foreign_key, enum_fields = self._list_accessors[name]
            order_by_map = {
                "outline_sections": "sequence_order ASC",
                "outline_beats": "sequence_order ASC",
                "outline_segments": "sequence_order ASC",
                "production_scene_plans": "scene_number ASC",
                "production_shot_items": "shot_number ASC",
                "production_shot_groups": "sequence_order ASC",
                "production_shot_group_items": "sequence_order ASC",
                "production_recording_blocks": "sequence_order ASC",
                "production_recording_block_items": "sequence_order ASC",
                "production_checklist_items": "sequence_order ASC",
                "production_approval_gates": "sequence_order ASC",
            }

            def loader(target_id: str):
                order_by = order_by_map.get(table, "created_at ASC")
                return self._entities(table, where=f"{foreign_key} = ?", params=(target_id,), order_by=order_by, enum_fields=enum_fields)

            return loader
        raise AttributeError(name)


def build_production_preparation_service(
    *,
    settings: AppSettings | None,
    paths: ProjectPaths,
    repository,
    brief_service: ContentBriefService | None = None,
    planning_service: Any | None = None,
    recommendation_service: Any | None = None,
    experiment_service: Any | None = None,
    content_library_service: Any | None = None,
    creator_memory_service: Any | None = None,
    creator_language_service: Any | None = None,
    creator_context_assembly_service: CreatorContextAssemblyService | None = None,
    creator_preference_application_service: CreatorPreferenceApplicationService | None = None,
    creator_voice_workflow_application_service: CreatorVoiceWorkflowApplicationService | None = None,
    creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
    audience_service: Any | None = None,
    platform_service: Any | None = None,
    packaging_service: Any | None = None,
    preferences: dict[str, object] | None = None,
    logger: logging.Logger | None = None,
) -> ProductionPreparationService:
    return ProductionPreparationService(
        settings=settings,
        paths=paths,
        repository=repository,
        brief_service=brief_service,
        planning_service=planning_service,
        recommendation_service=recommendation_service,
        experiment_service=experiment_service,
        content_library_service=content_library_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        creator_context_assembly_service=creator_context_assembly_service,
        creator_preference_application_service=creator_preference_application_service,
        creator_voice_workflow_application_service=creator_voice_workflow_application_service,
        creator_context_policy_registry=creator_context_policy_registry,
        audience_service=audience_service,
        platform_service=platform_service,
        packaging_service=packaging_service,
        preferences=preferences,
        logger=logger,
    )
