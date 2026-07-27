"""Construccion determinista de segmentos."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from uuid import uuid4

from creator_intelligence_studio.domain.audience_model.audience_types import AudienceConfidenceLevel, AudienceStatus
from creator_intelligence_studio.domain.audience_model.entities import AudienceSegment, AudienceSegmentDefinition
from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudienceLifecycleStage
from creator_intelligence_studio.domain.audience_model.segment_types import AudienceSegmentScope, AudienceSegmentType
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


def build_segment(
    *,
    creator_id: str,
    name: str,
    segment_type: AudienceSegmentType,
    scope: AudienceSegmentScope,
    description: str,
    platform: str | None,
    content_type: str | None,
    topic: str | None,
    lifecycle_stage: AudienceLifecycleStage | None,
    confidence_score: float,
    supporting_signal_count: int,
    contradicting_signal_count: int,
    first_observed_at: datetime | None,
    last_observed_at: datetime | None,
) -> AudienceSegment:
    timestamp = utc_now()
    return AudienceSegment(
        id=str(uuid4()),
        creator_id=creator_id,
        name=name,
        segment_type=segment_type,
        description=description,
        scope=scope,
        platform=platform,
        content_type=content_type,
        topic=topic,
        lifecycle_stage=lifecycle_stage,
        status=AudienceStatus.ACTIVE,
        confidence_level=_confidence_level(confidence_score),
        confidence_score=round(confidence_score, 3),
        supporting_signal_count=supporting_signal_count,
        contradicting_signal_count=contradicting_signal_count,
        first_observed_at=first_observed_at,
        last_observed_at=last_observed_at,
        created_at=timestamp,
        updated_at=timestamp,
    )


def build_definition(segment_id: str, rule_type: str, field_key: str, operator: str, value: object) -> AudienceSegmentDefinition:
    return AudienceSegmentDefinition(
        id=str(uuid4()),
        segment_id=segment_id,
        rule_type=rule_type,
        field_key=field_key,
        operator=operator,
        value_json=json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at=utc_now(),
    )
