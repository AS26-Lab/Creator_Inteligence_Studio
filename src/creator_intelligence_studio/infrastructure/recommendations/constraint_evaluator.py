from __future__ import annotations


def evaluate_constraints(constraints: list[dict[str, object]]) -> dict[str, object]:
    return {"blocking": any(bool(item.get("blocking")) and not bool(item.get("satisfied", True)) for item in constraints), "count": len(constraints)}
