"""Metadatos de metricas oficiales de YouTube."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class YouTubeMetricScope(str, Enum):
    CHANNEL = "channel"
    VIDEO = "video"
    BOTH = "both"


class YouTubeMetricAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE_FROM_API = "unavailable_from_api"
    UNSUPPORTED_DIMENSION = "unsupported_dimension"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    DATA_NOT_READY = "data_not_ready"
    RESTRICTED_METRIC = "restricted_metric"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class YouTubeMetricSpec:
    internal_key: str
    raw_metric_name: str
    unit: str
    scope: YouTubeMetricScope
    availability: YouTubeMetricAvailability = YouTubeMetricAvailability.AVAILABLE
    dimensions: tuple[str, ...] = ()
    description: str = ""


YOUTUBE_METRIC_MAP: tuple[YouTubeMetricSpec, ...] = (
    YouTubeMetricSpec("views", "views", "count", YouTubeMetricScope.BOTH, description="Views."),
    YouTubeMetricSpec("engaged_views", "engagedViews", "count", YouTubeMetricScope.VIDEO, description="Engaged views."),
    YouTubeMetricSpec("estimated_minutes_watched", "estimatedMinutesWatched", "minutes", YouTubeMetricScope.BOTH, description="Estimated minutes watched."),
    YouTubeMetricSpec("average_view_duration_seconds", "averageViewDuration", "seconds", YouTubeMetricScope.BOTH, description="Average view duration."),
    YouTubeMetricSpec("average_percentage_viewed", "viewerPercentage", "percent", YouTubeMetricScope.BOTH, description="Average percentage viewed."),
    YouTubeMetricSpec("likes", "likes", "count", YouTubeMetricScope.BOTH, description="Likes."),
    YouTubeMetricSpec("comments", "comments", "count", YouTubeMetricScope.BOTH, description="Comments."),
    YouTubeMetricSpec("shares", "shares", "count", YouTubeMetricScope.BOTH, description="Shares."),
    YouTubeMetricSpec("subscribers_gained", "subscribersGained", "count", YouTubeMetricScope.BOTH, description="Subscribers gained."),
    YouTubeMetricSpec("subscribers_lost", "subscribersLost", "count", YouTubeMetricScope.BOTH, description="Subscribers lost."),
    YouTubeMetricSpec("impressions", "impressions", "count", YouTubeMetricScope.VIDEO, description="Impressions."),
    YouTubeMetricSpec("impressions_ctr", "impressionClickThroughRate", "percent", YouTubeMetricScope.VIDEO, description="Impression CTR."),
    YouTubeMetricSpec("returning_viewers", "returningViewers", "count", YouTubeMetricScope.CHANNEL, availability=YouTubeMetricAvailability.UNKNOWN, description="Returning viewers."),
    YouTubeMetricSpec("unique_viewers", "uniqueViewers", "count", YouTubeMetricScope.BOTH, availability=YouTubeMetricAvailability.UNKNOWN, description="Unique viewers."),
    YouTubeMetricSpec("traffic_source", "trafficSourceType", "category", YouTubeMetricScope.BOTH, availability=YouTubeMetricAvailability.UNSUPPORTED_DIMENSION, description="Traffic source."),
)

