"""Reglas puras del dominio para Creator Memory."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict

from .entities import CreatorProfile, CreatorProfileSnapshot


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def build_creator_memory_fingerprint(payload: dict[str, object]) -> str:
    canonical = _stable_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_profile_snapshot_fingerprint(profile: CreatorProfile, *, traits: Iterable[dict[str, object]], examples: Iterable[dict[str, object]], vocabulary: Iterable[dict[str, object]], rules: Iterable[dict[str, object]], limits: Iterable[dict[str, object]], evidence: Iterable[dict[str, object]]) -> str:
    payload = {
        "profile": profile.to_dict(),
        "traits": list(traits),
        "examples": list(examples),
        "vocabulary": list(vocabulary),
        "rules": list(rules),
        "limits": list(limits),
        "evidence": list(evidence),
    }
    return build_creator_memory_fingerprint(payload)


def snapshot_payload(profile: CreatorProfile, *, traits: list[dict[str, object]], examples: list[dict[str, object]], vocabulary: list[dict[str, object]], rules: list[dict[str, object]], limits: list[dict[str, object]], evidence: list[dict[str, object]], feedback: list[dict[str, object]]) -> dict[str, object]:
    return {
        "profile": profile.to_dict(),
        "traits": traits,
        "examples": examples,
        "vocabulary": vocabulary,
        "rules": rules,
        "limits": limits,
        "evidence": evidence,
        "feedback": feedback,
    }

