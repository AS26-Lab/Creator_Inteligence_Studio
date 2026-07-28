"""Tipos de riesgo."""

from __future__ import annotations

from enum import Enum


class RiskType(str, Enum):
    COPYING = "copying"
    BRAND = "brand"
    AUTHENTICITY = "authenticity"
    AUDIENCE_MISMATCH = "audience_mismatch"
    PLATFORM_MISMATCH = "platform_mismatch"
    OPERATIONAL_COMPLEXITY = "operational_complexity"
    RESOURCE = "resource"
    TIMING = "timing"
    SATURATION = "saturation"
    TREND_DECAY = "trend_decay"
    MEASUREMENT = "measurement"
    DATA_QUALITY = "data_quality"
    EVIDENCE = "evidence"
    REPUTATION = "reputation"
    CREATOR_BOUNDARY = "creator_boundary"
    OVEREXPOSURE = "overexposure"
    REPETITION = "repetition"
    CANNIBALIZATION = "cannibalization"
    DEPENDENCY = "dependency"
    LEGAL_OR_RIGHTS = "legal_or_rights"
    PRIVACY = "privacy"
    UNKNOWN = "unknown"


class RiskSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
