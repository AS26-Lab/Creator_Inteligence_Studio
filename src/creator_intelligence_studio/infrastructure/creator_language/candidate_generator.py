"""Generador heuristico de candidatos para Creator Memory."""

from __future__ import annotations

from creator_intelligence_studio.domain.creator_language.value_objects import (
    CreatorLanguageCandidateStatus,
    CreatorLanguageConfidenceLevel,
    CreatorLanguageScope,
    CreatorLanguageTargetMemoryType,
)


def generate_language_candidates(*, creator_id: str, analysis_run_id: str, profile_payload: dict[str, object], evidence_payloads: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    section_map = {
        "opening": ("opening_style", CreatorLanguageTargetMemoryType.TRAIT),
        "development": ("content_structure", CreatorLanguageTargetMemoryType.STYLE_RULE),
        "explanation": ("explanation_style", CreatorLanguageTargetMemoryType.TRAIT),
        "humor": ("humor", CreatorLanguageTargetMemoryType.TRAIT),
        "pacing": ("pacing_preference", CreatorLanguageTargetMemoryType.TRAIT),
        "closing": ("closing_style", CreatorLanguageTargetMemoryType.TRAIT),
    }
    for section_name, (proposed_key, target) in section_map.items():
        section = profile_payload.get(section_name, [])
        if not section:
            continue
        section_entry = section[0] if isinstance(section, list) else section
        candidates.append(
            {
                "creator_id": creator_id,
                "analysis_run_id": analysis_run_id,
                "candidate_type": f"{section_name}_candidate",
                "target_memory_type": target.value,
                "proposed_key": proposed_key,
                "proposed_value_json": str(section_entry),
                "scope": CreatorLanguageScope.CREATOR_GENERAL.value,
                "platform": None,
                "content_type": None,
                "topic": None,
                "evidence_json": str(evidence_payloads[:3]),
                "confidence_level": CreatorLanguageConfidenceLevel.LOW.value,
                "status": CreatorLanguageCandidateStatus.PENDING.value,
                "review_reason": None,
            }
        )
    return candidates
