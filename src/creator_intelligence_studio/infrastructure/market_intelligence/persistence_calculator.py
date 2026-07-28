"""Persistencia observada de una señal."""

from __future__ import annotations


def calculate_persistence(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    if len(valid) < 2:
        return None
    direction_changes = 0
    last_direction = 0
    for previous, current in zip(valid, valid[1:], strict=False):
        if current == previous:
            continue
        direction = 1 if current > previous else -1
        if last_direction and direction != last_direction:
            direction_changes += 1
        last_direction = direction
    stability = max(0, len(valid) - 1 - direction_changes) / max(1, len(valid) - 1)
    return round(stability, 3)

