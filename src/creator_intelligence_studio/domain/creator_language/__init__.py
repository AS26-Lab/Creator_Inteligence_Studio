"""Dominio para Creator Language Analysis / Narrative Profile."""

from .analysis_types import (
    CreatorLanguageCorpusSelection,
    CreatorLanguageProfileComparison,
    CreatorLanguageQueryFilters,
    CreatorLanguageRetrievalResult,
)
from .entities import (
    CreatorLanguageAnalysisRun,
    CreatorLanguageCandidate,
    CreatorLanguageCorpus,
    CreatorLanguageCorpusSource,
    CreatorLanguageMetric,
    CreatorLanguagePattern,
    CreatorLanguagePatternEvidence,
    CreatorLanguageProfileSnapshot,
    CreatorNarrativeProfile,
)
from .errors import CreatorLanguageError, CreatorLanguageNotFoundError, CreatorLanguageStateError, CreatorLanguageValidationError
from .repositories import CreatorLanguageRepository
from .services import build_creator_language_fingerprint, build_narrative_profile_fingerprint, build_source_snapshot_payload
from .value_objects import (
    CreatorLanguageAnalysisRunStatus,
    CreatorLanguageCandidateReviewDecision,
    CreatorLanguageCandidateStatus,
    CreatorLanguageConfidenceLevel,
    CreatorLanguageCorpusSourceIncludeStatus,
    CreatorLanguageCorpusStatus,
    CreatorLanguagePatternStatus,
    CreatorLanguagePatternType,
    CreatorLanguageScope,
    CreatorLanguageSourceType,
    CreatorLanguageTargetMemoryType,
)

__all__ = [
    "CreatorLanguageAnalysisRun",
    "CreatorLanguageAnalysisRunStatus",
    "CreatorLanguageCandidate",
    "CreatorLanguageCandidateReviewDecision",
    "CreatorLanguageCandidateStatus",
    "CreatorLanguageConfidenceLevel",
    "CreatorLanguageCorpus",
    "CreatorLanguageCorpusSelection",
    "CreatorLanguageCorpusSource",
    "CreatorLanguageCorpusSourceIncludeStatus",
    "CreatorLanguageCorpusStatus",
    "CreatorLanguageError",
    "CreatorLanguageMetric",
    "CreatorLanguageNotFoundError",
    "CreatorLanguagePattern",
    "CreatorLanguagePatternEvidence",
    "CreatorLanguagePatternStatus",
    "CreatorLanguagePatternType",
    "CreatorLanguageProfileComparison",
    "CreatorLanguageProfileSnapshot",
    "CreatorLanguageQueryFilters",
    "CreatorLanguageRepository",
    "CreatorLanguageRetrievalResult",
    "CreatorLanguageScope",
    "CreatorLanguageSourceType",
    "CreatorLanguageStateError",
    "CreatorLanguageTargetMemoryType",
    "CreatorLanguageValidationError",
    "CreatorNarrativeProfile",
    "build_creator_language_fingerprint",
    "build_narrative_profile_fingerprint",
    "build_source_snapshot_payload",
]
