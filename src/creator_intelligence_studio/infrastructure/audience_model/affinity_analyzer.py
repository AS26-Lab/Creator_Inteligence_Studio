"""Construccion local de afinidades observables."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean
from uuid import uuid4

from creator_intelligence_studio.domain.audience_model.audience_types import AudienceConfidenceLevel, AudienceStatus
from creator_intelligence_studio.domain.audience_model.entities import AudienceAffinity
from creator_intelligence_studio.shared.dates import utc_now


def _confidence_level(score: float) -> AudienceConfidenceLevel:
    if score >= 0.85:
        return AudienceConfidenceLevel.VERY_HIGH
    if score >= 0.7:
        return AudienceConfidenceLevel.HIGH
    if score >= 0.5:
        return AudienceConfidenceLevel.MEDIUM
    if score >= 0.3:
        return AudienceConfidenceLevel.LOW
    return AudienceConfidenceLevel.VERY_LOW


def build_affinity(
    *,
    creator_id: str,
    affinity_type: str,
    target_key: str,
    target_value: str,
    platform: str | None,
    content_type: str | None,
    score: float,
    supporting_example_count: int,
    contradicting_example_count: int,
    segment_id: str | None = None,
) -> AudienceAffinity:
    timestamp = utc_now()
    return AudienceAffinity(
        id=str(uuid4()),
        creator_id=creator_id,
        segment_id=segment_id,
        affinity_type=affinity_type,
        target_key=target_key,
        target_value=target_value,
        platform=platform,
        content_type=content_type,
        score=round(score, 3),
        supporting_example_count=supporting_example_count,
        contradicting_example_count=contradicting_example_count,
        confidence_level=_confidence_level(score),
        status=AudienceStatus.ACTIVE,
        created_at=timestamp,
        updated_at=timestamp,
    )

