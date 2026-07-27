"""Tipos de metricas para TikTok."""

from __future__ import annotations

from enum import Enum


class TikTokMetricScope(str, Enum):
    PROFILE = "profile"
    VIDEO = "video"
    MANUAL_SNAPSHOT = "manual_snapshot"


class TikTokMetricSourceType(str, Enum):
    TIKTOK_DISPLAY_API = "tiktok_display_api"
    TIKTOK_MANUAL_CSV = "tiktok_manual_csv"
    TIKTOK_MANUAL_XLSX = "tiktok_manual_xlsx"
    MANUAL_OTHER = "manual_other"


class TikTokMetricStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE_FROM_DISPLAY_API = "unavailable_from_display_api"
    MANUAL_IMPORT_AVAILABLE = "manual_import_available"
    METRIC_NOT_SUPPORTED = "metric_not_supported"
    MISSING_SCOPE = "missing_scope"
    DATA_NOT_RETURNED = "data_not_returned"
    UNKNOWN = "unknown"

