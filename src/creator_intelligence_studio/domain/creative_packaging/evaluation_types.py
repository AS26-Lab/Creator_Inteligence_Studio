"""Tipos de evaluacion de packaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PackagingPairEvaluationResult:
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
    evidence: dict[str, object]
    warnings: tuple[str, ...]
    risks: tuple[str, ...]
    limitations: tuple[str, ...]
    recommendation_status: str

    def to_dict(self) -> dict[str, object]:
        return {
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
            "evidence": self.evidence,
            "warnings": list(self.warnings),
            "risks": list(self.risks),
            "limitations": list(self.limitations),
            "recommendation_status": self.recommendation_status,
        }


@dataclass(frozen=True, slots=True)
class CreativeConceptResult:
    concept_type: str
    title: str
    summary: str
    evidence: dict[str, object]
    confidence_level: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "concept_type": self.concept_type,
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class ThumbnailReviewResult:
    overall_status: str
    what_works: tuple[str, ...]
    what_does_not: tuple[str, ...]
    brand_fit: str
    content_fit: str
    audience_fit: str
    platform_fit: str
    historical_fit: str
    differentiation: str
    promise: str
    risks: tuple[str, ...]
    keep: tuple[str, ...]
    change: tuple[str, ...]
    revision_instructions: str
    another_generation_needed: bool
    confidence_level: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_status": self.overall_status,
            "what_works": list(self.what_works),
            "what_does_not": list(self.what_does_not),
            "brand_fit": self.brand_fit,
            "content_fit": self.content_fit,
            "audience_fit": self.audience_fit,
            "platform_fit": self.platform_fit,
            "historical_fit": self.historical_fit,
            "differentiation": self.differentiation,
            "promise": self.promise,
            "risks": list(self.risks),
            "keep": list(self.keep),
            "change": list(self.change),
            "revision_instructions": self.revision_instructions,
            "another_generation_needed": self.another_generation_needed,
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }

