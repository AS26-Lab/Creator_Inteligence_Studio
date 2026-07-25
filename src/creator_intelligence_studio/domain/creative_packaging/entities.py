"""Entidades persistidas de packaging creativo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    PackagingAssetStatus,
    PackagingAssetType,
    PackagingDecisionType,
    PackagingPromptTargetTool,
    PackagingRecommendationStatus,
    PackagingReviewDecision,
    PackagingRunStatus,
)


@dataclass(frozen=True, slots=True)
class PackagingAsset:
    id: str
    creator_id: str
    publication_id: str | None
    video_asset_id: str | None
    asset_type: PackagingAssetType
    platform: str
    content_type: str
    topic: str | None
    status: PackagingAssetStatus
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "asset_type": self.asset_type.value,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "status": self.status.value,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TitleVersion:
    id: str
    packaging_asset_id: str
    version_number: int
    title_text: str
    source_type: str
    language: str
    platform: str
    content_type: str
    topic: str | None
    is_published: bool
    is_selected: bool
    creator_approval_status: str
    creator_feedback: str | None
    source_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "packaging_asset_id": self.packaging_asset_id,
            "version_number": self.version_number,
            "title_text": self.title_text,
            "source_type": self.source_type,
            "language": self.language,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "is_published": self.is_published,
            "is_selected": self.is_selected,
            "creator_approval_status": self.creator_approval_status,
            "creator_feedback": self.creator_feedback,
            "source_fingerprint": self.source_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailVersion:
    id: str
    packaging_asset_id: str
    version_number: int
    image_path: str | None
    source_type: str
    width: int | None
    height: int | None
    file_fingerprint: str | None
    concept_id: str | None
    is_published: bool
    is_selected: bool
    creator_approval_status: str
    creator_feedback: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "packaging_asset_id": self.packaging_asset_id,
            "version_number": self.version_number,
            "image_path": self.image_path,
            "source_type": self.source_type,
            "width": self.width,
            "height": self.height,
            "file_fingerprint": self.file_fingerprint,
            "concept_id": self.concept_id,
            "is_published": self.is_published,
            "is_selected": self.is_selected,
            "creator_approval_status": self.creator_approval_status,
            "creator_feedback": self.creator_feedback,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PackagingReferenceAsset:
    id: str
    creator_id: str
    reference_type: str
    image_path: str | None
    text_content: str | None
    platform: str | None
    content_type: str | None
    topic: str | None
    source_type: str
    source_creator_name: str | None
    source_url: str | None
    usage_permission: str
    represents_creator: bool
    approval_status: str
    reference_purpose: str
    notes: str | None
    file_fingerprint: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "reference_type": self.reference_type,
            "image_path": self.image_path,
            "text_content": self.text_content,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "source_type": self.source_type,
            "source_creator_name": self.source_creator_name,
            "source_url": self.source_url,
            "usage_permission": self.usage_permission,
            "represents_creator": self.represents_creator,
            "approval_status": self.approval_status,
            "reference_purpose": self.reference_purpose,
            "notes": self.notes,
            "file_fingerprint": self.file_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class PackagingBrandProfile:
    id: str
    creator_id: str
    profile_version: int
    brand_summary: str
    visual_identity_json: str
    preferred_composition_json: str
    preferred_palette_json: str
    typography_guidance_json: str
    subject_guidance_json: str
    expression_guidance_json: str
    approved_patterns_json: str
    rejected_patterns_json: str
    prohibited_elements_json: str
    platform_differences_json: str
    source_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "profile_version": self.profile_version,
            "brand_summary": self.brand_summary,
            "visual_identity_json": self.visual_identity_json,
            "preferred_composition_json": self.preferred_composition_json,
            "preferred_palette_json": self.preferred_palette_json,
            "typography_guidance_json": self.typography_guidance_json,
            "subject_guidance_json": self.subject_guidance_json,
            "expression_guidance_json": self.expression_guidance_json,
            "approved_patterns_json": self.approved_patterns_json,
            "rejected_patterns_json": self.rejected_patterns_json,
            "prohibited_elements_json": self.prohibited_elements_json,
            "platform_differences_json": self.platform_differences_json,
            "source_fingerprint": self.source_fingerprint,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class TitleAnalysisRun:
    id: str
    creator_id: str
    title_version_id: str
    analyzer_version: str
    status: PackagingRunStatus
    configuration_json: str
    creator_memory_snapshot_id: str | None
    creator_language_snapshot_id: str | None
    brand_profile_version: int | None
    source_fingerprint: str
    warning_count: int
    created_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "title_version_id": self.title_version_id,
            "analyzer_version": self.analyzer_version,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "creator_memory_snapshot_id": self.creator_memory_snapshot_id,
            "creator_language_snapshot_id": self.creator_language_snapshot_id,
            "brand_profile_version": self.brand_profile_version,
            "source_fingerprint": self.source_fingerprint,
            "warning_count": self.warning_count,
            "created_at": to_iso_z(self.created_at),
            "completed_at": to_iso_z(self.completed_at),
        }


@dataclass(frozen=True, slots=True)
class TitleAnalysisMetric:
    id: str
    analysis_run_id: str
    metric_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    confidence_level: str
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "metric_key": self.metric_key,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "confidence_level": self.confidence_level,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailAnalysisRun:
    id: str
    creator_id: str
    thumbnail_version_id: str
    analyzer_version: str
    status: PackagingRunStatus
    configuration_json: str
    creator_memory_snapshot_id: str | None
    creator_language_snapshot_id: str | None
    brand_profile_version: int | None
    source_fingerprint: str
    warning_count: int
    created_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "thumbnail_version_id": self.thumbnail_version_id,
            "analyzer_version": self.analyzer_version,
            "status": self.status.value,
            "configuration_json": self.configuration_json,
            "creator_memory_snapshot_id": self.creator_memory_snapshot_id,
            "creator_language_snapshot_id": self.creator_language_snapshot_id,
            "brand_profile_version": self.brand_profile_version,
            "source_fingerprint": self.source_fingerprint,
            "warning_count": self.warning_count,
            "created_at": to_iso_z(self.created_at),
            "completed_at": to_iso_z(self.completed_at),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailAnalysisMetric:
    id: str
    analysis_run_id: str
    metric_key: str
    numeric_value: float | None
    text_value: str | None
    unit: str
    confidence_level: str
    warning_codes_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "metric_key": self.metric_key,
            "numeric_value": self.numeric_value,
            "text_value": self.text_value,
            "unit": self.unit,
            "confidence_level": self.confidence_level,
            "warning_codes_json": self.warning_codes_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PackagingPairEvaluation:
    id: str
    creator_id: str
    title_version_id: str
    thumbnail_version_id: str
    publication_id: str | None
    status: PackagingRunStatus
    visual_quality_score: float | None
    content_alignment_score: float | None
    creator_brand_alignment_score: float | None
    audience_fit_score: float | None
    platform_fit_score: float | None
    historical_fit_score: float | None
    niche_fit_score: float | None
    differentiation_score: float | None
    clarity_score: float | None
    curiosity_score: float | None
    hierarchy_score: float | None
    complement_score: float | None
    authenticity_score: float | None
    promise_alignment_score: float | None
    evidence_json: str
    warnings_json: str
    risks_json: str
    limitations_json: str
    recommendation_status: PackagingRecommendationStatus
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "title_version_id": self.title_version_id,
            "thumbnail_version_id": self.thumbnail_version_id,
            "publication_id": self.publication_id,
            "status": self.status.value,
            "visual_quality_score": self.visual_quality_score,
            "content_alignment_score": self.content_alignment_score,
            "creator_brand_alignment_score": self.creator_brand_alignment_score,
            "audience_fit_score": self.audience_fit_score,
            "platform_fit_score": self.platform_fit_score,
            "historical_fit_score": self.historical_fit_score,
            "niche_fit_score": self.niche_fit_score,
            "differentiation_score": self.differentiation_score,
            "clarity_score": self.clarity_score,
            "curiosity_score": self.curiosity_score,
            "hierarchy_score": self.hierarchy_score,
            "complement_score": self.complement_score,
            "authenticity_score": self.authenticity_score,
            "promise_alignment_score": self.promise_alignment_score,
            "evidence_json": self.evidence_json,
            "warnings_json": self.warnings_json,
            "risks_json": self.risks_json,
            "limitations_json": self.limitations_json,
            "recommendation_status": self.recommendation_status.value,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailFrameCandidate:
    id: str
    creator_id: str
    video_asset_id: str
    timestamp_seconds: float
    frame_path: str
    frame_fingerprint: str
    width: int
    height: int
    sharpness_score: float | None
    brightness_score: float | None
    contrast_score: float | None
    face_presence: bool | None
    motion_blur_score: float | None
    quality_status: str
    warning_codes_json: str
    creator_decision: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "video_asset_id": self.video_asset_id,
            "timestamp_seconds": self.timestamp_seconds,
            "frame_path": self.frame_path,
            "frame_fingerprint": self.frame_fingerprint,
            "width": self.width,
            "height": self.height,
            "sharpness_score": self.sharpness_score,
            "brightness_score": self.brightness_score,
            "contrast_score": self.contrast_score,
            "face_presence": self.face_presence,
            "motion_blur_score": self.motion_blur_score,
            "quality_status": self.quality_status,
            "warning_codes_json": self.warning_codes_json,
            "creator_decision": self.creator_decision,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreativeConcept:
    id: str
    creator_id: str
    publication_id: str | None
    video_asset_id: str | None
    concept_type: str
    platform: str
    content_type: str
    topic: str | None
    title: str
    premise: str
    subject_description: str
    action_description: str
    composition_description: str
    emotion_description: str
    background_description: str
    color_guidance: str
    text_guidance: str
    visual_hierarchy: str
    relation_to_title: str
    brand_alignment_notes: str
    audience_fit_notes: str
    platform_fit_notes: str
    differentiation_notes: str
    authenticity_notes: str
    risks_json: str
    reference_requirements_json: str
    status: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "publication_id": self.publication_id,
            "video_asset_id": self.video_asset_id,
            "concept_type": self.concept_type,
            "platform": self.platform,
            "content_type": self.content_type,
            "topic": self.topic,
            "title": self.title,
            "premise": self.premise,
            "subject_description": self.subject_description,
            "action_description": self.action_description,
            "composition_description": self.composition_description,
            "emotion_description": self.emotion_description,
            "background_description": self.background_description,
            "color_guidance": self.color_guidance,
            "text_guidance": self.text_guidance,
            "visual_hierarchy": self.visual_hierarchy,
            "relation_to_title": self.relation_to_title,
            "brand_alignment_notes": self.brand_alignment_notes,
            "audience_fit_notes": self.audience_fit_notes,
            "platform_fit_notes": self.platform_fit_notes,
            "differentiation_notes": self.differentiation_notes,
            "authenticity_notes": self.authenticity_notes,
            "risks_json": self.risks_json,
            "reference_requirements_json": self.reference_requirements_json,
            "status": self.status,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreativePrompt:
    id: str
    concept_id: str
    target_tool: PackagingPromptTargetTool
    prompt_text: str
    negative_guidance: str | None
    reference_instructions_json: str
    tool_usage_notes_json: str
    expected_output_notes: str
    version_number: int
    creator_approval_status: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "target_tool": self.target_tool.value,
            "prompt_text": self.prompt_text,
            "negative_guidance": self.negative_guidance,
            "reference_instructions_json": self.reference_instructions_json,
            "tool_usage_notes_json": self.tool_usage_notes_json,
            "expected_output_notes": self.expected_output_notes,
            "version_number": self.version_number,
            "creator_approval_status": self.creator_approval_status,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreativePromptReference:
    id: str
    prompt_id: str
    reference_asset_id: str | None
    reference_role: str
    required_level: str
    instruction: str
    risk_notes: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "reference_asset_id": self.reference_asset_id,
            "reference_role": self.reference_role,
            "required_level": self.required_level,
            "instruction": self.instruction,
            "risk_notes": self.risk_notes,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailReview:
    id: str
    creator_id: str
    thumbnail_version_id: str
    title_version_id: str | None
    publication_id: str | None
    review_type: str
    overall_status: str
    visual_quality_json: str
    content_alignment_json: str
    brand_alignment_json: str
    audience_fit_json: str
    platform_fit_json: str
    historical_fit_json: str
    niche_fit_json: str
    differentiation_json: str
    strengths_json: str
    weaknesses_json: str
    keep_json: str
    change_json: str
    risks_json: str
    final_recommendation: str
    confidence_level: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "thumbnail_version_id": self.thumbnail_version_id,
            "title_version_id": self.title_version_id,
            "publication_id": self.publication_id,
            "review_type": self.review_type,
            "overall_status": self.overall_status,
            "visual_quality_json": self.visual_quality_json,
            "content_alignment_json": self.content_alignment_json,
            "brand_alignment_json": self.brand_alignment_json,
            "audience_fit_json": self.audience_fit_json,
            "platform_fit_json": self.platform_fit_json,
            "historical_fit_json": self.historical_fit_json,
            "niche_fit_json": self.niche_fit_json,
            "differentiation_json": self.differentiation_json,
            "strengths_json": self.strengths_json,
            "weaknesses_json": self.weaknesses_json,
            "keep_json": self.keep_json,
            "change_json": self.change_json,
            "risks_json": self.risks_json,
            "final_recommendation": self.final_recommendation,
            "confidence_level": self.confidence_level,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PackagingDecision:
    id: str
    creator_id: str
    target_type: str
    target_id: str
    decision: PackagingDecisionType
    reason: str | None
    modified_value_json: str | None
    decided_at: datetime
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "decision": self.decision.value,
            "reason": self.reason,
            "modified_value_json": self.modified_value_json,
            "decided_at": to_iso_z(self.decided_at),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class PackagingExperimentLink:
    id: str
    packaging_asset_id: str
    experiment_id: str
    assignment_id: str | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "packaging_asset_id": self.packaging_asset_id,
            "experiment_id": self.experiment_id,
            "assignment_id": self.assignment_id,
            "created_at": to_iso_z(self.created_at),
        }

