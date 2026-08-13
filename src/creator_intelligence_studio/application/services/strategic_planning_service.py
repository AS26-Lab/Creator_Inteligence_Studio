"""Servicio determinista para Strategic Planning and Content Roadmap Foundation."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.strategic_planning import (
    BacklogStatus,
    BacklogType,
    Campaign,
    CampaignType,
    CapacityAllocation,
    CapacityAllocationStatus,
    CapacityProfile,
    CapacityProfileStatus,
    ContentLibraryLink,
    ContentPillar,
    ContentPillarStatus,
    ContentSeries,
    ConflictResolutionStatus,
    ConflictType,
    CycleType,
    DependencyLink,
    DependencyType,
    FeasibilityReport,
    FeasibilityStatus,
    FreshnessStatus,
    HorizonType,
    Initiative,
    InitiativeType,
    LifecycleStatus,
    MetricAvailabilityStatus,
    MetricRole,
    Milestone,
    MilestoneType,
    ObjectiveType,
    PlanningBacklogItem,
    PlanningConflict,
    PlanningContextSnapshot,
    PlanningCycle,
    PlanningPlan,
    PlanningReport,
    PlanningReview,
    PlanningScenario,
    PlanningSnapshot,
    PlanningTask,
    PlanningRunStatus,
    PlanStatus,
    PriorityLevel,
    ResourceConstraint,
    ResourceConstraintType,
    ReviewDecision,
    ReviewType,
    RiskSeverity,
    RiskType,
    RoadmapItem,
    RoadmapItemMetric,
    RoadmapItemRisk,
    RoadmapItemStatus,
    RoadmapItemType,
    ScenarioType,
    SeriesType,
    SourceType,
    StrategicObjective,
    StrategicObjectiveMetric,
    StrategyTheme,
    StrategyThemeType,
    ContentLibraryLink,
)
from creator_intelligence_studio.domain.strategic_planning.errors import (
    StrategicPlanningConflictError,
    StrategicPlanningNotFoundError,
    StrategicPlanningStateError,
    StrategicPlanningValidationError,
)
from creator_intelligence_studio.domain.strategic_planning.repositories import StrategicPlanningRepository
from creator_intelligence_studio.domain.strategic_planning.services import build_planning_fingerprint
from creator_intelligence_studio.domain.strategic_planning.value_objects import CycleType, ObjectiveType, SourceType
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.application.services.creator_context_assembly_service import CreatorContextAssemblyService
from creator_intelligence_studio.application.services.creator_context_policy import (
    CreatorContextPolicyRegistry,
    build_default_creator_context_policy_registry,
)
from creator_intelligence_studio.shared.dates import utc_now, to_iso_z
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback: object) -> object:
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return value if value is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _now() -> str:
    return to_iso_z(utc_now()) or ""


def _safe_list(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_csv_value(value: object) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _entity_from_row(cls, row: dict[str, Any] | None, enum_fields: dict[str, Any] | None = None):
    if row is None:
        return None
    payload = dict(row)
    for field_name, enum_cls in (enum_fields or {}).items():
        if payload.get(field_name) is None:
            continue
        try:
            payload[field_name] = enum_cls(payload[field_name])
        except Exception:
            pass
    return cls(**payload)


def _priority_value(value: str | None) -> str:
    if not value:
        return PriorityLevel.UNKNOWN.value
    if value in {item.value for item in PriorityLevel}:
        return value
    return PriorityLevel.UNKNOWN.value


def _default_preferences() -> dict[str, object]:
    return {
        "default_horizon": "quarterly",
        "default_cycle_type": "monthly",
        "default_timezone": "America/Mexico_City",
        "require_human_review": True,
        "allow_automatic_activation": False,
        "allow_automatic_confirmed_dates": False,
        "default_capacity_units": "abstract",
        "default_available_hours": None,
        "default_max_active_items": 6,
        "default_max_publications_per_cycle": 3,
        "capacity_buffer_percentage": 0.15,
        "overload_warning_threshold": 0.85,
        "overload_block_threshold": 1.0,
        "minimum_evergreen_percentage": 0.2,
        "maximum_trend_percentage": 0.5,
        "maximum_experiment_percentage": 0.3,
        "maximum_single_platform_percentage": 0.7,
        "stale_plan_days": 30,
        "backlog_review_days": 14,
        "default_review_frequency_days": 14,
        "roadmap_max_items_per_cycle": 24,
        "scenario_generation_enabled": True,
        "show_numeric_scores": True,
        "automatic_external_calendar_sync": False,
        "automatic_publication": False,
        "planning_cache_hours": 12,
        "report_default_format": "json",
    }


class StrategicPlanningService:
    ENGINE_VERSION = "v28"

    def __init__(
        self,
        *,
        settings: AppSettings | None,
        paths: ProjectPaths,
        repository: StrategicPlanningRepository,
        recommendation_service: Any | None = None,
        creator_memory_service: Any | None = None,
        creator_language_service: Any | None = None,
        creator_context_assembly_service: CreatorContextAssemblyService | None = None,
        creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
        audience_service: Any | None = None,
        analytics_service: Any | None = None,
        analytics_lab_service: Any | None = None,
        market_service: Any | None = None,
        experiment_service: Any | None = None,
        content_library_service: Any | None = None,
        platform_service: Any | None = None,
        preferences: dict[str, object] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.recommendation_service = recommendation_service
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.creator_context_assembly_service = creator_context_assembly_service
        self.creator_context_policy_registry = creator_context_policy_registry or build_default_creator_context_policy_registry()
        self.audience_service = audience_service
        self.analytics_service = analytics_service
        self.analytics_lab_service = analytics_lab_service
        self.market_service = market_service
        self.experiment_service = experiment_service
        self.content_library_service = content_library_service
        self.platform_service = platform_service
        self.creator_feedback_service = None
        self.preferences = {**_default_preferences(), **(preferences or {})}
        self.logger = logger or logging.getLogger("creator_intelligence_studio.strategic_planning")
        self._reports_root = self.paths.data_directory / "planning" / "reports"
        self._snapshots_root = self.paths.data_directory / "planning" / "snapshots"
        self._reports_root.mkdir(parents=True, exist_ok=True)
        self._snapshots_root.mkdir(parents=True, exist_ok=True)

    def _upsert(self, table: str, payload: dict[str, Any], conflict_columns: tuple[str, ...] = ("id",)) -> dict[str, Any]:
        return self.repository.upsert_record(table, payload, conflict_columns=conflict_columns)

    def _fetch(self, table: str, *, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        return self.repository.fetch_record(table, where=where, params=params)

    def _fetch_many(self, table: str, *, where: str = "", params: tuple[Any, ...] = (), order_by: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        return self.repository.fetch_records(table, where=where, params=params, order_by=order_by, limit=limit)

    def _list_entities(self, table: str, cls, *, where: str, params: tuple[Any, ...], order_by: str | None = None, enum_fields: dict[str, Any] | None = None):
        return [_entity_from_row(cls, row, enum_fields) for row in self._fetch_many(table, where=where, params=params, order_by=order_by)]

    def _fetch_entity(self, table: str, cls, *, where: str, params: tuple[Any, ...], enum_fields: dict[str, Any] | None = None):
        return _entity_from_row(cls, self._fetch(table, where=where, params=params), enum_fields)

    def _latest_id(self, items: list[Any]) -> str | None:
        return items[0].id if items else None

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

    def _recommendation_payload(self, creator_id: str) -> dict[str, object]:
        recommendations = []
        if self.recommendation_service is not None:
            recommendations = list(self._safe_call(self.recommendation_service, ("list_recommendations",), creator_id) or [])
        approved = []
        deferred = []
        blocked = []
        rejected = []
        expired = []
        for recommendation in recommendations:
            item = recommendation.to_dict() if hasattr(recommendation, "to_dict") else dict(recommendation)
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
            "items": [item if isinstance(item, dict) else item.to_dict() for item in recommendations],
        }

    def create_context_snapshot(
        self,
        creator_id: str,
        *,
        recommendation_snapshot_id: str | None = None,
        created_at: str | None = None,
        preferences: dict[str, object] | None = None,
        constraints: list[dict[str, object]] | None = None,
        capacity: dict[str, object] | None = None,
        stale_data: list[str] | None = None,
        missing_data: list[str] | None = None,
        conflicts: list[dict[str, object]] | None = None,
        use_creator_context: bool = True,
    ) -> PlanningContextSnapshot:
        created_at = created_at or _now()
        context_policy = self.creator_context_policy_registry.get_by_workflow("strategic_planning")
        creator_memory_snapshot_id = self._snapshot_identifier(self.creator_memory_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots"), creator_id)
        creator_language_snapshot_id = self._snapshot_identifier(self.creator_language_service, ("create_profile_snapshot", "get_profile_snapshot", "list_profile_snapshots"), creator_id)
        audience_snapshot_id = self._snapshot_identifier(self.audience_service, ("build_profile", "get_profile", "list_profiles"), creator_id)
        analytics_snapshot_id = self._snapshot_identifier(self.analytics_lab_service, ("generate_weekly_report", "list_reports"), creator_id)
        market_snapshot_id = self._snapshot_identifier(self.market_service, ("build_snapshot", "list_snapshots"), creator_id)
        experiment_snapshot_id = self._snapshot_identifier(self.experiment_service, ("list_experiments", "list_reports"), creator_id)
        content_library_snapshot_id = self._snapshot_identifier(self.content_library_service, ("list_content", "list_items", "list_entries", "list_assets"), creator_id)
        platform_snapshot_id = self._snapshot_identifier(self.platform_service, ("list_reports", "list_integrations", "list_connections"), creator_id)
        recommendation_payload = self._recommendation_payload(creator_id)
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
            planning_request_text = " | ".join(
                part
                for part in (
                    str(preferences or self.preferences),
                    str(capacity or {}),
                    str(constraints or []),
                    str(conflicts or []),
                    str(missing_data or []),
                    str(stale_data or []),
                    str((recommendation_payload.get("approved") or [{}])[0].get("title") if recommendation_payload.get("approved") else ""),
                )
                if part
            ) or "Strategic planning context"
            creator_context_request = context_policy.build_request(
                creator_id=creator_id,
                user_request=planning_request_text,
                query_text=planning_request_text,
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
            "preferences": dict(preferences or self.preferences),
            "recommendations": recommendation_payload,
            "constraints": constraints or [],
            "capacity": capacity or {},
            "stale_data": stale_data or [],
            "missing_data": missing_data or [],
            "conflicts": conflicts or [],
            "snapshot_ids": {
                "recommendation_snapshot_id": recommendation_snapshot_id,
                "creator_memory_snapshot_id": creator_memory_snapshot_id,
                "creator_language_snapshot_id": creator_language_snapshot_id,
                "audience_snapshot_id": audience_snapshot_id,
                "analytics_snapshot_id": analytics_snapshot_id,
                "market_snapshot_id": market_snapshot_id,
                "experiment_snapshot_id": experiment_snapshot_id,
                "content_library_snapshot_id": content_library_snapshot_id,
                "platform_snapshot_id": platform_snapshot_id,
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
        fingerprint = build_planning_fingerprint({**payload, **context_details})
        existing = self._fetch(
            "planning_context_snapshots",
            where="creator_id = ? AND source_fingerprint = ?",
            params=(creator_id, fingerprint),
        )
        if existing:
            return _entity_from_row(PlanningContextSnapshot, existing)
        snapshot = PlanningContextSnapshot(
            id=str(uuid4()),
            creator_id=creator_id,
            context_version=self.ENGINE_VERSION,
            recommendation_snapshot_id=recommendation_snapshot_id,
            creator_memory_snapshot_id=creator_memory_snapshot_id,
            creator_language_snapshot_id=creator_language_snapshot_id,
            audience_snapshot_id=audience_snapshot_id,
            analytics_snapshot_id=analytics_snapshot_id,
            market_snapshot_id=market_snapshot_id,
            experiment_snapshot_id=experiment_snapshot_id,
            content_library_snapshot_id=content_library_snapshot_id,
            platform_snapshot_id=platform_snapshot_id,
            source_fingerprint=fingerprint,
            context_json=_json_dumps({**payload, **context_details}),
            created_at=created_at,
        )
        return _entity_from_row(PlanningContextSnapshot, self._upsert("planning_context_snapshots", snapshot.to_dict()))

    def list_context_snapshots(self, creator_id: str) -> list[PlanningContextSnapshot]:
        return self._list_entities("planning_context_snapshots", PlanningContextSnapshot, where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def get_context_snapshot(self, snapshot_id: str) -> PlanningContextSnapshot | None:
        return self._fetch_entity("planning_context_snapshots", PlanningContextSnapshot, where="id = ?", params=(snapshot_id,))

    def create_plan(
        self,
        *,
        creator_id: str,
        name: str,
        context_snapshot_id: str,
        horizon_type: str | HorizonType = HorizonType.CUSTOM,
        description: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        timezone: str | None = None,
        primary_objective_id: str | None = None,
        parent_plan_id: str | None = None,
        version: int = 1,
    ) -> PlanningPlan:
        context_snapshot = self.get_context_snapshot(context_snapshot_id)
        if context_snapshot is None:
            raise StrategicPlanningValidationError("Se requiere un planning context snapshot valido.")
        plan = PlanningPlan(
            id=str(uuid4()),
            creator_id=creator_id,
            name=name,
            description=description,
            status=PlanStatus.DRAFT,
            horizon_type=HorizonType(horizon_type) if not isinstance(horizon_type, HorizonType) else horizon_type,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone or str(self.preferences.get("default_timezone")),
            primary_objective_id=primary_objective_id,
            context_snapshot_id=context_snapshot_id,
            version=version,
            parent_plan_id=parent_plan_id,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(PlanningPlan, self._upsert("strategic_plans", plan.to_dict()), enum_fields={"status": PlanStatus, "horizon_type": HorizonType})

    def list_plans(self, creator_id: str) -> list[PlanningPlan]:
        return self._list_entities("strategic_plans", PlanningPlan, where="creator_id = ?", params=(creator_id,), order_by="updated_at DESC", enum_fields={"status": PlanStatus, "horizon_type": HorizonType})

    def get_plan(self, plan_id: str) -> PlanningPlan | None:
        return self._fetch_entity("strategic_plans", PlanningPlan, where="id = ?", params=(plan_id,), enum_fields={"status": PlanStatus, "horizon_type": HorizonType})

    def update_plan(self, plan_id: str, **changes) -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        updated = replace(
            plan,
            name=changes.get("name", plan.name),
            description=changes.get("description", plan.description),
            status=PlanStatus(changes.get("status", plan.status.value)),
            horizon_type=HorizonType(changes.get("horizon_type", plan.horizon_type.value)),
            start_date=changes.get("start_date", plan.start_date),
            end_date=changes.get("end_date", plan.end_date),
            timezone=changes.get("timezone", plan.timezone),
            primary_objective_id=changes.get("primary_objective_id", plan.primary_objective_id),
            parent_plan_id=changes.get("parent_plan_id", plan.parent_plan_id),
            version=int(changes.get("version", plan.version)),
            updated_at=_now(),
        )
        return _entity_from_row(PlanningPlan, self._upsert("strategic_plans", updated.to_dict()), enum_fields={"status": PlanStatus, "horizon_type": HorizonType})

    def submit_plan_for_review(self, plan_id: str, *, reason: str = "submitted_for_review", reviewer: str | None = None) -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        self.record_review(
            strategic_plan_id=plan.id,
            target_type="plan",
            target_id=plan.id,
            review_type=ReviewType.PLAN_REVIEW,
            decision=ReviewDecision.DEFER,
            reason=reason,
            reviewer=reviewer,
        )
        return self.update_plan(plan_id, status=PlanStatus.NEEDS_REVIEW.value)

    def approve_plan(self, plan_id: str, *, reason: str, reviewer: str | None = None) -> PlanningPlan:
        self.record_review(
            strategic_plan_id=plan_id,
            target_type="plan",
            target_id=plan_id,
            review_type=ReviewType.PLAN_REVIEW,
            decision=ReviewDecision.APPROVE,
            reason=reason,
            reviewer=reviewer,
        )
        plan = self.get_plan(plan_id)
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None and plan is not None:
            feedback_service.record_acceptance(
                creator_id=plan.creator_id,
                workflow_type="strategic_planning",
                artifact_type="strategic_plan",
                artifact_id=plan.id,
                project_id=None,
                metadata={
                    "reason": reason,
                    "reviewer": reviewer,
                    "review_type": "plan_review",
                    "decision": ReviewDecision.APPROVE.value,
                },
            )
        return self.update_plan(plan_id, status=PlanStatus.APPROVED.value)

    def activate_plan(self, plan_id: str, *, reason: str = "manual_activation", reviewer: str | None = None) -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        if plan.status not in {PlanStatus.APPROVED, PlanStatus.NEEDS_REVIEW, PlanStatus.PAUSED}:
            raise StrategicPlanningStateError("El plan no puede activarse en su estado actual.")
        self.record_review(
            strategic_plan_id=plan.id,
            target_type="plan",
            target_id=plan.id,
            review_type=ReviewType.PLAN_REVIEW,
            decision=ReviewDecision.RESUME if plan.status == PlanStatus.PAUSED else ReviewDecision.APPROVE,
            reason=reason,
            reviewer=reviewer,
        )
        return self.update_plan(plan_id, status=PlanStatus.ACTIVE.value)

    def pause_plan(self, plan_id: str, *, reason: str, reviewer: str | None = None) -> PlanningPlan:
        self.record_review(
            strategic_plan_id=plan_id,
            target_type="plan",
            target_id=plan_id,
            review_type=ReviewType.PLAN_REVIEW,
            decision=ReviewDecision.PAUSE,
            reason=reason,
            reviewer=reviewer,
        )
        return self.update_plan(plan_id, status=PlanStatus.PAUSED.value)

    def archive_plan(self, plan_id: str, *, reason: str, reviewer: str | None = None) -> PlanningPlan:
        self.record_review(
            strategic_plan_id=plan_id,
            target_type="plan",
            target_id=plan_id,
            review_type=ReviewType.PLAN_REVIEW,
            decision=ReviewDecision.ARCHIVE,
            reason=reason,
            reviewer=reviewer,
        )
        return self.update_plan(plan_id, status=PlanStatus.ARCHIVED.value)

    def version_plan(self, plan_id: str, *, name: str | None = None, reason: str = "versioned_plan") -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        return self.create_plan(
            creator_id=plan.creator_id,
            name=name or f"{plan.name} v{plan.version + 1}",
            context_snapshot_id=plan.context_snapshot_id,
            horizon_type=plan.horizon_type,
            description=plan.description,
            start_date=plan.start_date,
            end_date=plan.end_date,
            timezone=plan.timezone,
            primary_objective_id=plan.primary_objective_id,
            parent_plan_id=plan.id,
            version=plan.version + 1,
        )

    def supersede_plan(self, plan_id: str, *, replacement_name: str | None = None, reason: str) -> PlanningPlan:
        old_plan = self.get_plan(plan_id)
        if old_plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        self.update_plan(plan_id, status=PlanStatus.SUPERSEDED.value)
        feedback_service = getattr(self, "creator_feedback_service", None)
        if feedback_service is not None:
            feedback_service.record_supersession(
                creator_id=old_plan.creator_id,
                workflow_type="strategic_planning",
                artifact_type="strategic_plan",
                artifact_id=old_plan.id,
                project_id=None,
                metadata={
                    "reason": reason,
                    "replacement_name": replacement_name,
                    "previous_status": old_plan.status.value if hasattr(old_plan.status, "value") else str(old_plan.status),
                    "new_status": PlanStatus.SUPERSEDED.value,
                },
            )
        return self.version_plan(plan_id, name=replacement_name, reason=reason)

    def record_review(
        self,
        *,
        strategic_plan_id: str,
        target_type: str,
        target_id: str,
        review_type: ReviewType | str,
        decision: ReviewDecision | str,
        reason: str,
        reviewer: str | None = None,
        previous_value_json: str | None = None,
        new_value_json: str | None = None,
    ) -> PlanningReview:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        review = PlanningReview(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            target_type=target_type,
            target_id=target_id,
            review_type=ReviewType(review_type) if not isinstance(review_type, ReviewType) else review_type,
            decision=ReviewDecision(decision) if not isinstance(decision, ReviewDecision) else decision,
            previous_value_json=previous_value_json,
            new_value_json=new_value_json,
            reason=reason,
            reviewer=reviewer,
            reviewed_at=_now(),
            created_at=_now(),
        )
        return _entity_from_row(PlanningReview, self._upsert("planning_reviews", review.to_dict()), enum_fields={"review_type": ReviewType, "decision": ReviewDecision})

    def list_reviews(self, strategic_plan_id: str) -> list[PlanningReview]:
        return self._list_entities("planning_reviews", PlanningReview, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="reviewed_at DESC", enum_fields={"review_type": ReviewType, "decision": ReviewDecision})

    def create_objective(
        self,
        *,
        strategic_plan_id: str,
        objective_type: str | ObjectiveType,
        title: str,
        priority_level: str = "medium",
        status: str = LifecycleStatus.DRAFT.value,
        source_type: str | SourceType = SourceType.MANUAL,
        source_id: str | None = None,
        description: str | None = None,
        target_direction: str | None = None,
        baseline_json: str | None = None,
        target_json: str | None = None,
        measurement_window: str | None = None,
        confidence_level: str = "medium",
        metrics: list[dict[str, object]] | None = None,
        limitations: str | None = None,
        review_date: str | None = None,
    ) -> StrategicObjective:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        obj = StrategicObjective(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            objective_type=ObjectiveType(objective_type) if not isinstance(objective_type, ObjectiveType) else objective_type,
            title=title,
            description=description,
            priority_level=_priority_value(priority_level),
            status=LifecycleStatus(status) if not isinstance(status, LifecycleStatus) else status,
            target_direction=target_direction,
            baseline_json=baseline_json,
            target_json=target_json,
            measurement_window=measurement_window,
            confidence_level=confidence_level,
            source_type=SourceType(source_type) if not isinstance(source_type, SourceType) else source_type,
            source_id=source_id,
            created_at=_now(),
            updated_at=_now(),
        )
        created = self._upsert("strategic_objectives", obj.to_dict())
        if metrics:
            for metric in metrics:
                self.create_objective_metric(
                    strategic_objective_id=obj.id,
                    creator_id=plan.creator_id,
                    metric_role=str(metric.get("metric_role") or MetricRole.PRIMARY.value),
                    metric_key=str(metric.get("metric_key") or title.lower().replace(" ", "_")),
                    platform=metric.get("platform"),
                    internal_metric_key=metric.get("internal_metric_key"),
                    unit=metric.get("unit"),
                    period_semantics=metric.get("period_semantics"),
                    availability_status=str(metric.get("availability_status") or MetricAvailabilityStatus.UNKNOWN.value),
                    baseline_value=metric.get("baseline_value"),
                    target_value=metric.get("target_value"),
                    target_method=metric.get("target_method"),
                    measurement_window=metric.get("measurement_window"),
                    source_type=metric.get("source_type"),
                )
        self._detect_objective_conflicts(strategic_plan_id)
        return _entity_from_row(StrategicObjective, created, enum_fields={"objective_type": ObjectiveType, "status": LifecycleStatus, "source_type": SourceType})

    def list_objectives(self, strategic_plan_id: str) -> list[StrategicObjective]:
        return self._list_entities("strategic_objectives", StrategicObjective, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"objective_type": ObjectiveType, "status": LifecycleStatus, "source_type": SourceType})

    def get_objective(self, objective_id: str) -> StrategicObjective | None:
        return self._fetch_entity("strategic_objectives", StrategicObjective, where="id = ?", params=(objective_id,), enum_fields={"objective_type": ObjectiveType, "status": LifecycleStatus, "source_type": SourceType})

    def update_objective(self, objective_id: str, **changes) -> StrategicObjective:
        objective = self.get_objective(objective_id)
        if objective is None:
            raise StrategicPlanningNotFoundError("El objective no existe.")
        updated = replace(
            objective,
            title=changes.get("title", objective.title),
            description=changes.get("description", objective.description),
            objective_type=ObjectiveType(changes.get("objective_type", objective.objective_type.value)),
            priority_level=_priority_value(changes.get("priority_level", objective.priority_level)),
            status=LifecycleStatus(changes.get("status", objective.status.value)),
            target_direction=changes.get("target_direction", objective.target_direction),
            baseline_json=changes.get("baseline_json", objective.baseline_json),
            target_json=changes.get("target_json", objective.target_json),
            measurement_window=changes.get("measurement_window", objective.measurement_window),
            confidence_level=changes.get("confidence_level", objective.confidence_level),
            source_type=SourceType(changes.get("source_type", objective.source_type.value)),
            source_id=changes.get("source_id", objective.source_id),
            updated_at=_now(),
        )
        return _entity_from_row(StrategicObjective, self._upsert("strategic_objectives", updated.to_dict()), enum_fields={"objective_type": ObjectiveType, "status": LifecycleStatus, "source_type": SourceType})

    def create_objective_metric(self, *, strategic_objective_id: str, creator_id: str, metric_role: str | MetricRole, metric_key: str, availability_status: str | MetricAvailabilityStatus, platform: str | None = None, internal_metric_key: str | None = None, unit: str | None = None, period_semantics: str | None = None, baseline_value: str | None = None, target_value: str | None = None, target_method: str | None = None, measurement_window: str | None = None, source_type: str | None = None) -> StrategicObjectiveMetric:
        metric = StrategicObjectiveMetric(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_objective_id=strategic_objective_id,
            metric_role=MetricRole(metric_role) if not isinstance(metric_role, MetricRole) else metric_role,
            platform=platform,
            metric_key=metric_key,
            internal_metric_key=internal_metric_key,
            unit=unit,
            period_semantics=period_semantics,
            availability_status=MetricAvailabilityStatus(availability_status) if not isinstance(availability_status, MetricAvailabilityStatus) else availability_status,
            baseline_value=baseline_value,
            target_value=target_value,
            target_method=target_method,
            measurement_window=measurement_window,
            source_type=source_type,
            created_at=_now(),
        )
        return _entity_from_row(StrategicObjectiveMetric, self._upsert("strategic_objective_metrics", metric.to_dict()), enum_fields={"metric_role": MetricRole, "availability_status": MetricAvailabilityStatus})

    def list_objective_metrics(self, strategic_objective_id: str) -> list[StrategicObjectiveMetric]:
        return self._list_entities("strategic_objective_metrics", StrategicObjectiveMetric, where="strategic_objective_id = ?", params=(strategic_objective_id,), order_by="created_at ASC", enum_fields={"metric_role": MetricRole, "availability_status": MetricAvailabilityStatus})

    def create_theme(
        self,
        *,
        strategic_plan_id: str,
        name: str,
        theme_type: str | StrategyThemeType = StrategyThemeType.UNKNOWN,
        status: str = LifecycleStatus.DRAFT.value,
        priority_level: str = "medium",
        description: str | None = None,
        rationale: str = "",
        source_fingerprint: str | None = None,
    ) -> StrategyTheme:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        payload = {
            "creator_id": plan.creator_id,
            "strategic_plan_id": strategic_plan_id,
            "name": name,
            "theme_type": theme_type.value if isinstance(theme_type, StrategyThemeType) else StrategyThemeType(theme_type).value,
            "status": status,
            "priority_level": _priority_value(priority_level),
            "description": description,
            "rationale": rationale,
            "source_fingerprint": source_fingerprint or build_planning_fingerprint({"strategic_plan_id": strategic_plan_id, "name": name, "theme_type": str(theme_type)}),
            "created_at": _now(),
            "updated_at": _now(),
        }
        theme = StrategyTheme(id=str(uuid4()), **payload)
        return _entity_from_row(StrategyTheme, self._upsert("strategy_themes", theme.to_dict()), enum_fields={"theme_type": StrategyThemeType, "status": LifecycleStatus})

    def list_themes(self, strategic_plan_id: str) -> list[StrategyTheme]:
        return self._list_entities("strategy_themes", StrategyTheme, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"theme_type": StrategyThemeType, "status": LifecycleStatus})

    def create_pillar(
        self,
        *,
        strategic_plan_id: str,
        name: str,
        strategy_theme_id: str | None = None,
        status: str = ContentPillarStatus.DRAFT.value,
        rationale: str = "",
        description: str | None = None,
        purpose: str | None = None,
        audience_scope_json: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        target_mix_percentage: float | None = None,
        minimum_mix_percentage: float | None = None,
        maximum_mix_percentage: float | None = None,
    ) -> ContentPillar:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        pillar = ContentPillar(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            strategy_theme_id=strategy_theme_id,
            name=name,
            description=description,
            purpose=purpose,
            audience_scope_json=audience_scope_json,
            platform_scope_json=platform_scope_json,
            content_type_scope_json=content_type_scope_json,
            target_mix_percentage=target_mix_percentage,
            minimum_mix_percentage=minimum_mix_percentage,
            maximum_mix_percentage=maximum_mix_percentage,
            status=ContentPillarStatus(status),
            rationale=rationale,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(ContentPillar, self._upsert("content_pillars", pillar.to_dict()), enum_fields={"status": ContentPillarStatus})

    def list_pillars(self, strategic_plan_id: str) -> list[ContentPillar]:
        return self._list_entities("content_pillars", ContentPillar, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"status": ContentPillarStatus})

    def create_initiative(
        self,
        *,
        strategic_plan_id: str,
        title: str,
        initiative_type: str | InitiativeType = InitiativeType.UNKNOWN,
        status: str = PlanStatus.DRAFT.value,
        priority_level: str = "medium",
        expected_impact: str = "unknown",
        expected_learning_value: str = "unknown",
        confidence_level: str = "medium",
        effort_level: str = "medium",
        risk_level: str = "medium",
        strategic_objective_id: str | None = None,
        content_pillar_id: str | None = None,
        recommendation_candidate_id: str | None = None,
        experiment_id: str | None = None,
        description: str | None = None,
        start_window: str | None = None,
        end_window: str | None = None,
    ) -> Initiative:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        if recommendation_candidate_id is not None:
            existing = self._fetch(
                "strategic_initiatives",
                where="strategic_plan_id = ? AND recommendation_candidate_id = ?",
                params=(strategic_plan_id, recommendation_candidate_id),
            )
            if existing is not None:
                return _entity_from_row(Initiative, existing, enum_fields={"initiative_type": InitiativeType, "status": PlanStatus})
        if not strategic_objective_id and not description:
            raise StrategicPlanningValidationError("Una iniciativa requiere objetivo o razon.")
        initiative = Initiative(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            strategic_objective_id=strategic_objective_id,
            content_pillar_id=content_pillar_id,
            recommendation_candidate_id=recommendation_candidate_id,
            experiment_id=experiment_id,
            title=title,
            description=description,
            initiative_type=initiative_type.value if isinstance(initiative_type, InitiativeType) else InitiativeType(initiative_type).value,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            priority_level=_priority_value(priority_level),
            expected_impact=expected_impact,
            expected_learning_value=expected_learning_value,
            confidence_level=confidence_level,
            effort_level=effort_level,
            risk_level=risk_level,
            start_window=start_window,
            end_window=end_window,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(Initiative, self._upsert("strategic_initiatives", initiative.to_dict()), enum_fields={"initiative_type": InitiativeType, "status": PlanStatus})

    def list_initiatives(self, strategic_plan_id: str) -> list[Initiative]:
        return self._list_entities("strategic_initiatives", Initiative, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"initiative_type": InitiativeType, "status": PlanStatus})

    def create_campaign(self, *, strategic_plan_id: str, name: str, campaign_type: str | CampaignType = CampaignType.UNKNOWN, status: str = PlanStatus.DRAFT.value, strategic_initiative_id: str | None = None, description: str | None = None, platform_scope_json: str | None = None, audience_scope_json: str | None = None, objective_scope_json: str | None = None, start_window: str | None = None, end_window: str | None = None) -> Campaign:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        campaign = Campaign(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            strategic_initiative_id=strategic_initiative_id,
            name=name,
            description=description,
            campaign_type=campaign_type.value if isinstance(campaign_type, CampaignType) else CampaignType(campaign_type).value,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            platform_scope_json=platform_scope_json,
            audience_scope_json=audience_scope_json,
            objective_scope_json=objective_scope_json,
            start_window=start_window,
            end_window=end_window,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(Campaign, self._upsert("campaigns", campaign.to_dict()), enum_fields={"campaign_type": CampaignType, "status": PlanStatus})

    def list_campaigns(self, strategic_plan_id: str) -> list[Campaign]:
        return self._list_entities("campaigns", Campaign, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"campaign_type": CampaignType, "status": PlanStatus})

    def create_series(self, *, strategic_plan_id: str, name: str, series_type: str | SeriesType = SeriesType.UNKNOWN, status: str = PlanStatus.DRAFT.value, strategic_initiative_id: str | None = None, campaign_id: str | None = None, description: str | None = None, platform_scope_json: str | None = None, content_type_scope_json: str | None = None, planned_episode_count: int | None = None, minimum_episode_count: int | None = None, maximum_episode_count: int | None = None, cadence_type: str | None = None, cadence_value: str | None = None, success_criteria_json: str = "{}", stop_criteria_json: str = "{}") -> ContentSeries:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        series = ContentSeries(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            strategic_initiative_id=strategic_initiative_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            series_type=series_type.value if isinstance(series_type, SeriesType) else SeriesType(series_type).value,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            platform_scope_json=platform_scope_json,
            content_type_scope_json=content_type_scope_json,
            planned_episode_count=planned_episode_count,
            minimum_episode_count=minimum_episode_count,
            maximum_episode_count=maximum_episode_count,
            cadence_type=cadence_type,
            cadence_value=cadence_value,
            success_criteria_json=success_criteria_json,
            stop_criteria_json=stop_criteria_json,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(ContentSeries, self._upsert("content_series", series.to_dict()), enum_fields={"series_type": SeriesType, "status": PlanStatus})

    def list_series(self, strategic_plan_id: str) -> list[ContentSeries]:
        return self._list_entities("content_series", ContentSeries, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at ASC", enum_fields={"series_type": SeriesType, "status": PlanStatus})

    def create_cycle(self, *, strategic_plan_id: str, name: str, cycle_type: str | CycleType, start_date: str, end_date: str, status: str = PlanStatus.DRAFT.value, locked: bool = False, review_at: str | None = None) -> PlanningCycle:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        cycle = PlanningCycle(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            cycle_type=CycleType(cycle_type) if not isinstance(cycle_type, CycleType) else cycle_type,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            locked=locked,
            review_at=review_at,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(PlanningCycle, self._upsert("planning_cycles", cycle.to_dict()), enum_fields={"cycle_type": CycleType, "status": PlanStatus})

    def list_cycles(self, strategic_plan_id: str) -> list[PlanningCycle]:
        return self._list_entities("planning_cycles", PlanningCycle, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="start_date ASC", enum_fields={"cycle_type": CycleType, "status": PlanStatus})

    def create_backlog_item(self, *, strategic_plan_id: str, source_type: str | SourceType, title: str, backlog_type: str | BacklogType = BacklogType.UNKNOWN, status: str = BacklogStatus.ACTIVE.value, priority_level: str = "medium", source_id: str | None = None, description: str | None = None, platform_scope_json: str = "[]", content_type_scope_json: str = "[]", objective_scope_json: str = "[]", freshness_status: str | None = None, expires_at: str | None = None, estimated_effort: str | None = None, reason_not_scheduled: str | None = None, review_at: str | None = None) -> PlanningBacklogItem:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        source_value = source_type.value if isinstance(source_type, SourceType) else str(source_type)
        backlog_value = backlog_type.value if isinstance(backlog_type, BacklogType) else str(backlog_type)
        if source_id is not None:
            existing = self._fetch(
                "planning_backlog_items",
                where="strategic_plan_id = ? AND source_type = ? AND source_id = ? AND backlog_type = ?",
                params=(strategic_plan_id, source_value, source_id, backlog_value),
            )
            if existing is not None:
                return _entity_from_row(PlanningBacklogItem, existing, enum_fields={"source_type": SourceType, "backlog_type": BacklogType, "status": BacklogStatus, "freshness_status": FreshnessStatus})
        item = PlanningBacklogItem(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            source_type=SourceType(source_type) if not isinstance(source_type, SourceType) else source_type,
            source_id=source_id,
            title=title,
            description=description,
            backlog_type=BacklogType(backlog_type) if not isinstance(backlog_type, BacklogType) else backlog_type,
            status=BacklogStatus(status) if not isinstance(status, BacklogStatus) else status,
            priority_level=_priority_value(priority_level),
            platform_scope_json=platform_scope_json,
            content_type_scope_json=content_type_scope_json,
            objective_scope_json=objective_scope_json,
            freshness_status=FreshnessStatus(freshness_status) if freshness_status else None,
            expires_at=expires_at,
            estimated_effort=estimated_effort,
            reason_not_scheduled=reason_not_scheduled,
            review_at=review_at,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(PlanningBacklogItem, self._upsert("planning_backlog_items", item.to_dict()), enum_fields={"source_type": SourceType, "backlog_type": BacklogType, "status": BacklogStatus, "freshness_status": FreshnessStatus})

    def list_backlog_items(self, strategic_plan_id: str) -> list[PlanningBacklogItem]:
        return self._list_entities("planning_backlog_items", PlanningBacklogItem, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"source_type": SourceType, "backlog_type": BacklogType, "status": BacklogStatus, "freshness_status": FreshnessStatus})

    def create_capacity_profile(self, *, strategic_plan_id: str | None, creator_id: str, name: str, status: str = CapacityProfileStatus.ACTIVE.value, period_type: str = "weekly", available_hours: float | None = None, available_capacity_units: float | None = None, maximum_active_items: int | None = None, maximum_platforms: int | None = None, maximum_publications: int | None = None, configuration_json: str = "{}", effective_from: str | None = None, effective_to: str | None = None) -> CapacityProfile:
        profile = CapacityProfile(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_plan_id=strategic_plan_id,
            name=name,
            status=CapacityProfileStatus(status) if not isinstance(status, CapacityProfileStatus) else status,
            period_type=period_type,
            available_hours=available_hours,
            available_capacity_units=available_capacity_units,
            maximum_active_items=maximum_active_items,
            maximum_platforms=maximum_platforms,
            maximum_publications=maximum_publications,
            configuration_json=configuration_json,
            effective_from=effective_from,
            effective_to=effective_to,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(CapacityProfile, self._upsert("capacity_profiles", profile.to_dict()), enum_fields={"status": CapacityProfileStatus})

    def list_capacity_profiles(self, strategic_plan_id: str | None = None, creator_id: str | None = None) -> list[CapacityProfile]:
        if strategic_plan_id is not None:
            return self._list_entities("capacity_profiles", CapacityProfile, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"status": CapacityProfileStatus})
        if creator_id is not None:
            return self._list_entities("capacity_profiles", CapacityProfile, where="creator_id = ?", params=(creator_id,), order_by="created_at DESC", enum_fields={"status": CapacityProfileStatus})
        return self._list_entities("capacity_profiles", CapacityProfile, where="1 = 1", params=(), order_by="created_at DESC", enum_fields={"status": CapacityProfileStatus})

    def create_capacity_allocation(self, *, strategic_plan_id: str, creator_id: str, resource_type: str, planning_cycle_id: str | None = None, roadmap_item_id: str | None = None, allocated_hours: float | None = None, allocated_units: float | None = None, allocation_status: str = CapacityAllocationStatus.PLANNED.value) -> CapacityAllocation:
        allocation = CapacityAllocation(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_plan_id=strategic_plan_id,
            planning_cycle_id=planning_cycle_id,
            roadmap_item_id=roadmap_item_id,
            resource_type=resource_type,
            allocated_hours=allocated_hours,
            allocated_units=allocated_units,
            allocation_status=CapacityAllocationStatus(allocation_status) if not isinstance(allocation_status, CapacityAllocationStatus) else allocation_status,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(CapacityAllocation, self._upsert("capacity_allocations", allocation.to_dict()), enum_fields={"allocation_status": CapacityAllocationStatus})

    def list_capacity_allocations(self, strategic_plan_id: str) -> list[CapacityAllocation]:
        return self._list_entities("capacity_allocations", CapacityAllocation, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"allocation_status": CapacityAllocationStatus})

    def create_resource_constraint(self, *, strategic_plan_id: str, creator_id: str, constraint_type: str | ResourceConstraintType, title: str, description: str, severity: str, blocking: bool, available_value_json: str | None = None, required_value_json: str | None = None, resolution_action: str | None = None, effective_from: str | None = None, effective_to: str | None = None) -> ResourceConstraint:
        constraint = ResourceConstraint(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_plan_id=strategic_plan_id,
            constraint_type=ResourceConstraintType(constraint_type) if not isinstance(constraint_type, ResourceConstraintType) else constraint_type,
            title=title,
            description=description,
            severity=severity,
            blocking=blocking,
            available_value_json=available_value_json,
            required_value_json=required_value_json,
            resolution_action=resolution_action,
            effective_from=effective_from,
            effective_to=effective_to,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(ResourceConstraint, self._upsert("resource_constraints", constraint.to_dict()), enum_fields={"constraint_type": ResourceConstraintType})

    def list_resource_constraints(self, strategic_plan_id: str) -> list[ResourceConstraint]:
        return self._list_entities("resource_constraints", ResourceConstraint, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"constraint_type": ResourceConstraintType})

    def add_roadmap_item(
        self,
        *,
        strategic_plan_id: str,
        title: str,
        item_type: str | RoadmapItemType,
        status: str = RoadmapItemStatus.IDEA.value,
        priority_level: str = "medium",
        sequence_order: int = 0,
        planning_cycle_id: str | None = None,
        strategic_initiative_id: str | None = None,
        campaign_id: str | None = None,
        content_series_id: str | None = None,
        recommendation_candidate_id: str | None = None,
        experiment_id: str | None = None,
        internal_content_id: str | None = None,
        description: str | None = None,
        tentative_start: str | None = None,
        tentative_end: str | None = None,
        confirmed_start: str | None = None,
        confirmed_end: str | None = None,
        platform_scope_json: str | None = None,
        content_type_scope_json: str | None = None,
        objective_scope_json: str | None = None,
        estimated_effort: str | None = None,
        estimated_duration_hours: float | None = None,
        assigned_capacity_units: float | None = None,
        confidence_level: str | None = None,
        source_fingerprint: str | None = None,
    ) -> RoadmapItem:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        if tentative_start and confirmed_start and tentative_start > confirmed_start:
            raise StrategicPlanningValidationError("Una fecha tentativa no puede superar una fecha confirmada.")
        source_fingerprint = source_fingerprint or build_planning_fingerprint({
            "strategic_plan_id": strategic_plan_id,
            "title": title,
            "item_type": item_type.value if isinstance(item_type, RoadmapItemType) else str(item_type),
            "recommendation_candidate_id": recommendation_candidate_id,
            "experiment_id": experiment_id,
            "internal_content_id": internal_content_id,
            "tentative_start": tentative_start,
            "tentative_end": tentative_end,
        })
        existing = self._fetch("roadmap_items", where="strategic_plan_id = ? AND source_fingerprint = ?", params=(strategic_plan_id, source_fingerprint))
        if existing:
            return _entity_from_row(RoadmapItem, existing, enum_fields={"item_type": RoadmapItemType, "status": RoadmapItemStatus})
        item = RoadmapItem(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            planning_cycle_id=planning_cycle_id,
            strategic_initiative_id=strategic_initiative_id,
            campaign_id=campaign_id,
            content_series_id=content_series_id,
            recommendation_candidate_id=recommendation_candidate_id,
            experiment_id=experiment_id,
            internal_content_id=internal_content_id,
            item_type=RoadmapItemType(item_type) if not isinstance(item_type, RoadmapItemType) else item_type,
            title=title,
            description=description,
            status=RoadmapItemStatus(status) if not isinstance(status, RoadmapItemStatus) else status,
            priority_level=_priority_value(priority_level),
            sequence_order=sequence_order,
            tentative_start=tentative_start,
            tentative_end=tentative_end,
            confirmed_start=confirmed_start,
            confirmed_end=confirmed_end,
            platform_scope_json=platform_scope_json,
            content_type_scope_json=content_type_scope_json,
            objective_scope_json=objective_scope_json,
            estimated_effort=estimated_effort,
            estimated_duration_hours=estimated_duration_hours,
            assigned_capacity_units=assigned_capacity_units,
            confidence_level=confidence_level,
            source_fingerprint=source_fingerprint,
            created_at=_now(),
            updated_at=_now(),
        )
        saved = self._upsert("roadmap_items", item.to_dict())
        roadmap_item = _entity_from_row(RoadmapItem, saved, enum_fields={"item_type": RoadmapItemType, "status": RoadmapItemStatus})
        self._build_roadmap_item_metrics_and_risks(roadmap_item)
        return roadmap_item

    def _build_roadmap_item_metrics_and_risks(self, item: RoadmapItem) -> None:
        if item.confirmed_start and not item.tentative_start:
            self.create_roadmap_item_metric(
                roadmap_item_id=item.id,
                creator_id=item.creator_id,
                metric_role=MetricRole.PRIMARY,
                metric_key="publication_completion",
                availability_status=MetricAvailabilityStatus.MANUAL_IMPORT_REQUIRED,
                platform=None,
                measurement_window="local",
                target_direction="up",
            )
        if item.status == RoadmapItemStatus.BLOCKED:
            self.create_roadmap_item_risk(
                roadmap_item_id=item.id,
                creator_id=item.creator_id,
                risk_type=RiskType.SCHEDULE,
                severity=RiskSeverity.HIGH,
                description="Item bloqueado por estado.",
                blocking=True,
            )

    def list_roadmap_items(self, strategic_plan_id: str) -> list[RoadmapItem]:
        return self._list_entities("roadmap_items", RoadmapItem, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="sequence_order ASC, created_at ASC", enum_fields={"item_type": RoadmapItemType, "status": RoadmapItemStatus})

    def get_roadmap_item(self, item_id: str) -> RoadmapItem | None:
        return self._fetch_entity("roadmap_items", RoadmapItem, where="id = ?", params=(item_id,), enum_fields={"item_type": RoadmapItemType, "status": RoadmapItemStatus})

    def update_roadmap_item(self, item_id: str, **changes) -> RoadmapItem:
        item = self.get_roadmap_item(item_id)
        if item is None:
            raise StrategicPlanningNotFoundError("El roadmap item no existe.")
        if changes.get("confirmed_start") and not self.preferences.get("allow_automatic_confirmed_dates", False) and not item.confirmed_start:
            raise StrategicPlanningValidationError("Las fechas confirmadas solo pueden establecerse manualmente.")
        updated = replace(
            item,
            title=changes.get("title", item.title),
            description=changes.get("description", item.description),
            item_type=RoadmapItemType(changes.get("item_type", item.item_type.value)),
            status=RoadmapItemStatus(changes.get("status", item.status.value)),
            priority_level=_priority_value(changes.get("priority_level", item.priority_level)),
            sequence_order=int(changes.get("sequence_order", item.sequence_order)),
            tentative_start=changes.get("tentative_start", item.tentative_start),
            tentative_end=changes.get("tentative_end", item.tentative_end),
            confirmed_start=changes.get("confirmed_start", item.confirmed_start),
            confirmed_end=changes.get("confirmed_end", item.confirmed_end),
            platform_scope_json=changes.get("platform_scope_json", item.platform_scope_json),
            content_type_scope_json=changes.get("content_type_scope_json", item.content_type_scope_json),
            objective_scope_json=changes.get("objective_scope_json", item.objective_scope_json),
            estimated_effort=changes.get("estimated_effort", item.estimated_effort),
            estimated_duration_hours=changes.get("estimated_duration_hours", item.estimated_duration_hours),
            assigned_capacity_units=changes.get("assigned_capacity_units", item.assigned_capacity_units),
            confidence_level=changes.get("confidence_level", item.confidence_level),
            updated_at=_now(),
        )
        return _entity_from_row(RoadmapItem, self._upsert("roadmap_items", updated.to_dict()), enum_fields={"item_type": RoadmapItemType, "status": RoadmapItemStatus})

    def create_dependency(
        self,
        *,
        roadmap_item_id: str,
        depends_on_roadmap_item_id: str,
        dependency_type: str | DependencyType = DependencyType.FINISH_TO_START,
        blocking: bool = True,
        lag_days: int | None = None,
        reason: str,
    ) -> DependencyLink:
        item = self.get_roadmap_item(roadmap_item_id)
        other = self.get_roadmap_item(depends_on_roadmap_item_id)
        if item is None or other is None:
            raise StrategicPlanningNotFoundError("La dependencia apunta a un roadmap item inexistente.")
        if item.creator_id != other.creator_id:
            raise StrategicPlanningValidationError("No se permiten dependencias entre creadores.")
        if roadmap_item_id == depends_on_roadmap_item_id:
            raise StrategicPlanningValidationError("No se permite auto dependencia.")
        if self._dependency_path_exists(depends_on_roadmap_item_id, roadmap_item_id):
            raise StrategicPlanningValidationError("La dependencia crearia un ciclo.")
        dependency = DependencyLink(
            id=str(uuid4()),
            creator_id=item.creator_id,
            roadmap_item_id=roadmap_item_id,
            depends_on_roadmap_item_id=depends_on_roadmap_item_id,
            dependency_type=DependencyType(dependency_type) if not isinstance(dependency_type, DependencyType) else dependency_type,
            blocking=blocking,
            lag_days=lag_days,
            reason=reason,
            created_at=_now(),
        )
        return _entity_from_row(DependencyLink, self._upsert("roadmap_item_dependencies", dependency.to_dict()), enum_fields={"dependency_type": DependencyType})

    def _dependency_path_exists(self, start_item_id: str, target_item_id: str, visited: set[str] | None = None) -> bool:
        visited = visited or set()
        if start_item_id in visited:
            return False
        visited.add(start_item_id)
        for dependency in self.list_dependencies_for_item(start_item_id):
            if dependency.depends_on_roadmap_item_id == target_item_id:
                return True
            if self._dependency_path_exists(dependency.depends_on_roadmap_item_id, target_item_id, visited):
                return True
        return False

    def list_dependencies(self, strategic_plan_id: str) -> list[DependencyLink]:
        items = self.list_roadmap_items(strategic_plan_id)
        item_ids = {item.id for item in items}
        where = "roadmap_item_id IN ({})".format(",".join("?" for _ in item_ids)) if item_ids else "1 = 0"
        return self._list_entities("roadmap_item_dependencies", DependencyLink, where=where, params=tuple(item_ids), order_by="created_at ASC", enum_fields={"dependency_type": DependencyType})

    def list_dependencies_for_item(self, roadmap_item_id: str) -> list[DependencyLink]:
        return self._list_entities("roadmap_item_dependencies", DependencyLink, where="roadmap_item_id = ?", params=(roadmap_item_id,), order_by="created_at ASC", enum_fields={"dependency_type": DependencyType})

    def remove_dependency(self, dependency_id: str) -> bool:
        deleted = self.repository.delete_record("roadmap_item_dependencies", where="id = ?", params=(dependency_id,))
        return bool(deleted)

    def create_milestone(self, *, roadmap_item_id: str, title: str, milestone_type: str | MilestoneType = MilestoneType.CUSTOM, status: str = PlanStatus.DRAFT.value, description: str | None = None, target_date: str | None = None, completed_at: str | None = None) -> Milestone:
        item = self.get_roadmap_item(roadmap_item_id)
        if item is None:
            raise StrategicPlanningNotFoundError("El roadmap item no existe.")
        milestone = Milestone(
            id=str(uuid4()),
            creator_id=item.creator_id,
            roadmap_item_id=roadmap_item_id,
            title=title,
            description=description,
            milestone_type=MilestoneType(milestone_type) if not isinstance(milestone_type, MilestoneType) else milestone_type,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            target_date=target_date,
            completed_at=completed_at,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(Milestone, self._upsert("roadmap_item_milestones", milestone.to_dict()), enum_fields={"milestone_type": MilestoneType, "status": PlanStatus})

    def list_milestones(self, roadmap_item_id: str) -> list[Milestone]:
        return self._list_entities("roadmap_item_milestones", Milestone, where="roadmap_item_id = ?", params=(roadmap_item_id,), order_by="created_at ASC", enum_fields={"milestone_type": MilestoneType, "status": PlanStatus})

    def create_roadmap_item_metric(self, *, roadmap_item_id: str, creator_id: str, metric_role: str | MetricRole, metric_key: str, availability_status: str | MetricAvailabilityStatus, platform: str | None = None, internal_metric_key: str | None = None, measurement_window: str | None = None, target_direction: str | None = None) -> RoadmapItemMetric:
        metric = RoadmapItemMetric(
            id=str(uuid4()),
            creator_id=creator_id,
            roadmap_item_id=roadmap_item_id,
            metric_role=MetricRole(metric_role) if not isinstance(metric_role, MetricRole) else metric_role,
            platform=platform,
            metric_key=metric_key,
            internal_metric_key=internal_metric_key,
            measurement_window=measurement_window,
            target_direction=target_direction,
            availability_status=MetricAvailabilityStatus(availability_status) if not isinstance(availability_status, MetricAvailabilityStatus) else availability_status,
            created_at=_now(),
        )
        return _entity_from_row(RoadmapItemMetric, self._upsert("roadmap_item_metrics", metric.to_dict()), enum_fields={"metric_role": MetricRole, "availability_status": MetricAvailabilityStatus})

    def list_roadmap_item_metrics(self, roadmap_item_id: str) -> list[RoadmapItemMetric]:
        return self._list_entities("roadmap_item_metrics", RoadmapItemMetric, where="roadmap_item_id = ?", params=(roadmap_item_id,), order_by="created_at ASC", enum_fields={"metric_role": MetricRole, "availability_status": MetricAvailabilityStatus})

    def create_roadmap_item_risk(self, *, roadmap_item_id: str, creator_id: str, risk_type: str | RiskType, severity: str | RiskSeverity, description: str, blocking: bool, likelihood: str | None = None, impact: str | None = None, mitigation: str | None = None) -> RoadmapItemRisk:
        risk = RoadmapItemRisk(
            id=str(uuid4()),
            creator_id=creator_id,
            roadmap_item_id=roadmap_item_id,
            risk_type=RiskType(risk_type) if not isinstance(risk_type, RiskType) else risk_type,
            severity=RiskSeverity(severity) if not isinstance(severity, RiskSeverity) else severity,
            description=description,
            blocking=blocking,
            likelihood=likelihood,
            impact=impact,
            mitigation=mitigation,
            created_at=_now(),
        )
        return _entity_from_row(RoadmapItemRisk, self._upsert("roadmap_item_risks", risk.to_dict()), enum_fields={"risk_type": RiskType, "severity": RiskSeverity})

    def list_roadmap_item_risks(self, roadmap_item_id: str) -> list[RoadmapItemRisk]:
        return self._list_entities("roadmap_item_risks", RoadmapItemRisk, where="roadmap_item_id = ?", params=(roadmap_item_id,), order_by="created_at ASC", enum_fields={"risk_type": RiskType, "severity": RiskSeverity})

    def record_conflict(self, *, strategic_plan_id: str, conflict_type: str | ConflictType, severity: str, left_target_type: str, description: str, left_target_id: str | None = None, right_target_type: str | None = None, right_target_id: str | None = None, resolution_status: str | ConflictResolutionStatus = ConflictResolutionStatus.OPEN) -> PlanningConflict:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        conflict = PlanningConflict(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            conflict_type=ConflictType(conflict_type) if not isinstance(conflict_type, ConflictType) else conflict_type,
            severity=severity,
            left_target_type=left_target_type,
            left_target_id=left_target_id,
            right_target_type=right_target_type,
            right_target_id=right_target_id,
            description=description,
            resolution_status=ConflictResolutionStatus(resolution_status) if not isinstance(resolution_status, ConflictResolutionStatus) else resolution_status,
            created_at=_now(),
        )
        return _entity_from_row(PlanningConflict, self._upsert("planning_conflicts", conflict.to_dict()), enum_fields={"conflict_type": ConflictType, "resolution_status": ConflictResolutionStatus})

    def list_conflicts(self, strategic_plan_id: str) -> list[PlanningConflict]:
        return self._list_entities("planning_conflicts", PlanningConflict, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"conflict_type": ConflictType, "resolution_status": ConflictResolutionStatus})

    def create_scenario(self, *, strategic_plan_id: str, name: str, scenario_type: str | ScenarioType = ScenarioType.CUSTOM, description: str | None = None, assumptions_json: str = "[]", constraints_json: str = "[]", capacity_json: str = "{}", roadmap_summary_json: str = "[]", risk_summary_json: str = "[]", tradeoffs_json: str = "[]", status: str = PlanStatus.DRAFT.value, source_fingerprint: str | None = None) -> PlanningScenario:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        source_fingerprint = source_fingerprint or build_planning_fingerprint({
            "strategic_plan_id": strategic_plan_id,
            "name": name,
            "scenario_type": scenario_type.value if isinstance(scenario_type, ScenarioType) else str(scenario_type),
            "assumptions_json": assumptions_json,
            "constraints_json": constraints_json,
            "capacity_json": capacity_json,
            "roadmap_summary_json": roadmap_summary_json,
            "risk_summary_json": risk_summary_json,
            "tradeoffs_json": tradeoffs_json,
        })
        existing = self._fetch("planning_scenarios", where="strategic_plan_id = ? AND source_fingerprint = ?", params=(strategic_plan_id, source_fingerprint))
        if existing:
            return _entity_from_row(PlanningScenario, existing, enum_fields={"scenario_type": ScenarioType, "status": PlanStatus})
        scenario = PlanningScenario(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            name=name,
            description=description,
            scenario_type=scenario_type.value if isinstance(scenario_type, ScenarioType) else ScenarioType(scenario_type).value,
            status=PlanStatus(status) if not isinstance(status, PlanStatus) else status,
            assumptions_json=assumptions_json,
            constraints_json=constraints_json,
            capacity_json=capacity_json,
            roadmap_summary_json=roadmap_summary_json,
            risk_summary_json=risk_summary_json,
            tradeoffs_json=tradeoffs_json,
            source_fingerprint=source_fingerprint,
            created_at=_now(),
            updated_at=_now(),
        )
        return _entity_from_row(PlanningScenario, self._upsert("planning_scenarios", scenario.to_dict()), enum_fields={"scenario_type": ScenarioType, "status": PlanStatus})

    def list_scenarios(self, strategic_plan_id: str) -> list[PlanningScenario]:
        return self._list_entities("planning_scenarios", PlanningScenario, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC", enum_fields={"scenario_type": ScenarioType, "status": PlanStatus})

    def create_snapshot(self, *, strategic_plan_id: str, snapshot_type: str, plan_version: int, snapshot_json: str, source_fingerprint: str) -> PlanningSnapshot:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        snapshot = PlanningSnapshot(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            snapshot_type=snapshot_type,
            plan_version=plan_version,
            source_fingerprint=source_fingerprint,
            snapshot_json=snapshot_json,
            created_at=_now(),
        )
        existing = self._fetch("planning_snapshots", where="source_fingerprint = ?", params=(source_fingerprint,))
        if existing:
            return _entity_from_row(PlanningSnapshot, existing)
        return _entity_from_row(PlanningSnapshot, self._upsert("planning_snapshots", snapshot.to_dict()))

    def list_snapshots(self, strategic_plan_id: str) -> list[PlanningSnapshot]:
        return self._list_entities("planning_snapshots", PlanningSnapshot, where="strategic_plan_id = ?", params=(strategic_plan_id,), order_by="created_at DESC")

    def create_report(self, *, strategic_plan_id: str | None, creator_id: str, report_type: str, report_json: str, source_fingerprint: str, period_start: str | None = None, period_end: str | None = None) -> PlanningReport:
        report = PlanningReport(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_plan_id=strategic_plan_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            source_fingerprint=source_fingerprint,
            report_json=report_json,
            created_at=_now(),
        )
        existing = self._fetch("planning_reports", where="source_fingerprint = ?", params=(source_fingerprint,))
        if existing:
            return _entity_from_row(PlanningReport, existing)
        return _entity_from_row(PlanningReport, self._upsert("planning_reports", report.to_dict()))

    def list_reports(self, creator_id: str) -> list[PlanningReport]:
        return self._list_entities("planning_reports", PlanningReport, where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def get_report(self, report_id: str) -> PlanningReport | None:
        return self._fetch_entity("planning_reports", PlanningReport, where="id = ?", params=(report_id,))

    def get_report_by_fingerprint(self, source_fingerprint: str) -> PlanningReport | None:
        return self._fetch_entity("planning_reports", PlanningReport, where="source_fingerprint = ?", params=(source_fingerprint,))

    def link_content_item(self, *, strategic_plan_id: str, creator_id: str, target_type: str, target_id: str, internal_content_id: str) -> ContentLibraryLink:
        existing = self._fetch(
            "planning_content_links",
            where="strategic_plan_id = ? AND target_type = ? AND target_id = ? AND internal_content_id = ?",
            params=(strategic_plan_id, target_type, target_id, internal_content_id),
        )
        if existing is not None:
            return _entity_from_row(ContentLibraryLink, existing)
        link = ContentLibraryLink(
            id=str(uuid4()),
            creator_id=creator_id,
            strategic_plan_id=strategic_plan_id,
            target_type=target_type,
            target_id=target_id,
            internal_content_id=internal_content_id,
            created_at=_now(),
        )
        return _entity_from_row(ContentLibraryLink, self._upsert("planning_content_links", link.to_dict()))

    def build_overview(self, strategic_plan_id: str) -> dict[str, object]:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        objectives = self.list_objectives(strategic_plan_id)
        initiatives = self.list_initiatives(strategic_plan_id)
        roadmap_items = self.list_roadmap_items(strategic_plan_id)
        backlog_items = self.list_backlog_items(strategic_plan_id)
        conflicts = self.list_conflicts(strategic_plan_id)
        capacity = self.calculate_capacity_load(strategic_plan_id)
        expiring = [item.to_dict() for item in backlog_items if item.expires_at]
        return {
            "creator_id": plan.creator_id,
            "plan": plan.to_dict(),
            "version": plan.version,
            "horizon": plan.horizon_type.value,
            "objectives": len(objectives),
            "initiatives": len(initiatives),
            "roadmap_items": len(roadmap_items),
            "backlog_items": len(backlog_items),
            "current_capacity": capacity,
            "planned_load": capacity.get("planned_capacity", 0),
            "overload": capacity.get("status") == "overloaded",
            "blocked_items": sum(1 for item in roadmap_items if item.status == RoadmapItemStatus.BLOCKED),
            "expiring_opportunities": len(expiring),
            "unresolved_conflicts": sum(1 for conflict in conflicts if conflict.resolution_status != ConflictResolutionStatus.RESOLVED),
            "next_review": plan.updated_at,
            "plan_freshness": self._plan_freshness(plan),
        }

    def _plan_freshness(self, plan: PlanningPlan) -> str:
        return FreshnessStatus.RECENT.value if plan.status in {PlanStatus.DRAFT, PlanStatus.NEEDS_REVIEW, PlanStatus.APPROVED, PlanStatus.ACTIVE} else FreshnessStatus.UNKNOWN.value

    def calculate_capacity_load(self, strategic_plan_id: str) -> dict[str, object]:
        profiles = self.list_capacity_profiles(strategic_plan_id=strategic_plan_id)
        active_profile = next((profile for profile in profiles if profile.status == CapacityProfileStatus.ACTIVE), None)
        roadmap_items = self.list_roadmap_items(strategic_plan_id)
        planned_capacity = sum(float(item.assigned_capacity_units or 0) for item in roadmap_items if item.status not in {RoadmapItemStatus.CANCELLED, RoadmapItemStatus.ARCHIVED})
        confirmed_capacity = sum(float(item.assigned_capacity_units or 0) for item in roadmap_items if item.confirmed_start and item.confirmed_end)
        available_capacity = active_profile.available_capacity_units if active_profile and active_profile.available_capacity_units is not None else active_profile.available_hours if active_profile else None
        buffer = None
        if available_capacity is not None:
            buffer = float(available_capacity) * float(self.preferences.get("capacity_buffer_percentage", 0.15))
        status = "unknown"
        if available_capacity is not None:
            if planned_capacity > float(available_capacity):
                status = "overloaded"
            elif planned_capacity >= float(available_capacity) * float(self.preferences.get("overload_warning_threshold", 0.85)):
                status = "near_capacity"
            else:
                status = "balanced"
        return {
            "available_capacity": available_capacity,
            "planned_capacity": planned_capacity,
            "confirmed_capacity": confirmed_capacity,
            "active_load": confirmed_capacity,
            "blocked_load": sum(float(item.assigned_capacity_units or 0) for item in roadmap_items if item.status == RoadmapItemStatus.BLOCKED),
            "buffer": buffer,
            "overload": None if available_capacity is None else planned_capacity > float(available_capacity),
            "status": status,
            "by_cycle": {cycle.id: sum(float(item.assigned_capacity_units or 0) for item in roadmap_items if item.planning_cycle_id == cycle.id) for cycle in self.list_cycles(strategic_plan_id)},
            "by_platform": {},
            "by_content_type": {},
            "by_initiative": {},
            "by_resource": {},
        }

    def create_feasibility_report(self, *, strategic_plan_id: str, target_type: str, target_id: str, reason: str, constraints_json: str | None = None, warnings_json: str | None = None, status: FeasibilityStatus = FeasibilityStatus.UNKNOWN) -> FeasibilityReport:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        report = FeasibilityReport(
            id=str(uuid4()),
            creator_id=plan.creator_id,
            strategic_plan_id=strategic_plan_id,
            target_type=target_type,
            target_id=target_id,
            status=status,
            reason=reason,
            constraints_json=constraints_json,
            warnings_json=warnings_json,
            created_at=_now(),
        )
        return report

    def evaluate_feasibility(self, roadmap_item_id: str) -> FeasibilityReport:
        item = self.get_roadmap_item(roadmap_item_id)
        if item is None:
            raise StrategicPlanningNotFoundError("El roadmap item no existe.")
        plan = self.get_plan(item.strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        load = self.calculate_capacity_load(plan.id)
        status = FeasibilityStatus.FEASIBLE
        reason = "feasible"
        if load["status"] == "overloaded":
            status = FeasibilityStatus.BLOCKED if item.status == RoadmapItemStatus.BLOCKED else FeasibilityStatus.FEASIBLE_WITH_CONSTRAINTS
            reason = "overload"
        if self.list_dependencies_for_item(item.id):
            status = FeasibilityStatus.FEASIBLE_WITH_CONSTRAINTS if status == FeasibilityStatus.FEASIBLE else status
            reason = "dependencies"
        return self.create_feasibility_report(strategic_plan_id=plan.id, target_type="roadmap_item", target_id=item.id, reason=reason, constraints_json=_json_dumps(load), status=status)

    def _detect_objective_conflicts(self, strategic_plan_id: str) -> None:
        objectives = self.list_objectives(strategic_plan_id)
        if len(objectives) < 2:
            return
        seen_pairs: set[tuple[str, str]] = set()
        for left in objectives:
            for right in objectives:
                if left.id >= right.id:
                    continue
                pair = (left.objective_type.value, right.objective_type.value)
                if pair in seen_pairs:
                    continue
                if self._is_objective_conflict(pair[0], pair[1]):
                    self.record_conflict(
                        strategic_plan_id=strategic_plan_id,
                        conflict_type=ConflictType.OBJECTIVE_CONFLICT,
                        severity="medium",
                        left_target_type="objective",
                        left_target_id=left.id,
                        right_target_type="objective",
                        right_target_id=right.id,
                        description=f"Conflicto entre {left.objective_type.value} y {right.objective_type.value}.",
                        resolution_status=ConflictResolutionStatus.OPEN,
                    )
                    seen_pairs.add(pair)

    def _is_objective_conflict(self, left: str, right: str) -> bool:
        conflicts = {
            ("reach", "brand_consistency"),
            ("frequency", "sustainable_frequency"),
            ("experimentation", "stability"),
            ("short_term_trend", "evergreen"),
            ("multi_platform_expansion", "limited_capacity"),
            ("audience_growth", "audience_depth"),
            ("aggressive_packaging", "creator_identity"),
        }
        normalized = {left, right}
        return any(normalized == {a, b} for a, b in conflicts)

    def intake_recommendation(
        self,
        *,
        strategic_plan_id: str,
        recommendation_id: str,
        intake_status: str = "approved",
        reason: str = "",
        create_backlog_if_not_scheduled: bool = True,
    ) -> dict[str, object]:
        plan = self.get_plan(strategic_plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        recommendation = None
        if self.recommendation_service is not None:
            recommendation = self._safe_call(self.recommendation_service, ("get_recommendation", "show_recommendation"), recommendation_id)
        if recommendation is None:
            raise StrategicPlanningNotFoundError("La recomendacion no existe.")
        recommendation_payload = recommendation.to_dict() if hasattr(recommendation, "to_dict") else dict(recommendation)
        status = str(recommendation_payload.get("status") or "")
        if status in {"blocked", "expired"}:
            if create_backlog_if_not_scheduled:
                backlog = self.create_backlog_item(
                    strategic_plan_id=strategic_plan_id,
                    source_type=SourceType.RECOMMENDATION,
                    source_id=recommendation_id,
                    title=str(recommendation_payload.get("title") or "Recommendation"),
                    backlog_type=BacklogType.RECOMMENDATION,
                    status=BacklogStatus.ACTIVE.value,
                    priority_level=str(recommendation_payload.get("priority_level") or "medium"),
                    description=str(recommendation_payload.get("summary") or ""),
                    reason_not_scheduled=f"recommendation_{status}",
                )
                return {"recommendation": recommendation_payload, "backlog_item": backlog.to_dict(), "status": status}
            return {"recommendation": recommendation_payload, "status": status}
        if status == "rejected":
            return {"recommendation": recommendation_payload, "status": status, "converted": False}
        initiative = None
        if intake_status in {"approved", "deferred", "needs_more_data"}:
            initiative = self.create_initiative(
                strategic_plan_id=strategic_plan_id,
                title=str(recommendation_payload.get("title") or "Recommendation"),
                initiative_type=InitiativeType.CONTENT_PROGRAM,
                status=PlanStatus.DRAFT.value,
                priority_level=str(recommendation_payload.get("priority_level") or "medium"),
                expected_impact="unknown",
                expected_learning_value="unknown",
                confidence_level=str(recommendation_payload.get("confidence_level") or "medium"),
                effort_level="unknown",
                risk_level="medium",
                strategic_objective_id=plan.primary_objective_id,
                recommendation_candidate_id=recommendation_id,
                description=reason or str(recommendation_payload.get("summary") or ""),
            )
        backlog_item = None
        if create_backlog_if_not_scheduled and initiative is None:
            backlog_item = self.create_backlog_item(
                strategic_plan_id=strategic_plan_id,
                source_type=SourceType.RECOMMENDATION,
                source_id=recommendation_id,
                title=str(recommendation_payload.get("title") or "Recommendation"),
                backlog_type=BacklogType.RECOMMENDATION,
                description=str(recommendation_payload.get("summary") or ""),
                priority_level=str(recommendation_payload.get("priority_level") or "medium"),
                reason_not_scheduled=reason or "deferred",
            )
        roadmap_item = None
        if initiative and intake_status == "approved":
            roadmap_item = self.add_roadmap_item(
                strategic_plan_id=strategic_plan_id,
                title=str(recommendation_payload.get("title") or "Recommendation"),
                item_type=RoadmapItemType.EXPERIMENT if recommendation_payload.get("experiment_id") else RoadmapItemType.CONTENT_CONCEPT,
                status=RoadmapItemStatus.NEEDS_REVIEW.value,
                priority_level=str(recommendation_payload.get("priority_level") or "medium"),
                strategic_initiative_id=initiative.id,
                recommendation_candidate_id=recommendation_id,
                description=reason or str(recommendation_payload.get("summary") or ""),
                source_fingerprint=build_planning_fingerprint({"recommendation_id": recommendation_id, "plan_id": strategic_plan_id}),
            )
        return {
            "recommendation": recommendation_payload,
            "initiative": None if initiative is None else initiative.to_dict(),
            "backlog_item": None if backlog_item is None else backlog_item.to_dict(),
            "roadmap_item": None if roadmap_item is None else roadmap_item.to_dict(),
            "status": status,
        }

    def build_portfolio_balance(self, strategic_plan_id: str) -> dict[str, object]:
        roadmap_items = self.list_roadmap_items(strategic_plan_id)
        counts = {
            "evergreen": sum(1 for item in roadmap_items if item.item_type in {RoadmapItemType.CONTENT_CONCEPT, RoadmapItemType.CONTENT_PROJECT}),
            "trend": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.EXPERIMENT),
            "experimental": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.EXPERIMENT),
            "proven": sum(1 for item in roadmap_items if item.status == RoadmapItemStatus.SCHEDULED_CONFIRMED),
            "community": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.AUDIENCE_ACTIVITY),
            "discovery": sum(1 for item in roadmap_items if item.priority_level in {"high", "critical"}),
            "retention": sum(1 for item in roadmap_items if item.item_type in {RoadmapItemType.MEASUREMENT, RoadmapItemType.STRATEGIC_REVIEW}),
            "search": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.MARKET_REVIEW),
            "longform": 0,
            "shortform": 0,
            "platform_native": 0,
            "repurposed": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.REPURPOSE),
            "low_effort": sum(1 for item in roadmap_items if (item.estimated_duration_hours or 0) <= 2),
            "high_effort": sum(1 for item in roadmap_items if (item.estimated_duration_hours or 0) >= 6),
            "low_risk": sum(1 for item in roadmap_items if item.status != RoadmapItemStatus.BLOCKED),
            "high_learning_value": sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.EXPERIMENT),
        }
        return {
            "creator_id": roadmap_items[0].creator_id if roadmap_items else None,
            "items": counts,
            "warnings": self._portfolio_warnings(roadmap_items),
            "configurable_rules": dict(self.preferences),
        }

    def _portfolio_warnings(self, roadmap_items: list[RoadmapItem]) -> list[str]:
        warnings: list[str] = []
        if not roadmap_items:
            return warnings
        platforms = [item.platform_scope_json for item in roadmap_items if item.platform_scope_json]
        if len(platforms) == len(roadmap_items):
            warnings.append("platform_scope_present")
        if any(item.status == RoadmapItemStatus.BLOCKED for item in roadmap_items):
            warnings.append("blocked_items_present")
        if sum(1 for item in roadmap_items if item.item_type == RoadmapItemType.EXPERIMENT) > 3:
            warnings.append("over_experimentation")
        return warnings

    def build_dependency_graph(self, strategic_plan_id: str) -> dict[str, object]:
        items = self.list_roadmap_items(strategic_plan_id)
        dependencies = self.list_dependencies(strategic_plan_id)
        cycle = self._detect_dependency_cycle(items, dependencies)
        return {
            "items": [item.to_dict() for item in items],
            "dependencies": [dependency.to_dict() for dependency in dependencies],
            "cycle_detected": cycle,
            "blocking": sum(1 for dependency in dependencies if dependency.blocking),
            "missing_dependency": False,
            "self_dependency": any(dependency.roadmap_item_id == dependency.depends_on_roadmap_item_id for dependency in dependencies),
            "cross_creator_dependency": False,
            "blocked_dependency": any(dependency.blocking for dependency in dependencies),
            "impossible_date_order": False,
        }

    def _detect_dependency_cycle(self, items: list[RoadmapItem], dependencies: list[DependencyLink]) -> bool:
        adjacency: dict[str, set[str]] = {}
        for dependency in dependencies:
            adjacency.setdefault(dependency.roadmap_item_id, set()).add(dependency.depends_on_roadmap_item_id)
        visited: set[str] = set()
        stack: set[str] = set()

        def visit(node: str) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for neighbour in adjacency.get(node, set()):
                if visit(neighbour):
                    return True
            stack.remove(node)
            return False

        return any(visit(item.id) for item in items)

    def calculate_critical_path(self, strategic_plan_id: str) -> dict[str, object]:
        items = self.list_roadmap_items(strategic_plan_id)
        dependencies = self.list_dependencies(strategic_plan_id)
        durations = {item.id: float(item.estimated_duration_hours or 0) for item in items}
        adjacency: dict[str, set[str]] = {}
        indegree: dict[str, int] = {item.id: 0 for item in items}
        for dependency in dependencies:
            adjacency.setdefault(dependency.depends_on_roadmap_item_id, set()).add(dependency.roadmap_item_id)
            indegree[dependency.roadmap_item_id] = indegree.get(dependency.roadmap_item_id, 0) + 1
        queue = [item_id for item_id, degree in indegree.items() if degree == 0]
        order: list[str] = []
        longest: dict[str, float] = {item_id: durations.get(item_id, 0) for item_id in queue}
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbour in adjacency.get(node, set()):
                longest[neighbour] = max(longest.get(neighbour, 0), longest.get(node, 0) + durations.get(neighbour, 0))
                indegree[neighbour] -= 1
                if indegree[neighbour] == 0:
                    queue.append(neighbour)
        return {
            "estimated": True,
            "order": order,
            "longest_path": max(longest.values()) if longest else 0,
            "durations": durations,
        }

    def build_scenario(self, strategic_plan_id: str, scenario_type: str | ScenarioType) -> PlanningScenario:
        items = self.list_roadmap_items(strategic_plan_id)
        capacity = self.calculate_capacity_load(strategic_plan_id)
        included = [item.id for item in items]
        excluded: list[str] = []
        if ScenarioType(scenario_type) == ScenarioType.LOW_CAPACITY:
            included = included[: max(1, len(included) // 2)]
            excluded = [item.id for item in items if item.id not in included]
        elif ScenarioType(scenario_type) == ScenarioType.SINGLE_PLATFORM:
            included = [item.id for item in items if item.platform_scope_json is not None][: max(1, len(items) // 2)]
            excluded = [item.id for item in items if item.id not in included]
        payload = {
            "assumptions": self.preferences,
            "capacity": capacity,
            "included_items": included,
            "excluded_items": excluded,
            "objectives": [objective.id for objective in self.list_objectives(strategic_plan_id)],
            "risks": [risk.to_dict() for item in items for risk in self.list_roadmap_item_risks(item.id)],
            "tradeoffs": ["capacity_vs_scope", "learning_vs_stability"] if included else [],
            "expected_learning": "qualitative",
            "unresolved_conflicts": [conflict.id for conflict in self.list_conflicts(strategic_plan_id) if conflict.resolution_status != ConflictResolutionStatus.RESOLVED],
        }
        scenario = self.create_scenario(
            strategic_plan_id=strategic_plan_id,
            name=ScenarioType(scenario_type).value,
            scenario_type=scenario_type,
            assumptions_json=_json_dumps(self.preferences),
            constraints_json=_json_dumps([constraint.to_dict() for constraint in self.list_resource_constraints(strategic_plan_id)]),
            capacity_json=_json_dumps(capacity),
            roadmap_summary_json=_json_dumps(included),
            risk_summary_json=_json_dumps(payload["risks"]),
            tradeoffs_json=_json_dumps(payload["tradeoffs"]),
            status=PlanStatus.DRAFT.value,
            description="scenario_local",
            source_fingerprint=build_planning_fingerprint(payload),
        )
        return scenario

    def compare_scenarios(self, left_id: str, right_id: str) -> dict[str, object]:
        left = self._fetch_entity("planning_scenarios", PlanningScenario, where="id = ?", params=(left_id,), enum_fields={"scenario_type": ScenarioType, "status": PlanStatus})
        right = self._fetch_entity("planning_scenarios", PlanningScenario, where="id = ?", params=(right_id,), enum_fields={"scenario_type": ScenarioType, "status": PlanStatus})
        if left is None or right is None:
            raise StrategicPlanningNotFoundError("Uno de los escenarios no existe.")
        return {
            "left": left.to_dict(),
            "right": right.to_dict(),
            "tradeoffs": ["load", "risk", "scope"],
            "preferred": None,
        }

    def list_tasks(self, creator_id: str) -> list[PlanningTask]:
        tasks: list[PlanningTask] = []
        for plan in self.list_plans(creator_id):
            tasks.append(
                PlanningTask(
                    id=f"planning-run-{plan.id}",
                    creator_id=creator_id,
                    plan_id=plan.id,
                    version=plan.version,
                    current_stage="idle",
                    progress_percent=0.0,
                    status=PlanningRunStatus.COMPLETED,
                    created_at=plan.created_at,
                    updated_at=plan.updated_at,
                    horizon=plan.horizon_type.value,
                    recommendations_processed=len(self._recommendation_payload(creator_id).get("items", [])),
                    initiatives=len(self.list_initiatives(plan.id)),
                    roadmap_items=len(self.list_roadmap_items(plan.id)),
                    backlog_items=len(self.list_backlog_items(plan.id)),
                    conflicts=len(self.list_conflicts(plan.id)),
                    overload=self.calculate_capacity_load(plan.id).get("status") == "overloaded",
                    warnings=None,
                    errors=None,
                    payload_json=_json_dumps({"plan_id": plan.id, "version": plan.version}),
                    open_result=plan.id,
                )
            )
        return tasks

    def mark_run_interrupted(self, plan_id: str) -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        if plan.status != PlanStatus.ACTIVE:
            return plan
        return self.update_plan(plan_id, status=PlanStatus.PAUSED.value)

    def resume_run(self, plan_id: str) -> PlanningPlan:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise StrategicPlanningNotFoundError("El plan no existe.")
        if plan.status not in {PlanStatus.PAUSED, PlanStatus.NEEDS_REVIEW, PlanStatus.DRAFT}:
            return plan
        return self.update_plan(plan_id, status=PlanStatus.NEEDS_REVIEW.value)

    def build_report(
        self,
        *,
        strategic_plan_id: str | None,
        creator_id: str,
        report_type: str,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> PlanningReport:
        plan = self.get_plan(strategic_plan_id) if strategic_plan_id else None
        payload = {
            "creator_id": creator_id,
            "plan": None if plan is None else plan.to_dict(),
            "version": None if plan is None else plan.version,
            "horizon": None if plan is None else plan.horizon_type.value,
            "period_start": period_start,
            "period_end": period_end,
            "context_snapshot": None if plan is None else self.get_context_snapshot(plan.context_snapshot_id).to_dict() if self.get_context_snapshot(plan.context_snapshot_id) else None,
            "objectives": [] if plan is None else [objective.to_dict() for objective in self.list_objectives(plan.id)],
            "initiatives": [] if plan is None else [initiative.to_dict() for initiative in self.list_initiatives(plan.id)],
            "roadmap_items": [] if plan is None else [item.to_dict() for item in self.list_roadmap_items(plan.id)],
            "backlog_items": [] if plan is None else [item.to_dict() for item in self.list_backlog_items(plan.id)],
            "capacity": {} if plan is None else self.calculate_capacity_load(plan.id),
            "dependencies": [] if plan is None else [dependency.to_dict() for dependency in self.list_dependencies(plan.id)],
            "risks": [] if plan is None else [risk.to_dict() for item in self.list_roadmap_items(plan.id) for risk in self.list_roadmap_item_risks(item.id)],
            "conflicts": [] if plan is None else [conflict.to_dict() for conflict in self.list_conflicts(plan.id)],
            "limitations": ["local_only", "no_llm", "no_ml", "no_external_calendar"],
            "review_date": None if plan is None else plan.updated_at,
        }
        fingerprint = build_planning_fingerprint(payload)
        existing = self.get_report_by_fingerprint(fingerprint)
        if existing:
            return existing
        report = self.create_report(
            strategic_plan_id=None if plan is None else plan.id,
            creator_id=creator_id,
            report_type=report_type,
            report_json=_json_dumps(payload),
            source_fingerprint=fingerprint,
            period_start=period_start,
            period_end=period_end,
        )
        return report

    def export_report(self, report_id: str, format_name: str) -> Path:
        report = self.get_report(report_id)
        if report is None:
            raise StrategicPlanningNotFoundError("El reporte no existe.")
        destination = self._reports_root / f"{report.id}.{format_name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(report.report_json)
        if format_name == "json":
            destination.write_text(report.report_json, encoding="utf-8")
        elif format_name == "txt":
            lines = [
                f"Report type: {payload.get('report_type', '')}",
                f"Creator: {payload.get('creator_id', '')}",
                f"Plan: {payload.get('plan', {}).get('name', '') if isinstance(payload.get('plan'), dict) else ''}",
            ]
            destination.write_text("\n".join(lines), encoding="utf-8")
        elif format_name == "csv":
            with destination.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["id", "title", "status", "priority"])
                for item in _safe_list(payload.get("roadmap_items", [])):
                    if not isinstance(item, dict):
                        continue
                    writer.writerow([
                        _safe_csv_value(item.get("id")),
                        _safe_csv_value(item.get("title")),
                        _safe_csv_value(item.get("status")),
                        _safe_csv_value(item.get("priority_level")),
                    ])
        else:
            raise StrategicPlanningValidationError("Formato de exportacion no soportado.")
        return destination

    def ingest_recommendation(self, strategic_plan_id: str, recommendation_id: str, *, intake_status: str = "approved", reason: str = "") -> dict[str, object]:
        return self.intake_recommendation(strategic_plan_id=strategic_plan_id, recommendation_id=recommendation_id, intake_status=intake_status, reason=reason)


def build_strategic_planning_service(
    *,
    settings: AppSettings | None,
    paths: ProjectPaths,
    repository: StrategicPlanningRepository,
    recommendation_service: Any | None = None,
    creator_memory_service: Any | None = None,
    creator_language_service: Any | None = None,
    creator_context_assembly_service: CreatorContextAssemblyService | None = None,
    audience_service: Any | None = None,
    analytics_service: Any | None = None,
    analytics_lab_service: Any | None = None,
    market_service: Any | None = None,
    experiment_service: Any | None = None,
    content_library_service: Any | None = None,
    platform_service: Any | None = None,
    creator_context_policy_registry: CreatorContextPolicyRegistry | None = None,
    preferences: dict[str, object] | None = None,
    logger: logging.Logger | None = None,
) -> StrategicPlanningService:
    return StrategicPlanningService(
        settings=settings,
        paths=paths,
        repository=repository,
        recommendation_service=recommendation_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        creator_context_assembly_service=creator_context_assembly_service,
        creator_context_policy_registry=creator_context_policy_registry,
        audience_service=audience_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        market_service=market_service,
        experiment_service=experiment_service,
        content_library_service=content_library_service,
        platform_service=platform_service,
        preferences=preferences,
        logger=logger,
    )
