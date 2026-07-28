from __future__ import annotations


def evaluate_rule_set(candidate: dict[str, object]) -> dict[str, object]:
    return {"blocked": float(candidate.get("copying_risk", 0.0) or 0.0) >= 0.75, "rule_version": "v1"}
