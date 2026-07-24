"""Deteccion simple de contradicciones de aprendizaje."""

from __future__ import annotations


def detect_contradictions(
    *,
    supporting_example_count: int,
    contradicting_example_count: int,
    unresolved_examples: int = 0,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if contradicting_example_count > supporting_example_count:
        warnings.append("contradictory_results")
    if unresolved_examples:
        warnings.append("incomplete_execution")
    return tuple(sorted(set(warnings)))

