"""Objetos de valor para analytics manual y aprendizaje."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AnalyticsPlatformStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISABLED = "disabled"


class AnalyticsSourceType(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    MANUAL = "manual"


class AnalyticsContentType(str, Enum):
    LONGFORM_VIDEO = "longform_video"
    SHORT_VIDEO = "short_video"
    REEL = "reel"
    TIKTOK = "tiktok"
    LIVE_REPLAY = "live_replay"
    COMMUNITY_POST = "community_post"
    OTHER = "other"


class AnalyticsMetricCategory(str, Enum):
    DISCOVERY = "discovery"
    ATTENTION = "attention"
    CONVERSION = "conversion"
    INTERACTION = "interaction"
    RELATION = "relation"
    CONTEXT = "context"


class AnalyticsValueType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    CATEGORY = "category"


class AnalyticsAggregationType(str, Enum):
    LATEST = "latest"
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    COUNT = "count"


class AnalyticsQualityStatus(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"


class AnalyticsImportStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class AnalyticsImportRowStatus(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"


class AnalyticsFieldMappingOrigin(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class AnalyticsPlatformPreset:
    platform_key: str
    display_name: str
    default_content_types: tuple[AnalyticsContentType, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "platform_key": self.platform_key,
            "display_name": self.display_name,
            "default_content_types": [item.value for item in self.default_content_types],
        }


PLATFORM_PRESETS: tuple[AnalyticsPlatformPreset, ...] = (
    AnalyticsPlatformPreset("youtube_longform", "YouTube Longform", (AnalyticsContentType.LONGFORM_VIDEO,)),
    AnalyticsPlatformPreset("youtube_short", "YouTube Shorts", (AnalyticsContentType.SHORT_VIDEO,)),
    AnalyticsPlatformPreset("tiktok", "TikTok", (AnalyticsContentType.TIKTOK, AnalyticsContentType.SHORT_VIDEO)),
    AnalyticsPlatformPreset("instagram_reel", "Instagram Reels", (AnalyticsContentType.REEL, AnalyticsContentType.SHORT_VIDEO)),
    AnalyticsPlatformPreset("manual_other", "Manual / Other", (AnalyticsContentType.OTHER,)),
)
