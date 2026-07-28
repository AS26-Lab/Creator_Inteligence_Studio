from __future__ import annotations


def build_experiment_mapping(*, recommendation_id: str, objective: str) -> dict[str, object]:
    return {"recommendation_id": recommendation_id, "objective": objective, "link_type": "converted_to_experiment"}
