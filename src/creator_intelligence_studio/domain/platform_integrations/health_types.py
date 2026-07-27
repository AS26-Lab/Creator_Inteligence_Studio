"""Tipos cerrados para salud de plataforma."""

from __future__ import annotations

from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    HEALTHY_WITH_WARNINGS = "healthy_with_warnings"
    DEGRADED = "degraded"
    ACTION_REQUIRED = "action_required"
    DISCONNECTED = "disconnected"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
