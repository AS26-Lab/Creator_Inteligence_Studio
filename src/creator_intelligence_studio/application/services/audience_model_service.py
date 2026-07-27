"""Servicio central del modelo de audiencia."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.domain.audience_model.audience_types import (
    AudienceConfidenceLevel,
    AudienceModelRunStatus,
    AudienceReviewDecision,
    AudienceSignalType,
    AudienceStatus,
)
from creator_intelligence_studio.domain.audience_model.entities import (
    AudienceAffinity,
    AudienceJourney,
    AudienceJourneyStep,
    AudienceModelRun,
    AudienceProfile,
    AudienceProfileSnapshot,
    AudienceReview,
    AudienceSegment,
    AudienceSignal,
)
from creator_intelligence_studio.domain.audience_model.evidence_types import AudienceEvidenceType
from creator_intelligence_studio.domain.audience_model.errors import AudienceModelNotFoundError, AudienceModelStateError
from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudienceContentRole, AudiencePlatformRole
from creator_intelligence_studio.domain.audience_model.repositories import AudienceRepository
from creator_intelligence_studio.domain.audience_model.segment_types import AudienceSegmentScope, AudienceSegmentType
from creator_intelligence_studio.infrastructure.audience_model.affinity_analyzer import build_affinity
from creator_intelligence_studio.infrastructure.audience_model.contradiction_detector import detect_contradictions
from creator_intelligence_studio.infrastructure.audience_model.evidence_builder import build_evidence, dump_json
from creator_intelligence_studio.infrastructure.audience_model.journey_analyzer import build_journey, build_journey_step
from creator_intelligence_studio.infrastructure.audience_model.lifecycle_classifier import classify_content_role, classify_platform_role
from creator_intelligence_studio.infrastructure.audience_model.profile_builder import build_profile_summary, build_snapshot_payload
from creator_intelligence_studio.infrastructure.audience_model.segment_builder import build_definition, build_segment
from creator_intelligence_studio.infrastructure.audience_model.signal_normalizer import build_signal, signal_type_for_key
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class AudienceModelBuildResult:
    run: AudienceModelRun
    profile: AudienceProfile
    snapshot: AudienceProfileSnapshot
    signals: tuple[AudienceSignal, ...]
    segments: tuple[AudienceSegment, ...]
    affinities: tuple[AudienceAffinity, ...]
    journeys: tuple[AudienceJourney, ...]
    warnings: tuple[str, ...]
    contradictions: tuple[dict[str, object], ...]
    platform_roles: dict[str, dict[str, object]]
    content_roles: dict[str, dict[str, object]]
    missing_signals: tuple[str, ...]
    questions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "profile": self.profile.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "signals": [signal.to_dict() for signal in self.signals],
            "segments": [segment.to_dict() for segment in self.segments],
            "affinities": [affinity.to_dict() for affinity in self.affinities],
            "journeys": [journey.to_dict() for journey in self.journeys],
            "warnings": list(self.warnings),
            "contradictions": list(self.contradictions),
            "platform_roles": self.platform_roles,
            "content_roles": self.content_roles,
            "missing_signals": list(self.missing_signals),
            "questions": list(self.questions),
        }


AUDIENCE_METRIC_KEYS = {
    "new_viewers",
    "returning_viewers",
    "unique_viewers",
    "views",
    "engaged_views",
    "watch_time_minutes",
    "average_view_duration_seconds",
    "average_percentage_viewed",
    "completion_rate",
    "likes",
    "comments",
    "shares",
    "saves",
    "subscribers_gained",
    "subscribers_lost",
    "followers_gained",
    "profile_visits",
    "traffic_to_longform",
    "browse_views",
    "suggested_views",
    "search_views",
    "shorts_feed_views",
    "external_views",
    "direct_views",
    "notification_views",
    "playlist_views",
    "traffic_source",
    "topic",
    "format",
    "content_type",
    "platform",
    "device_share",
    "geography_share",
    "subscription_status_share",
}


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _csv_safe_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] in "=+-@":
        if not (stripped[0] in "+-" and stripped[1:].replace(".", "", 1).isdigit()):
            return "'" + value
    return value


def _confidence_level(score: float) -> AudienceConfidenceLevel:
    if score >= 0.85:
        return AudienceConfidenceLevel.VERY_HIGH
    if score >= 0.7:
        return AudienceConfidenceLevel.HIGH
    if score >= 0.5:
        return AudienceConfidenceLevel.MEDIUM
    if score >= 0.3:
        return AudienceConfidenceLevel.LOW
    return AudienceConfidenceLevel.VERY_LOW


def _platform_category(platform: str) -> str:
    if platform.startswith("youtube_short"):
        return "shortform"
    if platform.startswith("youtube_longform"):
        return "longform"
    if platform in {"instagram_reel", "tiktok"}:
        return "shortform"
    return "manual_other"


class AudienceModelService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        analytics_service: AnalyticsQueryService,
        repository: AudienceRepository,
        database: SQLiteDatabase,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.analytics_service = analytics_service
        self.repository = repository
        self.database = database
        self.logger = logger or logging.getLogger("creator_intelligence_studio.audience")
        self._exports_root = self.paths.data_directory / "audience"
        self._exports_root.mkdir(parents=True, exist_ok=True)

    def _source_payload(self, creator_id: str) -> dict[str, object]:
        publications = self.analytics_service.list_publications(creator_id)
        latest_metrics = {publication.id: self.analytics_service.get_latest_metrics(publication.id) for publication in publications}
        return {
            "creator_id": creator_id,
            "publication_ids": [publication.id for publication in publications],
            "publication_fingerprints": [publication.source_fingerprint for publication in publications],
            "metric_fingerprints": [
                _json_dumps({key: metric.to_dict() for key, metric in latest_metrics.get(publication.id, {}).items()})
                for publication in publications
            ],
        }

    def _fingerprint(self, creator_id: str, configuration: dict[str, object]) -> str:
        payload = {
            "creator_id": creator_id,
            "configuration": configuration,
            "source": self._source_payload(creator_id),
            "analyzer_version": "v1",
        }
        digest = hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()
        return digest

    def _normalize_signals(self, creator_id: str) -> tuple[list[AudienceSignal], list[str], list[str]]:
        publications = self.analytics_service.list_publications(creator_id)
        signals: list[AudienceSignal] = []
        warnings: list[str] = []
        missing_signals: list[str] = []
        for publication in publications:
            latest_metrics = self.analytics_service.get_latest_metrics(publication.id)
            observed_keys = set(latest_metrics)
            for metric_key, metric in latest_metrics.items():
                if metric_key not in AUDIENCE_METRIC_KEYS:
                    continue
                signal = build_signal(
                    creator_id=creator_id,
                    platform=publication.platform,
                    signal_key=metric_key,
                    numeric_value=metric.numeric_value,
                    text_value=metric.text_value,
                    unit=metric.unit,
                    channel_id=publication.channel_id,
                    publication_id=publication.id,
                    period_start=publication.published_at,
                    period_end=publication.published_at,
                    observed_at=metric.captured_at,
                    source_type="analytics_publication",
                    source_id=metric.source_import_id,
                    dimensions_json=_json_dumps(
                        {
                            "publication_title": publication.title,
                            "content_type": publication.content_type.value,
                            "quality_status": metric.quality_status.value,
                            "snapshot_date": metric.snapshot_date,
                        }
                    ),
                    quality_status=metric.quality_status.value,
                    warning_codes_json=metric.warning_codes_json,
                )
                signals.append(self.repository.upsert_signal(signal))
            if "returning_viewers" not in observed_keys:
                missing_signals.append("returning_viewers")
                quality_status = "platform_not_supported" if publication.platform in {"youtube_short", "instagram_reel", "tiktok", "manual_other"} else "metric_not_available"
                warnings.append(quality_status)
                signals.append(
                    self.repository.upsert_signal(
                        build_signal(
                            creator_id=creator_id,
                            platform=publication.platform,
                            signal_key="returning_viewers",
                            text_value="metric_not_available",
                            unit=None,
                            channel_id=publication.channel_id,
                            publication_id=publication.id,
                            period_start=publication.published_at,
                            period_end=publication.published_at,
                            observed_at=utc_now(),
                            source_type="data_quality",
                            source_id=None,
                            dimensions_json=_json_dumps({"reason": "metric_not_available"}),
                            quality_status=quality_status,
                            warning_codes_json=_json_dumps([quality_status]),
                        )
                    )
                )
        return signals, warnings, missing_signals

    def normalize_signals(self, creator_id: str) -> tuple[AudienceSignal, ...]:
        signals, _, _ = self._normalize_signals(creator_id)
        return tuple(signals)

    def get_signal(self, signal_id: str) -> AudienceSignal | None:
        return self.repository.get_signal(signal_id)

    def list_signals(self, creator_id: str, *, platform: str | None = None) -> list[AudienceSignal]:
        return self.repository.list_signals(creator_id, platform=platform)

    def _segment_from_signals(self, creator_id: str, signals: list[AudienceSignal]) -> list[AudienceSegment]:
        publications = self.analytics_service.list_publications(creator_id)
        if not publications:
            return []
        by_platform: dict[str, list[AudienceSignal]] = {}
        by_topic: dict[str, list[AudienceSignal]] = {}
        by_format: dict[str, list[AudienceSignal]] = {}
        for signal in signals:
            by_platform.setdefault(signal.platform, []).append(signal)
            if signal.signal_key == "topic" and signal.text_value:
                by_topic.setdefault(signal.text_value, []).append(signal)
            if signal.signal_key == "format" and signal.text_value:
                by_format.setdefault(signal.text_value, []).append(signal)
        segments: list[AudienceSegment] = []
        platform_viewers = {
            platform: sum(float(signal.numeric_value or 0.0) for signal in items if signal.signal_key == "views")
            for platform, items in by_platform.items()
        }
        top_platform = max(platform_viewers, key=platform_viewers.get) if platform_viewers else None
        longform_signals = [signal for signal in signals if signal.platform == "youtube_longform" and signal.signal_key in {"returning_viewers", "completion_rate", "watch_time_minutes"}]
        shorts_signals = [signal for signal in signals if signal.platform in {"youtube_short", "tiktok", "instagram_reel"} and signal.signal_key in {"new_viewers", "shorts_feed_views", "completion_rate"}]
        if shorts_signals:
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name="shorts_feed_discovery",
                    segment_type=AudienceSegmentType.SYSTEM_DEFINED,
                    scope=AudienceSegmentScope.PLATFORM,
                    description="Signals consistent with short-form discovery.",
                    platform=next((signal.platform for signal in shorts_signals), None),
                    content_type="short_form",
                    topic=None,
                    lifecycle_stage=None,
                    confidence_score=0.8,
                    supporting_signal_count=len(shorts_signals),
                    contradicting_signal_count=0,
                    first_observed_at=min(signal.observed_at for signal in shorts_signals),
                    last_observed_at=max(signal.observed_at for signal in shorts_signals),
                )
            )
        if longform_signals:
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name="longform_loyalty_candidate",
                    segment_type=AudienceSegmentType.SYSTEM_DEFINED,
                    scope=AudienceSegmentScope.PLATFORM,
                    description="Longform signals with returning or repeat behavior.",
                    platform="youtube_longform",
                    content_type="long_form",
                    topic=None,
                    lifecycle_stage=None,
                    confidence_score=0.82,
                    supporting_signal_count=len(longform_signals),
                    contradicting_signal_count=0,
                    first_observed_at=min(signal.observed_at for signal in longform_signals),
                    last_observed_at=max(signal.observed_at for signal in longform_signals),
                )
            )
        for topic, topic_signals in by_topic.items():
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name=f"topic_affinity:{topic}",
                    segment_type=AudienceSegmentType.EVIDENCE_SUGGESTED,
                    scope=AudienceSegmentScope.TOPIC,
                    description=f"Observable topic affinity for {topic}.",
                    platform=topic_signals[0].platform,
                    content_type=None,
                    topic=topic,
                    lifecycle_stage=None,
                    confidence_score=0.65,
                    supporting_signal_count=len(topic_signals),
                    contradicting_signal_count=0,
                    first_observed_at=min(signal.observed_at for signal in topic_signals),
                    last_observed_at=max(signal.observed_at for signal in topic_signals),
                )
            )
        for fmt, format_signals in by_format.items():
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name=f"format_affinity:{fmt}",
                    segment_type=AudienceSegmentType.EVIDENCE_SUGGESTED,
                    scope=AudienceSegmentScope.FORMAT,
                    description=f"Observable format affinity for {fmt}.",
                    platform=format_signals[0].platform,
                    content_type=fmt,
                    topic=None,
                    lifecycle_stage=None,
                    confidence_score=0.6,
                    supporting_signal_count=len(format_signals),
                    contradicting_signal_count=0,
                    first_observed_at=min(signal.observed_at for signal in format_signals),
                    last_observed_at=max(signal.observed_at for signal in format_signals),
                )
            )
        if platform_viewers:
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name="platform_specific",
                    segment_type=AudienceSegmentType.SYSTEM_DEFINED,
                    scope=AudienceSegmentScope.PLATFORM,
                    description=f"Primary observable platform is {top_platform}.",
                    platform=top_platform,
                    content_type=None,
                    topic=None,
                    lifecycle_stage=None,
                    confidence_score=0.55,
                    supporting_signal_count=len(by_platform.get(top_platform or "", [])),
                    contradicting_signal_count=max(0, len(signals) - len(by_platform.get(top_platform or "", []))),
                    first_observed_at=min(signal.observed_at for signal in signals),
                    last_observed_at=max(signal.observed_at for signal in signals),
                )
            )
        if len(publications) < 3 or len(signals) < 6:
            segments.append(
                build_segment(
                    creator_id=creator_id,
                    name="insufficiently_known",
                    segment_type=AudienceSegmentType.SYSTEM_DEFINED,
                    scope=AudienceSegmentScope.UNKNOWN,
                    description="Evidence is too limited for confident segmentation.",
                    platform=None,
                    content_type=None,
                    topic=None,
                    lifecycle_stage=None,
                    confidence_score=0.25,
                    supporting_signal_count=len(signals),
                    contradicting_signal_count=0,
                    first_observed_at=min((signal.observed_at for signal in signals), default=None),
                    last_observed_at=max((signal.observed_at for signal in signals), default=None),
                )
            )
        return segments

    def list_segments(self, creator_id: str) -> list[AudienceSegment]:
        return self.repository.list_segments(creator_id)

    def get_segment(self, segment_id: str) -> AudienceSegment | None:
        return self.repository.get_segment(segment_id)

    def create_segment(
        self,
        *,
        creator_id: str,
        name: str,
        segment_type: str,
        scope: str,
        description: str,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        lifecycle_stage: str | None = None,
    ) -> AudienceSegment:
        segment = build_segment(
            creator_id=creator_id,
            name=name,
            segment_type=AudienceSegmentType(segment_type),
            scope=AudienceSegmentScope(scope),
            description=description,
            platform=platform,
            content_type=content_type,
            topic=topic,
            lifecycle_stage=None,
            confidence_score=0.5,
            supporting_signal_count=0,
            contradicting_signal_count=0,
            first_observed_at=None,
            last_observed_at=None,
        )
        return self.repository.upsert_segment(segment)

    def review_segment(self, segment_id: str, decision: str, reason: str, previous_value_json: str | None = None, new_value_json: str | None = None) -> AudienceReview:
        segment = self.repository.get_segment(segment_id)
        if segment is None:
            raise AudienceModelNotFoundError("Segment not found.")
        review = AudienceReview(
            id=str(uuid4()),
            creator_id=segment.creator_id,
            target_type="segment",
            target_id=segment.id,
            decision=AudienceReviewDecision(decision),
            previous_value_json=previous_value_json,
            new_value_json=new_value_json,
            reason=reason,
            reviewed_at=utc_now(),
            created_at=utc_now(),
        )
        self.repository.upsert_review(review)
        if review.decision in {AudienceReviewDecision.REJECT, AudienceReviewDecision.DEPRECATE}:
            segment = replace(segment, status=AudienceStatus.ARCHIVED, updated_at=utc_now())
            self.repository.upsert_segment(segment)
        elif review.decision == AudienceReviewDecision.CONFIRM:
            segment = replace(segment, status=AudienceStatus.REVIEWED, updated_at=utc_now())
            self.repository.upsert_segment(segment)
        return review

    def archive_segment(self, segment_id: str) -> AudienceSegment:
        segment = self.repository.get_segment(segment_id)
        if segment is None:
            raise AudienceModelNotFoundError("Segment not found.")
        return self.repository.upsert_segment(replace(segment, status=AudienceStatus.ARCHIVED, updated_at=utc_now()))

    def list_affinities(self, creator_id: str) -> list[AudienceAffinity]:
        return self.repository.list_affinities(creator_id)

    def get_affinity(self, affinity_id: str) -> AudienceAffinity | None:
        return self.repository.get_affinity(affinity_id)

    def list_journeys(self, creator_id: str) -> list[AudienceJourney]:
        return self.repository.list_journeys(creator_id)

    def get_journey(self, journey_id: str) -> AudienceJourney | None:
        return self.repository.get_journey(journey_id)

    def list_journey_steps(self, journey_id: str):
        return self.repository.list_journey_steps(journey_id)

    def review_journey(self, journey_id: str, decision: str, reason: str, previous_value_json: str | None = None, new_value_json: str | None = None) -> AudienceReview:
        journey = self.repository.get_journey(journey_id)
        if journey is None:
            raise AudienceModelNotFoundError("Journey not found.")
        review = AudienceReview(
            id=str(uuid4()),
            creator_id=journey.creator_id,
            target_type="journey",
            target_id=journey.id,
            decision=AudienceReviewDecision(decision),
            previous_value_json=previous_value_json,
            new_value_json=new_value_json,
            reason=reason,
            reviewed_at=utc_now(),
            created_at=utc_now(),
        )
        self.repository.upsert_review(review)
        return review

    def list_reviews(self, creator_id: str, *, target_type: str | None = None) -> list[AudienceReview]:
        return self.repository.list_reviews(creator_id, target_type=target_type)

    def get_profile_history(self, creator_id: str) -> list[AudienceProfileSnapshot]:
        return self.repository.list_profile_snapshots(creator_id)

    def get_profile(self, creator_id: str, profile_version: int | None = None) -> AudienceProfile | None:
        return self.repository.get_profile(creator_id, profile_version=profile_version)

    def list_profiles(self, creator_id: str) -> list[AudienceProfile]:
        return self.repository.list_profiles(creator_id)

    def list_platform_roles(self, creator_id: str) -> dict[str, dict[str, object]]:
        signals = self.list_signals(creator_id)
        return self._build_platform_roles(list(signals))

    def list_content_roles(self, creator_id: str) -> dict[str, dict[str, object]]:
        signals = self.list_signals(creator_id)
        publications = self.analytics_service.list_publications(creator_id)
        return self._build_content_roles(publications, list(signals))

    def _build_affinities(self, creator_id: str, signals: list[AudienceSignal], segments: list[AudienceSegment]) -> list[AudienceAffinity]:
        publications = self.analytics_service.list_publications(creator_id)
        topic_examples: dict[str, list[str]] = {}
        format_examples: dict[str, list[str]] = {}
        platform_examples: dict[str, list[str]] = {}
        for publication in publications:
            latest = self.analytics_service.get_latest_metrics(publication.id)
            topic = latest.get("topic").text_value if latest.get("topic") else None
            fmt = latest.get("format").text_value if latest.get("format") else None
            if topic:
                topic_examples.setdefault(topic, []).append(publication.id)
            if fmt:
                format_examples.setdefault(fmt, []).append(publication.id)
            platform_examples.setdefault(publication.platform, []).append(publication.id)
        affinities: list[AudienceAffinity] = []
        for topic, examples in topic_examples.items():
            topic_signals = [signal for signal in signals if signal.signal_key == "topic" and signal.text_value == topic]
            score = min(1.0, 0.45 + 0.1 * len(examples) + 0.05 * len(topic_signals))
            affinities.append(
                build_affinity(
                    creator_id=creator_id,
                    affinity_type="topic",
                    target_key="topic",
                    target_value=topic,
                    platform=topic_signals[0].platform if topic_signals else (publications[0].platform if publications else None),
                    content_type=None,
                    score=score,
                    supporting_example_count=len(examples),
                    contradicting_example_count=0,
                    segment_id=segments[0].id if segments else None,
                )
            )
        for fmt, examples in format_examples.items():
            affinities.append(
                build_affinity(
                    creator_id=creator_id,
                    affinity_type="format",
                    target_key="format",
                    target_value=fmt,
                    platform=publications[0].platform if publications else None,
                    content_type=fmt,
                    score=min(1.0, 0.4 + 0.12 * len(examples)),
                    supporting_example_count=len(examples),
                    contradicting_example_count=0,
                    segment_id=segments[0].id if segments else None,
                )
            )
        for platform, examples in platform_examples.items():
            affinities.append(
                build_affinity(
                    creator_id=creator_id,
                    affinity_type="platform",
                    target_key="platform",
                    target_value=platform,
                    platform=platform,
                    content_type=None,
                    score=min(1.0, 0.35 + 0.1 * len(examples)),
                    supporting_example_count=len(examples),
                    contradicting_example_count=0,
                    segment_id=segments[0].id if segments else None,
                )
            )
        return affinities

    def _build_platform_roles(self, signals: list[AudienceSignal]) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        grouped: dict[str, list[AudienceSignal]] = {}
        for signal in signals:
            grouped.setdefault(signal.platform, []).append(signal)
        for platform, items in grouped.items():
            discovery = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"new_viewers", "search_views", "suggested_views", "shorts_feed_views", "browse_views", "external_views"})
            depth = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"watch_time_minutes", "average_view_duration_seconds", "average_percentage_viewed", "completion_rate"})
            conversion = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"subscribers_gained", "followers_gained", "profile_visits", "traffic_to_longform"})
            loyalty = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"returning_viewers", "revenue", "repeat_views"})
            community = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"likes", "comments", "shares", "saves"})
            experimentation = 1.0 if len(items) < 3 else 0.2
            role = classify_platform_role(discovery=discovery, depth=depth, conversion=conversion, loyalty=loyalty, community=community, experimentation=experimentation)
            payload[platform] = {
                "role": role.value,
                "discovery": round(discovery, 3),
                "depth": round(depth, 3),
                "conversion": round(conversion, 3),
                "loyalty": round(loyalty, 3),
                "community": round(community, 3),
                "confidence": round(max(discovery, depth, conversion, loyalty, community, experimentation), 3),
                "evidence": [item.signal_key for item in items[:8]],
            }
        return payload

    def _build_content_roles(self, publications: list, signals: list[AudienceSignal]) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        by_publication: dict[str, list[AudienceSignal]] = {}
        for signal in signals:
            if signal.publication_id:
                by_publication.setdefault(signal.publication_id, []).append(signal)
        for publication in publications:
            items = by_publication.get(publication.id, [])
            acquisition = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"new_viewers", "search_views", "suggested_views", "shorts_feed_views", "browse_views", "external_views"})
            engagement = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"likes", "comments", "shares", "saves", "engaged_views"})
            conversion = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"subscribers_gained", "followers_gained", "profile_visits", "traffic_to_longform"})
            loyalty = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"returning_viewers", "traffic_to_longform"})
            authority = sum(float(item.numeric_value or 0) for item in items if item.signal_key in {"watch_time_minutes", "average_view_duration_seconds", "average_percentage_viewed"})
            community = engagement
            bridge = conversion * 0.5 + loyalty * 0.5
            role = classify_content_role(acquisition=acquisition, engagement=engagement, conversion=conversion, loyalty=loyalty, authority=authority, community=community, bridge=bridge)
            payload[publication.id] = {
                "publication_title": publication.title,
                "role": role.value,
                "metrics": {
                    "views": self._metric_value(items, "views"),
                    "completion_rate": self._metric_value(items, "completion_rate"),
                    "subscribers_gained": self._metric_value(items, "subscribers_gained"),
                },
                "evidence": [item.signal_key for item in items[:8]],
                "warnings": [] if items else ["missing_signal"],
            }
        return payload

    @staticmethod
    def _metric_value(items: list[AudienceSignal], signal_key: str) -> float | None:
        for item in items:
            if item.signal_key == signal_key and item.numeric_value is not None:
                return float(item.numeric_value)
        return None

    def _build_journeys(self, creator_id: str, signals: list[AudienceSignal], publications: list) -> list[AudienceJourney]:
        journeys: list[AudienceJourney] = []
        short_publications = [publication for publication in publications if publication.platform in {"youtube_short", "instagram_reel", "tiktok"}]
        long_publications = [publication for publication in publications if publication.platform == "youtube_longform"]
        if short_publications and long_publications:
            short_publication = sorted(short_publications, key=lambda item: item.published_at)[0]
            long_publication = sorted(long_publications, key=lambda item: item.published_at)[0]
            evidence = {
                "warning": "aggregated_only",
                "path": "short_to_longform",
                "short_publication_id": short_publication.id,
                "long_publication_id": long_publication.id,
            }
            journey = build_journey(
                creator_id=creator_id,
                name="Short to longform",
                entry_platform=short_publication.platform,
                entry_source="shorts_feed",
                entry_content_type=short_publication.content_type.value,
                next_step_type="longform_view",
                conversion_type="traffic_to_longform",
                confidence_score=0.78,
                evidence=evidence,
                limitations=["individual_journey_unverifiable", "aggregated_only"],
            )
            journeys.append(journey)
            journeys.append(
                build_journey(
                    creator_id=creator_id,
                    name="Search to subscribe",
                    entry_platform="youtube_longform",
                    entry_source="search",
                    entry_content_type="youtube_longform",
                    next_step_type="subscribe",
                    conversion_type="subscribers_gained",
                    confidence_score=0.72,
                    evidence={"warning": "aggregated_only", "path": "search_longform_subscribe"},
                    limitations=["individual_journey_unverifiable", "aggregated_only"],
                )
            )
        return journeys

    def _build_profile(self, creator_id: str, signals: list[AudienceSignal], segments: list[AudienceSegment], affinities: list[AudienceAffinity], journeys: list[AudienceJourney], warnings: list[str], contradictions: list[dict[str, object]], missing_signals: list[str]) -> tuple[AudienceProfile, AudienceProfileSnapshot]:
        profile_version = len(self.repository.list_profiles(creator_id)) + 1
        summary = build_profile_summary(
            signals=[signal.to_dict() for signal in signals],
            segments=[segment.to_dict() for segment in segments],
            affinities=[affinity.to_dict() for affinity in affinities],
            journeys=[journey.to_dict() for journey in journeys],
            contradictions=contradictions,
            warnings=warnings,
            questions=missing_signals,
        )
        profile = AudienceProfile(
            id=str(uuid4()),
            creator_id=creator_id,
            profile_version=profile_version,
            status=AudienceStatus.ACTIVE if not warnings else AudienceStatus.DRAFT,
            summary=summary,
            evidence_quality="aggregated_observed_only",
            confidence_level=_confidence_level(min(1.0, 0.35 + 0.05 * len(signals) + 0.1 * len(segments))),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        profile = self.repository.upsert_profile(profile)
        snapshot = AudienceProfileSnapshot(
            id=str(uuid4()),
            creator_id=creator_id,
            profile_version=profile.profile_version,
            snapshot_json=build_snapshot_payload(
                {
                    "profile": profile.to_dict(),
                    "signals": [signal.to_dict() for signal in signals],
                    "segments": [segment.to_dict() for segment in segments],
                    "affinities": [affinity.to_dict() for affinity in affinities],
                    "journeys": [journey.to_dict() for journey in journeys],
                    "warnings": warnings,
                    "contradictions": contradictions,
                    "missing_signals": missing_signals,
                }
            ),
            source_fingerprint=self._fingerprint(creator_id, {"profile_version": profile_version}),
            status=profile.status,
            created_at=utc_now(),
        )
        snapshot = self.repository.upsert_profile_snapshot(snapshot)
        return profile, snapshot

    def build_profile(self, creator_id: str, *, force: bool = False, configuration: dict[str, object] | None = None) -> AudienceModelBuildResult:
        configuration = configuration or {}
        configuration_json = _json_dumps(configuration)
        fingerprint = self._fingerprint(creator_id, configuration)
        existing = self.repository.get_run_by_fingerprint(creator_id, fingerprint, configuration_json)
        if existing and existing.status in {AudienceModelRunStatus.COMPLETED, AudienceModelRunStatus.COMPLETED_WITH_WARNINGS} and not force:
            profile = self.repository.get_profile(creator_id)
            if profile is None:
                profile = self.repository.list_profiles(creator_id)[0]
            snapshots = self.repository.list_profile_snapshots(creator_id)
            snapshot = snapshots[0] if snapshots else AudienceProfileSnapshot(
                id=str(uuid4()),
                creator_id=creator_id,
                profile_version=profile.profile_version,
                snapshot_json="{}",
                source_fingerprint=existing.source_fingerprint,
                status=profile.status,
                created_at=utc_now(),
            )
            signals = tuple(self.repository.list_signals(creator_id))
            segments = tuple(self.repository.list_segments(creator_id))
            affinities = tuple(self.repository.list_affinities(creator_id))
            journeys = tuple(self.repository.list_journeys(creator_id))
            platform_roles = self._build_platform_roles(list(signals))
            content_roles = self._build_content_roles(self.analytics_service.list_publications(creator_id), list(signals))
            return AudienceModelBuildResult(existing, profile, snapshot, signals, segments, affinities, journeys, (), tuple(), platform_roles, content_roles, tuple(), tuple())

        run = AudienceModelRun(
            id=str(uuid4()),
            creator_id=creator_id,
            status=AudienceModelRunStatus.COLLECTING_SIGNALS,
            configuration_json=configuration_json,
            source_fingerprint=fingerprint,
            signal_count=0,
            segment_count=0,
            warning_count=0,
            started_at=utc_now(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=utc_now(),
        )
        run = self.repository.upsert_run(run)
        warnings: list[str] = []
        try:
            signals, signal_warnings, missing_signals = self._normalize_signals(creator_id)
            warnings.extend(signal_warnings)
            run = self.repository.upsert_run(replace(run, status=AudienceModelRunStatus.NORMALIZING, signal_count=len(signals)))
            publications = self.analytics_service.list_publications(creator_id)
            segments = self._segment_from_signals(creator_id, signals)
            for segment in segments:
                self.repository.upsert_segment(segment)
                self.repository.upsert_segment_definition(
                    build_definition(segment.id, "heuristic", "signal_set", "contains", {"segment_name": segment.name, "platform": segment.platform, "topic": segment.topic})
                )
                if segment.supporting_signal_count:
                    signal = next((item for item in signals if item.platform == segment.platform), None)
                    if signal:
                        self.repository.upsert_segment_evidence(
                            build_evidence(
                                segment_id=segment.id,
                                signal_id=signal.id,
                                publication_id=signal.publication_id,
                                evidence_type=AudienceEvidenceType.METRIC,
                                supports_segment=True,
                                weight=1.0,
                                notes=segment.description,
                            )
                        )
            run = self.repository.upsert_run(replace(run, status=AudienceModelRunStatus.BUILDING_SEGMENTS, segment_count=len(segments)))
            affinities = self._build_affinities(creator_id, signals, segments)
            for affinity in affinities:
                self.repository.upsert_affinity(affinity)
            run = self.repository.upsert_run(replace(run, status=AudienceModelRunStatus.BUILDING_AFFINITIES))
            journeys = self._build_journeys(creator_id, signals, publications)
            for journey in journeys:
                self.repository.upsert_journey(journey)
                self.repository.upsert_journey_step(
                    build_journey_step(
                        journey_id=journey.id,
                        step_order=1,
                        platform=journey.entry_platform or "unknown",
                        content_type=journey.entry_content_type,
                        action_type="entry",
                        metric_key="views",
                        observed_value=None,
                        evidence={"source": journey.entry_source, "aggregated": True},
                    )
                )
                self.repository.upsert_journey_step(
                    build_journey_step(
                        journey_id=journey.id,
                        step_order=2,
                        platform=journey.entry_platform or "unknown",
                        content_type=journey.entry_content_type,
                        action_type="next_step",
                        metric_key=journey.conversion_type,
                        observed_value=None,
                        evidence={"aggregated": True},
                    )
                )
            run = self.repository.upsert_run(replace(run, status=AudienceModelRunStatus.BUILDING_JOURNEYS))
            contradictions = detect_contradictions([signal.to_dict() for signal in signals])
            platform_roles = self._build_platform_roles(signals)
            content_roles = self._build_content_roles(publications, signals)
            profile, snapshot = self._build_profile(creator_id, signals, segments, affinities, journeys, warnings, contradictions, missing_signals)
            warning_count = len(warnings) + len(contradictions)
            completed_status = AudienceModelRunStatus.COMPLETED_WITH_WARNINGS if warning_count else AudienceModelRunStatus.COMPLETED
            completed = replace(run, status=completed_status, warning_count=warning_count, completed_at=utc_now())
            completed = self.repository.upsert_run(completed)
            return AudienceModelBuildResult(
                completed,
                profile,
                snapshot,
                tuple(signals),
                tuple(segments),
                tuple(affinities),
                tuple(journeys),
                tuple(warnings),
                tuple(contradictions),
                platform_roles,
                content_roles,
                tuple(missing_signals),
                tuple(
                    [
                        "aggregated_only",
                        "individual_journey_unverifiable",
                        "no_demographic_inference",
                    ]
                ),
            )
        except Exception as exc:
            failed = self.repository.upsert_run(replace(run, status=AudienceModelRunStatus.FAILED, error_code=type(exc).__name__, error_message=str(exc), completed_at=utc_now()))
            raise

    def get_profile_history(self, creator_id: str) -> list[AudienceProfileSnapshot]:
        return self.repository.list_profile_snapshots(creator_id)

    def compare_profiles(self, creator_id: str, base_version: int, compare_version: int) -> dict[str, object]:
        base = self.repository.get_profile(creator_id, base_version)
        compare = self.repository.get_profile(creator_id, compare_version)
        if base is None or compare is None:
            raise AudienceModelNotFoundError("Profile not found.")
        return {
            "base": base.to_dict(),
            "compare": compare.to_dict(),
            "summary_delta": len(compare.summary) - len(base.summary),
        }

    def export(self, creator_id: str, format_name: str) -> Path:
        profile = self.repository.get_profile(creator_id)
        if profile is None:
            raise AudienceModelNotFoundError("Profile not found.")
        signals = self.repository.list_signals(creator_id)
        segments = self.repository.list_segments(creator_id)
        affinities = self.repository.list_affinities(creator_id)
        journeys = self.repository.list_journeys(creator_id)
        payload = {
            "profile": profile.to_dict(),
            "signals": [signal.to_dict() for signal in signals],
            "segments": [segment.to_dict() for segment in segments],
            "affinities": [affinity.to_dict() for affinity in affinities],
            "journeys": [journey.to_dict() for journey in journeys],
        }
        path = self._exports_root / f"{creator_id}_audience.{format_name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path.write_text(_json_dumps(payload), encoding="utf-8")
        elif format_name == "txt":
            path.write_text(profile.summary + "\n" + _json_dumps(payload), encoding="utf-8")
        elif format_name == "csv":
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["signal_id", "platform", "signal_key", "numeric_value", "text_value", "unit", "quality_status"])
                for signal in signals:
                    writer.writerow([
                        signal.id,
                        signal.platform,
                        signal.signal_key,
                        _csv_safe_value(signal.numeric_value),
                        _csv_safe_value(signal.text_value),
                        _csv_safe_value(signal.unit),
                        signal.quality_status,
                    ])
        else:
            raise AudienceModelStateError("Unsupported export format.")
        return path

    def list_runs(self, creator_id: str) -> list[AudienceModelRun]:
        return self.repository.list_runs(creator_id)

    def get_run(self, run_id: str) -> AudienceModelRun | None:
        return self.repository.get_run(run_id)


def build_audience_model_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    analytics_service: AnalyticsQueryService,
    repository: AudienceRepository,
    database: SQLiteDatabase,
    logger: logging.Logger | None = None,
) -> AudienceModelService:
    return AudienceModelService(
        settings=settings,
        paths=paths,
        analytics_service=analytics_service,
        repository=repository,
        database=database,
        logger=logger,
    )
