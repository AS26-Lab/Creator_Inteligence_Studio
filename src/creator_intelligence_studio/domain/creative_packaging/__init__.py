"""Dominio de packaging creativo para titulos y miniaturas."""

from .entities import (
    CreativeConcept,
    CreativePrompt,
    CreativePromptReference,
    PackagingAsset,
    PackagingBrandProfile,
    PackagingDecision,
    PackagingExperimentLink,
    PackagingReferenceAsset,
    PackagingPairEvaluation,
    ThumbnailFrameCandidate,
    ThumbnailReview,
    ThumbnailVersion,
    TitleAnalysisMetric,
    TitleAnalysisRun,
    TitleVersion,
    ThumbnailAnalysisMetric,
    ThumbnailAnalysisRun,
)
from .evaluation_types import (
    CreativeConceptResult,
    PackagingPairEvaluationResult,
    ThumbnailReviewResult,
)
from .reference_types import ReferencePackageResult
from .prompt_types import CreativePromptResult
from .title_types import TitleAnalysisResult, TitlePatternType
from .thumbnail_types import ThumbnailAnalysisResult, ThumbnailReviewStatus
from .value_objects import (
    PackagingAssetStatus,
    PackagingAssetType,
    PackagingDecisionType,
    PackagingPromptTargetTool,
    PackagingRecommendationStatus,
    PackagingReviewDecision,
    PackagingRunStatus,
)

