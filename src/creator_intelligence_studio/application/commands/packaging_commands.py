"""Comandos de aplicacion para packaging creativo."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListPackagingAssetsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ShowPackagingAssetCommand:
    asset_id: str


@dataclass(frozen=True, slots=True)
class BuildPackagingBrandProfileCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListPackagingBrandProfileHistoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListPackagingReferencesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreatePackagingReferenceCommand:
    creator_id: str
    reference_type: str
    source_type: str
    reference_purpose: str
    usage_permission: str


@dataclass(frozen=True, slots=True)
class ReviewPackagingReferenceCommand:
    reference_id: str
    approval_status: str


@dataclass(frozen=True, slots=True)
class ListPackagingTitlesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreatePackagingTitleCommand:
    creator_id: str
    title_text: str
    platform: str
    content_type: str


@dataclass(frozen=True, slots=True)
class ShowPackagingTitleCommand:
    title_id: str


@dataclass(frozen=True, slots=True)
class AnalyzePackagingTitleCommand:
    title_id: str


@dataclass(frozen=True, slots=True)
class ComparePackagingTitlesCommand:
    title_id_a: str
    title_id_b: str


@dataclass(frozen=True, slots=True)
class ListPackagingThumbnailsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreatePackagingThumbnailCommand:
    creator_id: str
    platform: str
    content_type: str


@dataclass(frozen=True, slots=True)
class ShowPackagingThumbnailCommand:
    thumbnail_id: str


@dataclass(frozen=True, slots=True)
class AnalyzePackagingThumbnailCommand:
    thumbnail_id: str


@dataclass(frozen=True, slots=True)
class EvaluatePackagingPairCommand:
    title_id: str
    thumbnail_id: str


@dataclass(frozen=True, slots=True)
class ShowPackagingPairCommand:
    evaluation_id: str


@dataclass(frozen=True, slots=True)
class ListPackagingFrameCandidatesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ExtractPackagingFrameCandidatesCommand:
    creator_id: str
    video_asset_id: str


@dataclass(frozen=True, slots=True)
class ReviewPackagingFrameCommand:
    frame_id: str


@dataclass(frozen=True, slots=True)
class ListPackagingConceptsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreatePackagingConceptCommand:
    creator_id: str
    platform: str
    content_type: str


@dataclass(frozen=True, slots=True)
class BuildPackagingConceptCommand:
    creator_id: str
    platform: str
    content_type: str


@dataclass(frozen=True, slots=True)
class ShowPackagingConceptCommand:
    concept_id: str


@dataclass(frozen=True, slots=True)
class BuildPackagingPromptCommand:
    concept_id: str
    target_tool: str


@dataclass(frozen=True, slots=True)
class ShowPackagingPromptCommand:
    prompt_id: str


@dataclass(frozen=True, slots=True)
class ListPackagingPromptReferencesCommand:
    prompt_id: str


@dataclass(frozen=True, slots=True)
class ExportPackagingPromptCommand:
    prompt_id: str


@dataclass(frozen=True, slots=True)
class ReviewPackagingThumbnailCommand:
    thumbnail_id: str


@dataclass(frozen=True, slots=True)
class ShowPackagingReviewCommand:
    review_id: str


@dataclass(frozen=True, slots=True)
class RecordPackagingDecisionCommand:
    creator_id: str
    target_type: str
    target_id: str
    decision: str


@dataclass(frozen=True, slots=True)
class LinkPackagingExperimentCommand:
    packaging_asset_id: str
    experiment_id: str


@dataclass(frozen=True, slots=True)
class ExportPackagingCommand:
    creator_id: str
    format: str
