"""Valores cerrados para packaging creativo."""

from __future__ import annotations

from enum import Enum


class PackagingAssetType(str, Enum):
    TITLE = "title"
    THUMBNAIL = "thumbnail"
    TITLE_THUMBNAIL_PAIR = "title_thumbnail_pair"
    FRAME_CANDIDATE = "frame_candidate"
    CREATIVE_CONCEPT = "creative_concept"
    CREATIVE_PROMPT = "creative_prompt"
    REFERENCE_IMAGE = "reference_image"
    DESIGNER_BRIEF = "designer_brief"
    THUMBNAIL_REVIEW = "thumbnail_review"


class PackagingAssetStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PackagingRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    ANALYZING = "analyzing"
    EXTRACTING_FRAMES = "extracting_frames"
    BUILDING_CONCEPTS = "building_concepts"
    BUILDING_PROMPT = "building_prompt"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PackagingRecommendationStatus(str, Enum):
    APPROVED_AS_IS = "approved_as_is"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    VIABLE_BUT_OFF_BRAND = "viable_but_off_brand"
    VISUALLY_STRONG_BUT_MISLEADING = "visually_strong_but_misleading"
    ON_BRAND_BUT_WEAK = "on_brand_but_weak"
    NEEDS_MORE_CONTEXT = "needs_more_context"
    NOT_RECOMMENDED = "not_recommended"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PackagingReviewDecision(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    SELECTED = "selected"
    PUBLISHED = "published"
    NEEDS_MORE_WORK = "needs_more_work"
    NOT_APPLICABLE = "not_applicable"


class PackagingDecisionType(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    SELECTED = "selected"
    PUBLISHED = "published"
    NEEDS_MORE_WORK = "needs_more_work"
    NOT_APPLICABLE = "not_applicable"


class PackagingPromptTargetTool(str, Enum):
    GENERIC_IMAGE_TOOL = "generic_image_tool"
    CHATGPT_IMAGES = "chatgpt_images"
    ENVATO_AI = "envato_ai"
    MANUAL_DESIGNER = "manual_designer"
    MANUAL_CREATION = "manual_creation"
    OTHER = "other"

