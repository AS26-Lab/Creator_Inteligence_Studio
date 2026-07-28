from __future__ import annotations


def rank_candidates(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(candidates, key=lambda item: float(item.get("priority_score") or 0.0), reverse=True)
