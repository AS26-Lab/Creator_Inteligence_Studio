"""Detector simple de contradicciones para Creator Memory."""

from __future__ import annotations


def detect_contradiction_classification(*, platform: str | None, content_type: str | None, topic: str | None, first_observed_at, last_observed_at, supports: int, contradicts: int) -> str | None:
    if supports and contradicts:
        if platform and content_type:
            return "platform_difference"
        if topic:
            return "contextual_difference"
        if first_observed_at and last_observed_at and first_observed_at != last_observed_at:
            return "temporal_change"
        return "unresolved"
    return None

