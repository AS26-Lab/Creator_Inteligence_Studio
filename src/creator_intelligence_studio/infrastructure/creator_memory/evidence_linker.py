"""Linker determinista de evidencia para Creator Memory."""

from __future__ import annotations

from creator_intelligence_studio.domain.creator_memory.evidence_types import CreatorEvidenceLink
from creator_intelligence_studio.domain.creator_memory.value_objects import CreatorEvidenceType
from creator_intelligence_studio.shared.dates import utc_now


def build_evidence_link(
    *,
    source_type: str,
    source_id: str | None,
    publication_id: str | None = None,
    video_asset_id: str | None = None,
    transcript_segment_id: str | None = None,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    quoted_text: str | None = None,
    evidence_type: str | CreatorEvidenceType,
    supports_trait: bool,
    weight: float = 1.0,
    notes: str | None = None,
) -> CreatorEvidenceLink:
    return CreatorEvidenceLink(
        source_type=source_type,
        source_id=source_id,
        publication_id=publication_id,
        video_asset_id=video_asset_id,
        transcript_segment_id=transcript_segment_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        quoted_text=quoted_text,
        evidence_type=CreatorEvidenceType(evidence_type) if not isinstance(evidence_type, CreatorEvidenceType) else evidence_type,
        supports_trait=supports_trait,
        weight=weight,
        notes=notes,
        created_at=utc_now(),
    )

