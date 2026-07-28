from __future__ import annotations


def calculate_priority_score(*, fit: float, risk: float, freshness: float, evidence: float) -> float:
    return max(0.0, min(1.0, fit * 0.45 + freshness * 0.2 + evidence * 0.2 - risk * 0.35))
