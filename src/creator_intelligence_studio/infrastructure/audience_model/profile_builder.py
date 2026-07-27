"""Construccion de perfiles de audiencia."""

from __future__ import annotations

import json
from collections import Counter
from statistics import mean


def build_profile_summary(*, signals: list[dict[str, object]], segments: list[dict[str, object]], affinities: list[dict[str, object]], journeys: list[dict[str, object]], contradictions: list[dict[str, object]], warnings: list[str], questions: list[str]) -> str:
    platform_counts = Counter(str(signal.get("platform") or "unknown") for signal in signals)
    parts = [
        f"signals={len(signals)}",
        f"segments={len(segments)}",
        f"affinities={len(affinities)}",
        f"journeys={len(journeys)}",
        f"platforms={','.join(sorted(platform_counts)) if platform_counts else 'none'}",
    ]
    if warnings:
        parts.append("warnings=" + ",".join(sorted(set(warnings))))
    if contradictions:
        parts.append(f"contradictions={len(contradictions)}")
    if questions:
        parts.append(f"questions={len(questions)}")
    return " | ".join(parts)


def build_snapshot_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

