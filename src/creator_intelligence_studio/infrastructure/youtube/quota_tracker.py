"""Estimacion local de cuota para sincronizacion de YouTube."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuotaEstimate:
    operation_key: str
    estimated_cost: float
    request_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_key": self.operation_key,
            "estimated_cost": self.estimated_cost,
            "request_count": self.request_count,
        }


class QuotaTracker:
    def __init__(self) -> None:
        self._estimate: dict[str, QuotaEstimate] = {}

    def estimate(self, operation_key: str, *, estimated_cost: float, request_count: int = 1) -> QuotaEstimate:
        estimate = QuotaEstimate(operation_key, estimated_cost, request_count)
        self._estimate[operation_key] = estimate
        return estimate

    def get(self, operation_key: str) -> QuotaEstimate | None:
        return self._estimate.get(operation_key)

