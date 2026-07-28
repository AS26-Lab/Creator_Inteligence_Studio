"""Entidades persistidas para Strategic Planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .value_objects import (
    BacklogStatus,
    BacklogType,
    CampaignType,
    CapacityAllocationStatus,
    CapacityProfileStatus,
    ConflictResolutionStatus,
    ConflictType,
    CycleType,
    DependencyType,
    FeasibilityStatus,
    FreshnessStatus,
    HorizonType,
    InitiativeType,
    LifecycleStatus,
    MetricAvailabilityStatus,
    MetricRole,
    MilestoneType,
    ObjectiveType,
    PlanningRunStatus,
    PlanStatus,
    PriorityLevel,
    ResourceConstraintType,
    ReviewDecision,
    ReviewType,
    RiskSeverity,
    RiskType,
    ScenarioType,
    SeriesType,
    SourceType,
    StrategyThemeType,
    ContentPillarStatus,
    RoadmapItemStatus,
    RoadmapItemType,
)


def _to_dict(instance: object) -> dict[str, object]:
    payload = asdict(instance)
    for key, value in list(payload.items()):
        if hasattr(value, "value"):
            payload[key] = value.value
    return payload


@dataclass(frozen=True, slots=True)
class PlanningContextSnapshot:
    id: str
    creator_id: str
    context_version: str
    source_fingerprint: str
    context_json: str
    created_at: str
    recommendation_snapshot_id: str | None = None
    creator_memory_snapshot_id: str | None = None
    creator_language_snapshot_id: str | None = None
    audience_snapshot_id: str | None = None
    analytics_snapshot_id: str | None = None
    market_snapshot_id: str | None = None
    experiment_snapshot_id: str | None = None
    content_library_snapshot_id: str | None = None
    platform_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningPlan:
    id: str
    creator_id: str
    name: str
    status: PlanStatus
    horizon_type: HorizonType
    context_snapshot_id: str
    version: int
    created_at: str
    updated_at: str
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    timezone: str | None = None
    primary_objective_id: str | None = None
    parent_plan_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class StrategicObjective:
    id: str
    creator_id: str
    strategic_plan_id: str
    objective_type: ObjectiveType
    title: str
    priority_level: str
    status: LifecycleStatus
    confidence_level: str
    source_type: SourceType
    created_at: str
    updated_at: str
    description: str | None = None
    target_direction: str | None = None
    baseline_json: str | None = None
    target_json: str | None = None
    measurement_window: str | None = None
    source_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class StrategicObjectiveMetric:
    id: str
    creator_id: str
    strategic_objective_id: str
    metric_role: MetricRole
    metric_key: str
    availability_status: MetricAvailabilityStatus
    created_at: str
    platform: str | None = None
    internal_metric_key: str | None = None
    unit: str | None = None
    period_semantics: str | None = None
    baseline_value: str | None = None
    target_value: str | None = None
    target_method: str | None = None
    measurement_window: str | None = None
    source_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class StrategyTheme:
    id: str
    creator_id: str
    strategic_plan_id: str
    name: str
    theme_type: StrategyThemeType
    status: LifecycleStatus
    priority_level: str
    rationale: str
    source_fingerprint: str
    created_at: str
    updated_at: str
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ContentPillar:
    id: str
    creator_id: str
    strategic_plan_id: str
    name: str
    status: ContentPillarStatus
    rationale: str
    created_at: str
    updated_at: str
    strategy_theme_id: str | None = None
    description: str | None = None
    purpose: str | None = None
    audience_scope_json: str | None = None
    platform_scope_json: str | None = None
    content_type_scope_json: str | None = None
    target_mix_percentage: float | None = None
    minimum_mix_percentage: float | None = None
    maximum_mix_percentage: float | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class Initiative:
    id: str
    creator_id: str
    strategic_plan_id: str
    title: str
    initiative_type: InitiativeType
    status: PlanStatus
    priority_level: str
    expected_impact: str
    expected_learning_value: str
    confidence_level: str
    effort_level: str
    risk_level: str
    created_at: str
    updated_at: str
    strategic_objective_id: str | None = None
    content_pillar_id: str | None = None
    recommendation_candidate_id: str | None = None
    experiment_id: str | None = None
    description: str | None = None
    start_window: str | None = None
    end_window: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class Campaign:
    id: str
    creator_id: str
    strategic_plan_id: str
    name: str
    campaign_type: CampaignType
    status: PlanStatus
    created_at: str
    updated_at: str
    strategic_initiative_id: str | None = None
    description: str | None = None
    platform_scope_json: str | None = None
    audience_scope_json: str | None = None
    objective_scope_json: str | None = None
    start_window: str | None = None
    end_window: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ContentSeries:
    id: str
    creator_id: str
    strategic_plan_id: str
    name: str
    series_type: SeriesType
    status: PlanStatus
    success_criteria_json: str
    stop_criteria_json: str
    created_at: str
    updated_at: str
    strategic_initiative_id: str | None = None
    campaign_id: str | None = None
    description: str | None = None
    platform_scope_json: str | None = None
    content_type_scope_json: str | None = None
    planned_episode_count: int | None = None
    minimum_episode_count: int | None = None
    maximum_episode_count: int | None = None
    cadence_type: str | None = None
    cadence_value: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningCycle:
    id: str
    creator_id: str
    strategic_plan_id: str
    cycle_type: CycleType
    name: str
    start_date: str
    end_date: str
    status: PlanStatus
    locked: bool
    created_at: str
    updated_at: str
    review_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RoadmapItem:
    id: str
    creator_id: str
    strategic_plan_id: str
    item_type: RoadmapItemType
    title: str
    status: RoadmapItemStatus
    priority_level: str
    sequence_order: int
    source_fingerprint: str
    created_at: str
    updated_at: str
    planning_cycle_id: str | None = None
    strategic_initiative_id: str | None = None
    campaign_id: str | None = None
    content_series_id: str | None = None
    recommendation_candidate_id: str | None = None
    experiment_id: str | None = None
    internal_content_id: str | None = None
    description: str | None = None
    tentative_start: str | None = None
    tentative_end: str | None = None
    confirmed_start: str | None = None
    confirmed_end: str | None = None
    platform_scope_json: str | None = None
    content_type_scope_json: str | None = None
    objective_scope_json: str | None = None
    estimated_effort: str | None = None
    estimated_duration_hours: float | None = None
    assigned_capacity_units: float | None = None
    confidence_level: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class DependencyLink:
    id: str
    creator_id: str
    roadmap_item_id: str
    depends_on_roadmap_item_id: str
    dependency_type: DependencyType
    blocking: bool
    reason: str
    created_at: str
    lag_days: int | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class Milestone:
    id: str
    creator_id: str
    roadmap_item_id: str
    title: str
    milestone_type: MilestoneType
    status: PlanStatus
    created_at: str
    updated_at: str
    description: str | None = None
    target_date: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RoadmapItemMetric:
    id: str
    creator_id: str
    roadmap_item_id: str
    metric_role: MetricRole
    metric_key: str
    availability_status: MetricAvailabilityStatus
    created_at: str
    platform: str | None = None
    internal_metric_key: str | None = None
    measurement_window: str | None = None
    target_direction: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class RoadmapItemRisk:
    id: str
    creator_id: str
    roadmap_item_id: str
    risk_type: RiskType
    severity: RiskSeverity
    description: str
    blocking: bool
    created_at: str
    likelihood: str | None = None
    impact: str | None = None
    mitigation: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningBacklogItem:
    id: str
    creator_id: str
    strategic_plan_id: str
    source_type: SourceType
    title: str
    backlog_type: BacklogType
    status: BacklogStatus
    priority_level: str
    platform_scope_json: str
    content_type_scope_json: str
    objective_scope_json: str
    created_at: str
    updated_at: str
    source_id: str | None = None
    description: str | None = None
    freshness_status: FreshnessStatus | None = None
    expires_at: str | None = None
    estimated_effort: str | None = None
    reason_not_scheduled: str | None = None
    review_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class CapacityProfile:
    id: str
    creator_id: str
    status: CapacityProfileStatus
    period_type: str
    configuration_json: str
    created_at: str
    updated_at: str
    strategic_plan_id: str | None = None
    name: str | None = None
    available_hours: float | None = None
    available_capacity_units: float | None = None
    maximum_active_items: int | None = None
    maximum_platforms: int | None = None
    maximum_publications: int | None = None
    effective_from: str | None = None
    effective_to: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class CapacityAllocation:
    id: str
    creator_id: str
    strategic_plan_id: str
    resource_type: str
    allocation_status: CapacityAllocationStatus
    created_at: str
    updated_at: str
    planning_cycle_id: str | None = None
    roadmap_item_id: str | None = None
    allocated_hours: float | None = None
    allocated_units: float | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ResourceConstraint:
    id: str
    creator_id: str
    strategic_plan_id: str
    constraint_type: ResourceConstraintType
    title: str
    description: str
    severity: str
    blocking: bool
    created_at: str
    updated_at: str
    available_value_json: str | None = None
    required_value_json: str | None = None
    resolution_action: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningConflict:
    id: str
    creator_id: str
    strategic_plan_id: str
    conflict_type: ConflictType
    severity: str
    left_target_type: str
    description: str
    resolution_status: ConflictResolutionStatus
    created_at: str
    left_target_id: str | None = None
    right_target_type: str | None = None
    right_target_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningScenario:
    id: str
    creator_id: str
    strategic_plan_id: str
    name: str
    scenario_type: ScenarioType
    status: PlanStatus
    assumptions_json: str
    constraints_json: str
    capacity_json: str
    roadmap_summary_json: str
    risk_summary_json: str
    tradeoffs_json: str
    source_fingerprint: str
    created_at: str
    updated_at: str
    description: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningReview:
    id: str
    creator_id: str
    strategic_plan_id: str
    target_type: str
    target_id: str
    review_type: ReviewType
    decision: ReviewDecision
    reason: str
    reviewed_at: str
    created_at: str
    previous_value_json: str | None = None
    new_value_json: str | None = None
    reviewer: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    id: str
    creator_id: str
    strategic_plan_id: str
    snapshot_type: str
    plan_version: int
    source_fingerprint: str
    snapshot_json: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningReport:
    id: str
    creator_id: str
    strategic_plan_id: str | None
    report_type: str
    source_fingerprint: str
    report_json: str
    created_at: str
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class PlanningTask:
    id: str
    creator_id: str
    plan_id: str
    version: int
    current_stage: str
    progress_percent: float
    status: PlanningRunStatus
    created_at: str
    updated_at: str
    horizon: str | None = None
    recommendations_processed: int | None = None
    initiatives: int | None = None
    roadmap_items: int | None = None
    backlog_items: int | None = None
    conflicts: int | None = None
    overload: bool | None = None
    warnings: str | None = None
    errors: str | None = None
    payload_json: str | None = None
    open_result: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ContentLibraryLink:
    id: str
    creator_id: str
    strategic_plan_id: str
    target_type: str
    target_id: str
    internal_content_id: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class FeasibilityReport:
    id: str
    creator_id: str
    strategic_plan_id: str
    target_type: str
    target_id: str
    status: FeasibilityStatus
    reason: str
    created_at: str
    constraints_json: str | None = None
    warnings_json: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)
