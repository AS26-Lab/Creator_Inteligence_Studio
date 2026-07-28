"""Detector de contradicciones entre evidencias."""

from __future__ import annotations

from typing import Any


def detect_contradictions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    for item in items:
        if item.get("supports_signal") is False or item.get("supports_candidate") is False:
            contradictions.append(
                {
                    "source_id": item.get("source_id"),
                    "notes": item.get("notes"),
                    "reason": "explicit_contradiction",
                }
            )
    return contradictions

