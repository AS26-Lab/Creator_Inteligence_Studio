"""Construccion de resúmenes y perfiles del creador."""

from __future__ import annotations

from collections.abc import Iterable

from creator_intelligence_studio.domain.creator_memory.entities import CreatorProfile
from creator_intelligence_studio.domain.creator_memory.profile_types import CreatorObjectiveEntry, CreatorProfileSummary


def build_profile_summary(
    profile: CreatorProfile,
    *,
    trait_count: int,
    example_count: int,
    vocabulary_count: int,
    rule_count: int,
    limit_count: int,
) -> CreatorProfileSummary:
    return CreatorProfileSummary(
        creator_id=profile.creator_id,
        display_name=profile.display_name,
        profile_version=profile.profile_version,
        status=profile.status.value,
        primary_language=profile.primary_language,
        default_tone=profile.default_tone,
        default_formality=profile.default_formality,
        objective_count=_objective_count(profile.objectives_json),
        trait_count=trait_count,
        example_count=example_count,
        vocabulary_count=vocabulary_count,
        rule_count=rule_count,
        limit_count=limit_count,
        updated_at=profile.updated_at,
    )


def _objective_count(objectives_json: str) -> int:
    if not objectives_json:
        return 0
    try:
        import json

        payload = json.loads(objectives_json)
        return len(payload) if isinstance(payload, list) else 0
    except Exception:
        return 0

