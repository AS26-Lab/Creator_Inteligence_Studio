"""Servicio central de Market and Trend Intelligence Foundation."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from typing import Any

from creator_intelligence_studio.domain.market_intelligence.competitor_types import CompetitorApprovalStatus, CompetitorMonitoringStatus, RelationshipType
from creator_intelligence_studio.domain.market_intelligence.confidence_types import ConfidenceLevel
from creator_intelligence_studio.domain.market_intelligence.entities import (
    CompetitorProfile,
    CreatorMarketFitEvaluation,
    ExternalContentItem,
    ExternalContentSnapshot,
    MarketDefinition,
    MarketEntity,
    MarketObservation,
    MarketPattern,
    MarketPatternEvidence,
    MarketReport,
    MarketReview,
    MarketSnapshot,
    MarketSource,
    MarketTopic,
    OpportunityCandidate,
    OpportunityCandidateEvidence,
    ResearchItem,
    ResearchQuery,
    ResearchRun,
    TrendSignal,
    TrendSignalEvidence,
)
from creator_intelligence_studio.domain.market_intelligence.errors import MarketIntelligenceError
from creator_intelligence_studio.domain.market_intelligence.evidence_types import EvidenceType
from creator_intelligence_studio.domain.market_intelligence.lifecycle_types import LifecycleStage
from creator_intelligence_studio.domain.market_intelligence.market_types import MarketStatus, MarketType, TopicType
from creator_intelligence_studio.domain.market_intelligence.observation_types import EvidenceQuality, ObservationType, SubjectType
from creator_intelligence_studio.domain.market_intelligence.opportunity_types import FreshnessStatus, OpportunityStatus, OpportunityType, UrgencyLevel
from creator_intelligence_studio.domain.market_intelligence.pattern_types import EvidenceRole, PatternStatus, PatternType
from creator_intelligence_studio.domain.market_intelligence.repositories import MarketIntelligenceRepository
from creator_intelligence_studio.domain.market_intelligence.saturation_types import SaturationLevel
from creator_intelligence_studio.domain.market_intelligence.source_types import SourceType, TrustLevel
from creator_intelligence_studio.domain.market_intelligence.trend_types import TrendDirection, TrendSignalType
from creator_intelligence_studio.domain.market_intelligence.value_objects import (
    build_market_fingerprint,
    current_utc_iso,
    json_dumps,
    json_loads,
    normalize_identifier,
    normalize_platform,
    normalize_text,
    normalize_url,
    safe_slug,
)
from creator_intelligence_studio.infrastructure.market_intelligence.copying_risk_detector import detect_copying_risk
from creator_intelligence_studio.infrastructure.market_intelligence.creator_fit_evaluator import evaluate_creator_fit
from creator_intelligence_studio.infrastructure.market_intelligence.evidence_normalizer import normalize_evidence_list
from creator_intelligence_studio.infrastructure.market_intelligence.observation_normalizer import normalize_observation
from creator_intelligence_studio.infrastructure.market_intelligence.opportunity_candidate_builder import build_opportunity_candidate
from creator_intelligence_studio.infrastructure.market_intelligence.pattern_clusterer import cluster_patterns
from creator_intelligence_studio.infrastructure.market_intelligence.report_builder import build_report
from creator_intelligence_studio.infrastructure.market_sources.source_registry import SourceRegistry, build_default_source_registry
from creator_intelligence_studio.infrastructure.market_intelligence.trend_calculator import compute_trend_points
from creator_intelligence_studio.infrastructure.market_intelligence.velocity_calculator import calculate_velocity
from creator_intelligence_studio.infrastructure.market_intelligence.acceleration_calculator import calculate_acceleration
from creator_intelligence_studio.infrastructure.market_intelligence.persistence_calculator import calculate_persistence
from creator_intelligence_studio.infrastructure.market_intelligence.saturation_calculator import calculate_saturation
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.infrastructure.persistence.sqlite_market_intelligence_repository import SQLiteMarketIntelligenceRepository
from creator_intelligence_studio.shared.paths import ProjectPaths


def _row_to_model(cls, row: dict[str, Any]):
    return cls(**row)


def _ensure_json(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json_dumps(value)


def _default_query_text(payload: dict[str, Any]) -> str:
    text = normalize_text(payload.get("query_text") or payload.get("name") or payload.get("title"))
    return text or "market research"


@dataclass(frozen=True, slots=True)
class MarketOverviewRow:
    market_id: str
    market_name: str
    market_type: str
    topic_count: int
    source_count: int
    signal_count: int
    opportunity_count: int
    latest_research_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "market_id": self.market_id,
            "market_name": self.market_name,
            "market_type": self.market_type,
            "topic_count": self.topic_count,
            "source_count": self.source_count,
            "signal_count": self.signal_count,
            "opportunity_count": self.opportunity_count,
            "latest_research_at": self.latest_research_at,
        }


class MarketIntelligenceService:
    def __init__(
        self,
        *,
        settings,
        paths: ProjectPaths,
        repository: SQLiteMarketIntelligenceRepository,
        database: SQLiteDatabase,
        source_registry: SourceRegistry | None = None,
        catalog_service: Any | None = None,
        analytics_service: Any | None = None,
        creator_memory_service: Any | None = None,
        creator_language_service: Any | None = None,
        audience_service: Any | None = None,
        analytics_lab_service: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.database = database
        self.source_registry = source_registry or build_default_source_registry(
            youtube_api_key=getattr(settings, "youtube_public_api_key", None)
        )
        self.catalog_service = catalog_service
        self.analytics_service = analytics_service
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.audience_service = audience_service
        self.analytics_lab_service = analytics_lab_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.market")
        self._exports_root = self.paths.artifacts_directory / "market"
        self._exports_root.mkdir(parents=True, exist_ok=True)

    # --- markets
    def create_market_definition(
        self,
        *,
        creator_id: str,
        name: str,
        description: str | None = None,
        market_type: str = "market",
        primary_language: str | None = None,
        primary_region: str | None = None,
    ) -> MarketDefinition:
        record = MarketDefinition(
            id=f"market-{uuid4()}",
            creator_id=creator_id,
            name=normalize_text(name),
            description=normalize_text(description) or None,
            market_type=MarketType(market_type),
            primary_language=normalize_identifier(primary_language) or None,
            primary_region=normalize_identifier(primary_region) or None,
            status=MarketStatus.ACTIVE,
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_definitions", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketDefinition, saved)

    def list_market_definitions(self, creator_id: str) -> list[MarketDefinition]:
        rows = self.repository.fetch_records("market_definitions", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")
        return [_row_to_model(MarketDefinition, row) for row in rows]

    def get_market_definition(self, market_id: str) -> MarketDefinition | None:
        row = self.repository.fetch_record("market_definitions", where="id = ?", params=(market_id,))
        return _row_to_model(MarketDefinition, row) if row else None

    def archive_market_definition(self, market_id: str) -> MarketDefinition | None:
        market = self.get_market_definition(market_id)
        if market is None:
            return None
        updated = MarketDefinition(
            **{
                **market.to_dict(),
                "status": MarketStatus.ARCHIVED,
                "updated_at": current_utc_iso(),
            }
        )
        saved = self.repository.upsert_record("market_definitions", updated.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketDefinition, saved)

    # --- topics
    def create_market_topic(
        self,
        *,
        creator_id: str,
        market_id: str,
        canonical_name: str,
        display_name: str | None = None,
        description: str | None = None,
        topic_type: str = "topic",
        parent_topic_id: str | None = None,
        aliases: list[str] | None = None,
        excluded_terms: list[str] | None = None,
    ) -> MarketTopic:
        record = MarketTopic(
            id=f"topic-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            canonical_name=safe_slug(canonical_name),
            display_name=normalize_text(display_name) or normalize_text(canonical_name),
            description=normalize_text(description) or None,
            topic_type=TopicType(topic_type),
            aliases_json=_ensure_json(aliases or []),
            excluded_terms_json=_ensure_json(excluded_terms or []),
            status=MarketStatus.ACTIVE,
            parent_topic_id=parent_topic_id,
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_topics", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketTopic, saved)

    def list_market_topics(self, creator_id: str, market_id: str | None = None) -> list[MarketTopic]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_topics", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(MarketTopic, row) for row in rows]

    # --- sources
    def register_market_source(
        self,
        *,
        creator_id: str,
        source_type: str,
        name: str,
        access_method: str,
        trust_level: str,
        permission_status: str = "unknown",
        enabled: bool = True,
        platform: str | None = None,
        source_identifier: str | None = None,
        source_url: str | None = None,
        configuration: dict[str, Any] | None = None,
    ) -> MarketSource:
        record = MarketSource(
            id=f"source-{uuid4()}",
            creator_id=creator_id,
            source_type=SourceType(source_type),
            name=normalize_text(name),
            access_method=normalize_text(access_method) or "manual",
            trust_level=TrustLevel(trust_level),
            permission_status=permission_status,
            enabled=bool(enabled),
            platform=normalize_platform(platform) if platform else None,
            source_identifier=normalize_identifier(source_identifier) or None,
            source_url=normalize_url(source_url),
            configuration_json=_ensure_json(configuration or {}),
            last_checked_at=None,
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_sources", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketSource, saved)

    def list_market_sources(self, creator_id: str, platform: str | None = None) -> list[MarketSource]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if platform is not None:
            where += " AND platform = ?"
            params.append(normalize_platform(platform))
        rows = self.repository.fetch_records("market_sources", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(MarketSource, row) for row in rows]

    # --- research queries/runs
    def create_research_query(
        self,
        *,
        creator_id: str,
        platform: str,
        query_text: str | None = None,
        query_type: str = "search",
        market_id: str | None = None,
        language: str | None = None,
        region: str | None = None,
        published_after: str | None = None,
        published_before: str | None = None,
        max_results: int = 25,
        filters: dict[str, Any] | None = None,
    ) -> ResearchQuery:
        record = ResearchQuery(
            id=f"query-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            platform=normalize_platform(platform),
            query_text=_default_query_text({"query_text": query_text}),
            query_type=normalize_text(query_type) or "search",
            language=normalize_identifier(language) or None,
            region=normalize_identifier(region) or None,
            published_after=published_after,
            published_before=published_before,
            max_results=max(1, int(max_results)),
            filters_json=_ensure_json(filters or {}),
            status="queued",
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_research_queries", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(ResearchQuery, saved)

    def list_research_queries(self, creator_id: str, market_id: str | None = None) -> list[ResearchQuery]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_research_queries", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(ResearchQuery, row) for row in rows]

    def _query_adapter(self, platform: str, source_type: str) -> Any | None:
        source = self.source_registry.get(source_type)
        if source is not None and source.is_available():
            return source
        if platform:
            return self.source_registry.get(platform)
        return None

    def run_research_query(self, query_id: str) -> ResearchRun:
        query_row = self.repository.fetch_record("market_research_queries", where="id = ?", params=(query_id,))
        if query_row is None:
            raise MarketIntelligenceError(f"No se encontro la query {query_id}.")
        query = _row_to_model(ResearchQuery, query_row)
        source = self.repository.fetch_record("market_sources", where="creator_id = ? AND platform = ? AND enabled = 1", params=(query.creator_id, query.platform))
        source_model = _row_to_model(MarketSource, source) if source else None
        source_type = (
            str(getattr(source_model.source_type, "value", source_model.source_type))
            if source_model is not None
            else ("youtube_public" if query.platform == "youtube" else "manual")
        )
        adapter = self.source_registry.get(source_type)
        run = ResearchRun(
            id=f"run-{uuid4()}",
            creator_id=query.creator_id,
            source_id=source_model.id if source_model is not None else f"source-{query.platform}",
            research_query_id=query.id,
            status="running",
            configuration_json=json_dumps({"query_id": query.id, "platform": query.platform, "query_text": query.query_text}),
            cursor_json=None,
            discovered_count=0,
            imported_count=0,
            updated_count=0,
            skipped_count=0,
            warning_count=0,
            error_count=0,
            estimated_quota_cost=None,
            started_at=current_utc_iso(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=current_utc_iso(),
        )
        saved_run = self.repository.upsert_record("market_research_runs", run.to_dict(), conflict_columns=("id",))
        if adapter is None or not adapter.is_available():
            failed = ResearchRun(
                **{
                    **saved_run,
                    "status": "failed",
                    "completed_at": current_utc_iso(),
                    "error_code": "source_unavailable",
                    "error_message": "La fuente de investigacion no esta disponible.",
                }
            )
            self.repository.upsert_record("market_research_runs", failed.to_dict(), conflict_columns=("id",))
            return _row_to_model(ResearchRun, failed.to_dict())

        page = adapter.search(
            {
                "part": "snippet",
                "q": query.query_text,
                "type": "video",
                "maxResults": query.max_results,
                "regionCode": query.region,
                "relevanceLanguage": query.language,
                "publishedAfter": query.published_after,
                "publishedBefore": query.published_before,
            }
        )
        discovered = 0
        for item in page.items:
            discovered += 1
            external_content = self.record_external_content_from_youtube(
                creator_id=query.creator_id,
                source_id=source_model.id if source_model else run.source_id,
                payload=dict(item),
                market_id=query.market_id,
                source_type=SourceType.YOUTUBE_PUBLIC,
            )
            self.record_observation(
                creator_id=query.creator_id,
                source_id=source_model.id if source_model else run.source_id,
                platform=query.platform,
                observation_type=ObservationType.METADATA,
                subject_type=SubjectType.CONTENT,
                observed_value={
                    "external_content_item_id": external_content.id,
                    "title": external_content.title,
                    "platform": query.platform,
                },
                evidence_quality=EvidenceQuality.MEDIUM,
                confidence_level=ConfidenceLevel.MEDIUM,
                status="imported",
                market_id=query.market_id,
                subject_id=external_content.id,
            )
        completed = ResearchRun(
            **{
                **saved_run,
                "status": "completed_with_warnings" if discovered == 0 else "completed",
                "discovered_count": discovered,
                "imported_count": discovered,
                "completed_at": current_utc_iso(),
                "estimated_quota_cost": 100 if query.platform == "youtube" and query.query_type == "search" else 1,
                "cursor_json": page.next_cursor,
            }
        )
        self.repository.upsert_record("market_research_runs", completed.to_dict(), conflict_columns=("id",))
        if page.next_cursor:
            self.repository.upsert_record(
                "market_research_items",
                {
                    "id": f"item-{uuid4()}",
                    "research_run_id": completed.id,
                    "external_entity_type": "cursor",
                    "external_entity_id": page.next_cursor,
                    "action": "paginate",
                    "status": "pending",
                    "warning_codes_json": "[]",
                    "error_code": None,
                    "error_message": None,
                    "created_at": current_utc_iso(),
                },
                conflict_columns=("id",),
            )
        return _row_to_model(ResearchRun, completed.to_dict())

    def list_research_runs(self, creator_id: str) -> list[ResearchRun]:
        rows = self.repository.fetch_records("market_research_runs", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")
        return [_row_to_model(ResearchRun, row) for row in rows]

    def list_research_items(self, research_run_id: str) -> list[ResearchItem]:
        rows = self.repository.fetch_records("market_research_items", where="research_run_id = ?", params=(research_run_id,), order_by="created_at ASC")
        return [_row_to_model(ResearchItem, row) for row in rows]

    # --- external content / observations
    def record_external_content_from_youtube(
        self,
        *,
        creator_id: str,
        source_id: str,
        payload: dict[str, Any],
        market_id: str | None = None,
        source_type: SourceType = SourceType.YOUTUBE_PUBLIC,
    ) -> ExternalContentItem:
        title = normalize_text(payload.get("title") or payload.get("snippet", {}).get("title"))
        description = normalize_text(payload.get("description") or payload.get("snippet", {}).get("description"))
        raw_identifier = payload.get("id") or payload.get("external_content_id")
        if isinstance(raw_identifier, dict):
            content_id = str(raw_identifier.get("videoId") or raw_identifier.get("channelId") or raw_identifier.get("playlistId") or uuid4())
        else:
            content_id = str(raw_identifier or uuid4())
        entity = ExternalContentItem(
            id=f"content-{content_id}",
            creator_id=creator_id,
            market_entity_id=None,
            source_id=source_id,
            platform="youtube",
            external_content_id=content_id,
            content_type=str(payload.get("content_type") or "video"),
            title=title or None,
            description=description or None,
            published_at=str(payload.get("published_at") or payload.get("snippet", {}).get("publishedAt") or ""),
            duration_seconds=None,
            language=str(payload.get("language") or payload.get("snippet", {}).get("defaultLanguage") or "").lower() or None,
            region=str(payload.get("region") or "").lower() or None,
            source_url=normalize_url(payload.get("source_url") or payload.get("url")),
            thumbnail_url=normalize_url(payload.get("thumbnail_url") or payload.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url")),
            local_reference_asset_id=None,
            topic_labels_json=_ensure_json(payload.get("topic_labels") or []),
            format_labels_json=_ensure_json(payload.get("format_labels") or []),
            public_metrics_json=_ensure_json(payload.get("public_metrics") or payload.get("statistics") or {}),
            remote_fingerprint=build_market_fingerprint(content_id, title, description),
            first_observed_at=current_utc_iso(),
            last_observed_at=current_utc_iso(),
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("external_content_items", entity.to_dict(), conflict_columns=("id",))
        snapshot = ExternalContentSnapshot(
            id=f"snapshot-{uuid4()}",
            creator_id=creator_id,
            external_content_item_id=saved["id"],
            observed_at=current_utc_iso(),
            metrics_json=_ensure_json(payload.get("public_metrics") or payload.get("statistics") or {}),
            source_type=source_type,
            source_fingerprint=build_market_fingerprint(saved["id"], payload),
            quality_status="high",
            created_at=current_utc_iso(),
            warning_codes_json=_ensure_json([]),
        )
        self.repository.upsert_record("external_content_snapshots", snapshot.to_dict(), conflict_columns=("id",))
        return _row_to_model(ExternalContentItem, saved)

    def list_external_content_items(self, creator_id: str, market_entity_id: str | None = None) -> list[ExternalContentItem]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_entity_id is not None:
            where += " AND market_entity_id = ?"
            params.append(market_entity_id)
        rows = self.repository.fetch_records("external_content_items", where=where, params=tuple(params), order_by="last_observed_at DESC")
        return [_row_to_model(ExternalContentItem, row) for row in rows]

    def record_observation(
        self,
        *,
        creator_id: str,
        source_id: str,
        platform: str,
        observation_type: ObservationType | str,
        subject_type: SubjectType | str,
        observed_value: dict[str, Any],
        evidence_quality: EvidenceQuality | str,
        confidence_level: ConfidenceLevel | str,
        status: str,
        market_id: str | None = None,
        topic_id: str | None = None,
        subject_id: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> MarketObservation:
        record = MarketObservation(
            id=f"observation-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            topic_id=topic_id,
            source_id=source_id,
            platform=normalize_platform(platform),
            observation_type=ObservationType(observation_type),
            subject_type=SubjectType(subject_type),
            subject_id=subject_id,
            observed_value_json=_ensure_json(normalize_observation({"observed_value_json": observed_value})["observed_value_json"]),
            period_start=period_start,
            period_end=period_end,
            observed_at=current_utc_iso(),
            evidence_quality=EvidenceQuality(evidence_quality),
            confidence_level=ConfidenceLevel(confidence_level),
            status=status,
            created_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_observations", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketObservation, saved)

    def list_observations(self, creator_id: str, market_id: str | None = None) -> list[MarketObservation]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_observations", where=where, params=tuple(params), order_by="observed_at DESC")
        return [_row_to_model(MarketObservation, row) for row in rows]

    # --- entities / competitor profiles
    def register_market_entity(
        self,
        *,
        creator_id: str,
        platform: str,
        entity_type: str,
        canonical_name: str,
        display_name: str | None = None,
        source_id: str,
        external_id: str | None = None,
        source_url: str | None = None,
        country: str | None = None,
        language: str | None = None,
        market_id: str | None = None,
    ) -> MarketEntity:
        record = MarketEntity(
            id=f"entity-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            entity_type=entity_type,
            platform=normalize_platform(platform),
            external_id=external_id,
            canonical_name=normalize_text(canonical_name),
            display_name=normalize_text(display_name) or normalize_text(canonical_name),
            source_id=source_id,
            source_url=normalize_url(source_url),
            country=normalize_identifier(country) or None,
            language=normalize_identifier(language) or None,
            status="observed",
            first_observed_at=current_utc_iso(),
            last_observed_at=current_utc_iso(),
            remote_fingerprint=build_market_fingerprint(platform, canonical_name, external_id, source_url),
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_entities", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketEntity, saved)

    def register_competitor_profile(
        self,
        *,
        creator_id: str,
        market_entity_id: str,
        relationship_type: str,
        relevance_reason: str,
        relevance_scope: str,
        approval_status: str = "pending",
        monitoring_status: str = "active",
        copying_risk_level: str = "low",
        notes: str | None = None,
    ) -> CompetitorProfile:
        record = CompetitorProfile(
            id=f"competitor-{uuid4()}",
            creator_id=creator_id,
            market_entity_id=market_entity_id,
            relationship_type=RelationshipType(relationship_type),
            relevance_reason=normalize_text(relevance_reason),
            relevance_scope=normalize_text(relevance_scope),
            approval_status=CompetitorApprovalStatus(approval_status),
            monitoring_status=CompetitorMonitoringStatus(monitoring_status),
            copying_risk_level=copying_risk_level,
            notes=normalize_text(notes) or None,
            created_at=current_utc_iso(),
            updated_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("competitor_profiles", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(CompetitorProfile, saved)

    def list_competitor_profiles(self, creator_id: str) -> list[CompetitorProfile]:
        rows = self.repository.fetch_records("competitor_profiles", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")
        return [_row_to_model(CompetitorProfile, row) for row in rows]

    # --- trend signals / patterns
    def build_trend_signals(self, creator_id: str, market_id: str | None = None) -> list[TrendSignal]:
        observations = [item.to_dict() for item in self.list_observations(creator_id, market_id)]
        trend_points = compute_trend_points(observations)
        results: list[TrendSignal] = []
        for key, point in trend_points.items():
            latest = point.get("latest") or {}
            values = [value for value in point.get("values", []) if value is not None]
            if not values:
                continue
            direction = TrendDirection.UP if (point.get("velocity") or 0) > 0 else TrendDirection.DOWN if (point.get("velocity") or 0) < 0 else TrendDirection.FLAT
            lifecycle_stage = LifecycleStage.GROWING if direction == TrendDirection.UP else LifecycleStage.DECLINING if direction == TrendDirection.DOWN else LifecycleStage.UNKNOWN
            saturation = calculate_saturation(supporting_count=len(values), contradicting_count=0, sample_size=len(values)) or 0.0
            signal = TrendSignal(
                id=f"signal-{uuid4()}",
                creator_id=creator_id,
                market_id=market_id,
                topic_id=latest.get("topic_id"),
                platform=str(latest.get("platform") or "unknown"),
                region=latest.get("region"),
                language=latest.get("language"),
                signal_type=TrendSignalType.TOPIC_GROWTH if direction == TrendDirection.UP else TrendSignalType.TOPIC_DECLINE if direction == TrendDirection.DOWN else TrendSignalType.PERSISTENCE,
                lifecycle_stage=lifecycle_stage,
                direction=direction,
                magnitude=float(values[-1]) if values[-1] is not None else None,
                velocity=point.get("velocity"),
                acceleration=point.get("acceleration"),
                persistence=point.get("persistence"),
                saturation_level=SaturationLevel.HIGH if saturation > 0.6 else SaturationLevel.MEDIUM if saturation > 0.3 else SaturationLevel.LOW,
                novelty_level=max(0.0, 1.0 - saturation),
                sample_size=len(values),
                period_start=str(values[0]),
                period_end=str(values[-1]),
                confidence_level=ConfidenceLevel.MEDIUM if len(values) >= 3 else ConfidenceLevel.LOW,
                confidence_score=min(1.0, len(values) / 10),
                status="observed",
                created_at=current_utc_iso(),
                updated_at=current_utc_iso(),
                expires_at=None,
            )
            saved = self.repository.upsert_record("trend_signals", signal.to_dict(), conflict_columns=("id",))
            results.append(_row_to_model(TrendSignal, saved))
        return results

    def list_trend_signals(self, creator_id: str, market_id: str | None = None) -> list[TrendSignal]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("trend_signals", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(TrendSignal, row) for row in rows]

    def detect_patterns(self, creator_id: str, market_id: str | None = None) -> list[MarketPattern]:
        items = self.list_external_content_items(creator_id)
        clusters = cluster_patterns([item.to_dict() for item in items])
        patterns: list[MarketPattern] = []
        for cluster in clusters:
            pattern = MarketPattern(
                id=f"pattern-{uuid4()}",
                creator_id=creator_id,
                market_id=market_id,
                platform=None,
                pattern_type=PatternType(cluster.get("pattern_type") or PatternType.TOPIC.value),
                canonical_name=str(cluster.get("canonical_name") or "pattern"),
                description="Patron observado a partir de referencias publicas.",
                pattern_definition_json=_ensure_json(cluster),
                sample_size=int(cluster.get("sample_size") or 0),
                supporting_count=int(cluster.get("supporting_count") or 0),
                contradicting_count=int(cluster.get("contradicting_count") or 0),
                confidence_level=ConfidenceLevel.MEDIUM if int(cluster.get("sample_size") or 0) >= 3 else ConfidenceLevel.LOW,
                status=PatternStatus.ACTIVE,
                first_observed_at=current_utc_iso(),
                last_observed_at=current_utc_iso(),
                created_at=current_utc_iso(),
                updated_at=current_utc_iso(),
            )
            saved = self.repository.upsert_record("market_patterns", pattern.to_dict(), conflict_columns=("id",))
            patterns.append(_row_to_model(MarketPattern, saved))
        return patterns

    def list_patterns(self, creator_id: str, market_id: str | None = None) -> list[MarketPattern]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_patterns", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(MarketPattern, row) for row in rows]

    # --- fit / opportunity
    def evaluate_creator_market_fit(self, *, creator_id: str, target_type: str, target_id: str, market_topics: list[str] | None = None, platform_scope: list[str] | None = None, evidence_strength: float = 0.5, copying_risk: float = 0.0, creator_memory_snapshot_id: str | None = None, creator_language_snapshot_id: str | None = None, audience_profile_snapshot_id: str | None = None) -> CreatorMarketFitEvaluation:
        fit = evaluate_creator_fit(
            creator_profile={"creator_id": creator_id, "target_type": target_type, "target_id": target_id},
            market_topics=market_topics or [],
            platform_scope=platform_scope or [],
            evidence_strength=evidence_strength,
            copying_risk=copying_risk,
        )
        record = CreatorMarketFitEvaluation(
            id=f"fit-{uuid4()}",
            creator_id=creator_id,
            target_type=target_type,
            target_id=target_id,
            creator_memory_snapshot_id=creator_memory_snapshot_id,
            creator_language_snapshot_id=creator_language_snapshot_id,
            audience_profile_snapshot_id=audience_profile_snapshot_id,
            analytics_context_json=_ensure_json({}),
            brand_fit=fit["brand_fit"],
            audience_fit=fit["audience_fit"],
            historical_fit=fit["historical_fit"],
            platform_fit=fit["platform_fit"],
            strategic_fit=fit["strategic_fit"],
            authenticity_fit=fit["authenticity_fit"],
            capability_fit=fit["capability_fit"],
            timing_fit=fit["timing_fit"],
            differentiation_potential=fit["differentiation_potential"],
            copying_risk=copying_risk,
            overall_fit=fit["overall_fit"],
            confidence_level=ConfidenceLevel.MEDIUM,
            limitations_json=_ensure_json([]),
            created_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("creator_market_fit_evaluations", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(CreatorMarketFitEvaluation, saved)

    def build_opportunity_candidates(self, creator_id: str, market_id: str | None = None) -> list[OpportunityCandidate]:
        signals = self.list_trend_signals(creator_id, market_id)
        patterns = self.list_patterns(creator_id, market_id)
        results: list[OpportunityCandidate] = []
        for signal in signals[:10]:
            fit = self.evaluate_creator_market_fit(
                creator_id=creator_id,
                target_type="trend_signal",
                target_id=signal.id,
                market_topics=[signal.topic_id or signal.platform],
                platform_scope=[signal.platform],
                evidence_strength=signal.confidence_score or 0.5,
                copying_risk=0.1,
            )
            candidate = _row_to_model(
                OpportunityCandidate,
                build_opportunity_candidate(
                    creator_id=creator_id,
                    market_id=market_id,
                    topic_id=signal.topic_id,
                    trend_signal_id=signal.id,
                    pattern_id=patterns[0].id if patterns else None,
                    title=f"Oportunidad: {getattr(signal.signal_type, 'value', signal.signal_type)}",
                    summary=f"Señal {getattr(signal.direction, 'value', signal.direction)} con confianza {getattr(fit.confidence_level, 'value', fit.confidence_level)}",
                    opportunity_type=OpportunityType.TOPIC.value,
                    fit={
                        "overall_fit": fit.overall_fit,
                        "audience_fit": fit.audience_fit,
                        "historical_fit": fit.historical_fit,
                        "differentiation_potential": fit.differentiation_potential,
                        "copying_risk": fit.copying_risk,
                        "lifecycle_stage": getattr(signal.lifecycle_stage, "value", signal.lifecycle_stage),
                        "urgency": UrgencyLevel.MEDIUM.value,
                        "freshness_status": FreshnessStatus.FRESH.value,
                        "saturation_level": getattr(signal.saturation_level, "value", signal.saturation_level),
                    },
                    evidence_quality=EvidenceQuality.MEDIUM.value,
                    confidence_level=ConfidenceLevel.MEDIUM.value,
                    platform_scope_json=_ensure_json([signal.platform]),
                    content_type_scope_json=_ensure_json(["video"]),
                    expires_at=None,
                ),
            )
            saved = self.repository.upsert_record("opportunity_candidates", candidate.to_dict(), conflict_columns=("id",))
            results.append(_row_to_model(OpportunityCandidate, saved))
        return results

    def list_opportunity_candidates(self, creator_id: str, market_id: str | None = None) -> list[OpportunityCandidate]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("opportunity_candidates", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(OpportunityCandidate, row) for row in rows]

    def list_fit_evaluations(self, creator_id: str) -> list[CreatorMarketFitEvaluation]:
        rows = self.repository.fetch_records("creator_market_fit_evaluations", where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")
        return [_row_to_model(CreatorMarketFitEvaluation, row) for row in rows]

    def list_reviews(self, creator_id: str) -> list[MarketReview]:
        rows = self.repository.fetch_records("market_reviews", where="creator_id = ?", params=(creator_id,), order_by="reviewed_at DESC")
        return [_row_to_model(MarketReview, row) for row in rows]

    def list_snapshots(self, creator_id: str, market_id: str | None = None) -> list[MarketSnapshot]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_snapshots", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(MarketSnapshot, row) for row in rows]

    def list_reports(self, creator_id: str, market_id: str | None = None) -> list[MarketReport]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if market_id is not None:
            where += " AND market_id = ?"
            params.append(market_id)
        rows = self.repository.fetch_records("market_reports", where=where, params=tuple(params), order_by="created_at DESC")
        return [_row_to_model(MarketReport, row) for row in rows]

    def list_external_content_snapshots(self, creator_id: str, external_content_item_id: str | None = None) -> list[ExternalContentSnapshot]:
        where = "creator_id = ?"
        params: list[Any] = [creator_id]
        if external_content_item_id is not None:
            where += " AND external_content_item_id = ?"
            params.append(external_content_item_id)
        rows = self.repository.fetch_records("external_content_snapshots", where=where, params=tuple(params), order_by="observed_at DESC")
        return [_row_to_model(ExternalContentSnapshot, row) for row in rows]

    def cancel_research_run(self, run_id: str) -> ResearchRun | None:
        run = self.repository.fetch_record("market_research_runs", where="id = ?", params=(run_id,))
        if run is None:
            return None
        updated = {
            **run,
            "status": "cancelled",
            "completed_at": current_utc_iso(),
        }
        saved = self.repository.upsert_record("market_research_runs", updated, conflict_columns=("id",))
        return _row_to_model(ResearchRun, saved)

    def resume_research_run(self, run_id: str) -> ResearchRun | None:
        run = self.repository.fetch_record("market_research_runs", where="id = ?", params=(run_id,))
        if run is None:
            return None
        updated = {
            **run,
            "status": "running",
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "updated_at": current_utc_iso(),
        }
        saved = self.repository.upsert_record("market_research_runs", updated, conflict_columns=("id",))
        return _row_to_model(ResearchRun, saved)

    def evaluate_copying_risk(self, creator_id: str, external_content_item_id: str) -> dict[str, Any]:
        item = self.repository.fetch_record("external_content_items", where="id = ? AND creator_id = ?", params=(external_content_item_id, creator_id))
        if item is None:
            return {"copying_risk": 0.0, "reason": "missing_item"}
        creator_profile = {}
        if self.creator_memory_service is not None:
            try:
                profile = self.creator_memory_service.get_profile(creator_id)
                creator_profile = profile.to_dict() if hasattr(profile, "to_dict") else dict(profile or {})
            except Exception:
                creator_profile = {}
        return detect_copying_risk(external_content=item, creator_profile=creator_profile)

    # --- reviews / snapshots / reports
    def review_target(self, *, creator_id: str, target_type: str, target_id: str, decision: str, reason: str, previous_value: dict[str, Any] | None = None, new_value: dict[str, Any] | None = None) -> MarketReview:
        record = MarketReview(
            id=f"review-{uuid4()}",
            creator_id=creator_id,
            target_type=target_type,
            target_id=target_id,
            decision=decision,
            previous_value_json=_ensure_json(previous_value),
            new_value_json=_ensure_json(new_value),
            reason=normalize_text(reason),
            reviewed_at=current_utc_iso(),
            created_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_reviews", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketReview, saved)

    def snapshot_market(self, *, creator_id: str, market_id: str | None, snapshot_type: str, period_start: str, period_end: str, payload: dict[str, Any]) -> MarketSnapshot:
        record = MarketSnapshot(
            id=f"snapshot-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            snapshot_type=snapshot_type,
            period_start=period_start,
            period_end=period_end,
            source_fingerprint=build_market_fingerprint(creator_id, market_id, snapshot_type, period_start, period_end, payload),
            snapshot_json=_ensure_json(payload) or "{}",
            created_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_snapshots", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketSnapshot, saved)

    def store_market_report(self, *, creator_id: str, market_id: str | None, report_type: str, period_start: str | None, period_end: str | None, payload: dict[str, Any]) -> MarketReport:
        record = MarketReport(
            id=f"report-{uuid4()}",
            creator_id=creator_id,
            market_id=market_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            source_fingerprint=build_market_fingerprint(creator_id, market_id, report_type, period_start, period_end, payload),
            report_json=_ensure_json(payload) or "{}",
            created_at=current_utc_iso(),
        )
        saved = self.repository.upsert_record("market_reports", record.to_dict(), conflict_columns=("id",))
        return _row_to_model(MarketReport, saved)

    def build_overview(self, creator_id: str) -> list[MarketOverviewRow]:
        markets = self.list_market_definitions(creator_id)
        rows: list[MarketOverviewRow] = []
        for market in markets:
            topics = self.list_market_topics(creator_id, market.id)
            sources = self.list_market_sources(creator_id)
            signals = self.list_trend_signals(creator_id, market.id)
            opportunities = self.list_opportunity_candidates(creator_id, market.id)
            latest_runs = self.repository.fetch_records(
                "market_research_runs",
                where="creator_id = ?",
                params=(creator_id,),
                order_by="created_at DESC",
            )
            latest_research = latest_runs[0] if latest_runs else None
            rows.append(
                MarketOverviewRow(
                    market_id=market.id,
                    market_name=market.name,
                    market_type=market.market_type.value if hasattr(market.market_type, "value") else str(market.market_type),
                    topic_count=len(topics),
                    source_count=len(sources),
                    signal_count=len(signals),
                    opportunity_count=len(opportunities),
                    latest_research_at=latest_research.get("completed_at") if latest_research else None,
                )
            )
        return rows

    def build_market_report(self, creator_id: str, market_id: str | None = None) -> MarketReport:
        payload = {
            "overview": [row.to_dict() for row in self.build_overview(creator_id)],
            "markets": [item.to_dict() for item in self.list_market_definitions(creator_id)],
            "topics": [item.to_dict() for item in self.list_market_topics(creator_id, market_id)],
            "sources": [item.to_dict() for item in self.list_market_sources(creator_id)],
            "queries": [item.to_dict() for item in self.list_research_queries(creator_id, market_id)],
            "runs": [item.to_dict() for item in self.list_research_runs(creator_id)],
            "observations": [item.to_dict() for item in self.list_observations(creator_id, market_id)],
            "signals": [item.to_dict() for item in self.list_trend_signals(creator_id, market_id)],
            "patterns": [item.to_dict() for item in self.list_patterns(creator_id, market_id)],
            "opportunities": [item.to_dict() for item in self.list_opportunity_candidates(creator_id, market_id)],
        }
        report = build_report(
            creator_id=creator_id,
            report_type="market_overview",
            market_id=market_id,
            period_start=None,
            period_end=None,
            payload=payload,
        )
        return _row_to_model(MarketReport, report)

    def export_market_report(self, report_id: str, format_name: str = "json") -> Path:
        report = self.repository.fetch_record("market_reports", where="id = ?", params=(report_id,))
        if report is None:
            raise MarketIntelligenceError(f"No se encontro el reporte {report_id}.")
        report_payload = json_loads(report.get("report_json"), {})
        export_dir = self._exports_root / report_id
        export_dir.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            path = export_dir / f"{report_id}.json"
            path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            return path
        if format_name == "txt":
            path = export_dir / f"{report_id}.txt"
            lines = [f"{key}: {value}" for key, value in report_payload.items()]
            path.write_text("\n".join(lines), encoding="utf-8")
            return path
        if format_name == "csv":
            path = export_dir / f"{report_id}.csv"
            rows = report_payload.get("opportunities") or []
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row.keys()})) if rows else csv.writer(handle)
                if rows:
                    writer.writeheader()
                    for row in rows:
                        sanitized = {key: (f"'{value}" if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value) for key, value in row.items()}
                        writer.writerow(sanitized)
                else:
                    handle.write("empty\n")
            return path
        raise MarketIntelligenceError(f"Formato no soportado: {format_name}")

    def build_background_tasks(self, creator_id: str) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for run in self.list_research_runs(creator_id):
            tasks.append(
                {
                    "task_id": run.id,
                    "title": "Investigacion de mercado",
                    "status": run.status,
                    "stage_name": run.status,
                    "progress_percent": 100.0 if run.status in {"completed", "completed_with_warnings"} else 0.0,
                    "message": run.error_message or run.status,
                    "error": run.error_message,
                    "cancellable": run.status in {"queued", "running"},
                    "created_at": run.created_at,
                    "updated_at": run.completed_at or run.created_at,
                    "payload": {"kind": "market_research_run", "run": run.to_dict(), "creator_id": creator_id, "source_id": run.source_id},
                }
            )
        for candidate in self.list_opportunity_candidates(creator_id):
            tasks.append(
                {
                    "task_id": candidate.id,
                    "title": "Candidato de oportunidad",
                    "status": candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status),
                    "stage_name": candidate.opportunity_type.value if hasattr(candidate.opportunity_type, "value") else str(candidate.opportunity_type),
                    "progress_percent": 0.0,
                    "message": candidate.summary,
                    "error": None,
                    "cancellable": False,
                    "created_at": candidate.created_at,
                    "updated_at": candidate.updated_at,
                    "payload": {"kind": "market_opportunity_candidate", "candidate": candidate.to_dict(), "creator_id": creator_id},
                }
            )
        return tasks


def build_market_intelligence_service(
    *,
    settings,
    paths: ProjectPaths,
    repository: SQLiteMarketIntelligenceRepository,
    database: SQLiteDatabase,
    source_registry: SourceRegistry | None = None,
    catalog_service: Any | None = None,
    analytics_service: Any | None = None,
    creator_memory_service: Any | None = None,
    creator_language_service: Any | None = None,
    audience_service: Any | None = None,
    analytics_lab_service: Any | None = None,
    logger: logging.Logger | None = None,
) -> MarketIntelligenceService:
    return MarketIntelligenceService(
        settings=settings,
        paths=paths,
        repository=repository,
        database=database,
        source_registry=source_registry,
        catalog_service=catalog_service,
        analytics_service=analytics_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        analytics_lab_service=analytics_lab_service,
        logger=logger,
    )
