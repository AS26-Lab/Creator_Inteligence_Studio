from __future__ import annotations


def calculate_confidence(*, evidence_quality: str, sample_size: int) -> str:
    if evidence_quality == "high" and sample_size >= 3:
        return "high"
    if evidence_quality in {"high", "medium"} and sample_size >= 1:
        return "medium"
    return "low"
