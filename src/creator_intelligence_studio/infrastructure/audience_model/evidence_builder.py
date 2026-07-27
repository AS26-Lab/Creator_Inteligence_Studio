"""Construccion de evidencia de audiencia."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.audience_model.evidence_types import AudienceEvidenceType
from creator_intelligence_studio.domain.audience_model.entities import AudienceSegmentEvidence
from creator_intelligence_studio.shared.dates import utc_now


def build_evidence(
    *,
    segment_id: str,
    signal_id: str | None = None,
    publication_id: str | None = None,
    analytics_finding_id: str | None = None,
    experiment_id: str | None = None,
    evidence_type: AudienceEvidenceType,
    supports_segment: bool,
    weight: float,
    notes: str | None = None,
    created_at: datetime | None = None,
) -> AudienceSegmentEvidence:
    timestamp = created_at or utc_now()
    return AudienceSegmentEvidence(
        id=str(uuid4()),
        segment_id=segment_id,
        signal_id=signal_id,
        publication_id=publication_id,
        analytics_finding_id=analytics_finding_id,
        experiment_id=experiment_id,
        evidence_type=evidence_type,
        supports_segment=supports_segment,
        weight=weight,
        notes=notes,
        created_at=timestamp,
    )


def dump_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

