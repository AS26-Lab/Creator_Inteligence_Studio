from __future__ import annotations


def detect_contradictions(candidate: dict[str, object]) -> list[str]:
    contradictions: list[str] = []
    if float(candidate.get("copying_risk", 0.0) or 0.0) >= 0.75:
        contradictions.append("high_momentum_high_copying_risk")
    if candidate.get("freshness_status") in {"stale", "expired"}:
        contradictions.append("stale_data_conflict")
    return contradictions
