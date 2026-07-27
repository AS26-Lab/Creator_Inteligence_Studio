"""Tipos de disponibilidad de datos para plataformas."""

from __future__ import annotations

from enum import Enum


class DataCategory(str, Enum):
    PROFILE = "profile"
    CONTENT = "content"
    PUBLIC_METRICS = "public_metrics"
    PRIVATE_ANALYTICS = "private_analytics"
    RETENTION = "retention"
    TRAFFIC_SOURCES = "traffic_sources"
    AUDIENCE = "audience"
    SCHEDULES = "schedules"
    MANUAL_IMPORT = "manual_import"


class DataAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    UNAVAILABLE = "unavailable"
    MANUAL_IMPORT_ONLY = "manual_import_only"
    PERMISSION_REQUIRED = "permission_required"
    APPROVAL_REQUIRED = "approval_required"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class DataAvailabilitySourceType(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    NATIVE = "native"
    MANUAL_IMPORT = "manual_import"
