"""Evaluacion conjunta de titulo + miniatura."""

from __future__ import annotations

import json
from statistics import mean

from creator_intelligence_studio.domain.creative_packaging.evaluation_types import PackagingPairEvaluationResult


def _score_from(value: float | None, scale: float = 100.0) -> float | None:
    if value is None:
        return None
    return max(0.0, min(scale, value))


def evaluate_title_thumbnail_pair(
    *,
    title_analysis: dict[str, object],
    thumbnail_analysis: dict[str, object],
    brand_profile: dict[str, object] | None,
    history_summary: dict[str, object] | None,
    publication: dict[str, object] | None,
    title_text: str,
    thumbnail_text: str | None = None,
) -> PackagingPairEvaluationResult:
    title_metrics = {metric["metric_key"]: metric for metric in title_analysis.get("metrics", [])}
    thumb_metrics = {metric["metric_key"]: metric for metric in thumbnail_analysis.get("metrics", [])}
    clarity = 100.0 * float(title_metrics.get("specificity_score", {}).get("numeric_value") or 0.5)
    curiosity = 100.0 * (0.65 if title_analysis.get("pattern_type") in {"question", "curiosity_gap", "conflict"} else 0.45)
    visual_quality = 100.0 * float(thumb_metrics.get("contrast", {}).get("numeric_value") or 0.5)
    content_alignment = 100.0 * (0.8 if title_text and len(title_text) > 3 else 0.4)
    brand_alignment = 100.0 * float((brand_profile or {}).get("completeness") or 0.35)
    audience_fit = 100.0 * 0.6
    platform_fit = 100.0 * (0.75 if publication and publication.get("platform") in {"youtube_longform", "youtube_short", "instagram_reel", "tiktok"} else 0.5)
    historical_fit = 100.0 * float((history_summary or {}).get("fit_score") or 0.45)
    niche_fit = 100.0 * 0.5
    differentiation = 100.0 * (0.65 if "copying_risk" not in thumbnail_analysis.get("warnings", []) else 0.2)
    hierarchy = 100.0 * float(thumb_metrics.get("visual_density", {}).get("numeric_value") or 0.5)
    complement = 100.0 * (0.7 if title_analysis.get("recommendation_status") != "insufficient_evidence" else 0.4)
    authenticity = 100.0 * (0.75 if brand_alignment >= 50 else 0.45)
    promise_alignment = 100.0 * (0.75 if "misleading" not in thumbnail_analysis.get("warnings", []) else 0.3)
    warnings = []
    risks = []
    if title_analysis.get("recommendation_status") == "insufficient_evidence":
        warnings.append("missing_title_context")
    if "copying_risk" in thumbnail_analysis.get("warnings", []):
        risks.append("copying_risk")
    if brand_alignment < 50:
        warnings.append("incomplete_brand_profile")
    recommendation_status = "approved_as_is"
    if risks:
        recommendation_status = "not_recommended"
    elif brand_alignment < 55:
        recommendation_status = "needs_more_context"
    elif visual_quality < 40:
        recommendation_status = "visually_strong_but_misleading"
    evidence = {
        "title_pattern": title_analysis.get("pattern_type"),
        "title_metrics": title_analysis.get("metrics", []),
        "thumbnail_metrics": thumbnail_analysis.get("metrics", []),
        "brand_profile_present": bool(brand_profile),
        "publication_platform": publication.get("platform") if publication else None,
    }
    limitations = []
    if not brand_profile:
        limitations.append("incomplete_brand_profile")
    return PackagingPairEvaluationResult(
        visual_quality_score=_score_from(visual_quality),
        content_alignment_score=_score_from(content_alignment),
        creator_brand_alignment_score=_score_from(brand_alignment),
        audience_fit_score=_score_from(audience_fit),
        platform_fit_score=_score_from(platform_fit),
        historical_fit_score=_score_from(historical_fit),
        niche_fit_score=_score_from(niche_fit),
        differentiation_score=_score_from(differentiation),
        clarity_score=_score_from(clarity),
        curiosity_score=_score_from(curiosity),
        hierarchy_score=_score_from(hierarchy),
        complement_score=_score_from(complement),
        authenticity_score=_score_from(authenticity),
        promise_alignment_score=_score_from(promise_alignment),
        evidence=evidence,
        warnings=tuple(sorted(set(warnings))),
        risks=tuple(sorted(set(risks))),
        limitations=tuple(sorted(set(limitations))),
        recommendation_status=recommendation_status,
    )

