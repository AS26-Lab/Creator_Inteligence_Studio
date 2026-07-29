"""Dominio de Content Brief and Pre-Production Foundation."""

from __future__ import annotations

from .errors import (
    ContentBriefConflictError,
    ContentBriefError,
    ContentBriefNotFoundError,
    ContentBriefStateError,
    ContentBriefValidationError,
)
from .value_objects import (
    ApprovalGateType,
    AngleType,
    AssetType,
    AudienceType,
    BoundaryType,
    BriefRequestStatus,
    BriefStatus,
    BriefType,
    ClaimType,
    ClaimVerificationStatus,
    CopyingRiskLevel,
    DependencyType,
    HookType,
    MessageLevel,
    NarrativeOutlineType,
    ProductionRequirementType,
    ReadinessStatus,
    ReviewDecision,
    RightsStatus,
    RightsType,
    RiskType,
    SectionType,
    PromiseType,
)
from .entities import BriefRecord
from .repositories import ContentBriefRepository
from .services import build_brief_fingerprint

__all__ = [
    "ContentBriefError",
    "ContentBriefValidationError",
    "ContentBriefNotFoundError",
    "ContentBriefStateError",
    "ContentBriefConflictError",
    "ApprovalGateType",
    "AngleType",
    "AssetType",
    "AudienceType",
    "BoundaryType",
    "BriefRequestStatus",
    "BriefStatus",
    "BriefType",
    "ClaimType",
    "ClaimVerificationStatus",
    "CopyingRiskLevel",
    "DependencyType",
    "HookType",
    "MessageLevel",
    "NarrativeOutlineType",
    "ProductionRequirementType",
    "ReadinessStatus",
    "ReviewDecision",
    "RightsStatus",
    "RightsType",
    "RiskType",
    "SectionType",
    "PromiseType",
    "BriefRecord",
    "ContentBriefRepository",
    "build_brief_fingerprint",
]

