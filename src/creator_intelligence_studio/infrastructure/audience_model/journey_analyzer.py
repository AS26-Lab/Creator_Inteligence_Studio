"""Construccion de journeys agregados."""

from __future__ import annotations

import json
from uuid import uuid4

from creator_intelligence_studio.domain.audience_model.audience_types import AudienceConfidenceLevel, AudienceStatus
from creator_intelligence_studio.domain.audience_model.entities import AudienceJourney, AudienceJourneyStep
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


def build_journey(
    *,
    creator_id: str,
    name: str,
    entry_platform: str | None,
    entry_source: str | None,
    entry_content_type: str | None,
    next_step_type: str | None,
    conversion_type: str | None,
    confidence_score: float,
    evidence: dict[str, object],
    limitations: list[str],
) -> AudienceJourney:
    timestamp = utc_now()
    return AudienceJourney(
        id=str(uuid4()),
        creator_id=creator_id,
        name=name,
        entry_platform=entry_platform,
        entry_source=entry_source,
        entry_content_type=entry_content_type,
        next_step_type=next_step_type,
        conversion_type=conversion_type,
        status=AudienceStatus.ACTIVE,
        confidence_level=_confidence_level(confidence_score),
        evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        limitations_json=json.dumps(limitations, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_journey_step(
    *,
    journey_id: str,
    step_order: int,
    platform: str,
    content_type: str | None,
    action_type: str,
    metric_key: str | None,
    observed_value: float | None,
    evidence: dict[str, object],
) -> AudienceJourneyStep:
    timestamp = utc_now()
    return AudienceJourneyStep(
        id=str(uuid4()),
        journey_id=journey_id,
        step_order=step_order,
        platform=platform,
        content_type=content_type,
        action_type=action_type,
        metric_key=metric_key,
        observed_value=observed_value,
        evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at=timestamp,
    )

