"""Tipos de capacidades para la consolidacion de plataformas."""

from __future__ import annotations

from enum import Enum


class CapabilityCategory(str, Enum):
    AUTHENTICATION = "authentication"
    CONTENT = "content"
    METRICS = "metrics"
    SYNC = "sync"
    WRITE = "write"


class CapabilityAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    UNAVAILABLE = "unavailable"
    MANUAL_IMPORT_ONLY = "manual_import_only"
    PERMISSION_REQUIRED = "permission_required"
    APPROVAL_REQUIRED = "approval_required"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ComparabilityStatus(str, Enum):
    DIRECTLY_COMPARABLE = "directly_comparable"
    COMPARABLE_WITH_NORMALIZATION = "comparable_with_normalization"
    DIRECTIONAL_ONLY = "directional_only"
    NOT_COMPARABLE = "not_comparable"
    UNKNOWN = "unknown"
