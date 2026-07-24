"""Generacion de memoria de aprendizaje estructurada."""

from __future__ import annotations

import json

from creator_intelligence_studio.domain.experiments.value_objects import LearningType, LearningStatus


def build_learning_payload(
    *,
    experiment_id: str,
    source_type: str,
    source_id: str,
    statement: str,
    evidence: dict[str, object],
    supporting_example_count: int,
    contradicting_example_count: int,
    confidence_level: str,
    scope: str,
    platform: str | None,
    content_type: str | None,
    topic: str | None,
) -> dict[str, object]:
    learning_type = LearningType.PROVISIONAL_LEARNING if supporting_example_count >= contradicting_example_count else LearningType.NEEDS_MORE_DATA
    status = LearningStatus.PROVISIONAL if learning_type == LearningType.PROVISIONAL_LEARNING else LearningStatus.NEEDS_MORE_DATA
    return {
        "experiment_id": experiment_id,
        "source_type": source_type,
        "source_id": source_id,
        "learning_type": learning_type.value,
        "scope": scope,
        "platform": platform,
        "content_type": content_type,
        "topic": topic,
        "statement": statement,
        "evidence_json": json.dumps(evidence, ensure_ascii=False, sort_keys=True),
        "supporting_example_count": supporting_example_count,
        "contradicting_example_count": contradicting_example_count,
        "confidence_level": confidence_level,
        "confidence_score": None,
        "status": status.value,
    }

