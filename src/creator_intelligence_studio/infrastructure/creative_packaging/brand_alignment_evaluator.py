"""Construccion de perfil de marca para packaging."""

from __future__ import annotations

import json
from dataclasses import dataclass

from creator_intelligence_studio.domain.creative_packaging.brand_alignment_types import BrandAlignmentResult


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_brand_alignment_profile(
    *,
    creator_id: str,
    memory_detail: object | None = None,
    language_detail: object | None = None,
    references: list[dict[str, object]] | None = None,
    titles: list[dict[str, object]] | None = None,
    thumbnails: list[dict[str, object]] | None = None,
    analytics_summary: dict[str, object] | None = None,
    experiments_summary: dict[str, object] | None = None,
) -> BrandAlignmentResult:
    references = references or []
    titles = titles or []
    thumbnails = thumbnails or []
    visual_identity = {
        "creator_id": creator_id,
        "tone": getattr(memory_detail.profile, "default_tone", None) if memory_detail else None,
        "formality": getattr(memory_detail.profile, "default_formality", None) if memory_detail else None,
        "languages": {
            "primary": getattr(memory_detail.profile, "primary_language", None) if memory_detail else None,
            "secondary": json.loads(getattr(memory_detail.profile, "secondary_languages_json", "[]")) if memory_detail else [],
        },
        "style_rules": len(getattr(memory_detail, "rules", []) or []),
        "approved_examples": len([item for item in getattr(memory_detail, "examples", []) or [] if getattr(item, "approval_status", None) and item.approval_status.value == "approved"]),
        "references": len(references),
        "titles": len(titles),
        "thumbnails": len(thumbnails),
        "analytics_summary": analytics_summary or {},
        "experiments_summary": experiments_summary or {},
    }
    platform_differences = {
        "youtube_longform": {"text_density": "medium", "text_overlay": "low"},
        "youtube_short": {"text_density": "high", "text_overlay": "medium"},
        "instagram_reel": {"text_density": "medium", "text_overlay": "medium"},
        "tiktok": {"text_density": "medium", "text_overlay": "medium"},
    }
    completeness = 1.0 if references or titles or thumbnails else 0.35
    warnings = ()
    summary = "Perfil de marca derivado de memoria, lenguaje y historial."
    if completeness < 0.5:
        warnings = ("incomplete_brand_profile",)
        summary = "Perfil de marca incompleto; faltan referencias y/o historial."
    return BrandAlignmentResult(
        visual_identity=visual_identity,
        platform_differences=platform_differences,
        completeness=completeness,
        warnings=warnings,
        summary=summary,
    )

