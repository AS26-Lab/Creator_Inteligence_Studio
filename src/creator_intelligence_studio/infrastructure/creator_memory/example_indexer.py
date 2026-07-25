"""Indexación determinista de ejemplos de creador."""

from __future__ import annotations

import re


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def example_rank_score(*, platform_match: bool, content_type_match: bool, topic_match: bool, approval_status: str, confidence_score: float | None, representativeness: float | None, recency_days: int | None) -> float:
    score = 0.0
    score += 3.0 if platform_match else 0.0
    score += 2.0 if content_type_match else 0.0
    score += 2.0 if topic_match else 0.0
    score += 1.5 if approval_status == "approved" else 0.0
    score += (confidence_score or 0.0) * 1.5
    score += (representativeness or 0.0) * 2.0
    if recency_days is not None:
        score += max(0.0, 1.0 - min(recency_days, 365) / 365.0)
    return score

