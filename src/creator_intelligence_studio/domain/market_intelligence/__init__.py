"""Dominio para Market and Trend Intelligence Foundation."""

from .competitor_types import CompetitorApprovalStatus, CompetitorMonitoringStatus, RelationshipType
from .confidence_types import ConfidenceLevel
from .evidence_types import EvidenceType
from .entities import (
    CompetitorProfile,
    CreatorMarketFitEvaluation,
    ExternalContentItem,
    ExternalContentSnapshot,
    MarketDefinition,
    MarketEntity,
    MarketObservation,
    MarketPattern,
    MarketPatternEvidence,
    MarketReport,
    MarketReview,
    MarketSnapshot,
    MarketSource,
    MarketTopic,
    OpportunityCandidate,
    OpportunityCandidateEvidence,
    ResearchItem,
    ResearchQuery,
    ResearchRun,
    TrendSignal,
    TrendSignalEvidence,
)
from .lifecycle_types import LifecycleStage
from .market_types import MarketStatus, MarketType, TopicType
from .observation_types import EvidenceQuality, ObservationType, SubjectType
from .opportunity_types import FreshnessStatus, OpportunityStatus, OpportunityType, UrgencyLevel
from .pattern_types import EvidenceRole, PatternStatus, PatternType
from .repositories import MarketIntelligenceRepository
from .saturation_types import SaturationLevel
from .source_types import SourceType, TrustLevel
from .trend_types import TrendDirection, TrendSignalType
from .value_objects import (
    build_market_fingerprint,
    current_utc_iso,
    json_dumps,
    json_loads,
    normalize_identifier,
    normalize_platform,
    normalize_text,
    normalize_url,
    safe_slug,
)

__all__ = [
    "CompetitorApprovalStatus",
    "CompetitorMonitoringStatus",
    "RelationshipType",
    "ConfidenceLevel",
    "EvidenceType",
    "CompetitorProfile",
    "CreatorMarketFitEvaluation",
    "ExternalContentItem",
    "ExternalContentSnapshot",
    "MarketDefinition",
    "MarketEntity",
    "MarketObservation",
    "MarketPattern",
    "MarketPatternEvidence",
    "MarketReport",
    "MarketReview",
    "MarketSnapshot",
    "MarketSource",
    "MarketTopic",
    "OpportunityCandidate",
    "OpportunityCandidateEvidence",
    "ResearchItem",
    "ResearchQuery",
    "ResearchRun",
    "TrendSignal",
    "TrendSignalEvidence",
    "LifecycleStage",
    "MarketStatus",
    "MarketType",
    "TopicType",
    "EvidenceQuality",
    "ObservationType",
    "SubjectType",
    "FreshnessStatus",
    "OpportunityStatus",
    "OpportunityType",
    "UrgencyLevel",
    "EvidenceRole",
    "PatternStatus",
    "PatternType",
    "MarketIntelligenceRepository",
    "SaturationLevel",
    "SourceType",
    "TrustLevel",
    "TrendDirection",
    "TrendSignalType",
    "build_market_fingerprint",
    "current_utc_iso",
    "json_dumps",
    "json_loads",
    "normalize_identifier",
    "normalize_platform",
    "normalize_text",
    "normalize_url",
    "safe_slug",
]
