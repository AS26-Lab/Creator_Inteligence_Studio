"""Entidades del dominio de mercado."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .competitor_types import CompetitorApprovalStatus, CompetitorMonitoringStatus, RelationshipType
from .confidence_types import ConfidenceLevel
from .evidence_types import EvidenceType
from .lifecycle_types import LifecycleStage
from .market_types import MarketStatus, MarketType, TopicType
from .observation_types import EvidenceQuality, ObservationType, SubjectType
from .opportunity_types import FreshnessStatus, OpportunityStatus, OpportunityType, UrgencyLevel
from .pattern_types import EvidenceRole, PatternStatus, PatternType
from .saturation_types import SaturationLevel
from .source_types import SourceType, TrustLevel
from .trend_types import TrendDirection, TrendSignalType


def _to_dict(instance: object) -> dict[str, object]:
    payload = asdict(instance)
    return payload


@dataclass(frozen=True, slots=True)
class MarketDefinition:
    id: str
    creator_id: str
    name: str
    market_type: MarketType
    status: MarketStatus
    description: str | None = None
    primary_language: str | None = None
    primary_region: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketTopic:
    id: str
    creator_id: str
    market_id: str
    canonical_name: str
    display_name: str
    topic_type: TopicType
    status: MarketStatus
    parent_topic_id: str | None = None
    description: str | None = None
    aliases_json: str | None = None
    excluded_terms_json: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketSource:
    id: str
    creator_id: str
    source_type: SourceType
    name: str
    access_method: str
    trust_level: TrustLevel
    permission_status: str
    enabled: bool
    platform: str | None = None
    source_identifier: str | None = None
    source_url: str | None = None
    configuration_json: str | None = None
    last_checked_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ResearchQuery:
    id: str
    creator_id: str
    platform: str
    query_text: str
    query_type: str
    status: str
    max_results: int
    market_id: str | None = None
    language: str | None = None
    region: str | None = None
    published_after: str | None = None
    published_before: str | None = None
    filters_json: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ResearchRun:
    id: str
    creator_id: str
    source_id: str
    status: str
    discovered_count: int
    imported_count: int
    updated_count: int
    skipped_count: int
    warning_count: int
    error_count: int
    configuration_json: str
    started_at: str
    created_at: str
    research_query_id: str | None = None
    cursor_json: str | None = None
    estimated_quota_cost: int | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ResearchItem:
    id: str
    research_run_id: str
    external_entity_type: str
    action: str
    status: str
    created_at: str
    external_entity_id: str | None = None
    warning_codes_json: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketEntity:
    id: str
    creator_id: str
    entity_type: str
    platform: str
    canonical_name: str
    display_name: str
    source_id: str
    status: str
    first_observed_at: str
    last_observed_at: str
    market_id: str | None = None
    external_id: str | None = None
    source_url: str | None = None
    country: str | None = None
    language: str | None = None
    remote_fingerprint: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class CompetitorProfile:
    id: str
    creator_id: str
    market_entity_id: str
    relationship_type: RelationshipType
    relevance_reason: str
    relevance_scope: str
    approval_status: CompetitorApprovalStatus
    monitoring_status: CompetitorMonitoringStatus
    copying_risk_level: str
    created_at: str = ""
    updated_at: str = ""
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ExternalContentItem:
    id: str
    creator_id: str
    source_id: str
    platform: str
    content_type: str
    first_observed_at: str
    last_observed_at: str
    created_at: str = ""
    updated_at: str = ""
    market_entity_id: str | None = None
    external_content_id: str | None = None
    title: str | None = None
    description: str | None = None
    published_at: str | None = None
    duration_seconds: int | None = None
    language: str | None = None
    region: str | None = None
    source_url: str | None = None
    thumbnail_url: str | None = None
    local_reference_asset_id: str | None = None
    topic_labels_json: str | None = None
    format_labels_json: str | None = None
    public_metrics_json: str | None = None
    remote_fingerprint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class ExternalContentSnapshot:
    id: str
    creator_id: str
    external_content_item_id: str
    observed_at: str
    metrics_json: str
    source_type: SourceType
    source_fingerprint: str
    quality_status: str
    created_at: str = ""
    warning_codes_json: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketObservation:
    id: str
    creator_id: str
    source_id: str
    platform: str
    observation_type: ObservationType
    subject_type: SubjectType
    observed_value_json: str
    observed_at: str
    evidence_quality: EvidenceQuality
    confidence_level: ConfidenceLevel
    status: str
    created_at: str = ""
    market_id: str | None = None
    topic_id: str | None = None
    subject_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class TrendSignal:
    id: str
    creator_id: str
    platform: str
    signal_type: TrendSignalType
    lifecycle_stage: LifecycleStage
    direction: TrendDirection
    sample_size: int
    period_start: str
    period_end: str
    confidence_level: ConfidenceLevel
    status: str
    created_at: str = ""
    updated_at: str = ""
    market_id: str | None = None
    topic_id: str | None = None
    region: str | None = None
    language: str | None = None
    magnitude: float | None = None
    velocity: float | None = None
    acceleration: float | None = None
    persistence: float | None = None
    saturation_level: SaturationLevel = SaturationLevel.UNKNOWN
    novelty_level: float | None = None
    confidence_score: float | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class TrendSignalEvidence:
    id: str
    trend_signal_id: str
    evidence_type: EvidenceType
    supports_signal: bool
    weight: float
    created_at: str = ""
    source_id: str | None = None
    observation_id: str | None = None
    external_content_item_id: str | None = None
    snapshot_id: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketPattern:
    id: str
    creator_id: str
    pattern_type: PatternType
    canonical_name: str
    description: str
    sample_size: int
    supporting_count: int
    contradicting_count: int
    confidence_level: ConfidenceLevel
    status: PatternStatus
    created_at: str = ""
    updated_at: str = ""
    market_id: str | None = None
    platform: str | None = None
    pattern_definition_json: str | None = None
    first_observed_at: str | None = None
    last_observed_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketPatternEvidence:
    id: str
    pattern_id: str
    evidence_role: EvidenceRole
    created_at: str = ""
    external_content_item_id: str | None = None
    observation_id: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class CreatorMarketFitEvaluation:
    id: str
    creator_id: str
    target_type: str
    target_id: str
    brand_fit: float
    audience_fit: float
    historical_fit: float
    platform_fit: float
    strategic_fit: float
    authenticity_fit: float
    capability_fit: float
    timing_fit: float
    differentiation_potential: float
    copying_risk: float
    overall_fit: float
    confidence_level: ConfidenceLevel
    created_at: str = ""
    creator_memory_snapshot_id: str | None = None
    creator_language_snapshot_id: str | None = None
    audience_profile_snapshot_id: str | None = None
    analytics_context_json: str | None = None
    limitations_json: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    id: str
    creator_id: str
    title: str
    summary: str
    opportunity_type: OpportunityType
    lifecycle_stage: LifecycleStage
    urgency: UrgencyLevel
    freshness_status: FreshnessStatus
    saturation_level: SaturationLevel
    creator_fit: float
    audience_fit: float
    historical_fit: float
    differentiation_potential: float
    copying_risk: float
    evidence_quality: EvidenceQuality
    confidence_level: ConfidenceLevel
    status: OpportunityStatus
    created_at: str = ""
    updated_at: str = ""
    market_id: str | None = None
    topic_id: str | None = None
    trend_signal_id: str | None = None
    pattern_id: str | None = None
    platform_scope_json: str | None = None
    content_type_scope_json: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class OpportunityCandidateEvidence:
    id: str
    opportunity_candidate_id: str
    evidence_type: EvidenceType
    supports_candidate: bool
    weight: float
    created_at: str = ""
    source_id: str | None = None
    trend_signal_id: str | None = None
    pattern_id: str | None = None
    external_content_item_id: str | None = None
    internal_publication_id: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketReview:
    id: str
    creator_id: str
    target_type: str
    target_id: str
    decision: str
    reason: str
    reviewed_at: str
    created_at: str = ""
    previous_value_json: str | None = None
    new_value_json: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    id: str
    creator_id: str
    snapshot_type: str
    period_start: str
    period_end: str
    source_fingerprint: str
    snapshot_json: str
    created_at: str = ""
    market_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)


@dataclass(frozen=True, slots=True)
class MarketReport:
    id: str
    creator_id: str
    report_type: str
    source_fingerprint: str
    report_json: str
    created_at: str = ""
    market_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None

    def to_dict(self) -> dict[str, object]:
        return _to_dict(self)
