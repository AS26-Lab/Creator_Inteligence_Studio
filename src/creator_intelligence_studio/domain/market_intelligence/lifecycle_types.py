"""Etapas de ciclo de vida."""

from __future__ import annotations

from enum import Enum


class LifecycleStage(str, Enum):
    UNKNOWN = "unknown"
    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    DECLINING = "declining"
    SATURATED = "saturated"
    SEASONAL = "seasonal"
    EPHEMERAL = "ephemeral"

