"""Tipos de metricas."""

from __future__ import annotations

from enum import Enum


class MetricRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GUARDRAIL = "guardrail"
    DIAGNOSTIC = "diagnostic"
    LEARNING = "learning"
    INVALIDATION = "invalidation"


class MetricAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MANUAL_IMPORT_REQUIRED = "manual_import_required"
    UNAVAILABLE = "unavailable"
    PROXY_ONLY = "proxy_only"
