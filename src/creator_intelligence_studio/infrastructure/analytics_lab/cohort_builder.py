"""Construccion de cohortes comparables para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from creator_intelligence_studio.domain.analytics.entities import AnalyticsPublication, AnalyticsMetricSnapshot


@dataclass(frozen=True, slots=True)
class CohortSelectionResult:
    publication_ids: tuple[str, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    comparable: bool
    available_metrics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "publication_ids": list(self.publication_ids),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "comparable": self.comparable,
            "available_metrics": list(self.available_metrics),
        }


def _published_at_bounds(filters: dict[str, object]) -> tuple[datetime | None, datetime | None]:
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    return (
        datetime.fromisoformat(date_from) if isinstance(date_from, str) and date_from else None,
        datetime.fromisoformat(date_to) if isinstance(date_to, str) and date_to else None,
    )


def publication_context(publication: AnalyticsPublication, latest_metrics: dict[str, AnalyticsMetricSnapshot]) -> dict[str, object]:
    context = {
        "platform": publication.platform,
        "content_type": publication.content_type.value,
        "channel_id": publication.channel_id,
        "video_asset_id": publication.video_asset_id,
        "published_at": publication.published_at,
        "duration_seconds": publication.duration_seconds,
        "topic": None,
        "format": None,
        "language": None,
        "linked": publication.video_asset_id is not None,
    }
    for key in ("topic", "format", "language"):
        snapshot = latest_metrics.get(key)
        if snapshot is not None:
            context[key] = snapshot.text_value
    return context


def select_publications(
    publications: Iterable[AnalyticsPublication],
    latest_metrics_by_publication: dict[str, dict[str, AnalyticsMetricSnapshot]],
    filters: dict[str, object],
) -> CohortSelectionResult:
    platform = filters.get("platform")
    content_type = filters.get("content_type")
    channel_id = filters.get("channel_id")
    linked = filters.get("linked")
    duration_min = filters.get("duration_min_seconds")
    duration_max = filters.get("duration_max_seconds")
    topic = filters.get("topic")
    format_ = filters.get("format")
    language = filters.get("language")
    date_from, date_to = _published_at_bounds(filters)
    selected: list[str] = []
    warnings: list[str] = []
    available_metrics: set[str] = set()
    for publication in publications:
        context = publication_context(publication, latest_metrics_by_publication.get(publication.id, {}))
        if platform and publication.platform != platform:
            continue
        if content_type and publication.content_type.value != content_type:
            continue
        if channel_id and publication.channel_id != channel_id:
            continue
        if linked is True and publication.video_asset_id is None:
            continue
        if linked is False and publication.video_asset_id is not None:
            continue
        if duration_min is not None and (publication.duration_seconds is None or publication.duration_seconds < float(duration_min)):
            continue
        if duration_max is not None and (publication.duration_seconds is None or publication.duration_seconds > float(duration_max)):
            continue
        if topic and context.get("topic") != topic:
            continue
        if format_ and context.get("format") != format_:
            continue
        if language and context.get("language") != language:
            continue
        if date_from and publication.published_at < date_from:
            continue
        if date_to and publication.published_at > date_to:
            continue
        selected.append(publication.id)
        available_metrics.update(latest_metrics_by_publication.get(publication.id, {}).keys())
    if len(selected) < 4:
        warnings.append("insufficient_sample")
    if (date_from is None) ^ (date_to is None):
        warnings.append("mixed_window")
    if (duration_min is None) ^ (duration_max is None):
        warnings.append("mixed_window")
    limitations: list[str] = []
    if platform is None:
        limitations.append("mixed_platform")
    if content_type is None:
        limitations.append("mixed_content_type")
    if duration_min is None and duration_max is None:
        limitations.append("mixed_duration")
    comparable = len(selected) >= 2 and platform is not None and content_type is not None
    return CohortSelectionResult(
        publication_ids=tuple(selected),
        warnings=tuple(dict.fromkeys(warnings)),
        limitations=tuple(dict.fromkeys(limitations)),
        comparable=comparable,
        available_metrics=tuple(sorted(available_metrics)),
    )
