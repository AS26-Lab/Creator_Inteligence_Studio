"""Servicio determinista para Content Brief and Pre-Production Foundation."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable
from uuid import NAMESPACE_URL, uuid5, uuid4

from creator_intelligence_studio.domain.content_briefs import (
    ApprovalGateType,
    AngleType,
    AssetType,
    AudienceType,
    BoundaryType,
    BriefRecord,
    BriefRequestStatus,
    BriefStatus,
    BriefType,
    ClaimType,
    ClaimVerificationStatus,
    ContentBriefConflictError,
    ContentBriefNotFoundError,
    ContentBriefRepository,
    ContentBriefStateError,
    ContentBriefValidationError,
    CopyingRiskLevel,
    DependencyType,
    HookType,
    MessageLevel,
    NarrativeOutlineType,
    ProductionRequirementType,
    PromiseType,
    ReadinessStatus,
    ReviewDecision,
    RightsStatus,
    RightsType,
    RiskType,
    SectionType,
    build_brief_fingerprint,
)
from creator_intelligence_studio.application.services.creator_context_assembly_service import (
    CreatorContextAssemblyService,
)
from creator_intelligence_studio.application.services.creator_context_policy import (
    CreatorContextPolicyRegistry,
    build_default_creator_context_policy_registry,
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


def _default_preferences() -> dict[str, object]:
    return {
        "default_brief_type": BriefType.UNKNOWN.value,
        "default_platform_scope": [],
        "default_content_type": [],
        "require_human_review": True,
        "allow_automatic_approval": False,
        "allow_ready_for_production_without_all_gates": False,
        "require_verified_sensitive_claims": True,
        "require_rights_checks": True,
        "require_creator_language_review": True,
        "require_packaging_review": True,
        "require_measurement_plan": True,
        "maximum_copying_risk": CopyingRiskLevel.HIGH.value,
        "minimum_context_freshness": "recent",
        "readiness_warning_threshold": 70,
        "readiness_block_threshold": 50,
        "default_target_duration_seconds": 180,
        "max_angles_per_brief": 3,
        "max_references_per_brief": 10,
        "max_shot_plan_items": 6,
        "automatic_media_download": False,
        "automatic_reference_download": False,
        "automatic_script_generation": False,
        "automatic_image_generation": False,
        "automatic_publication": False,
        "brief_cache_hours": 24,
        "report_default_format": "json",
    }


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


def _row_to_entity(row: dict[str, Any] | None, *, enum_fields: dict[str, Any] | None = None) -> BriefRecord | None:
    if row is None:
        return None
    payload = dict(row)
    for field, enum_cls in (enum_fields or {}).items():
        if field in payload:
            payload[field] = _enum_value(enum_cls, payload[field], payload[field])
    return BriefRecord(**payload)


class ContentBriefService:
    ENGINE_VERSION = "v29"

    def __init__(
        self,
        *,
        settings: AppSettings | None,
        paths: ProjectPaths,
        repository: ContentBriefRepository,
        planning_service: Any | None = None,
        recommendation_service: Any | None = None,
        experiment_service: Any | None = None,
        content_library_service: Any | None = None,
        creator_memory_service: Any | None = None,
        creator_language_service: Any | None = None,
        creator_context_assembly_service: CreatorContextAssemblyService | None = None,
        creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
        audience_service: Any | None = None,
        analytics_service: Any | None = None,
        analytics_lab_service: Any | None = None,
        market_service: Any | None = None,
        platform_service: Any | None = None,
        packaging_service: Any | None = None,
        preferences: dict[str, object] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.planning_service = planning_service
        self.recommendation_service = recommendation_service
        self.experiment_service = experiment_service
        self.content_library_service = content_library_service
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.creator_context_assembly_service = creator_context_assembly_service
        self.creator_context_policy_registry = creator_context_policy_registry or build_default_creator_context_policy_registry()
        self.audience_service = audience_service
        self.analytics_service = analytics_service
        self.analytics_lab_service = analytics_lab_service
        self.market_service = market_service
        self.platform_service = platform_service
        self.packaging_service = packaging_service
        self.creator_feedback_service = None
        self.preferences = {**_default_preferences(), **(preferences or {})}
        self.logger = logger or logging.getLogger("creator_intelligence_studio.content_briefs")
        self._reports_root = self.paths.data_directory / "briefs" / "reports"
        self._snapshots_root = self.paths.data_directory / "briefs" / "snapshots"
        self._reports_root.mkdir(parents=True, exist_ok=True)
        self._snapshots_root.mkdir(parents=True, exist_ok=True)
        self._list_accessors: dict[str, tuple[str, str, dict[str, Any] | None]] = {
            "list_sections": ("brief_sections", "content_brief_id", {"completion_status": None}),
            "list_audience_definitions": ("brief_audience_definitions", "content_brief_id", {"confidence_level": None}),
            "list_promises": ("brief_content_promises", "content_brief_id", {"status": None}),
            "list_angles": ("brief_content_angles", "content_brief_id", {"status": None}),
            "list_message_hierarchy": ("brief_message_hierarchy", "content_brief_id", {"status": None}),
            "list_hooks": ("brief_hook_directions", "content_brief_id", {"status": None}),
            "list_outlines": ("brief_narrative_outlines", "content_brief_id", {"status": None}),
            "list_talking_points": ("brief_talking_points", "content_brief_id", {"status": None}),
            "list_claims": ("brief_claims", "content_brief_id", {"verification_status": None}),
            "list_fact_checks": ("brief_fact_checks", "content_brief_id", {"status": None}),
            "list_packaging": ("brief_packaging_directions", "content_brief_id", {"status": None}),
            "list_visual": ("brief_visual_directions", "content_brief_id", {"status": None}),
            "list_audio": ("brief_audio_directions", "content_brief_id", {"status": None}),
            "list_adaptations": ("brief_platform_adaptations", "content_brief_id", {"status": None}),
            "list_boundaries": ("brief_boundaries", "content_brief_id", {"status": None}),
            "list_references": ("brief_references", "content_brief_id", {"copying_risk": None}),
            "list_rights": ("brief_rights_checks", "content_brief_id", {"status": None}),
            "list_assets": ("brief_asset_requirements", "content_brief_id", {"readiness_status": None}),
            "list_requirements": ("brief_production_requirements", "content_brief_id", {"availability_status": None}),
            "list_shots": ("brief_shot_plan_items", "content_brief_id", {"status": None}),
            "list_checklists": ("brief_checklists", "content_brief_id", {"status": None}),
            "list_checklist_items": ("brief_checklist_items", "checklist_id", {"status": None}),
            "list_gates": ("brief_approval_gates", "content_brief_id", {"status": None}),
            "list_risks": ("brief_risks", "content_brief_id", {"severity": None}),
            "list_dependencies": ("brief_dependencies", "content_brief_id", {"blocking": None}),
            "list_reviews": ("brief_reviews", "content_brief_id", {"decision": None}),
            "list_snapshots": ("brief_snapshots", "content_brief_id", None),
            "list_reports": ("brief_reports", "content_brief_id", None),
        }

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

    def _entity(self, table: str, *, where: str, params: tuple[Any, ...], enum_fields: dict[str, Any] | None = None) -> BriefRecord | None:
        return _row_to_entity(self._fetch(table, where=where, params=params), enum_fields=enum_fields)

    def _entities(self, table: str, *, where: str, params: tuple[Any, ...], order_by: str | None = None, enum_fields: dict[str, Any] | None = None) -> list[BriefRecord]:
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

    def _latest_id(self, items: list[Any]) -> str | None:
        if not items:
            return None
        first = items[0]
        if hasattr(first, "id"):
            return str(first.id)
        if isinstance(first, dict):
            return str(first.get("id")) if first.get("id") is not None else None
        return None

    def _snapshot_identifier(self, service: Any | None, method_names: tuple[str, ...], creator_id: str) -> str | None:
        result = self._safe_call(service, method_names, creator_id)
        if result is None:
            return None
        if isinstance(result, list):
            return self._latest_id(result)
        if hasattr(result, "id"):
            return str(result.id)
        if isinstance(result, dict):
            return str(result.get("id")) if result.get("id") is not None else None
        return None

    def _load_reference_payload(self, creator_id: str) -> dict[str, object]:
        recommendations = []
        if self.recommendation_service is not None:
            recommendations = list(self._safe_call(self.recommendation_service, ("list_recommendations", "list_candidates"), creator_id) or [])
        approved: list[dict[str, object]] = []
        deferred: list[dict[str, object]] = []
        blocked: list[dict[str, object]] = []
        rejected: list[dict[str, object]] = []
        expired: list[dict[str, object]] = []
        for recommendation in recommendations:
            item = self._safe_payload(recommendation)
            status = str(item.get("status") or "")
            if status == "approved":
                approved.append(item)
            elif status == "deferred":
                deferred.append(item)
            elif status == "blocked":
                blocked.append(item)
            elif status == "rejected":
                rejected.append(item)
            elif status == "expired":
                expired.append(item)
        return {
            "approved": approved,
            "deferred": deferred,
            "blocked": blocked,
            "rejected": rejected,
            "expired": expired,
            "items": [self._safe_payload(item) for item in recommendations],
        }

    def _validate_creator(self, creator_id: str) -> None:
        if not creator_id:
            raise ContentBriefValidationError("Se requiere creator_id.")

    def _load_source(self, creator_id: str, source_type: str, source_id: str) -> dict[str, Any]:
        source_type = str(source_type or "").strip()
        source_id = str(source_id or "").strip()
        if not source_type:
            raise ContentBriefValidationError("Se requiere source_type.")
        if source_type == "manual_request":
            return {
                "source_type": source_type,
                "source_id": source_id or _stable_id("manual-request", creator_id, _now()),
                "creator_id": creator_id,
                "status": "draft",
                "title": "Manual request",
                "summary": "Solicitud manual de brief.",
                "platform_scope_json": _json_dumps(self.preferences.get("default_platform_scope", [])),
                "content_type_scope_json": _json_dumps(self.preferences.get("default_content_type", [])),
                "objective_scope_json": _json_dumps([]),
                "copying_risk": CopyingRiskLevel.UNKNOWN.value,
                "rights_status": RightsStatus.UNKNOWN.value,
                "measurement_status": "unknown",
                "references": [],
                "constraints": [],
                "dependencies": [],
                "limitations": ["manual_request"],
            }
        if self.planning_service is not None and source_type == "roadmap_item":
            item = self._safe_call(self.planning_service, ("get_roadmap_item", "show_roadmap_item"), source_id)
            if item is None:
                raise ContentBriefNotFoundError("El roadmap item no existe.")
            payload = self._safe_payload(item)
            if str(payload.get("creator_id") or creator_id) != creator_id:
                raise ContentBriefValidationError("No se permite cross-creator leakage.")
            plan = self._safe_call(self.planning_service, ("get_plan",), str(payload.get("strategic_plan_id") or ""))
            plan_payload = self._safe_payload(plan) if plan is not None else {}
            return {
                "source_type": source_type,
                "source_id": source_id,
                "creator_id": creator_id,
                "status": str(payload.get("status") or "unknown"),
                "title": str(payload.get("title") or "Roadmap item"),
                "summary": str(payload.get("description") or payload.get("title") or "Roadmap item"),
                "platform_scope_json": payload.get("platform_scope_json") or payload.get("platform_scope") or plan_payload.get("platform_scope_json") or _json_dumps([]),
                "content_type_scope_json": payload.get("content_type_scope_json") or payload.get("content_type_scope") or _json_dumps([]),
                "objective_scope_json": payload.get("objective_scope_json") or _json_dumps([]),
                "copying_risk": str(payload.get("copying_risk") or CopyingRiskLevel.MODERATE.value),
                "rights_status": str(payload.get("rights_status") or RightsStatus.UNKNOWN.value),
                "measurement_status": str(payload.get("measurement_status") or "unknown"),
                "reference_titles": [str(payload.get("title") or "Roadmap item")],
                "references": [],
                "constraints": [],
                "dependencies": self._safe_call(self.planning_service, ("list_dependencies_for_item",), source_id) or [],
                "source_plan_id": payload.get("strategic_plan_id"),
                "source_plan_name": plan_payload.get("name"),
                "source_plan_status": plan_payload.get("status"),
                "limitations": [f"roadmap_status:{payload.get('status') or 'unknown'}"],
            }
        if self.recommendation_service is not None and source_type in {"recommendation", "approved_recommendation"}:
            recommendation = self._safe_call(self.recommendation_service, ("get_recommendation", "show_recommendation", "get_candidate"), source_id)
            if recommendation is None:
                raise ContentBriefNotFoundError("La recomendacion no existe.")
            payload = self._safe_payload(recommendation)
            if str(payload.get("creator_id") or creator_id) != creator_id:
                raise ContentBriefValidationError("No se permite cross-creator leakage.")
            return {
                "source_type": source_type,
                "source_id": source_id,
                "creator_id": creator_id,
                "status": str(payload.get("status") or "unknown"),
                "title": str(payload.get("title") or "Recommendation"),
                "summary": str(payload.get("summary") or payload.get("title") or "Recommendation"),
                "platform_scope_json": payload.get("platform_scope_json") or _json_dumps([]),
                "content_type_scope_json": payload.get("content_type_scope_json") or _json_dumps([]),
                "objective_scope_json": payload.get("objective_scope_json") or _json_dumps([]),
                "copying_risk": str(payload.get("copying_risk") or payload.get("overall_risk") or CopyingRiskLevel.UNKNOWN.value),
                "rights_status": str(payload.get("rights_status") or RightsStatus.UNKNOWN.value),
                "measurement_status": str(payload.get("measurement_status") or "unknown"),
                "references": payload.get("evidence_json") or payload.get("evidence") or [],
                "constraints": payload.get("constraints_json") or [],
                "limitations": [f"recommendation_status:{payload.get('status') or 'unknown'}"],
                "experiment_id": payload.get("experiment_id"),
            }
        if self.experiment_service is not None and source_type == "experiment":
            experiment = self._safe_call(self.experiment_service, ("get_experiment", "show_experiment"), source_id)
            if experiment is None:
                raise ContentBriefNotFoundError("El experimento no existe.")
            payload = self._safe_payload(experiment)
            if str(payload.get("creator_id") or creator_id) != creator_id:
                raise ContentBriefValidationError("No se permite cross-creator leakage.")
            return {
                "source_type": source_type,
                "source_id": source_id,
                "creator_id": creator_id,
                "status": str(payload.get("status") or "unknown"),
                "title": str(payload.get("title") or "Experiment"),
                "summary": str(payload.get("summary") or payload.get("title") or "Experiment"),
                "platform_scope_json": payload.get("platform_scope_json") or _json_dumps([]),
                "content_type_scope_json": payload.get("content_type_scope_json") or _json_dumps([]),
                "objective_scope_json": payload.get("objective_scope_json") or _json_dumps([]),
                "copying_risk": str(payload.get("copying_risk") or CopyingRiskLevel.UNKNOWN.value),
                "rights_status": str(payload.get("rights_status") or RightsStatus.UNKNOWN.value),
                "measurement_status": str(payload.get("measurement_status") or "unknown"),
                "references": payload.get("hypothesis_json") or [],
                "constraints": payload.get("constraints_json") or [],
                "limitations": ["experiment_source"],
                "experiment_id": source_id,
            }
        if self.content_library_service is not None and source_type in {"internal_content_draft", "content_library"}:
            content = self._safe_call(self.content_library_service, ("get_content_item", "get_content", "show_content", "get_item"), source_id)
            if content is None:
                raise ContentBriefNotFoundError("El contenido interno no existe.")
            payload = self._safe_payload(content)
            if str(payload.get("creator_id") or creator_id) != creator_id:
                raise ContentBriefValidationError("No se permite cross-creator leakage.")
            return {
                "source_type": source_type,
                "source_id": source_id,
                "creator_id": creator_id,
                "status": str(payload.get("status") or "draft"),
                "title": str(payload.get("title") or "Internal content"),
                "summary": str(payload.get("summary") or payload.get("title") or "Internal content"),
                "platform_scope_json": payload.get("platform_scope_json") or _json_dumps([]),
                "content_type_scope_json": payload.get("content_type_scope_json") or _json_dumps([]),
                "objective_scope_json": payload.get("objective_scope_json") or _json_dumps([]),
                "copying_risk": str(payload.get("copying_risk") or CopyingRiskLevel.NONE.value),
                "rights_status": str(payload.get("rights_status") or RightsStatus.UNKNOWN.value),
                "measurement_status": str(payload.get("measurement_status") or "unknown"),
                "references": payload.get("references") or [],
                "constraints": payload.get("constraints") or [],
                "limitations": ["internal_content_source"],
            }
        if self.planning_service is not None and source_type in {"strategic_initiative", "campaign", "content_series", "backlog_item"}:
            lookup_methods = {
                "strategic_initiative": ("get_initiative", "show_initiative"),
                "campaign": ("get_campaign", "show_campaign"),
                "content_series": ("get_series", "show_series"),
                "backlog_item": ("get_backlog_item", "show_backlog_item"),
            }
            source = self._safe_call(self.planning_service, lookup_methods[source_type], source_id)
            if source is None:
                raise ContentBriefNotFoundError("La fuente estrategica no existe.")
            payload = self._safe_payload(source)
            if str(payload.get("creator_id") or creator_id) != creator_id:
                raise ContentBriefValidationError("No se permite cross-creator leakage.")
            return {
                "source_type": source_type,
                "source_id": source_id,
                "creator_id": creator_id,
                "status": str(payload.get("status") or "unknown"),
                "title": str(payload.get("name") or payload.get("title") or source_type.replace("_", " ").title()),
                "summary": str(payload.get("description") or payload.get("title") or source_type.replace("_", " ").title()),
                "platform_scope_json": payload.get("platform_scope_json") or _json_dumps([]),
                "content_type_scope_json": payload.get("content_type_scope_json") or _json_dumps([]),
                "objective_scope_json": payload.get("objective_scope_json") or _json_dumps([]),
                "copying_risk": str(payload.get("copying_risk") or CopyingRiskLevel.UNKNOWN.value),
                "rights_status": str(payload.get("rights_status") or RightsStatus.UNKNOWN.value),
                "measurement_status": str(payload.get("measurement_status") or "unknown"),
                "references": payload.get("references") or [],
                "constraints": payload.get("constraints") or [],
                "limitations": [f"{source_type}_source"],
            }
        if source_type == "manual_request":
            return self._load_source(creator_id, source_type, source_id)
        raise ContentBriefNotFoundError("La fuente de brief no existe o no esta soportada.")

    def _brief_type_for_source(self, source: dict[str, Any], request_payload: dict[str, Any]) -> BriefType:
        content_types = set()
        try:
            content_types = set(_safe_list(_json_loads(str(source.get("content_type_scope_json") or "[]"), [])))
        except Exception:
            content_types = set()
        platforms = set()
        try:
            platforms = set(_safe_list(_json_loads(str(source.get("platform_scope_json") or "[]"), [])))
        except Exception:
            platforms = set()
        source_type = str(source.get("source_type") or "")
        if source_type == "experiment":
            return BriefType.EXPERIMENT_BRIEF
        if source_type == "internal_content_draft":
            return BriefType.REPURPOSE_BRIEF
        if source_type == "campaign":
            return BriefType.CAMPAIGN_CONTENT_BRIEF
        if source_type == "content_series":
            return BriefType.SERIES_EPISODE_BRIEF
        if "youtube" in platforms and ("longform" in content_types or "long_form" in content_types or "educational" in str(source.get("summary") or "").lower()):
            return BriefType.LONGFORM_VIDEO_BRIEF
        if platforms.intersection({"tiktok", "instagram"}):
            return BriefType.SHORT_VIDEO_BRIEF
        if source_type in {"roadmap_item", "strategic_initiative", "recommendation", "approved_recommendation"}:
            return BriefType.VIDEO_BRIEF
        return _enum_value(BriefType, request_payload.get("brief_type"), BriefType.VIDEO_BRIEF)

    def create_context_snapshot(
        self,
        creator_id: str,
        *,
        roadmap_item_id: str | None = None,
        strategic_plan_id: str | None = None,
        recommendation_candidate_id: str | None = None,
        experiment_id: str | None = None,
        internal_content_id: str | None = None,
        created_at: str | None = None,
        preferences: dict[str, object] | None = None,
        constraints: list[dict[str, object]] | None = None,
        resources: list[dict[str, object]] | None = None,
        stale_data: list[str] | None = None,
        missing_data: list[str] | None = None,
        contradictions: list[dict[str, object]] | None = None,
        use_creator_context: bool = True,
    ) -> BriefRecord:
        self._validate_creator(creator_id)
        created_at = created_at or _now()
        context_policy = self.creator_context_policy_registry.get_by_workflow("content_brief")
        creator_memory_snapshot_id = self._snapshot_identifier(self.creator_memory_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots", "list_snapshots"), creator_id)
        creator_language_snapshot_id = self._snapshot_identifier(self.creator_language_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots", "list_snapshots"), creator_id)
        audience_snapshot_id = self._snapshot_identifier(self.audience_service, ("build_profile", "get_profile", "list_profiles"), creator_id)
        analytics_snapshot_id = self._snapshot_identifier(self.analytics_lab_service, ("generate_weekly_report", "list_reports"), creator_id)
        market_snapshot_id = self._snapshot_identifier(self.market_service, ("build_snapshot", "list_snapshots", "list_reports"), creator_id)
        platform_snapshot_id = self._snapshot_identifier(self.platform_service, ("list_reports", "list_integrations", "list_connections"), creator_id)
        packaging_snapshot_id = self._snapshot_identifier(self.packaging_service, ("list_concepts", "list_versions", "list_reports"), creator_id)
        recommendation_payload = self._load_reference_payload(creator_id)
        creator_context_bundle = None
        creator_context_package: dict[str, object] = {}
        creator_context_prompt: str | None = None
        creator_context_usage: dict[str, object] = {
            "enabled": False,
            "policy_id": None if context_policy is None else context_policy.policy_id,
            "grounding_mode": None if context_policy is None else context_policy.grounding_mode.value,
            "item_count": 0,
            "estimated_tokens": 0,
            "estimated_characters": 0,
            "truncated": False,
        }
        if use_creator_context and self.creator_context_assembly_service is not None and context_policy is not None and context_policy.is_context_allowed():
            brief_request_text = " | ".join(
                part
                for part in (
                    roadmap_item_id,
                    strategic_plan_id,
                    recommendation_candidate_id,
                    experiment_id,
                    internal_content_id,
                    str((recommendation_payload.get("approved") or [{}])[0].get("title") if recommendation_payload.get("approved") else ""),
                    str((recommendation_payload.get("items") or [{}])[0].get("summary") if recommendation_payload.get("items") else ""),
                )
                if part
            ) or "Content brief context"
            creator_context_request = context_policy.build_request(
                creator_id=creator_id,
                user_request=brief_request_text,
                query_text=brief_request_text,
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
        payload = {
            "creator_id": creator_id,
            "context_version": self.ENGINE_VERSION,
            "roadmap_item_id": roadmap_item_id,
            "strategic_plan_id": strategic_plan_id,
            "recommendation_candidate_id": recommendation_candidate_id,
            "experiment_id": experiment_id,
            "internal_content_id": internal_content_id,
            "preferences": dict(preferences or self.preferences),
            "constraints": constraints or [],
            "resources": resources or [],
            "stale_data": stale_data or [],
            "missing_data": missing_data or [],
            "contradictions": contradictions or [],
            "recommendations": recommendation_payload,
            "snapshot_ids": {
                "creator_memory_snapshot_id": creator_memory_snapshot_id,
                "creator_language_snapshot_id": creator_language_snapshot_id,
                "audience_snapshot_id": audience_snapshot_id,
                "analytics_snapshot_id": analytics_snapshot_id,
                "market_snapshot_id": market_snapshot_id,
                "platform_snapshot_id": platform_snapshot_id,
                "packaging_snapshot_id": packaging_snapshot_id,
            },
        }
        context_details = {
            "creator_context_enabled": bool(creator_context_usage["enabled"]),
            "creator_context_policy_id": creator_context_usage["policy_id"],
            "creator_context_grounding_mode": creator_context_usage["grounding_mode"],
            "creator_context_usage": creator_context_usage,
            "creator_context_bundle": creator_context_bundle.to_dict() if creator_context_bundle else None,
            "creator_context_package": creator_context_package,
            "creator_context_prompt": creator_context_prompt,
        }
        fingerprint = build_brief_fingerprint({**payload, **context_details})
        existing = self._fetch("brief_context_snapshots", where="creator_id = ? AND source_fingerprint = ?", params=(creator_id, fingerprint))
        if existing:
            return _row_to_entity(existing)
        record = BriefRecord(
            id=_stable_id("brief-context", creator_id, fingerprint),
            creator_id=creator_id,
            context_version=self.ENGINE_VERSION,
            roadmap_item_id=roadmap_item_id,
            strategic_plan_id=strategic_plan_id,
            recommendation_candidate_id=recommendation_candidate_id,
            experiment_id=experiment_id,
            internal_content_id=internal_content_id,
            creator_memory_snapshot_id=creator_memory_snapshot_id,
            creator_language_snapshot_id=creator_language_snapshot_id,
            audience_snapshot_id=audience_snapshot_id,
            analytics_snapshot_id=analytics_snapshot_id,
            market_snapshot_id=market_snapshot_id,
            platform_snapshot_id=platform_snapshot_id,
            packaging_snapshot_id=packaging_snapshot_id,
            source_fingerprint=fingerprint,
            context_json=_json_dumps({**payload, **context_details}),
            created_at=created_at,
        )
        return _row_to_entity(self._upsert("brief_context_snapshots", record.to_dict()))

    def list_context_snapshots(self, creator_id: str) -> list[BriefRecord]:
        return self._entities("brief_context_snapshots", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def get_context_snapshot(self, snapshot_id: str) -> BriefRecord | None:
        return self._entity("brief_context_snapshots", where="id = ?", params=(snapshot_id,))

    def create_request(
        self,
        *,
        creator_id: str,
        source_type: str,
        source_id: str | None,
        request_type: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        objective_scope_json: str | None = None,
        constraints_json: str | None = None,
        preferences_json: str | None = None,
        status: str | None = None,
        requested_at: str | None = None,
    ) -> BriefRecord:
        self._validate_creator(creator_id)
        requested_at = requested_at or _now()
        source = self._load_source(creator_id, source_type, source_id or "")
        payload = {
            "creator_id": creator_id,
            "source_type": source_type,
            "source_id": source.get("source_id") or source_id or _stable_id("brief-request", creator_id, source_type, requested_at),
            "request_type": request_type or source_type,
            "platform_scope_json": platform_scope_json or str(source.get("platform_scope_json") or "[]"),
            "content_type_scope_json": content_type_scope_json or str(source.get("content_type_scope_json") or "[]"),
            "objective_scope_json": objective_scope_json or str(source.get("objective_scope_json") or "[]"),
            "constraints_json": constraints_json or _json_dumps(source.get("constraints") or []),
            "preferences_json": preferences_json or _json_dumps(self.preferences),
            "status": status or BriefRequestStatus.QUEUED.value,
            "requested_at": requested_at,
            "created_at": requested_at,
            "updated_at": requested_at,
        }
        fingerprint = build_brief_fingerprint(payload)
        payload["id"] = _stable_id("brief-request", creator_id, str(payload["source_type"]), str(payload["source_id"]), str(payload["request_type"]))
        existing = self._fetch(
            "brief_requests",
            where="creator_id = ? AND source_type = ? AND source_id = ? AND request_type = ?",
            params=(creator_id, payload["source_type"], payload["source_id"], payload["request_type"]),
        )
        if existing:
            return _row_to_entity(existing)
        return _row_to_entity(self._upsert("brief_requests", payload))

    def list_requests(self, creator_id: str) -> list[BriefRecord]:
        return self._entities("brief_requests", where="creator_id = ?", params=(creator_id,), order_by="updated_at DESC")

    def get_request(self, request_id: str) -> BriefRecord | None:
        return self._entity("brief_requests", where="id = ?", params=(request_id,))

    def _load_brief_by_source(self, creator_id: str, source_type: str, source_id: str) -> BriefRecord | None:
        return self._entity(
            "content_briefs",
            where="creator_id = ? AND brief_request_id IN (SELECT id FROM brief_requests WHERE creator_id = ? AND source_type = ? AND source_id = ?)",
            params=(creator_id, creator_id, source_type, source_id),
            enum_fields={
                "status": BriefStatus,
                "brief_type": BriefType,
                "readiness_status": ReadinessStatus,
                "copying_risk": CopyingRiskLevel,
            },
        )

    def _brief_payload_from_source(self, request: BriefRecord, source: dict[str, Any], context_snapshot: BriefRecord) -> dict[str, Any]:
        platform_scope = _json_loads(str(request.platform_scope_json or source.get("platform_scope_json") or "[]"), [])
        content_type_scope = _json_loads(str(request.content_type_scope_json or source.get("content_type_scope_json") or "[]"), [])
        objective_scope = _json_loads(str(request.objective_scope_json or source.get("objective_scope_json") or "[]"), [])
        created_at = _now()
        title = str(source.get("title") or request.request_type or "Content brief")
        brief_type = self._brief_type_for_source(source, request.to_dict())
        status = BriefStatus.NEEDS_REVIEW
        source_status = str(source.get("status") or "")
        if source_status in {"blocked", "expired", "rejected"}:
            status = BriefStatus.BLOCKED
        brief_payload = {
            "creator_id": request.creator_id,
            "brief_request_id": request.id,
            "context_snapshot_id": context_snapshot.id,
            "strategic_plan_id": source.get("source_plan_id") or request.to_dict().get("strategic_plan_id"),
            "roadmap_item_id": source.get("source_id") if source.get("source_type") == "roadmap_item" else None,
            "recommendation_candidate_id": source.get("source_id") if str(source.get("source_type")) in {"recommendation", "approved_recommendation"} else source.get("recommendation_candidate_id"),
            "experiment_id": source.get("experiment_id") if source.get("experiment_id") is not None else (source.get("source_id") if source.get("source_type") == "experiment" else None),
            "internal_content_id": source.get("source_id") if source.get("source_type") in {"internal_content_draft", "content_library"} else None,
            "parent_brief_id": None,
            "version": 1,
            "title": title,
            "working_title": f"{title} (working)",
            "summary": str(source.get("summary") or title),
            "brief_type": brief_type,
            "status": status,
            "platform_scope_json": _json_dumps(platform_scope),
            "content_type_scope_json": _json_dumps(content_type_scope),
            "primary_objective": str(_safe_list(objective_scope)[0]) if _safe_list(objective_scope) else str(source.get("objective") or source.get("request_type") or "unknown"),
            "secondary_objectives_json": _json_dumps(_safe_list(objective_scope)[1:]),
            "non_goals_json": _json_dumps(source.get("non_goals") or ["final script", "final thumbnail", "publication"]),
            "audience_summary": str(source.get("audience_summary") or source.get("summary") or "Audience por definir"),
            "content_promise": str(source.get("promise") or source.get("summary") or "Promesa trazable"),
            "core_message": str(source.get("core_message") or source.get("summary") or title),
            "desired_audience_action": str(source.get("desired_audience_action") or "review"),
            "creator_fit": str(source.get("creator_fit") or "medium"),
            "audience_fit": str(source.get("audience_fit") or "medium"),
            "strategic_fit": str(source.get("strategic_fit") or "high"),
            "platform_fit": str(source.get("platform_fit") or "high"),
            "operational_feasibility": str(source.get("operational_feasibility") or "medium"),
            "confidence_level": str(source.get("confidence_level") or "medium"),
            "copying_risk": _enum_value(CopyingRiskLevel, source.get("copying_risk"), CopyingRiskLevel.UNKNOWN),
            "readiness_status": ReadinessStatus.NEEDS_REVIEW,
            "created_at": created_at,
            "updated_at": created_at,
        }
        brief_payload["id"] = _stable_id("content-brief", request.id, str(brief_payload["version"]))
        return brief_payload

    def _build_standard_records(self, brief: BriefRecord, source: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        platform_scope = _safe_list(_json_loads(str(brief.platform_scope_json or "[]"), []))
        content_type_scope = _safe_list(_json_loads(str(brief.content_type_scope_json or "[]"), []))
        objective_scope = _safe_list(_json_loads(str(brief.secondary_objectives_json or "[]"), []))
        audience_segment = str(source.get("audience_segment") or "primary audience")
        summary = str(brief.audience_summary or brief.summary or "")
        title = str(brief.title or "Content brief")
        platform_text = ", ".join(str(item) for item in platform_scope) if platform_scope else "platform local"
        sections = [
            {"section_type": SectionType.AUDIENCE, "title": "Audience", "content_json": _json_dumps({"segment": audience_segment, "summary": summary}), "sequence_order": 1, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.PROMISE, "title": "Content Promise", "content_json": _json_dumps({"promise": brief.content_promise, "audience_value": "value", "proof": "required"}), "sequence_order": 2, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.ANGLE, "title": "Angle", "content_json": _json_dumps({"angles": [brief.brief_type.value, "problem_solution", "evergreen"]}), "sequence_order": 3, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.MESSAGE, "title": "Message", "content_json": _json_dumps({"core": brief.core_message, "supporting": objective_scope, "non_goals": _safe_list(_json_loads(str(brief.non_goals_json or "[]"), []))}), "sequence_order": 4, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.CLAIMS, "title": "Claims", "content_json": _json_dumps({"claims": []}), "sequence_order": 5, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.PACKAGING, "title": "Packaging", "content_json": _json_dumps({"title_direction": f"{title} direction", "platform": platform_text}), "sequence_order": 6, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.REFERENCES, "title": "References", "content_json": _json_dumps({"references": source.get("references") or []}), "sequence_order": 7, "required": False, "completion_status": "complete"},
            {"section_type": SectionType.RIGHTS, "title": "Rights", "content_json": _json_dumps({"copying_risk": brief.copying_risk.value}), "sequence_order": 8, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.ASSETS, "title": "Assets", "content_json": _json_dumps({"assets": []}), "sequence_order": 9, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.PREPRODUCTION, "title": "Pre-production", "content_json": _json_dumps({"requirements": ["research", "fact_check", "creator_approval"]}), "sequence_order": 10, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.CHECKLIST, "title": "Checklist", "content_json": _json_dumps({"items": ["research", "rights", "assets", "approval"]}), "sequence_order": 11, "required": True, "completion_status": "complete"},
            {"section_type": SectionType.READINESS, "title": "Readiness", "content_json": _json_dumps({"status": brief.readiness_status.value}), "sequence_order": 12, "required": True, "completion_status": "complete"},
        ]
        audience = [
            {
                "audience_type": AudienceType.PRIMARY,
                "segment_name": audience_segment,
                "description": summary or "Audience general",
                "needs_json": _json_dumps(source.get("needs") or []),
                "pain_points_json": _json_dumps(source.get("pain_points") or []),
                "desired_outcomes_json": _json_dumps(source.get("desired_outcomes") or []),
                "awareness_level": source.get("awareness_level"),
                "relationship_stage": source.get("relationship_stage"),
                "platform_behavior_json": _json_dumps(source.get("platform_behavior") or platform_scope),
                "evidence_json": _json_dumps(source.get("evidence") or []),
                "confidence_level": str(source.get("confidence_level") or "medium"),
                "limitations_json": _json_dumps(source.get("limitations") or []),
            }
        ]
        promises = [
            {
                "promise_type": PromiseType.DIRECT,
                "statement": brief.content_promise,
                "audience_value": "Relevant value",
                "credibility_basis": "source_snapshot",
                "required_proof_json": _json_dumps(source.get("proof") or []),
                "risk_level": "medium",
                "status": "draft",
            }
        ]
        angles = [
            {
                "angle_type": AngleType.PROBLEM_SOLUTION,
                "title": "Problem-solution",
                "description": "Abordaje centrado en resolver un problema concreto.",
                "differentiation": "trazable y adaptable",
                "creator_fit": brief.creator_fit,
                "audience_fit": brief.audience_fit,
                "market_fit": brief.strategic_fit,
                "copying_risk": CopyingRiskLevel.MODERATE.value,
                "status": "draft",
            }
        ]
        messages = [
            {"message_level": MessageLevel.CORE, "sequence_order": 1, "message": brief.core_message, "message_role": "core", "supporting_evidence_json": _json_dumps(source.get("evidence") or []), "mandatory": True, "status": "draft"},
            {"message_level": MessageLevel.SUPPORTING, "sequence_order": 2, "message": "Support", "message_role": "supporting", "supporting_evidence_json": _json_dumps([]), "mandatory": True, "status": "draft"},
            {"message_level": MessageLevel.CTA, "sequence_order": 3, "message": "CTA direction", "message_role": "cta", "supporting_evidence_json": _json_dumps([]), "mandatory": False, "status": "draft"},
        ]
        hooks = [
            {"platform": platform_scope[0] if platform_scope else "youtube", "hook_type": HookType.RESULT_FIRST, "direction": "Mostrar el resultado antes de explicar.", "purpose": "capture_attention", "constraints_json": _json_dumps([]), "risks_json": _json_dumps([]), "evidence_json": _json_dumps([]), "status": "draft"},
        ]
        outlines = [
            {"outline_type": NarrativeOutlineType.MISTAKE_CORRECTION_PRACTICE, "platform": platform_scope[0] if platform_scope else None, "structure_json": _json_dumps([{"block": "hook"}, {"block": "explain"}, {"block": "practice"}]), "target_duration_seconds": self.preferences.get("default_target_duration_seconds"), "pacing_direction": "fast", "transition_notes_json": _json_dumps([]), "status": "draft"},
        ]
        talking_points = [
            {"sequence_order": 1, "point_type": "fact", "title": "Problem", "description": "Problema a resolver", "required": True, "evidence_required": True, "claim_id": None, "status": "draft"},
            {"sequence_order": 2, "point_type": "inference", "title": "Interpretation", "description": "Lo que significa para la audiencia", "required": True, "evidence_required": True, "claim_id": None, "status": "draft"},
            {"sequence_order": 3, "point_type": "action", "title": "Next step", "description": "Siguiente paso recomendado", "required": False, "evidence_required": False, "claim_id": None, "status": "draft"},
        ]
        claims = [
            {"id": self._stable_claim_id(brief.id, 0), "claim_type": ClaimType.HYPOTHESIS, "claim_text": f"Hipotesis para {title}", "fact_inference_hypothesis": "hypothesis", "source_type": source.get("source_type"), "source_id": source.get("source_id"), "verification_status": ClaimVerificationStatus.VERIFICATION_REQUIRED, "risk_level": "medium", "required_before_production": True, "notes": "Revisar antes de producir"},
        ]
        fact_checks = [
            {"claim_id": self._stable_claim_id(brief.id, 0), "check_type": "source_check", "status": "pending", "source_url": None, "source_reference": None, "checked_at": None, "notes": "Requiere validacion humana"},
        ]
        packaging = [
            {"platform": platform_scope[0] if platform_scope else "youtube", "packaging_type": "direction", "title_direction": f"{title} direction", "thumbnail_direction": "Direction only", "cover_direction": "Direction only", "visual_promise": "Clear promise", "text_constraints_json": _json_dumps(["no final title"]), "brand_constraints_json": _json_dumps(["preserve creator language"]), "copying_risk": CopyingRiskLevel.MODERATE, "source_thumbnail_lab_id": None, "status": "draft"},
        ]
        visual = [
            {"direction_type": "thumbnail_direction", "description": "Composicion sobria y diferenciada", "composition_notes_json": _json_dumps(["clear focal point"]), "color_notes_json": _json_dumps(["aligned to creator"]), "typography_notes_json": _json_dumps(["readable"]), "motion_notes_json": _json_dumps([]), "prohibited_elements_json": _json_dumps(["copying"]), "reference_scope_json": _json_dumps([]), "status": "draft"},
        ]
        audio = [
            {"direction_type": "audio_direction", "description": "Audio de voz claro", "voice_notes_json": _json_dumps(["voiceover optional"]), "music_notes_json": _json_dumps([]), "sound_effect_notes_json": _json_dumps([]), "rights_required": True, "prohibited_elements_json": _json_dumps([]), "status": "draft"},
        ]
        adaptations = [
            {"platform": platform_scope[0] if platform_scope else "youtube", "adaptation_type": "native", "content_type": content_type_scope[0] if content_type_scope else "video", "duration_target": self.preferences.get("default_target_duration_seconds"), "aspect_ratio": "16:9", "safe_area_notes": "local", "caption_direction": "manual", "metadata_direction_json": _json_dumps({"objective": brief.primary_objective}), "platform_constraints_json": _json_dumps([]), "measurement_plan_json": _json_dumps([]), "status": "draft"},
        ]
        boundaries = [
            {"boundary_type": BoundaryType.CREATOR_BOUNDARY, "source": "creator_memory", "description": "Respeta Creator Memory", "blocking": True, "status": "active"},
            {"boundary_type": BoundaryType.RIGHTS_BOUNDARY, "source": "rights", "description": "No copiar contenido ajeno", "blocking": True, "status": "active"},
        ]
        references = []
        for index, reference in enumerate(_safe_list(source.get("references"))[: int(self.preferences.get("max_references_per_brief") or 10)]):
            ref_payload = self._safe_payload(reference)
            references.append(
                {
                    "reference_type": ref_payload.get("reference_type") or "topic_reference",
                    "source_type": ref_payload.get("source_type") or "manual",
                    "source_id": ref_payload.get("source_id"),
                    "source_url": ref_payload.get("source_url"),
                    "local_asset_id": ref_payload.get("local_asset_id"),
                    "title": ref_payload.get("title"),
                    "description": str(ref_payload.get("description") or "Reference"),
                    "usage_purpose": str(ref_payload.get("usage_purpose") or "inspiration"),
                    "allowed_usage": str(ref_payload.get("allowed_usage") or "reference_only"),
                    "copying_risk": CopyingRiskLevel._value2member_map_.get(str(ref_payload.get("copying_risk") or CopyingRiskLevel.UNKNOWN.value), CopyingRiskLevel.UNKNOWN).value,
                    "permission_status": str(ref_payload.get("permission_status") or "unknown"),
                    "observed_at": ref_payload.get("observed_at"),
                }
            )
        rights = [
            {"reference_id": None, "rights_type": RightsType.COPYRIGHT, "status": RightsStatus.UNKNOWN, "owner": None, "permission_evidence": None, "expiration_date": None, "restrictions_json": _json_dumps([]), "blocking": True, "notes": "Rights review required"},
        ]
        assets = [
            {"asset_type": AssetType.CREATOR_RECORDING, "title": "Creator recording", "description": "Asset required before production", "source_type": "creator", "existing_asset_id": None, "required": True, "rights_status": RightsStatus.UNKNOWN.value, "readiness_status": "missing", "assigned_owner": None, "due_date": None},
            {"asset_type": AssetType.THUMBNAIL_ASSET, "title": "Packaging concept", "description": "Direction only", "source_type": "thumbnail_lab", "existing_asset_id": None, "required": True, "rights_status": RightsStatus.UNKNOWN.value, "readiness_status": "direction_only", "assigned_owner": None, "due_date": None},
        ]
        requirements = [
            {"requirement_type": ProductionRequirementType.RESEARCH, "title": "Research", "description": "Verify source and context", "required": True, "availability_status": "required", "blocking": True, "estimated_effort": "medium", "assigned_owner": None, "due_date": None},
            {"requirement_type": ProductionRequirementType.FACT_CHECK, "title": "Fact check", "description": "Review claims", "required": True, "availability_status": "required", "blocking": True, "estimated_effort": "medium", "assigned_owner": None, "due_date": None},
            {"requirement_type": ProductionRequirementType.CREATOR_APPROVAL, "title": "Creator approval", "description": "Human review required", "required": True, "availability_status": "required", "blocking": True, "estimated_effort": "low", "assigned_owner": None, "due_date": None},
        ]
        shots = [
            {"sequence_order": 1, "shot_type": "talking_head", "title": "Hook", "description": "Abrir con la promesa", "purpose": "attention", "location": None, "participants_json": _json_dumps([]), "props_json": _json_dumps([]), "equipment_json": _json_dumps([]), "estimated_duration_seconds": 15, "required": True, "status": "draft"},
            {"sequence_order": 2, "shot_type": "demonstration", "title": "Main demo", "description": "Explicar el punto central", "purpose": "explain", "location": None, "participants_json": _json_dumps([]), "props_json": _json_dumps([]), "equipment_json": _json_dumps([]), "estimated_duration_seconds": 60, "required": True, "status": "draft"},
        ]
        checklist_id = _stable_id("brief-checklist", brief.id, "preproduction")
        checklists = [{"id": checklist_id, "checklist_type": "preproduction", "title": "Pre-production checklist", "status": "draft"}]
        checklist_items = [
            {"checklist_id": checklist_id, "sequence_order": 1, "item_type": "research", "title": "Research", "description": "Verify source and evidence", "required": True, "blocking": True, "status": "pending", "completed_at": None, "completed_by": None},
            {"checklist_id": checklist_id, "sequence_order": 2, "item_type": "rights", "title": "Rights", "description": "Confirm permissions", "required": True, "blocking": True, "status": "pending", "completed_at": None, "completed_by": None},
            {"checklist_id": checklist_id, "sequence_order": 3, "item_type": "assets", "title": "Assets", "description": "Confirm required assets", "required": True, "blocking": True, "status": "pending", "completed_at": None, "completed_by": None},
        ]
        gates = [
            {"gate_type": ApprovalGateType.CONCEPT_APPROVAL, "sequence_order": 1, "required": True, "status": "pending", "approver": None, "approved_at": None, "rejection_reason": None},
            {"gate_type": ApprovalGateType.FACT_CHECK_APPROVAL, "sequence_order": 2, "required": True, "status": "pending", "approver": None, "approved_at": None, "rejection_reason": None},
            {"gate_type": ApprovalGateType.RIGHTS_APPROVAL, "sequence_order": 3, "required": True, "status": "pending", "approver": None, "approved_at": None, "rejection_reason": None},
            {"gate_type": ApprovalGateType.FINAL_PRODUCTION_READINESS, "sequence_order": 4, "required": True, "status": "pending", "approver": None, "approved_at": None, "rejection_reason": None},
        ]
        risks = [
            {"risk_type": RiskType.COPYING, "severity": "high", "likelihood": None, "impact": "blocked", "description": "Copying risk requires review", "mitigation": "abstract the principle", "blocking": True, "owner": None, "review_at": None},
            {"risk_type": RiskType.RIGHTS, "severity": "high", "likelihood": None, "impact": "blocked", "description": "Rights may be unresolved", "mitigation": "rights check", "blocking": True, "owner": None, "review_at": None},
            {"risk_type": RiskType.CAPACITY, "severity": "medium", "likelihood": None, "impact": "delay", "description": "Capacity may limit pre-production", "mitigation": "reduce scope", "blocking": False, "owner": None, "review_at": None},
        ]
        dependencies = [
            {"dependency_type": DependencyType.ROADMAP_ITEM, "source_type": source.get("source_type"), "source_id": source.get("source_id"), "description": "Source must remain traceable", "blocking": True, "status": "pending", "due_date": None},
            {"dependency_type": DependencyType.APPROVAL, "source_type": "brief", "source_id": brief.id, "description": "Human review required", "blocking": True, "status": "pending", "due_date": None},
        ]
        snapshots = [
            {"snapshot_type": "draft_brief", "brief_version": brief.version, "snapshot_json": _json_dumps({"title": title, "brief_type": brief.brief_type.value}), "source_fingerprint": _stable_id("brief-snapshot", brief.id, "draft")},
        ]
        return {
            "sections": sections,
            "audience": audience,
            "promises": promises,
            "angles": angles,
            "messages": messages,
            "hooks": hooks,
            "outlines": outlines,
            "talking_points": talking_points,
            "claims": claims,
            "fact_checks": fact_checks,
            "packaging": packaging,
            "visual": visual,
            "audio": audio,
            "adaptations": adaptations,
            "boundaries": boundaries,
            "references": references,
            "rights": rights,
            "assets": assets,
            "requirements": requirements,
            "shots": shots,
            "checklists": checklists,
            "checklist_items": checklist_items,
            "gates": gates,
            "risks": risks,
            "dependencies": dependencies,
            "snapshots": snapshots,
        }

    def _calculate_brief_readiness(self, brief: BriefRecord) -> dict[str, object]:
        claims = self.list_claims(brief.id)
        rights = self.list_rights(brief.id)
        assets = self.list_assets(brief.id)
        checklists = self.list_checklists(brief.id)
        gates = self.list_gates(brief.id)
        risks = self.list_risks(brief.id)
        blockers: list[str] = []
        warnings: list[str] = []
        if brief.copying_risk in {CopyingRiskLevel.HIGH, CopyingRiskLevel.PROHIBITED}:
            blockers.append("copying_risk")
        if any(str(right.status) in {RightsStatus.DENIED.value, RightsStatus.BLOCKED.value, RightsStatus.RESTRICTED.value} for right in rights):
            blockers.append("rights")
        if any(str(claim.verification_status) in {ClaimVerificationStatus.CONTRADICTED.value, ClaimVerificationStatus.BLOCKED.value} for claim in claims):
            blockers.append("claim_contradicted")
        if any(str(claim.verification_status) in {ClaimVerificationStatus.UNVERIFIED.value, ClaimVerificationStatus.VERIFICATION_REQUIRED.value} and getattr(claim, "required_before_production", False) for claim in claims):
            warnings.append("claims_pending")
        if any(getattr(asset, "required", False) and str(getattr(asset, "readiness_status", "")) not in {"ready", "complete"} for asset in assets):
            warnings.append("assets_pending")
        if any(str(gate.status) in {"pending", "rejected", "blocked"} and getattr(gate, "required", False) for gate in gates):
            warnings.append("gates_pending")
        if any(getattr(risk, "blocking", False) for risk in risks):
            warnings.append("risks_present")
        required_checklists = [checklist for checklist in checklists if True]
        if not required_checklists:
            warnings.append("no_checklist")
        score = 100
        score -= len(blockers) * 30
        score -= len(warnings) * 8
        score = max(0, min(100, score))
        if blockers:
            status = ReadinessStatus.BLOCKED
        elif score >= 80 and not warnings:
            status = ReadinessStatus.READY_FOR_PREPRODUCTION
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
                "assets": len(assets),
                "checklists": len(checklists),
                "gates": len(gates),
                "risks": len(risks),
            },
            "blockers": blockers,
            "warnings": warnings,
            "missing_data": [item for item in ["rights", "claims", "assets"] if not locals().get(item)],
            "critical_requirements": [gate.to_dict() for gate in gates if getattr(gate, "required", False)],
            "recommended_next_action": "human_review",
        }

    def _store_related(self, brief: BriefRecord, source: dict[str, Any], payloads: dict[str, list[dict[str, Any]]]) -> None:
        tables_without_updated_at = {
            "brief_audience_definitions",
            "brief_boundaries",
            "brief_references",
            "brief_risks",
            "brief_snapshots",
        }

        def store(table: str, items: list[dict[str, Any]], *, id_prefix: str, conflict_columns: tuple[str, ...] = ("id",), extra: Callable[[dict[str, Any], int], dict[str, Any]] | None = None) -> None:
            for index, item in enumerate(items):
                record = dict(item)
                if extra is not None:
                    record.update(extra(record, index))
                record.setdefault("id", _stable_id(id_prefix, brief.id, str(index), _json_dumps(record)))
                record.setdefault("creator_id", brief.creator_id)
                record.setdefault("content_brief_id", brief.id)
                record.setdefault("created_at", _now())
                if table not in tables_without_updated_at:
                    record.setdefault("updated_at", record["created_at"])
                if table == "brief_fact_checks":
                    record.setdefault("claim_id", self._stable_claim_id(brief.id, index))
                if table == "brief_checklist_items":
                    record.setdefault("checklist_id", payloads["checklists"][0]["id"])
                    record.pop("content_brief_id", None)
                self._upsert(table, record, conflict_columns=conflict_columns)

        store("brief_sections", payloads["sections"], id_prefix="brief-section", conflict_columns=("content_brief_id", "section_type", "sequence_order"))
        store("brief_audience_definitions", payloads["audience"], id_prefix="brief-audience", conflict_columns=("content_brief_id", "audience_type", "segment_name"))
        store("brief_content_promises", payloads["promises"], id_prefix="brief-promise", conflict_columns=("content_brief_id", "promise_type"))
        store("brief_content_angles", payloads["angles"], id_prefix="brief-angle", conflict_columns=("content_brief_id", "angle_type", "title"))
        store("brief_message_hierarchy", payloads["messages"], id_prefix="brief-message", conflict_columns=("content_brief_id", "message_level", "sequence_order"))
        store("brief_hook_directions", payloads["hooks"], id_prefix="brief-hook", conflict_columns=("content_brief_id", "platform", "hook_type"))
        store("brief_narrative_outlines", payloads["outlines"], id_prefix="brief-outline", conflict_columns=("content_brief_id", "outline_type", "platform"))
        store("brief_talking_points", payloads["talking_points"], id_prefix="brief-point", conflict_columns=("content_brief_id", "sequence_order"))
        store("brief_claims", payloads["claims"], id_prefix="brief-claim", conflict_columns=("content_brief_id", "claim_text"))
        store("brief_fact_checks", payloads["fact_checks"], id_prefix="brief-fact-check", conflict_columns=("content_brief_id", "claim_id", "check_type"))
        store("brief_packaging_directions", payloads["packaging"], id_prefix="brief-packaging", conflict_columns=("content_brief_id", "platform", "packaging_type"))
        store("brief_visual_directions", payloads["visual"], id_prefix="brief-visual", conflict_columns=("content_brief_id", "direction_type"))
        store("brief_audio_directions", payloads["audio"], id_prefix="brief-audio", conflict_columns=("content_brief_id", "direction_type"))
        store("brief_platform_adaptations", payloads["adaptations"], id_prefix="brief-adaptation", conflict_columns=("content_brief_id", "platform", "adaptation_type"))
        store("brief_boundaries", payloads["boundaries"], id_prefix="brief-boundary", conflict_columns=("content_brief_id", "boundary_type", "source"))
        store("brief_references", payloads["references"], id_prefix="brief-reference", conflict_columns=("content_brief_id", "reference_type", "source_type", "source_id", "source_url", "local_asset_id"))
        store("brief_rights_checks", payloads["rights"], id_prefix="brief-rights", conflict_columns=("content_brief_id", "rights_type", "reference_id"))
        store("brief_asset_requirements", payloads["assets"], id_prefix="brief-asset", conflict_columns=("content_brief_id", "asset_type", "title"))
        store("brief_production_requirements", payloads["requirements"], id_prefix="brief-production", conflict_columns=("content_brief_id", "requirement_type", "title"))
        store("brief_shot_plan_items", payloads["shots"], id_prefix="brief-shot", conflict_columns=("content_brief_id", "sequence_order"))
        store("brief_checklists", payloads["checklists"], id_prefix="brief-checklist", conflict_columns=("content_brief_id", "checklist_type"))
        store("brief_checklist_items", payloads["checklist_items"], id_prefix="brief-checklist-item", conflict_columns=("checklist_id", "sequence_order"))
        store("brief_approval_gates", payloads["gates"], id_prefix="brief-gate", conflict_columns=("content_brief_id", "gate_type", "sequence_order"))
        store("brief_risks", payloads["risks"], id_prefix="brief-risk", conflict_columns=("content_brief_id", "risk_type", "description"))
        store("brief_dependencies", payloads["dependencies"], id_prefix="brief-dependency", conflict_columns=("content_brief_id", "dependency_type", "source_type", "source_id"))
        store("brief_snapshots", payloads["snapshots"], id_prefix="brief-snapshot", conflict_columns=("source_fingerprint",))

    def _stable_claim_id(self, brief_id: str, index: int) -> str:
        return _stable_id("brief-claim", brief_id, str(index))

    def generate_brief(
        self,
        *,
        request_id: str | None = None,
        creator_id: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        request_type: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        objective_scope_json: str | None = None,
        constraints_json: str | None = None,
        preferences_json: str | None = None,
    ) -> BriefRecord:
        if request_id is None:
            if creator_id is None or source_type is None:
                raise ContentBriefValidationError("Se requiere request_id o creator_id/source_type.")
            request = self.create_request(
                creator_id=creator_id,
                source_type=source_type,
                source_id=source_id,
                request_type=request_type,
                platform_scope_json=platform_scope_json,
                content_type_scope_json=content_type_scope_json,
                objective_scope_json=objective_scope_json,
                constraints_json=constraints_json,
                preferences_json=preferences_json,
                status=BriefRequestStatus.QUEUED.value,
            )
        else:
            request = self.get_request(request_id)
            if request is None:
                raise ContentBriefNotFoundError("La solicitud de brief no existe.")
        creator_id = request.creator_id
        source = self._load_source(creator_id, request.source_type, str(request.source_id))
        if str(source.get("status") or "") in {"rejected", "expired"}:
            request = self._update_request_status(request.id, BriefRequestStatus.COMPLETED_WITH_WARNINGS.value)
        else:
            request = self._update_request_status(request.id, BriefRequestStatus.ASSEMBLING_CONTEXT.value)
        context_snapshot = self.create_context_snapshot(
            creator_id,
            roadmap_item_id=source.get("source_id") if source.get("source_type") == "roadmap_item" else None,
            strategic_plan_id=source.get("source_plan_id"),
            recommendation_candidate_id=source.get("source_id") if source.get("source_type") in {"recommendation", "approved_recommendation"} else None,
            experiment_id=source.get("experiment_id"),
            internal_content_id=source.get("source_id") if source.get("source_type") in {"internal_content_draft", "content_library"} else None,
            preferences=_safe_dict(_json_loads(request.preferences_json, {})) or None,
            constraints=_safe_list(_json_loads(request.constraints_json, [])),
        )
        existing = self._load_brief_by_source(creator_id, request.source_type, str(source.get("source_id") or request.source_id))
        if existing is not None:
            request = self._update_request_status(request.id, BriefRequestStatus.COMPLETED.value)
            return existing
        brief_payload = self._brief_payload_from_source(request, source, context_snapshot)
        existing = self._fetch("content_briefs", where="brief_request_id = ?", params=(request.id,))
        if existing:
            brief = _row_to_entity(existing, enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})
        else:
            brief = _row_to_entity(self._upsert("content_briefs", brief_payload), enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})
        payloads = self._build_standard_records(brief, source)
        self._store_related(brief, source, payloads)
        readiness = self.calculate_readiness(brief.id)
        self._upsert(
            "content_briefs",
            {
                **brief.to_dict(),
                "readiness_status": readiness["status"].value if hasattr(readiness["status"], "value") else str(readiness["status"]),
                "updated_at": _now(),
            },
        )
        request = self._update_request_status(request.id, BriefRequestStatus.COMPLETED_WITH_WARNINGS.value if readiness["warnings"] else BriefRequestStatus.COMPLETED.value)
        return self.get_brief(brief.id) or brief

    def _update_request_status(self, request_id: str, status: str) -> BriefRecord:
        request = self.get_request(request_id)
        if request is None:
            raise ContentBriefNotFoundError("La solicitud de brief no existe.")
        updated = BriefRecord(**{**request.to_dict(), "status": status, "updated_at": _now()})
        return _row_to_entity(self._upsert("brief_requests", updated.to_dict()))

    def list_briefs(self, creator_id: str) -> list[BriefRecord]:
        return self._entities(
            "content_briefs",
            where="creator_id = ?",
            params=(creator_id,),
            order_by="updated_at DESC",
            enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )

    def get_brief(self, brief_id: str) -> BriefRecord | None:
        return self._entity(
            "content_briefs",
            where="id = ?",
            params=(brief_id,),
            enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )

    def review_brief(self, brief_id: str, *, decision: str, reason: str, reviewer: str | None = None) -> BriefRecord:
        brief = self.get_brief(brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        previous = brief.to_dict()
        mapping = {
            ReviewDecision.APPROVE.value: BriefStatus.APPROVED,
            ReviewDecision.REJECT.value: BriefStatus.CANCELLED,
            ReviewDecision.DEFER.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.NEEDS_INFORMATION.value: BriefStatus.NEEDS_INFORMATION,
            ReviewDecision.REQUEST_CHANGES.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.REDUCE_SCOPE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_OBJECTIVE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_AUDIENCE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_PLATFORM.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_FORMAT.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_ANGLE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.CHANGE_MESSAGE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.REMOVE_CLAIM.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.REQUEST_FACT_CHECK.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.REPLACE_REFERENCE.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.REQUEST_RIGHTS_REVIEW.value: BriefStatus.NEEDS_REVIEW,
            ReviewDecision.APPROVE_PREPRODUCTION.value: BriefStatus.READY_FOR_PREPRODUCTION,
            ReviewDecision.APPROVE_PRODUCTION_READINESS.value: BriefStatus.READY_FOR_PRODUCTION,
            ReviewDecision.BLOCK.value: BriefStatus.BLOCKED,
            ReviewDecision.SUPERSEDE.value: BriefStatus.SUPERSEDED,
            ReviewDecision.ARCHIVE.value: BriefStatus.ARCHIVED,
        }
        new_status = mapping.get(decision, BriefStatus.NEEDS_REVIEW)
        updated = BriefRecord(**{**brief.to_dict(), "status": new_status, "updated_at": _now()})
        self._upsert("content_briefs", updated.to_dict())
        review = BriefRecord(
            id=_stable_id("brief-review", brief_id, decision, reason, reviewer or ""),
            creator_id=brief.creator_id,
            content_brief_id=brief_id,
            review_type="brief_review",
            decision=decision,
            previous_status=brief.status.value if hasattr(brief.status, "value") else str(brief.status),
            new_status=new_status.value,
            reason=reason,
            reviewer=reviewer,
            reviewed_at=_now(),
            created_at=_now(),
        )
        self._upsert("brief_reviews", review.to_dict())
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None:
            feedback_kwargs = {
                "creator_id": brief.creator_id,
                "workflow_type": "content_brief",
                "artifact_type": "content_brief",
                "artifact_id": brief.id,
                "project_id": None,
                "metadata": {
                    "decision": decision,
                    "reason": reason,
                    "reviewer": reviewer,
                    "review_type": "brief_review",
                    "previous_status": brief.status.value if hasattr(brief.status, "value") else str(brief.status),
                    "new_status": new_status.value,
                },
            }
            if decision in {ReviewDecision.APPROVE.value, ReviewDecision.APPROVE_PREPRODUCTION.value, ReviewDecision.APPROVE_PRODUCTION_READINESS.value}:
                feedback_service.record_acceptance(**feedback_kwargs)
            elif decision == ReviewDecision.REJECT.value:
                feedback_service.record_rejection(**feedback_kwargs)
            elif decision == ReviewDecision.SUPERSEDE.value:
                feedback_service.record_supersession(**feedback_kwargs)
        return self.get_brief(brief_id) or updated

    def version_brief(self, brief_id: str, *, reason: str = "versioned_brief") -> BriefRecord:
        brief = self.get_brief(brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        version = int(brief.version or 1) + 1
        context_snapshot = self.create_context_snapshot(
            brief.creator_id,
            roadmap_item_id=brief.roadmap_item_id,
            strategic_plan_id=brief.strategic_plan_id,
            recommendation_candidate_id=brief.recommendation_candidate_id,
            experiment_id=brief.experiment_id,
            internal_content_id=brief.internal_content_id,
        )
        payload = brief.to_dict()
        payload.update(
            {
                "id": _stable_id("content-brief-version", brief.id, str(version), reason),
                "parent_brief_id": brief.id,
                "brief_request_id": None,
                "version": version,
                "context_snapshot_id": context_snapshot.id,
                "status": BriefStatus.DRAFT.value,
                "readiness_status": ReadinessStatus.NEEDS_REVIEW.value,
                "updated_at": _now(),
            }
        )
        return _row_to_entity(self._upsert("content_briefs", payload), enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel})

    def supersede_brief(self, brief_id: str, *, replacement_id: str | None = None, reason: str) -> BriefRecord:
        brief = self.get_brief(brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        if replacement_id:
            replacement = self.get_brief(replacement_id)
            if replacement is None:
                raise ContentBriefNotFoundError("El replacement brief no existe.")
            self._upsert("content_briefs", {**brief.to_dict(), "status": BriefStatus.SUPERSEDED.value, "updated_at": _now()})
            return replacement
        self._upsert("content_briefs", {**brief.to_dict(), "status": BriefStatus.SUPERSEDED.value, "updated_at": _now()})
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None:
            feedback_service.record_supersession(
                creator_id=brief.creator_id,
                workflow_type="content_brief",
                artifact_type="content_brief",
                artifact_id=brief.id,
                project_id=None,
                metadata={
                    "reason": reason,
                    "replacement_id": replacement_id,
                    "previous_status": brief.status.value if hasattr(brief.status, "value") else str(brief.status),
                    "new_status": BriefStatus.SUPERSEDED.value,
                },
            )
        existing_children = self._entities(
            "content_briefs",
            where="creator_id = ? AND parent_brief_id = ?",
            params=(brief.creator_id, brief.id),
            order_by="CAST(version AS INTEGER) DESC, updated_at DESC",
            enum_fields={"status": BriefStatus, "brief_type": BriefType, "readiness_status": ReadinessStatus, "copying_risk": CopyingRiskLevel},
        )
        if existing_children:
            return existing_children[0]
        return self.version_brief(brief_id, reason=reason)

    def calculate_readiness(self, brief_id: str) -> dict[str, object]:
        brief = self.get_brief(brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        readiness = self._calculate_brief_readiness(brief)
        readiness["status"] = _enum_value(ReadinessStatus, readiness["status"], ReadinessStatus.UNKNOWN)
        return readiness

    def build_overview(self, creator_id: str) -> dict[str, object]:
        briefs = self.list_briefs(creator_id)
        active = next((brief for brief in briefs if brief.status == BriefStatus.APPROVED), briefs[0] if briefs else None)
        return {
            "creator_id": creator_id,
            "total_briefs": len(briefs),
            "drafts": sum(1 for brief in briefs if brief.status == BriefStatus.DRAFT),
            "needs_review": sum(1 for brief in briefs if brief.status == BriefStatus.NEEDS_REVIEW),
            "blocked": sum(1 for brief in briefs if brief.status == BriefStatus.BLOCKED),
            "ready_for_preproduction": sum(1 for brief in briefs if brief.status == BriefStatus.READY_FOR_PREPRODUCTION),
            "ready_for_production": sum(1 for brief in briefs if brief.status == BriefStatus.READY_FOR_PRODUCTION),
            "missing_claims": sum(1 for brief in briefs if not self.list_claims(brief.id)),
            "pending_rights": sum(1 for brief in briefs if any(r.status in {RightsStatus.PENDING, RightsStatus.UNKNOWN} for r in self.list_rights(brief.id))),
            "missing_assets": sum(1 for brief in briefs if any(getattr(asset, "readiness_status", "") not in {"ready", "complete"} for asset in self.list_assets(brief.id))),
            "incomplete_checklists": sum(1 for brief in briefs if any(getattr(item, "status", "") != "completed" for checklist in self.list_checklists(brief.id) for item in self.list_checklist_items(checklist.id))),
            "approval_gates_pending": sum(1 for brief in briefs if any(gate.status == "pending" for gate in self.list_gates(brief.id))),
            "next_review": None,
            "plan_freshness": "recent" if briefs else "unknown",
            "active_brief": None if active is None else active.to_dict(),
        }

    def create_snapshot(self, brief_id: str, *, snapshot_type: str = "draft_brief") -> BriefRecord:
        brief = self.get_brief(brief_id)
        if brief is None:
            raise ContentBriefNotFoundError("El brief no existe.")
        payload = {
            "creator_id": brief.creator_id,
            "content_brief_id": brief.id,
            "snapshot_type": snapshot_type,
            "brief_version": brief.version,
            "source_fingerprint": _stable_id("brief-snapshot", brief.id, snapshot_type, str(brief.version)),
            "snapshot_json": _json_dumps({"brief": brief.to_dict(), "snapshot_type": snapshot_type}),
            "created_at": _now(),
        }
        payload["id"] = _stable_id("brief-snapshot-record", brief.id, snapshot_type, str(brief.version))
        return _row_to_entity(self._upsert("brief_snapshots", payload))

    def compare_snapshots(self, left_id: str, right_id: str) -> dict[str, object]:
        left = self._entity("brief_snapshots", where="id = ?", params=(left_id,))
        right = self._entity("brief_snapshots", where="id = ?", params=(right_id,))
        if left is None or right is None:
            raise ContentBriefNotFoundError("Uno de los snapshots no existe.")
        left_json = _json_loads(str(left.snapshot_json), {})
        right_json = _json_loads(str(right.snapshot_json), {})
        return {"left": left.to_dict(), "right": right.to_dict(), "differences": {"left_keys": sorted(left_json.keys()), "right_keys": sorted(right_json.keys())}}

    def build_report(
        self,
        *,
        content_brief_id: str | None,
        creator_id: str,
        report_type: str,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> BriefRecord:
        brief = self.get_brief(content_brief_id) if content_brief_id else None
        payload = {
            "creator_id": creator_id,
            "content_brief_id": None if brief is None else brief.id,
            "brief": None if brief is None else brief.to_dict(),
            "version": None if brief is None else brief.version,
            "source": None if brief is None else brief.brief_request_id,
            "context_snapshot": None if brief is None else (self.get_context_snapshot(brief.context_snapshot_id).to_dict() if self.get_context_snapshot(brief.context_snapshot_id) else None),
            "objective": None if brief is None else brief.primary_objective,
            "audience": None if brief is None else brief.audience_summary,
            "platform": None if brief is None else brief.platform_scope_json,
            "format": None if brief is None else brief.brief_type.value,
            "evidence": [],
            "claims": [] if brief is None else [claim.to_dict() for claim in self.list_claims(brief.id)],
            "limitations": ["local_only", "no_llm", "no_ml", "no_generation", "no_external_calendar", "no_publication"],
            "risks": [] if brief is None else [risk.to_dict() for risk in self.list_risks(brief.id)],
            "rights": [] if brief is None else [right.to_dict() for right in self.list_rights(brief.id)],
            "assets": [] if brief is None else [asset.to_dict() for asset in self.list_assets(brief.id)],
            "requirements": [] if brief is None else [requirement.to_dict() for requirement in self.list_requirements(brief.id)],
            "readiness": None if brief is None else self.calculate_readiness(brief.id),
            "approvals": [] if brief is None else [gate.to_dict() for gate in self.list_gates(brief.id)],
            "review_date": None if brief is None else brief.updated_at,
        }
        fingerprint = build_brief_fingerprint(payload)
        existing = self._fetch("brief_reports", where="source_fingerprint = ?", params=(fingerprint,))
        if existing:
            return _row_to_entity(existing)
        report = BriefRecord(
            id=_stable_id("brief-report", creator_id, fingerprint),
            creator_id=creator_id,
            content_brief_id=None if brief is None else brief.id,
            report_type=report_type,
            source_fingerprint=fingerprint,
            report_json=_json_dumps(payload),
            created_at=_now(),
        )
        return _row_to_entity(self._upsert("brief_reports", report.to_dict()))

    def export_report(self, report_id: str, format_name: str) -> Path:
        report = self.get_report(report_id)
        if report is None:
            raise ContentBriefNotFoundError("El reporte no existe.")
        destination = self._reports_root / f"{report.id}.{format_name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(report.report_json)
        if format_name == "json":
            destination.write_text(report.report_json, encoding="utf-8")
        elif format_name == "txt":
            destination.write_text(
                "\n".join(
                    [
                        f"Report type: {payload.get('report_type', '')}",
                        f"Creator: {payload.get('creator_id', '')}",
                        f"Brief: {payload.get('brief', {}).get('title', '') if isinstance(payload.get('brief'), dict) else ''}",
                    ]
                ),
                encoding="utf-8",
            )
        elif format_name == "csv":
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["id", "title", "status", "objective"])
                brief = payload.get("brief") if isinstance(payload.get("brief"), dict) else {}
                writer.writerow([
                    _safe_csv_value(payload.get("content_brief_id")),
                    _safe_csv_value(brief.get("title")),
                    _safe_csv_value(brief.get("status")),
                    _safe_csv_value(payload.get("objective")),
                ])
        else:
            raise ContentBriefValidationError("Formato de exportacion no soportado.")
        return destination

    def get_report(self, report_id: str) -> BriefRecord | None:
        return self._entity("brief_reports", where="id = ?", params=(report_id,))

    def cancel_run(self, request_id: str, *, reason: str = "cancelled") -> BriefRecord:
        return self._update_request_status(request_id, BriefRequestStatus.CANCELLED.value)

    def mark_run_interrupted(self, request_id: str, *, reason: str = "interrupted") -> BriefRecord:
        return self._update_request_status(request_id, BriefRequestStatus.INTERRUPTED.value)

    def resume_run(self, request_id: str) -> BriefRecord:
        request = self.get_request(request_id)
        if request is None:
            raise ContentBriefNotFoundError("La solicitud de brief no existe.")
        next_status = BriefRequestStatus.ASSEMBLING_CONTEXT.value if request.status in {BriefRequestStatus.INTERRUPTED.value, BriefRequestStatus.CANCELLED.value} else BriefRequestStatus.QUEUED.value
        return self._update_request_status(request_id, next_status)

    def list_tasks(self, creator_id: str) -> list[BriefRecord]:
        tasks: list[BriefRecord] = []
        for request in self.list_requests(creator_id):
            brief = next((item for item in self.list_briefs(creator_id) if item.brief_request_id == request.id), None)
            progress = {
                BriefRequestStatus.DRAFT.value: 0.0,
                BriefRequestStatus.QUEUED.value: 5.0,
                BriefRequestStatus.ASSEMBLING_CONTEXT.value: 10.0,
                BriefRequestStatus.VALIDATING_SOURCE.value: 20.0,
                BriefRequestStatus.MAPPING_OBJECTIVE.value: 30.0,
                BriefRequestStatus.MAPPING_AUDIENCE.value: 40.0,
                BriefRequestStatus.BUILDING_PROMISE.value: 50.0,
                BriefRequestStatus.BUILDING_ANGLES.value: 60.0,
                BriefRequestStatus.BUILDING_MESSAGES.value: 70.0,
                BriefRequestStatus.BUILDING_STRUCTURE.value: 75.0,
                BriefRequestStatus.MAPPING_PACKAGING.value: 80.0,
                BriefRequestStatus.VALIDATING_CLAIMS.value: 85.0,
                BriefRequestStatus.VALIDATING_REFERENCES.value: 87.5,
                BriefRequestStatus.EVALUATING_RIGHTS.value: 90.0,
                BriefRequestStatus.BUILDING_REQUIREMENTS.value: 92.5,
                BriefRequestStatus.BUILDING_CHECKLISTS.value: 95.0,
                BriefRequestStatus.CALCULATING_READINESS.value: 97.5,
                BriefRequestStatus.SAVING.value: 98.0,
                BriefRequestStatus.COMPLETED.value: 100.0,
                BriefRequestStatus.COMPLETED_WITH_WARNINGS.value: 100.0,
            }.get(request.status, 0.0)
            tasks.append(
                BriefRecord(
                    id=request.id,
                    task_id=request.id,
                    creator_id=creator_id,
                    brief_id=None if brief is None else brief.id,
                    source_id=request.source_id,
                    title=str(brief.title if brief is not None else request.request_type),
                    status=request.status,
                    stage_name=request.status,
                    progress_percent=progress,
                    message="Brief en progreso" if request.status not in {BriefRequestStatus.COMPLETED.value, BriefRequestStatus.COMPLETED_WITH_WARNINGS.value} else "Brief completado",
                    error=None if request.status not in {BriefRequestStatus.FAILED.value, BriefRequestStatus.CANCELLED.value} else request.status,
                    cancellable=True,
                    updated_at=request.updated_at,
                    payload={"kind": "brief_run", "request": request.to_dict(), "brief": None if brief is None else brief.to_dict()},
                )
            )
        return tasks

    def __getattr__(self, name: str):
        if name in self._list_accessors:
            table, key_field, enum_fields = self._list_accessors[name]

            def _loader(target_id: str) -> list[BriefRecord]:
                if enum_fields is None:
                    return self._entities(table, where=f"{key_field} = ?", params=(target_id,), order_by="created_at DESC")
                return self._entities(table, where=f"{key_field} = ?", params=(target_id,), order_by="created_at DESC", enum_fields=enum_fields)

            return _loader
        raise AttributeError(name)


def build_content_brief_service(
    *,
    settings: AppSettings | None,
    paths: ProjectPaths,
    repository: ContentBriefRepository,
    planning_service: Any | None = None,
    recommendation_service: Any | None = None,
    experiment_service: Any | None = None,
    content_library_service: Any | None = None,
    creator_memory_service: Any | None = None,
    creator_language_service: Any | None = None,
    creator_context_assembly_service: CreatorContextAssemblyService | None = None,
    creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
    audience_service: Any | None = None,
    analytics_service: Any | None = None,
    analytics_lab_service: Any | None = None,
    market_service: Any | None = None,
    platform_service: Any | None = None,
    packaging_service: Any | None = None,
    preferences: dict[str, object] | None = None,
    logger: logging.Logger | None = None,
) -> ContentBriefService:
    return ContentBriefService(
        settings=settings,
        paths=paths,
        repository=repository,
        planning_service=planning_service,
        recommendation_service=recommendation_service,
        experiment_service=experiment_service,
        content_library_service=content_library_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        creator_context_assembly_service=creator_context_assembly_service,
        creator_context_policy_registry=creator_context_policy_registry,
        audience_service=audience_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        market_service=market_service,
        platform_service=platform_service,
        packaging_service=packaging_service,
        preferences=preferences,
        logger=logger,
    )
