from __future__ import annotations


def calculate_risk(*, copying_risk: float, saturation: float, measurement_gap: bool) -> float:
    return max(0.0, min(1.0, copying_risk * 0.6 + saturation * 0.25 + (0.15 if measurement_gap else 0.0)))
