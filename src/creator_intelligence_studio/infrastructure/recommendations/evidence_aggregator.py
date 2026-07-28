from __future__ import annotations


def aggregate_evidence(items: list[dict[str, object]]) -> dict[str, object]:
    return {"count": len(items), "supports": sum(1 for item in items if item.get("supports_recommendation"))}
