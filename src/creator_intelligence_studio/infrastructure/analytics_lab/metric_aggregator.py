"""Agregaciones y metricas derivadas para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, median

from .percentile_calculator import calculate_percentile, median_absolute_deviation, robust_z_score


@dataclass(frozen=True, slots=True)
class MetricSummary:
    metric_key: str
    values: tuple[float, ...]
    count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    lower_quartile: float | None
    upper_quartile: float | None
    percentile_90: float | None
    mad: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_key": self.metric_key,
            "values": list(self.values),
            "count": self.count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "mean": self.mean,
            "median": self.median,
            "lower_quartile": self.lower_quartile,
            "upper_quartile": self.upper_quartile,
            "percentile_90": self.percentile_90,
            "mad": self.mad,
        }


def summarize_metric(metric_key: str, values: list[float]) -> MetricSummary:
    cleaned = tuple(float(value) for value in values)
    if not cleaned:
        return MetricSummary(metric_key, (), 0, None, None, None, None, None, None, None, None)
    ordered = list(sorted(cleaned))
    return MetricSummary(
        metric_key=metric_key,
        values=cleaned,
        count=len(cleaned),
        minimum=ordered[0],
        maximum=ordered[-1],
        mean=float(mean(cleaned)),
        median=float(median(cleaned)),
        lower_quartile=calculate_percentile(ordered, 25.0),
        upper_quartile=calculate_percentile(ordered, 75.0),
        percentile_90=calculate_percentile(ordered, 90.0),
        mad=median_absolute_deviation(ordered),
    )


def derived_engagement_rate_by_views(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    if not views:
        return None, ("missing_denominator",)
    numerator = sum(float(metrics.get(key) or 0.0) for key in ("likes", "comments", "shares", "saves"))
    return numerator / float(views), ()


def derived_subscriber_conversion_rate(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    subscribers = metrics.get("subscribers_gained")
    if not views or subscribers is None:
        return None, ("missing_denominator",)
    return float(subscribers) / float(views), ()


def derived_follower_conversion_rate(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    followers = metrics.get("followers_gained")
    if not views or followers is None:
        return None, ("missing_denominator",)
    return float(followers) / float(views), ()


def derived_watch_time_per_view(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    watch_time_minutes = metrics.get("watch_time_minutes")
    if not views or watch_time_minutes is None:
        return None, ("missing_denominator",)
    return (float(watch_time_minutes) * 60.0) / float(views), ()


def derived_views_per_day(metrics: dict[str, float | None], *, published_at: datetime) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    if views is None:
        return None, ("missing_denominator",)
    age_days = max(1, (datetime.now(timezone.utc) - published_at).days)
    return float(views) / float(age_days), ()


def derived_share_rate(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    shares = metrics.get("shares")
    if not views or shares is None:
        return None, ("missing_denominator",)
    return float(shares) / float(views), ()


def derived_save_rate(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    saves = metrics.get("saves")
    if not views or saves is None:
        return None, ("missing_denominator",)
    return float(saves) / float(views), ()


def derived_comment_rate(metrics: dict[str, float | None]) -> tuple[float | None, tuple[str, ...]]:
    views = metrics.get("views")
    comments = metrics.get("comments")
    if not views or comments is None:
        return None, ("missing_denominator",)
    return float(comments) / float(views), ()


def derived_completion_gap(completion_rate: float | None, cohort_median_completion_rate: float | None) -> tuple[float | None, tuple[str, ...]]:
    if completion_rate is None or cohort_median_completion_rate is None:
        return None, ("missing_reference",)
    return float(completion_rate) - float(cohort_median_completion_rate), ()


def derived_metric_payloads(metrics: dict[str, float | None], *, published_at: datetime) -> dict[str, tuple[float | None, tuple[str, ...]]]:
    payload = {
        "engagement_rate_by_views": derived_engagement_rate_by_views(metrics),
        "subscriber_conversion_rate": derived_subscriber_conversion_rate(metrics),
        "follower_conversion_rate": derived_follower_conversion_rate(metrics),
        "watch_time_per_view": derived_watch_time_per_view(metrics),
        "views_per_day": derived_views_per_day(metrics, published_at=published_at),
        "share_rate": derived_share_rate(metrics),
        "save_rate": derived_save_rate(metrics),
        "comment_rate": derived_comment_rate(metrics),
    }
    return payload
