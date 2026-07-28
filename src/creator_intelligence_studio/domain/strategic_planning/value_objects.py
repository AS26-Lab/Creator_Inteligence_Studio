"""Enumeraciones y tipos de Strategic Planning."""

from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - conveniencia
        return self.value


class PlanStatus(_StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class PriorityLevel(_StrEnum):
    BLOCKED = "blocked"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HorizonType(_StrEnum):
    IMMEDIATE = "immediate"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEAR = "half_year"
    ANNUAL = "annual"
    CUSTOM = "custom"


class CycleType(_StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SPRINT = "sprint"
    CUSTOM = "custom"


class ObjectiveType(_StrEnum):
    AUDIENCE_GROWTH = "audience_growth"
    AUDIENCE_DEPTH = "audience_depth"
    AWARENESS = "awareness"
    REACH = "reach"
    DISCOVERY = "discovery"
    VIEWS = "views"
    WATCH_TIME = "watch_time"
    RETENTION = "retention"
    COMPLETION = "completion"
    ENGAGEMENT = "engagement"
    SAVES = "saves"
    SHARES = "shares"
    COMMENTS = "comments"
    SUBSCRIBER_GROWTH = "subscriber_growth"
    FOLLOWER_GROWTH = "follower_growth"
    RETURNING_AUDIENCE = "returning_audience"
    SEARCH_DISCOVERY = "search_discovery"
    PLATFORM_CONVERSION = "platform_conversion"
    LONGFORM_CONVERSION = "longform_conversion"
    SHORTFORM_CONVERSION = "shortform_conversion"
    BRAND_CONSISTENCY = "brand_consistency"
    CREATOR_POSITIONING = "creator_positioning"
    MARKET_VALIDATION = "market_validation"
    AUDIENCE_VALIDATION = "audience_validation"
    PACKAGING_LEARNING = "packaging_learning"
    CONTENT_LEARNING = "content_learning"
    OPERATIONAL_EFFICIENCY = "operational_efficiency"
    SUSTAINABLE_FREQUENCY = "sustainable_frequency"
    DIVERSIFICATION = "diversification"
    RISK_REDUCTION = "risk_reduction"
    UNKNOWN = "unknown"


class StrategyThemeType(_StrEnum):
    GROWTH = "growth"
    AUDIENCE = "audience"
    AUTHORITY = "authority"
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    COMMUNITY = "community"
    EXPERIMENTATION = "experimentation"
    PACKAGING = "packaging"
    SEARCH = "search"
    RETENTION = "retention"
    PLATFORM_EXPANSION = "platform_expansion"
    CROSS_PLATFORM = "cross_platform"
    MONETIZATION_PREPARATION = "monetization_preparation"
    BRAND = "brand"
    OPERATIONAL = "operational"
    EVERGREEN = "evergreen"
    SEASONAL = "seasonal"
    TREND_RESPONSE = "trend_response"
    RISK_REDUCTION = "risk_reduction"
    UNKNOWN = "unknown"


class ContentPillarStatus(_StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    PAUSED = "paused"
    ARCHIVED = "archived"


class InitiativeType(_StrEnum):
    CONTENT_PROGRAM = "content_program"
    EXPERIMENT_PROGRAM = "experiment_program"
    AUDIENCE_PROGRAM = "audience_program"
    PLATFORM_PROGRAM = "platform_program"
    PACKAGING_PROGRAM = "packaging_program"
    RESEARCH_PROGRAM = "research_program"
    SERIES_PROGRAM = "series_program"
    REVIVAL_PROGRAM = "revival_program"
    REPURPOSE_PROGRAM = "repurpose_program"
    BRAND_PROGRAM = "brand_program"
    OPERATIONAL_PROGRAM = "operational_program"
    RISK_REDUCTION_PROGRAM = "risk_reduction_program"
    SEASONAL_PROGRAM = "seasonal_program"
    CAMPAIGN_PROGRAM = "campaign_program"
    UNKNOWN = "unknown"


class CampaignType(_StrEnum):
    GROWTH = "growth"
    SEASONAL = "seasonal"
    LEARNING = "learning"
    COMMUNITY = "community"
    BRAND = "brand"
    SEARCH = "search"
    EXPERIMENT = "experiment"
    UNKNOWN = "unknown"


class SeriesType(_StrEnum):
    PILOT = "pilot"
    EVERGREEN = "evergreen"
    EXPERIMENTAL = "experimental"
    COMMUNITY = "community"
    RESEARCH = "research"
    REVIVAL = "revival"
    REPURPOSE = "repurpose"
    UNKNOWN = "unknown"


class RoadmapItemType(_StrEnum):
    RESEARCH = "research"
    EXPERIMENT = "experiment"
    CONTENT_CONCEPT = "content_concept"
    CONTENT_PROJECT = "content_project"
    SERIES_EPISODE = "series_episode"
    PACKAGING_TEST = "packaging_test"
    PLATFORM_ADAPTATION = "platform_adaptation"
    REPURPOSE = "repurpose"
    AUDIENCE_ACTIVITY = "audience_activity"
    ANALYTICS_REVIEW = "analytics_review"
    STRATEGIC_REVIEW = "strategic_review"
    MARKET_REVIEW = "market_review"
    PRODUCTION_PREPARATION = "production_preparation"
    PUBLICATION_PLACEHOLDER = "publication_placeholder"
    MEASUREMENT = "measurement"
    RETROSPECTIVE = "retrospective"
    UNKNOWN = "unknown"


class RoadmapItemStatus(_StrEnum):
    IDEA = "idea"
    BACKLOG = "backlog"
    PROPOSED = "proposed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SCHEDULED_TENTATIVE = "scheduled_tentative"
    SCHEDULED_CONFIRMED = "scheduled_confirmed"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class BacklogType(_StrEnum):
    RECOMMENDATION = "recommendation"
    OPPORTUNITY = "opportunity"
    EXPERIMENT = "experiment"
    TOPIC = "topic"
    FORMAT = "format"
    CONTENT_CONCEPT = "content_concept"
    SERIES = "series"
    CAMPAIGN = "campaign"
    RESEARCH = "research"
    REPURPOSE = "repurpose"
    REVIVAL = "revival"
    PACKAGING = "packaging"
    PLATFORM = "platform"
    RISK_REDUCTION = "risk_reduction"
    UNKNOWN = "unknown"


class BacklogStatus(_StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"
    NO_LONGER_RELEVANT = "no_longer_relevant"
    PLATFORM_UNAVAILABLE = "platform_unavailable"
    SUPERSEDED = "superseded"
    ALREADY_EXECUTED = "already_executed"
    REJECTED = "rejected"
    NEEDS_MORE_DATA = "needs_more_data"
    ARCHIVED = "archived"


class CapacityProfileStatus(_StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class CapacityAllocationStatus(_StrEnum):
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    BLOCKED = "blocked"
    RELEASED = "released"


class ResourceConstraintType(_StrEnum):
    TIME = "time"
    BUDGET = "budget"
    EQUIPMENT = "equipment"
    SOFTWARE = "software"
    TEAM = "team"
    LOCATION = "location"
    RIGHTS = "rights"
    BRAND_REVIEW = "brand_review"
    LEGAL_REVIEW = "legal_review"
    PLATFORM_ACCESS = "platform_access"
    MEASUREMENT = "measurement"
    SOURCE_DATA = "source_data"
    DEPENDENCY = "dependency"
    CREATOR_ENERGY = "creator_energy"
    FREQUENCY_LIMIT = "frequency_limit"
    UNKNOWN = "unknown"


class DependencyType(_StrEnum):
    FINISH_TO_START = "finish_to_start"
    START_TO_START = "start_to_start"
    FINISH_TO_FINISH = "finish_to_finish"
    RESEARCH_BEFORE_DECISION = "research_before_decision"
    RECOMMENDATION_BEFORE_PLAN = "recommendation_before_plan"
    PLAN_BEFORE_PRODUCTION = "plan_before_production"
    PRODUCTION_BEFORE_PACKAGING = "production_before_packaging"
    PACKAGING_BEFORE_PUBLICATION = "packaging_before_publication"
    PUBLICATION_BEFORE_MEASUREMENT = "publication_before_measurement"
    MEASUREMENT_BEFORE_REVIEW = "measurement_before_review"
    EXPERIMENT_BEFORE_SCALE = "experiment_before_scale"
    RIGHTS_BEFORE_USE = "rights_before_use"
    APPROVAL_BEFORE_EXECUTION = "approval_before_execution"
    PLATFORM_ACCESS_BEFORE_SYNC = "platform_access_before_sync"
    CUSTOM = "custom"


class MilestoneType(_StrEnum):
    RESEARCH_COMPLETE = "research_complete"
    RECOMMENDATION_APPROVED = "recommendation_approved"
    EXPERIMENT_READY = "experiment_ready"
    CONCEPT_READY = "concept_ready"
    SCRIPT_BRIEF_READY = "script_brief_ready"
    PRODUCTION_READY = "production_ready"
    PACKAGING_READY = "packaging_ready"
    PUBLICATION_READY = "publication_ready"
    PUBLICATION_MANUAL = "publication_manual"
    MEASUREMENT_WINDOW_COMPLETE = "measurement_window_complete"
    REVIEW_COMPLETE = "review_complete"
    CAMPAIGN_COMPLETE = "campaign_complete"
    CUSTOM = "custom"


class RiskType(_StrEnum):
    CAPACITY = "capacity"
    SCHEDULE = "schedule"
    DEPENDENCY = "dependency"
    PLATFORM = "platform"
    DATA = "data"
    EVIDENCE = "evidence"
    FRESHNESS = "freshness"
    SATURATION = "saturation"
    COPYING = "copying"
    RIGHTS = "rights"
    BRAND = "brand"
    CREATOR_BOUNDARY = "creator_boundary"
    MEASUREMENT = "measurement"
    OPERATIONAL = "operational"
    RESOURCE = "resource"
    REPETITION = "repetition"
    AUDIENCE = "audience"
    STRATEGIC = "strategic"
    UNKNOWN = "unknown"


class RiskSeverity(_StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ReviewType(_StrEnum):
    PLAN_REVIEW = "plan_review"
    OBJECTIVE_REVIEW = "objective_review"
    CYCLE_REVIEW = "cycle_review"
    CAPACITY_REVIEW = "capacity_review"
    RISK_REVIEW = "risk_review"
    MILESTONE_REVIEW = "milestone_review"
    PERFORMANCE_REVIEW = "performance_review"
    EXPERIMENT_REVIEW = "experiment_review"
    MARKET_REVIEW = "market_review"
    RECOMMENDATION_REVIEW = "recommendation_review"
    RETROSPECTIVE = "retrospective"


class ReviewDecision(_StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"
    PAUSE = "pause"
    RESUME = "resume"
    REDUCE_SCOPE = "reduce_scope"
    EXPAND_SCOPE = "expand_scope"
    MOVE_TO_BACKLOG = "move_to_backlog"
    SCHEDULE_TENTATIVE = "schedule_tentative"
    SCHEDULE_CONFIRMED = "schedule_confirmed"
    CHANGE_PRIORITY = "change_priority"
    CHANGE_DATES = "change_dates"
    CHANGE_PLATFORM = "change_platform"
    CHANGE_OBJECTIVE = "change_objective"
    CHANGE_PILLAR = "change_pillar"
    RESOLVE_CONFLICT = "resolve_conflict"
    CANCEL = "cancel"
    ARCHIVE = "archive"
    SUPERSEDE = "supersede"


class ScenarioType(_StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GROWTH_FOCUSED = "growth_focused"
    LEARNING_FOCUSED = "learning_focused"
    LOW_CAPACITY = "low_capacity"
    HIGH_CAPACITY = "high_capacity"
    SINGLE_PLATFORM = "single_platform"
    MULTI_PLATFORM = "multi_platform"
    EVERGREEN_FOCUSED = "evergreen_focused"
    TREND_RESPONSIVE = "trend_responsive"
    CUSTOM = "custom"


class MetricRole(_StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GUARDRAIL = "guardrail"
    DIAGNOSTIC = "diagnostic"
    LEARNING = "learning"
    INVALIDATION = "invalidation"


class MetricAvailabilityStatus(_StrEnum):
    AVAILABLE = "available"
    MANUAL_IMPORT_REQUIRED = "manual_import_required"
    PROXY_ONLY = "proxy_only"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class FeasibilityStatus(_StrEnum):
    FEASIBLE = "feasible"
    FEASIBLE_WITH_CONSTRAINTS = "feasible_with_constraints"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    BLOCKED = "blocked"
    NOT_FEASIBLE = "not_feasible"
    UNKNOWN = "unknown"


class PlanningRunStatus(_StrEnum):
    QUEUED = "queued"
    ASSEMBLING_CONTEXT = "assembling_context"
    VALIDATING_RECOMMENDATIONS = "validating_recommendations"
    BUILDING_OBJECTIVES = "building_objectives"
    BUILDING_THEMES = "building_themes"
    BUILDING_PILLARS = "building_pillars"
    BUILDING_INITIATIVES = "building_initiatives"
    EVALUATING_CAPACITY = "evaluating_capacity"
    RESOLVING_DEPENDENCIES = "resolving_dependencies"
    DETECTING_CONFLICTS = "detecting_conflicts"
    BALANCING_PORTFOLIO = "balancing_portfolio"
    BUILDING_ROADMAP = "building_roadmap"
    BUILDING_SCENARIOS = "building_scenarios"
    SAVING = "saving"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    FAILED = "failed"


class LifecycleStatus(_StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class SourceType(_StrEnum):
    RECOMMENDATION = "recommendation"
    EXPERIMENT = "experiment"
    CONTENT_LIBRARY = "content_library"
    ANALYTICS = "analytics"
    AUDIENCE = "audience"
    MEMORY = "memory"
    LANGUAGE = "language"
    MARKET = "market"
    PLATFORM = "platform"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ConflictType(_StrEnum):
    OBJECTIVE_CONFLICT = "objective_conflict"
    DATE_CONFLICT = "date_conflict"
    CAPACITY_CONFLICT = "capacity_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    PLATFORM_CONFLICT = "platform_conflict"
    RECOMMENDATION_CONFLICT = "recommendation_conflict"
    EXPERIMENT_CONFLICT = "experiment_conflict"
    CREATOR_BOUNDARY_CONFLICT = "creator_boundary_conflict"
    RIGHTS_CONFLICT = "rights_conflict"
    METRIC_CONFLICT = "metric_conflict"
    DUPLICATE_CONTENT_CONFLICT = "duplicate_content_conflict"
    SERIES_OVERLAP = "series_overlap"
    CAMPAIGN_OVERLAP = "campaign_overlap"
    FRESHNESS_CONFLICT = "freshness_conflict"
    UNKNOWN = "unknown"


class ConflictResolutionStatus(_StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    BLOCKED = "blocked"
    DISMISSED = "dismissed"


class FreshnessStatus(_StrEnum):
    FRESH = "fresh"
    RECENT = "recent"
    AGING = "aging"
    STALE = "stale"
    EXPIRED = "expired"
    EVERGREEN = "evergreen"
    SEASONAL = "seasonal"
    UNKNOWN = "unknown"
