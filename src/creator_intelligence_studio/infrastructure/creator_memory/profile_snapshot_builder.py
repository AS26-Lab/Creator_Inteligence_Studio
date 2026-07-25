"""Construccion de snapshots de memoria."""

from __future__ import annotations

import json

from uuid import uuid4

from creator_intelligence_studio.domain.creator_memory.entities import (
    CreatorExample,
    CreatorLimit,
    CreatorProfile,
    CreatorProfileSnapshot,
    CreatorStyleRule,
    CreatorTrait,
    CreatorTraitEvidence,
    CreatorVocabulary,
)
from creator_intelligence_studio.domain.creator_memory.value_objects import CreatorSnapshotStatus
from creator_intelligence_studio.domain.creator_memory.services import build_profile_snapshot_fingerprint, snapshot_payload
from creator_intelligence_studio.shared.dates import utc_now


def build_profile_snapshot(
    profile: CreatorProfile,
    *,
    traits: list[CreatorTrait],
    examples: list[CreatorExample],
    vocabulary: list[CreatorVocabulary],
    rules: list[CreatorStyleRule],
    limits: list[CreatorLimit],
    evidence: list[CreatorTraitEvidence],
    feedback: list[dict[str, object]],
) -> tuple[CreatorProfileSnapshot, dict[str, object]]:
    payload = snapshot_payload(
        profile,
        traits=[item.to_dict() for item in traits],
        examples=[item.to_dict() for item in examples],
        vocabulary=[item.to_dict() for item in vocabulary],
        rules=[item.to_dict() for item in rules],
        limits=[item.to_dict() for item in limits],
        evidence=[item.to_dict() for item in evidence],
        feedback=feedback,
    )
    fingerprint = build_profile_snapshot_fingerprint(
        profile,
        traits=payload["traits"],
        examples=payload["examples"],
        vocabulary=payload["vocabulary"],
        rules=payload["rules"],
        limits=payload["limits"],
        evidence=payload["evidence"],
    )
    snapshot = CreatorProfileSnapshot(
        id=str(uuid4()),
        creator_id=profile.creator_id,
        profile_version=profile.profile_version,
        snapshot_json=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        source_fingerprint=fingerprint,
        status=CreatorSnapshotStatus.ACTIVE,
        created_at=utc_now(),
    )
    return snapshot, payload
