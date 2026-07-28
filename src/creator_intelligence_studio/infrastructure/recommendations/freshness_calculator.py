from __future__ import annotations


def calculate_freshness(*, freshness_status: str) -> float:
    mapping = {"fresh": 1.0, "recent": 0.85, "aging": 0.65, "stale": 0.3, "expired": 0.0, "evergreen": 0.9, "seasonal": 0.7}
    return mapping.get(freshness_status, 0.5)
