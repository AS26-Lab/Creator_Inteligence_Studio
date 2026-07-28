"""Servicio determinista para Opportunity and Recommendation Engine Foundation."""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.application.services.analytics_lab_service import AnalyticsLabService
from creator_intelligence_studio.application.services.audience_model_service import AudienceModelService
from creator_intelligence_studio.application.services.catalog_service import CatalogService
from creator_intelligence_studio.application.services.creator_language_service import CreatorLanguageService
from creator_intelligence_studio.application.services.creator_memory_service import CreatorMemoryService
from creator_intelligence_studio.application.services.creative_packaging_service import CreativePackagingService
from creator_intelligence_studio.application.services.experiment_service import ExperimentService
from creator_intelligence_studio.application.services.market_intelligence_service import MarketIntelligenceService
from creator_intelligence_studio.application.services.platform_integration_service import PlatformIntegrationService
from creator_intelligence_studio.domain.recommendations import (
    AlternativeType,
    ConfidenceLevel,
    ConstraintType,
    EvidenceQuality,
    EvidenceStrength,
    EvidenceType,
    FactInferenceHypothesis,
    FreshnessStatus,
    LifecycleStage,
    MetricAvailabilityStatus,
    MetricRole,
    ObjectiveType,
    PriorityLevel,
    RecommendationAction,
    RecommendationAlternative,
    RecommendationCandidate,
    RecommendationConstraint,
    RecommendationContextSnapshot,
    RecommendationContradiction,
    RecommendationEvidence,
    RecommendationExperimentLink,
    RecommendationExecutionRecord,
    RecommendationFeedback,
    RecommendationInvalidationCriterion,
    RecommendationLifecycleStatus,
    RecommendationMetric,
    RecommendationOutcomeSnapshot,
    RecommendationRequest,
    RecommendationReport,
    RecommendationReview,
    RecommendationRun,
    RecommendationRunStatus,
    RecommendationSnapshot,
    RecommendationType,
    ReviewDecision,
    RecommendationRisk,
    RiskSeverity,
    RiskType,
)
from creator_intelligence_studio.domain.recommendations.entities import RecommendationRunItem
from creator_intelligence_studio.domain.recommendations.errors import RecommendationNotFoundError, RecommendationValidationError
from creator_intelligence_studio.domain.recommendations.services import build_recommendation_fingerprint
from creator_intelligence_studio.domain.recommendations.recommendation_types import FeedbackType
from creator_intelligence_studio.domain.recommendations.repositories import RecommendationRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback: object) -> object:
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return value if value is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _normalize_enum(value: str | None, enum_cls, fallback):
    if value is None:
        return fallback
    try:
        return enum_cls(value)
    except Exception:
        return fallback


def _safe_list(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _safe_csv_value(value: object) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def _entity_from_row(cls, row: dict[str, Any] | None, enum_fields: dict[str, Any] | None = None):
    if row is None:
        return None
    payload = dict(row)
    for field_name, enum_cls in (enum_fields or {}).items():
        if payload.get(field_name) is None:
            continue
        try:
            payload[field_name] = enum_cls(payload[field_name])
        except Exception:
            pass
    return cls(**payload)


@dataclass(frozen=True, slots=True)
class RecommendationGenerationResult:
    run: RecommendationRun
    request: RecommendationRequest
    context_snapshot: RecommendationContextSnapshot
    recommendations: tuple[RecommendationCandidate, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "run": self.run.to_dict(),
            "request": self.request.to_dict(),
            "context_snapshot": self.context_snapshot.to_dict(),
            "recommendations": [item.to_dict() for item in self.recommendations],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class RecommendationEngineService:
    ENGINE_VERSION = "v1"

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        database: SQLiteDatabase,
        repository: RecommendationRepository,
        catalog_service: CatalogService | None = None,
        analytics_service: AnalyticsQueryService | None = None,
        analytics_lab_service: AnalyticsLabService | None = None,
        creator_memory_service: CreatorMemoryService | None = None,
        creator_language_service: CreatorLanguageService | None = None,
        audience_service: AudienceModelService | None = None,
        market_service: MarketIntelligenceService | None = None,
        platform_service: PlatformIntegrationService | None = None,
        creative_packaging_service: CreativePackagingService | None = None,
        experiment_service: ExperimentService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.database = database
        self.repository = repository
        self.catalog_service = catalog_service
        self.analytics_service = analytics_service
        self.analytics_lab_service = analytics_lab_service
        self.creator_memory_service = creator_memory_service
        self.creator_language_service = creator_language_service
        self.audience_service = audience_service
        self.market_service = market_service
        self.platform_service = platform_service
        self.creative_packaging_service = creative_packaging_service
        self.experiment_service = experiment_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.recommendations")
        self._reports_root = self.paths.data_directory / "recommendations" / "reports"
        self._reports_root.mkdir(parents=True, exist_ok=True)

    def _upsert(self, table: str, payload: dict[str, Any], conflict_columns: tuple[str, ...] = ("id",)) -> dict[str, Any]:
        return self.repository.upsert_record(table, payload, conflict_columns=conflict_columns)

    def _fetch(self, table: str, *, where: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        return self.repository.fetch_record(table, where=where, params=params)

    def _fetch_many(self, table: str, *, where: str = "", params: tuple[Any, ...] = (), order_by: str | None = None) -> list[dict[str, Any]]:
        return self.repository.fetch_records(table, where=where, params=params, order_by=order_by)

    def _list_entities(self, table: str, cls, *, where: str, params: tuple[Any, ...], order_by: str | None = None, enum_fields: dict[str, Any] | None = None):
        return [
            _entity_from_row(cls, row, enum_fields)
            for row in self._fetch_many(table, where=where, params=params, order_by=order_by)
        ]

    def _fetch_entity(self, table: str, cls, *, where: str, params: tuple[Any, ...], enum_fields: dict[str, Any] | None = None):
        return _entity_from_row(cls, self._fetch(table, where=where, params=params), enum_fields)

    def _latest_snapshot_id(self, snapshots: list[Any]) -> str | None:
        return snapshots[0].id if snapshots else None

    def _first_or_none(self, items: list[Any]) -> Any | None:
        return items[0] if items else None

    def _safe_get_creator(self, creator_id: str):
        if self.catalog_service is None:
            return None
        try:
            return self.catalog_service.get_creator(creator_id)
        except Exception:
            return None

    def _collect_context_payload(self, creator_id: str, request_payload: dict[str, object]) -> tuple[RecommendationContextSnapshot, dict[str, object], list[str]]:
        warnings: list[str] = []
        creator_memory_snapshot_id = None
        creator_language_snapshot_id = None
        audience_snapshot_id = None
        analytics_snapshot_id = None
        market_snapshot_id = None
        platform_snapshot_id = None
        experiment_snapshot_id = None
        packaging_snapshot_id = None

        if self.creator_memory_service is not None:
            try:
                snapshots = self.creator_memory_service.list_profile_snapshots(creator_id)
                creator_memory_snapshot_id = self._latest_snapshot_id(snapshots)
            except Exception:
                warnings.append("creator_memory_unavailable")
        else:
            warnings.append("creator_memory_missing")

        if self.creator_language_service is not None:
            try:
                snapshots = self.creator_language_service.list_profile_snapshots(creator_id)
                creator_language_snapshot_id = self._latest_snapshot_id(snapshots)
            except Exception:
                warnings.append("creator_language_unavailable")
        else:
            warnings.append("creator_language_missing")

        if self.audience_service is not None:
            try:
                profiles = self.audience_service.list_profiles(creator_id)
                audience_snapshot_id = self._latest_snapshot_id(profiles)
            except Exception:
                warnings.append("audience_unavailable")
        else:
            warnings.append("audience_missing")

        if self.analytics_lab_service is not None:
            try:
                reports = self.analytics_lab_service.list_reports(creator_id)
                analytics_snapshot_id = self._latest_snapshot_id(reports)
            except Exception:
                warnings.append("analytics_lab_unavailable")
        else:
            warnings.append("analytics_lab_missing")

        if self.market_service is not None:
            try:
                snapshots = self.market_service.list_snapshots(creator_id)
                market_snapshot_id = self._latest_snapshot_id(snapshots)
            except Exception:
                warnings.append("market_unavailable")
        else:
            warnings.append("market_missing")

        if self.platform_service is not None:
            try:
                reports = self.platform_service.list_reports(creator_id)
                platform_snapshot_id = self._latest_snapshot_id(reports)
            except Exception:
                warnings.append("platform_unavailable")
        else:
            warnings.append("platform_missing")

        if self.experiment_service is not None:
            try:
                experiments = self.experiment_service.list_experiments(creator_id)
                experiment_snapshot_id = self._latest_snapshot_id(experiments)
            except Exception:
                warnings.append("experiments_unavailable")
        else:
            warnings.append("experiments_missing")

        if self.creative_packaging_service is not None:
            try:
                profiles = self.creative_packaging_service.list_brand_profiles(creator_id)
                packaging_snapshot_id = self._latest_snapshot_id(profiles)
            except Exception:
                warnings.append("packaging_unavailable")
        else:
            warnings.append("packaging_missing")

        payload = {
            "creator_id": creator_id,
            "request": request_payload,
            "snapshots": {
                "creator_memory_snapshot_id": creator_memory_snapshot_id,
                "creator_language_snapshot_id": creator_language_snapshot_id,
                "audience_snapshot_id": audience_snapshot_id,
                "analytics_snapshot_id": analytics_snapshot_id,
                "market_snapshot_id": market_snapshot_id,
                "platform_snapshot_id": platform_snapshot_id,
                "experiment_snapshot_id": experiment_snapshot_id,
                "packaging_snapshot_id": packaging_snapshot_id,
            },
            "warnings": warnings,
            "engine_version": self.ENGINE_VERSION,
            "created_at": utc_now().isoformat(),
        }
        fingerprint = build_recommendation_fingerprint(payload)
        snapshot = RecommendationContextSnapshot(
            id=str(uuid4()),
            creator_id=creator_id,
            context_type="recommendation_context",
            context_version=self.ENGINE_VERSION,
            creator_memory_snapshot_id=creator_memory_snapshot_id,
            creator_language_snapshot_id=creator_language_snapshot_id,
            audience_snapshot_id=audience_snapshot_id,
            analytics_snapshot_id=analytics_snapshot_id,
            market_snapshot_id=market_snapshot_id,
            platform_snapshot_id=platform_snapshot_id,
            experiment_snapshot_id=experiment_snapshot_id,
            packaging_snapshot_id=packaging_snapshot_id,
            source_fingerprint=fingerprint,
            context_json=_json_dumps(payload),
            created_at=utc_now().isoformat(),
        )
        return snapshot, payload, warnings

    def _objective(self, value: str | None) -> ObjectiveType:
        if value is None:
            return ObjectiveType.UNKNOWN
        try:
            return ObjectiveType(value)
        except Exception:
            return ObjectiveType.UNKNOWN

    def _request_type(self, value: str | None) -> str:
        return value or "general_strategy"

    def create_request(
        self,
        *,
        creator_id: str,
        request_type: str,
        objective_type: str | None = None,
        platform_scope_json: str = "[]",
        content_type_scope_json: str = "[]",
        market_id: str | None = None,
        topic_id: str | None = None,
        time_horizon: str | None = None,
        constraints_json: str = "{}",
        preferences_json: str = "{}",
        status: str = "requested",
    ) -> RecommendationRequest:
        request = RecommendationRequest(
            id=str(uuid4()),
            creator_id=creator_id,
            request_type=self._request_type(request_type),
            objective_type=self._objective(objective_type),
            platform_scope_json=platform_scope_json,
            content_type_scope_json=content_type_scope_json,
            market_id=market_id,
            topic_id=topic_id,
            time_horizon=time_horizon,
            constraints_json=constraints_json,
            preferences_json=preferences_json,
            status=status,
            requested_at=utc_now().isoformat(),
            created_at=utc_now().isoformat(),
            updated_at=utc_now().isoformat(),
        )
        saved = self._upsert("recommendation_requests", request.to_dict())
        return _entity_from_row(RecommendationRequest, saved, {"objective_type": ObjectiveType})

    def list_requests(self, creator_id: str) -> list[RecommendationRequest]:
        return self._list_entities(
            "recommendation_requests",
            RecommendationRequest,
            where="creator_id = ?",
            params=(creator_id,),
            order_by="created_at DESC",
            enum_fields={"objective_type": ObjectiveType},
        )

    def get_request(self, request_id: str) -> RecommendationRequest | None:
        return self._fetch_entity("recommendation_requests", RecommendationRequest, where="id = ?", params=(request_id,), enum_fields={"objective_type": ObjectiveType})

    def _platform_list(self, scope_json: str | None) -> list[str]:
        value = _json_loads(scope_json, [])
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    def _content_type_list(self, scope_json: str | None) -> list[str]:
        value = _json_loads(scope_json, [])
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    def _objective_metric(self, objective: ObjectiveType) -> str:
        mapping = {
            ObjectiveType.WATCH_TIME: "watch_time",
            ObjectiveType.RETENTION: "retention",
            ObjectiveType.COMPLETION: "completion",
            ObjectiveType.ENGAGEMENT: "engagement",
            ObjectiveType.SAVES: "saves",
            ObjectiveType.SHARES: "shares",
            ObjectiveType.COMMENTS: "comments",
            ObjectiveType.SUBSCRIBER_GROWTH: "subscribers_gained",
            ObjectiveType.FOLLOWER_GROWTH: "followers_gained",
            ObjectiveType.SEARCH_DISCOVERY: "search_discovery",
            ObjectiveType.PLATFORM_CONVERSION: "platform_conversion",
            ObjectiveType.LONGFORM_CONVERSION: "longform_conversion",
            ObjectiveType.SHORTFORM_CONVERSION: "shortform_conversion",
            ObjectiveType.PACKAGING_LEARNING: "ctr",
            ObjectiveType.MARKET_VALIDATION: "public_views",
            ObjectiveType.AUDIENCE_VALIDATION: "audience_fit",
            ObjectiveType.CREATOR_POSITIONING: "creator_positioning",
            ObjectiveType.BRAND_CONSISTENCY: "brand_fit",
            ObjectiveType.OPERATIONAL_EFFICIENCY: "effort",
        }
        return mapping.get(objective, "views")

    def _opportunity_to_recommendation_type(self, opportunity_type: str) -> RecommendationType:
        mapping = {
            "topic": RecommendationType.TOPIC,
            "format": RecommendationType.FORMAT,
            "angle": RecommendationType.DIFFERENTIATION,
            "comparison": RecommendationType.RESEARCH,
            "audience": RecommendationType.AUDIENCE,
            "saturation_gap": RecommendationType.CONTENT_GAP,
            "cross_platform_adaptation": RecommendationType.CROSS_PLATFORM_ADAPTATION,
        }
        return mapping.get(opportunity_type, RecommendationType.TOPIC)

    def _build_evidence(self, recommendation_candidate_id: str, candidate: Any, request: RecommendationRequest, context_snapshot_id: str, market_source: str) -> tuple[RecommendationEvidence, ...]:
        evidence: list[RecommendationEvidence] = []
        evidence.append(
            RecommendationEvidence(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                evidence_type=EvidenceType.PUBLIC_METRIC_SNAPSHOT,
                source_domain="market_intelligence",
                source_id=getattr(candidate, "market_id", None),
                source_snapshot_id=context_snapshot_id,
                supports_recommendation=True,
                evidence_strength=EvidenceStrength.STRONG if getattr(candidate, "confidence_level", None) else EvidenceStrength.MODERATE,
                evidence_quality=EvidenceQuality.MEDIUM,
                weight=0.5,
                fact_inference_hypothesis=FactInferenceHypothesis.FACT,
                description=f"Opportunity candidate from {market_source}",
                created_at=utc_now().isoformat(),
                limitations_json=_json_dumps(["candidate_from_market_intelligence", "platform_specific"]),
            )
        )
        if request.objective_type is not None:
            evidence.append(
                RecommendationEvidence(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    evidence_type=EvidenceType.HUMAN_NOTE,
                    source_domain="request",
                    source_id=request.id,
                    source_snapshot_id=context_snapshot_id,
                    supports_recommendation=True,
                    evidence_strength=EvidenceStrength.MODERATE,
                    evidence_quality=EvidenceQuality.MEDIUM,
                    weight=0.25,
                    fact_inference_hypothesis=FactInferenceHypothesis.INFERENCE,
                    description=f"Objective alignment: {request.objective_type.value}",
                    created_at=utc_now().isoformat(),
                    limitations_json=_json_dumps(["user_objective"]),
                )
            )
        return tuple(evidence)

    def _build_risks(self, recommendation_candidate_id: str, candidate: Any, request: RecommendationRequest) -> tuple[RecommendationRisk, ...]:
        risks: list[RecommendationRisk] = []
        copying_risk = float(getattr(candidate, "copying_risk", 0.0) or 0.0)
        if copying_risk >= 0.75:
            risks.append(
                RecommendationRisk(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    risk_type=RiskType.COPYING,
                    severity=RiskSeverity.CRITICAL,
                    description="Copying risk alto; no se debe ejecutar automaticamente.",
                    blocking=True,
                    likelihood=copying_risk,
                    impact=0.9,
                    mitigation="Extraer principio abstracto y pedir revision humana.",
                    created_at=utc_now().isoformat(),
                )
            )
        if request.time_horizon and str(request.time_horizon).lower() in {"short", "weekly"}:
            risks.append(
                RecommendationRisk(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    risk_type=RiskType.TIMING,
                    severity=RiskSeverity.WARNING,
                    description="Ventana temporal corta; la frescura debe vigilarse.",
                    blocking=False,
                    likelihood=0.4,
                    impact=0.3,
                    mitigation="Revisar antes de expirar.",
                    created_at=utc_now().isoformat(),
                )
            )
        if getattr(candidate, "saturation_level", None) and str(getattr(candidate, "saturation_level")) in {"high", "very_high"}:
            risks.append(
                RecommendationRisk(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    risk_type=RiskType.SATURATION,
                    severity=RiskSeverity.WARNING,
                    description="El mercado muestra saturacion relevante.",
                    blocking=False,
                    likelihood=0.6,
                    impact=0.4,
                    mitigation="Diferenciacion y alcance limitado.",
                    created_at=utc_now().isoformat(),
                )
            )
        return tuple(risks)

    def _build_constraints(self, recommendation_candidate_id: str, request: RecommendationRequest, platform_available: bool, measurement_available: bool) -> tuple[RecommendationConstraint, ...]:
        raw_constraints = _safe_list(_json_loads(request.constraints_json, []))
        constraints: list[RecommendationConstraint] = []
        for index, constraint in enumerate(raw_constraints, start=1):
            if not isinstance(constraint, dict):
                continue
            constraints.append(
                RecommendationConstraint(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    constraint_type=_normalize_enum(str(constraint.get("constraint_type") or "unknown"), ConstraintType, ConstraintType.UNKNOWN),
                    source=str(constraint.get("source") or "user"),
                    description=str(constraint.get("description") or ""),
                    satisfied=bool(constraint.get("satisfied", True)),
                    blocking=bool(constraint.get("blocking", False)),
                    resolution_action=constraint.get("resolution_action"),
                    created_at=utc_now().isoformat(),
                )
            )
        constraints.append(
            RecommendationConstraint(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                constraint_type=ConstraintType.PLATFORM_CAPABILITY,
                source="platform_integration",
                description="La plataforma objetivo debe estar disponible.",
                satisfied=platform_available,
                blocking=True,
                resolution_action="Reconnect or choose another platform" if not platform_available else None,
                created_at=utc_now().isoformat(),
            )
        )
        constraints.append(
            RecommendationConstraint(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                constraint_type=ConstraintType.MEASUREMENT_AVAILABILITY,
                source="metric_selector",
                description="La metrica primaria debe ser medible o declarada manual.",
                satisfied=measurement_available,
                blocking=not measurement_available,
                resolution_action="Importar metricas manuales" if not measurement_available else None,
                created_at=utc_now().isoformat(),
            )
        )
        return tuple(constraints)

    def _build_alternatives(self, recommendation_candidate_id: str, candidate: Any, request: RecommendationRequest, blocked: bool) -> tuple[RecommendationAlternative, ...]:
        alternatives: list[RecommendationAlternative] = []
        if blocked:
            alternatives.append(
                RecommendationAlternative(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    alternative_type=AlternativeType.LOWER_RISK,
                    title="Alternativa de menor riesgo",
                    summary="Reducir el parecido con la referencia externa y conservar solo el principio.",
                    reason="copying_risk_block",
                    platform_scope_json=request.platform_scope_json,
                    confidence_level=ConfidenceLevel.MEDIUM,
                    tradeoffs_json=_json_dumps(["lower_similarity", "lower_velocity"]),
                    created_at=utc_now().isoformat(),
                )
            )
            alternatives.append(
                RecommendationAlternative(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    alternative_type=AlternativeType.DO_NOTHING,
                    title="No perseguir por ahora",
                    summary="Esperar nueva evidencia o menor saturacion.",
                    reason="blocked_by_risk",
                    platform_scope_json=request.platform_scope_json,
                    confidence_level=ConfidenceLevel.HIGH,
                    tradeoffs_json=_json_dumps(["preserves_identity", "delays_learning"]),
                    created_at=utc_now().isoformat(),
                )
            )
        else:
            alternatives.append(
                RecommendationAlternative(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    alternative_type=AlternativeType.LOWER_EFFORT,
                    title="Validacion ligera",
                    summary="Probar una version corta o unica antes de ampliar.",
                    reason="reduce_scope",
                    platform_scope_json=request.platform_scope_json,
                    confidence_level=ConfidenceLevel.MEDIUM,
                    tradeoffs_json=_json_dumps(["less_depth", "faster_learning"]),
                    created_at=utc_now().isoformat(),
                )
            )
        return tuple(alternatives)

    def _build_metrics(self, recommendation_candidate_id: str, request: RecommendationRequest, platform: str) -> tuple[RecommendationMetric, ...]:
        objective = request.objective_type or ObjectiveType.UNKNOWN
        primary_metric = self._objective_metric(objective)
        availability = MetricAvailabilityStatus.AVAILABLE
        if platform == "tiktok" and primary_metric in {"watch_time", "retention", "completion", "saves", "profile_views"}:
            availability = MetricAvailabilityStatus.MANUAL_IMPORT_REQUIRED
        metrics = [
            RecommendationMetric(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                metric_role=MetricRole.PRIMARY,
                platform=platform,
                metric_key=primary_metric,
                internal_metric_key=primary_metric,
                availability_status=availability,
                unit="count",
                period_semantics="period",
                target_direction="up",
                measurement_window=request.time_horizon,
                source_type="automatic" if availability == MetricAvailabilityStatus.AVAILABLE else "manual",
                created_at=utc_now().isoformat(),
            ),
            RecommendationMetric(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                metric_role=MetricRole.GUARDRAIL,
                platform=platform,
                metric_key="copying_risk",
                internal_metric_key="copying_risk",
                availability_status=MetricAvailabilityStatus.AVAILABLE,
                unit="ratio",
                period_semantics="instant",
                target_direction="down",
                measurement_window=request.time_horizon,
                source_type="internal",
                created_at=utc_now().isoformat(),
            ),
        ]
        return tuple(metrics)

    def _build_invalidation_criteria(self, recommendation_candidate_id: str, candidate: Any, request: RecommendationRequest, blocked: bool) -> tuple[RecommendationInvalidationCriterion, ...]:
        metric_key = self._objective_metric(request.objective_type or ObjectiveType.UNKNOWN)
        criteria = [
            RecommendationInvalidationCriterion(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                criterion_type="metric_below_threshold",
                description=f"{metric_key} no mejora respecto al baseline.",
                metric_key=metric_key,
                operator="<",
                threshold_value="baseline",
                evaluation_window=request.time_horizon,
                severity="high" if blocked else "warning",
                created_at=utc_now().isoformat(),
            ),
            RecommendationInvalidationCriterion(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                criterion_type="guardrail_violation",
                description="Violacion de guardrail o boundary del creador.",
                severity="critical" if blocked else "high",
                evaluation_window=request.time_horizon,
                created_at=utc_now().isoformat(),
            ),
        ]
        return tuple(criteria)

    def _build_actions(self, recommendation_candidate_id: str, candidate: Any, blocked: bool) -> tuple[RecommendationAction, ...]:
        if blocked:
            return (
                RecommendationAction(
                    id=str(uuid4()),
                    recommendation_candidate_id=recommendation_candidate_id,
                    sequence_order=1,
                    action_type="stop",
                    title="Detener",
                    description="No ejecutar hasta revisar copying risk y restricciones.",
                    required=True,
                    estimated_effort="low",
                    dependency_ids_json=_json_dumps([]),
                    status="proposed",
                    created_at=utc_now().isoformat(),
                    updated_at=utc_now().isoformat(),
                ),
            )
        return (
            RecommendationAction(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                sequence_order=1,
                action_type="investigate",
                title="Investigar",
                description="Revisar evidencia, contexto y restricciones.",
                required=True,
                estimated_effort="low",
                dependency_ids_json=_json_dumps([]),
                status="proposed",
                created_at=utc_now().isoformat(),
                updated_at=utc_now().isoformat(),
            ),
            RecommendationAction(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                sequence_order=2,
                action_type="validate",
                title="Validar",
                description="Confirmar medicion y compatibilidad con la identidad del creador.",
                required=True,
                estimated_effort="medium",
                dependency_ids_json=_json_dumps([]),
                status="proposed",
                created_at=utc_now().isoformat(),
                updated_at=utc_now().isoformat(),
            ),
            RecommendationAction(
                id=str(uuid4()),
                recommendation_candidate_id=recommendation_candidate_id,
                sequence_order=3,
                action_type="review",
                title="Revisar",
                description="Exigir revision humana antes de ejecutar.",
                required=True,
                estimated_effort="low",
                dependency_ids_json=_json_dumps([]),
                status="proposed",
                created_at=utc_now().isoformat(),
                updated_at=utc_now().isoformat(),
            ),
        )

    def _score_candidate(self, opportunity: Any, request: RecommendationRequest, platform_available: bool, measurement_available: bool) -> dict[str, float | str]:
        platform_scope = self._platform_list(request.platform_scope_json)
        platform_fit = float(getattr(opportunity, "platform_fit", 0.5) or 0.5)
        if platform_scope and getattr(opportunity, "platform_scope_json", None):
            opportunity_scope = set(self._platform_list(getattr(opportunity, "platform_scope_json", "[]")))
            if opportunity_scope and not (opportunity_scope & set(platform_scope)):
                platform_fit = 0.2
        creator_fit = float(getattr(opportunity, "creator_fit", 0.5) or 0.5)
        audience_fit = float(getattr(opportunity, "audience_fit", 0.5) or 0.5)
        historical_fit = float(getattr(opportunity, "historical_fit", 0.5) or 0.5)
        market_fit = float(getattr(opportunity, "overall_fit", 0.5) or 0.5)
        strategic_fit = _clamp((creator_fit + audience_fit + historical_fit + market_fit + platform_fit) / 5.0)
        authenticity_fit = _clamp(1.0 - float(getattr(opportunity, "copying_risk", 0.0) or 0.0) * 0.7)
        timing_fit = 1.0
        if getattr(opportunity, "freshness_status", None) == "stale":
            timing_fit = 0.35
        elif getattr(opportunity, "freshness_status", None) == "expired":
            timing_fit = 0.1
        differentiation_potential = float(getattr(opportunity, "differentiation_potential", 0.5) or 0.5)
        operational_feasibility = 0.85 if platform_available else 0.2
        expected_learning_value = 0.7 if measurement_available else 0.45
        copying_risk = float(getattr(opportunity, "copying_risk", 0.0) or 0.0)
        overall_risk = _clamp((copying_risk + (1.0 - authenticity_fit) + (1.0 - operational_feasibility) + (0.35 if not measurement_available else 0.0)) / 4.0)
        raw_priority = strategic_fit * 0.25 + creator_fit * 0.15 + audience_fit * 0.1 + historical_fit * 0.1 + market_fit * 0.1 + platform_fit * 0.1 + differentiation_potential * 0.1 + expected_learning_value * 0.1 + timing_fit * 0.1 - overall_risk * 0.45
        return {
            "creator_fit": _clamp(creator_fit),
            "audience_fit": _clamp(audience_fit),
            "historical_fit": _clamp(historical_fit),
            "market_fit": _clamp(market_fit),
            "platform_fit": _clamp(platform_fit),
            "strategic_fit": _clamp(strategic_fit),
            "authenticity_fit": _clamp(authenticity_fit),
            "timing_fit": _clamp(timing_fit),
            "differentiation_potential": _clamp(differentiation_potential),
            "operational_feasibility": _clamp(operational_feasibility),
            "expected_learning_value": _clamp(expected_learning_value),
            "copying_risk": _clamp(copying_risk),
            "overall_risk": _clamp(overall_risk),
            "priority_score": round(_clamp(raw_priority), 4),
            "priority_level": self._priority_level(raw_priority, copying_risk, platform_available, measurement_available),
            "confidence_level": self._confidence_level(opportunity, request),
            "freshness_status": getattr(opportunity, "freshness_status", FreshnessStatus.UNKNOWN.value) or FreshnessStatus.UNKNOWN.value,
        }

    def _confidence_level(self, opportunity: Any, request: RecommendationRequest) -> ConfidenceLevel:
        evidence_quality = getattr(opportunity, "evidence_quality", None)
        if evidence_quality in {"high", EvidenceQuality.HIGH}:
            return ConfidenceLevel.HIGH
        if evidence_quality in {"medium", EvidenceQuality.MEDIUM}:
            return ConfidenceLevel.MEDIUM
        if evidence_quality in {"low", EvidenceQuality.LOW}:
            return ConfidenceLevel.LOW
        if request.time_horizon:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.UNKNOWN

    def _priority_level(self, priority_score: float, copying_risk: float, platform_available: bool, measurement_available: bool) -> PriorityLevel:
        if copying_risk >= 0.75:
            return PriorityLevel.BLOCKED
        if not platform_available or not measurement_available:
            return PriorityLevel.BLOCKED
        if priority_score >= 0.8:
            return PriorityLevel.CRITICAL
        if priority_score >= 0.7:
            return PriorityLevel.VERY_HIGH
        if priority_score >= 0.55:
            return PriorityLevel.HIGH
        if priority_score >= 0.4:
            return PriorityLevel.MEDIUM
        if priority_score >= 0.25:
            return PriorityLevel.LOW
        return PriorityLevel.VERY_LOW

    def _freshness(self, opportunity: Any) -> FreshnessStatus:
        return _normalize_enum(getattr(opportunity, "freshness_status", None), FreshnessStatus, FreshnessStatus.UNKNOWN)

    def _build_candidate_summary(self, opportunity: Any, request: RecommendationRequest, priority_level: PriorityLevel, blocked: bool) -> str:
        platform_scope = ",".join(self._platform_list(request.platform_scope_json) or [getattr(opportunity, "platform_scope_json", "platform") or "platform"])
        objective = request.objective_type.value if request.objective_type is not None else "unknown"
        base = f"Probar {getattr(opportunity, 'title', 'oportunidad')} en {platform_scope} para {objective}."
        if blocked:
            return base + " La propuesta queda bloqueada por riesgo o restriccion."
        return base + f" Prioridad {priority_level.value}."

    def _recommendation_type_from_opportunity(self, opportunity: Any, request: RecommendationRequest) -> RecommendationType:
        if request.request_type == "reduce_risk":
            return RecommendationType.RISK_REDUCTION
        return self._opportunity_to_recommendation_type(str(getattr(opportunity, "opportunity_type", "topic")))

    def _measurement_available(self, platform_scope: list[str], request: RecommendationRequest) -> bool:
        metric = self._objective_metric(request.objective_type or ObjectiveType.UNKNOWN)
        if not platform_scope:
            return True
        if any(platform == "tiktok" for platform in platform_scope) and metric in {"watch_time", "retention", "completion", "saves", "profile_views"}:
            return False
        return True

    def _platform_available(self, creator_id: str, platform_scope: list[str]) -> bool:
        if not platform_scope:
            return True
        if self.platform_service is None:
            return False
        try:
            connections = self.platform_service.list_connections(creator_id)
        except Exception:
            connections = []
        available = {getattr(connection, "platform", None).value if hasattr(getattr(connection, "platform", None), "value") else getattr(connection, "platform", None) for connection in connections}
        return any(platform in available for platform in platform_scope)

    def _create_recommendation_record(self, opportunity: Any, request: RecommendationRequest, run: RecommendationRun, context_snapshot_id: str, platform_available: bool, measurement_available: bool) -> RecommendationCandidate:
        score = self._score_candidate(opportunity, request, platform_available, measurement_available)
        blocked = score["priority_level"] == PriorityLevel.BLOCKED
        recommendation_type = self._recommendation_type_from_opportunity(opportunity, request)
        candidate = RecommendationCandidate(
            id=str(uuid4()),
            creator_id=request.creator_id,
            recommendation_run_id=run.id,
            source_opportunity_candidate_id=getattr(opportunity, "id", None),
            recommendation_type=recommendation_type,
            objective_type=request.objective_type or ObjectiveType.UNKNOWN,
            title=getattr(opportunity, "title", "Recomendacion") or "Recomendacion",
            summary=self._build_candidate_summary(opportunity, request, score["priority_level"], blocked),
            platform_scope_json=request.platform_scope_json,
            content_type_scope_json=request.content_type_scope_json,
            audience_scope_json=_json_dumps({"audience_fit": score["audience_fit"]}),
            market_scope_json=_json_dumps({"market_fit": score["market_fit"]}),
            topic_scope_json=_json_dumps({"topic_id": request.topic_id, "market_id": request.market_id}),
            time_horizon=request.time_horizon,
            status=RecommendationLifecycleStatus.BLOCKED if blocked else RecommendationLifecycleStatus.NEEDS_REVIEW,
            priority_level=score["priority_level"],
            priority_score=score["priority_score"],
            confidence_level=score["confidence_level"],
            confidence_score=score["priority_score"],
            freshness_status=self._freshness(opportunity),
            creator_fit=score["creator_fit"],
            audience_fit=score["audience_fit"],
            historical_fit=score["historical_fit"],
            market_fit=score["market_fit"],
            platform_fit=score["platform_fit"],
            strategic_fit=score["strategic_fit"],
            authenticity_fit=score["authenticity_fit"],
            timing_fit=score["timing_fit"],
            differentiation_potential=score["differentiation_potential"],
            operational_feasibility=score["operational_feasibility"],
            expected_learning_value=score["expected_learning_value"],
            copying_risk=score["copying_risk"],
            overall_risk=score["overall_risk"],
            created_at=utc_now().isoformat(),
            updated_at=utc_now().isoformat(),
            expires_at=None,
        )
        saved = self._upsert("recommendation_candidates", candidate.to_dict())
        candidate = _entity_from_row(RecommendationCandidate, saved, {"recommendation_type": RecommendationType, "objective_type": ObjectiveType, "status": RecommendationLifecycleStatus, "priority_level": PriorityLevel, "confidence_level": ConfidenceLevel, "freshness_status": FreshnessStatus})
        evidence = self._build_evidence(candidate.id, opportunity, request, context_snapshot_id, "market_intelligence")
        risks = self._build_risks(candidate.id, opportunity, request)
        constraints = self._build_constraints(candidate.id, request, platform_available, measurement_available)
        alternatives = self._build_alternatives(candidate.id, opportunity, request, blocked)
        metrics = self._build_metrics(
            candidate.id,
            request,
            self._platform_list(request.platform_scope_json)[0] if self._platform_list(request.platform_scope_json) else getattr(opportunity, "platform", "youtube"),
        )
        invalidations = self._build_invalidation_criteria(candidate.id, opportunity, request, blocked)
        actions = self._build_actions(candidate.id, opportunity, blocked)

        for item in evidence:
            self._upsert("recommendation_evidence", item.to_dict())
        for item in risks:
            self._upsert("recommendation_risks", item.to_dict())
        for item in constraints:
            self._upsert("recommendation_constraints", {**item.to_dict(), "recommendation_candidate_id": candidate.id})
        for item in alternatives:
            self._upsert("recommendation_alternatives", item.to_dict())
        for item in metrics:
            self._upsert("recommendation_metrics", {**item.to_dict(), "recommendation_candidate_id": candidate.id})
        for item in invalidations:
            self._upsert("recommendation_invalidation_criteria", item.to_dict())
        for item in actions:
            self._upsert("recommendation_actions", item.to_dict())

        contradiction_types = []
        if float(getattr(opportunity, "copying_risk", 0.0) or 0.0) >= 0.75:
            contradiction_types.append(("high_popularity_low_fit" if score["creator_fit"] < 0.5 else "high_momentum_high_copying_risk", "high"))
        if score["freshness_status"] in {"stale", "expired"}:
            contradiction_types.append(("stale_data_conflict", "warning"))
        for contradiction_type, severity in contradiction_types:
            self._upsert(
                "recommendation_contradictions",
                RecommendationContradiction(
                    id=str(uuid4()),
                    recommendation_candidate_id=candidate.id,
                    contradiction_type=contradiction_type,
                    severity=severity,
                    description="Contradiccion derivada de la evidencia agregada.",
                    created_at=utc_now().isoformat(),
                    source_id=getattr(opportunity, "id", None),
                    resolution_status="open",
                ).to_dict(),
            )
        self._upsert(
            "recommendation_snapshots",
            RecommendationSnapshot(
                id=str(uuid4()),
                creator_id=request.creator_id,
                recommendation_candidate_id=candidate.id,
                snapshot_type="generated",
                source_fingerprint=build_recommendation_fingerprint(
                    {
                        "candidate_id": candidate.id,
                        "run_id": run.id,
                        "objective": request.objective_type.value if request.objective_type else None,
                        "timestamp": utc_now().isoformat(),
                    }
                ),
                snapshot_json=_json_dumps(candidate.to_dict()),
                created_at=utc_now().isoformat(),
            ).to_dict(),
        )
        return candidate

    def generate_recommendations(
        self,
        *,
        request_id: str | None = None,
        creator_id: str | None = None,
        request_type: str | None = None,
        objective_type: str | None = None,
        platform_scope_json: str = "[]",
        content_type_scope_json: str = "[]",
        market_id: str | None = None,
        topic_id: str | None = None,
        time_horizon: str | None = None,
        constraints_json: str = "{}",
        preferences_json: str = "{}",
    ) -> RecommendationGenerationResult:
        if request_id is not None:
            request = self.get_request(request_id)
            if request is None:
                raise RecommendationNotFoundError("La solicitud no existe.")
        else:
            if creator_id is None or request_type is None:
                raise RecommendationValidationError("Se requiere creator_id y request_type si no existe request_id.")
            request = self.create_request(
                creator_id=creator_id,
                request_type=request_type,
                objective_type=objective_type,
                platform_scope_json=platform_scope_json,
                content_type_scope_json=content_type_scope_json,
                market_id=market_id,
                topic_id=topic_id,
                time_horizon=time_horizon,
                constraints_json=constraints_json,
                preferences_json=preferences_json,
            )
        snapshot, payload, warnings = self._collect_context_payload(request.creator_id, request.to_dict())
        self._upsert("recommendation_context_snapshots", snapshot.to_dict())

        opportunities: list[Any] = []
        if self.market_service is not None:
            try:
                opportunities = self.market_service.list_opportunity_candidates(request.creator_id, request.market_id)
            except Exception:
                opportunities = []

        if not opportunities:
            opportunities = [
                SimpleNamespace(
                    id=str(uuid4()),
                    creator_id=request.creator_id,
                    market_id=request.market_id,
                    topic_id=request.topic_id,
                    title="General strategy",
                    summary="Fallback candidate",
                    opportunity_type="topic",
                    lifecycle_stage=LifecycleStage.UNCLEAR.value,
                    urgency="medium",
                    freshness_status=FreshnessStatus.UNKNOWN.value,
                    saturation_level="unknown",
                    creator_fit=0.5,
                    audience_fit=0.5,
                    historical_fit=0.5,
                    differentiation_potential=0.5,
                    copying_risk=0.0,
                    evidence_quality=EvidenceQuality.UNKNOWN.value,
                    confidence_level=ConfidenceLevel.UNKNOWN.value,
                    status="requires_review",
                    created_at=utc_now().isoformat(),
                    updated_at=utc_now().isoformat(),
                    platform_scope_json=request.platform_scope_json,
                    content_type_scope_json=request.content_type_scope_json,
                    overall_fit=0.5,
                    platform_fit=0.5,
                )
            ]

        run = RecommendationRun(
            id=str(uuid4()),
            creator_id=request.creator_id,
            request_id=request.id,
            context_snapshot_id=snapshot.id,
            status=RecommendationRunStatus.ASSEMBLING_CONTEXT,
            configuration_json=_json_dumps({"engine_version": self.ENGINE_VERSION, "request": request.to_dict()}),
            candidate_count=0,
            generated_count=0,
            skipped_count=0,
            warning_count=len(warnings),
            error_count=0,
            started_at=utc_now().isoformat(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_runs", run.to_dict())
        platform_scope = self._platform_list(request.platform_scope_json)
        platform_available = self._platform_available(request.creator_id, platform_scope)
        measurement_available = self._measurement_available(platform_scope, request)
        recommendations: list[RecommendationCandidate] = []
        run_items: list[RecommendationRunItem] = []
        for opportunity in opportunities[: self._run_limit(request)]:
            candidate = self._create_recommendation_record(opportunity, request, run, snapshot.id, platform_available, measurement_available)
            recommendations.append(candidate)
            run_items.append(
                RecommendationRunItem(
                    id=str(uuid4()),
                    recommendation_run_id=run.id,
                    source_candidate_type="opportunity_candidate",
                    source_candidate_id=getattr(opportunity, "id", None),
                    action="generated",
                    status="completed" if candidate.priority_level != PriorityLevel.BLOCKED else "blocked",
                    warning_codes_json=_json_dumps(["copying_risk"] if candidate.priority_level == PriorityLevel.BLOCKED else []),
                    created_at=utc_now().isoformat(),
                    error_code=None,
                    error_message=None,
                )
            )

        for item in run_items:
            self._upsert("recommendation_run_items", item.to_dict())

        completed_status = RecommendationRunStatus.COMPLETED_WITH_WARNINGS if warnings or any(item.status == "blocked" for item in run_items) else RecommendationRunStatus.COMPLETED
        run = replace(run, status=completed_status, candidate_count=len(recommendations), generated_count=len(recommendations), skipped_count=0, warning_count=len(warnings) + sum(1 for item in run_items if item.status == "blocked"), completed_at=utc_now().isoformat())
        self._upsert("recommendation_runs", run.to_dict())
        for candidate in recommendations:
            self._upsert(
                "recommendation_reviews",
                RecommendationReview(
                    id=str(uuid4()),
                    creator_id=request.creator_id,
                    recommendation_candidate_id=candidate.id,
                    decision=ReviewDecision.NEEDS_MORE_DATA if candidate.priority_level == PriorityLevel.BLOCKED else ReviewDecision.DEFER,
                    previous_status="generated",
                    new_status=candidate.status.value,
                    reason="auto_generated_needs_human_review" if candidate.priority_level != PriorityLevel.BLOCKED else "blocked_by_risk",
                    reviewer=None,
                    reviewed_at=utc_now().isoformat(),
                    created_at=utc_now().isoformat(),
                ).to_dict(),
            )
        return RecommendationGenerationResult(
            run=run,
            request=request,
            context_snapshot=snapshot,
            recommendations=tuple(recommendations),
            warnings=tuple(warnings),
            errors=tuple(),
        )

    def _run_limit(self, request: RecommendationRequest) -> int:
        try:
            preferences = _safe_dict(_json_loads(request.preferences_json, {}))
            limit = int(preferences.get("max_recommendations_per_run", 5))
            return max(1, min(limit, 25))
        except Exception:
            return 5

    def list_runs(self, creator_id: str) -> list[RecommendationRun]:
        return self._list_entities(
            "recommendation_runs",
            RecommendationRun,
            where="creator_id = ?",
            params=(creator_id,),
            order_by="created_at DESC",
            enum_fields={"status": RecommendationRunStatus},
        )

    def get_run(self, run_id: str) -> RecommendationRun | None:
        return self._fetch_entity("recommendation_runs", RecommendationRun, where="id = ?", params=(run_id,), enum_fields={"status": RecommendationRunStatus})

    def list_run_items(self, run_id: str) -> list[RecommendationRunItem]:
        return self._list_entities("recommendation_run_items", RecommendationRunItem, where="recommendation_run_id = ?", params=(run_id,), order_by="created_at ASC")

    def cancel_run(self, run_id: str) -> RecommendationRun | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        if run.status in {RecommendationRunStatus.COMPLETED, RecommendationRunStatus.COMPLETED_WITH_WARNINGS, RecommendationRunStatus.FAILED}:
            return run
        updated = replace(run, status=RecommendationRunStatus.CANCELLED, completed_at=utc_now().isoformat(), error_code="cancelled", error_message="Run cancelled locally")
        self._upsert("recommendation_runs", updated.to_dict())
        return updated

    def resume_run(self, run_id: str) -> RecommendationRun | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        if run.status in {RecommendationRunStatus.COMPLETED, RecommendationRunStatus.COMPLETED_WITH_WARNINGS}:
            return run
        updated = replace(run, status=RecommendationRunStatus.QUEUED, error_code=None, error_message=None)
        self._upsert("recommendation_runs", updated.to_dict())
        return updated

    def list_recommendations(self, creator_id: str) -> list[RecommendationCandidate]:
        return self._list_entities(
            "recommendation_candidates",
            RecommendationCandidate,
            where="creator_id = ?",
            params=(creator_id,),
            order_by="created_at DESC",
            enum_fields={
                "recommendation_type": RecommendationType,
                "objective_type": ObjectiveType,
                "status": RecommendationLifecycleStatus,
                "priority_level": PriorityLevel,
                "confidence_level": ConfidenceLevel,
                "freshness_status": FreshnessStatus,
            },
        )

    def get_recommendation(self, recommendation_id: str) -> RecommendationCandidate | None:
        return self._fetch_entity(
            "recommendation_candidates",
            RecommendationCandidate,
            where="id = ?",
            params=(recommendation_id,),
            enum_fields={
                "recommendation_type": RecommendationType,
                "objective_type": ObjectiveType,
                "status": RecommendationLifecycleStatus,
                "priority_level": PriorityLevel,
                "confidence_level": ConfidenceLevel,
                "freshness_status": FreshnessStatus,
            },
        )

    def list_evidence(self, recommendation_id: str) -> list[RecommendationEvidence]:
        return self._list_entities(
            "recommendation_evidence",
            RecommendationEvidence,
            where="recommendation_candidate_id = ?",
            params=(recommendation_id,),
            order_by="created_at ASC",
            enum_fields={
                "evidence_type": EvidenceType,
                "evidence_strength": EvidenceStrength,
                "evidence_quality": EvidenceQuality,
                "fact_inference_hypothesis": FactInferenceHypothesis,
            },
        )

    def list_risks(self, recommendation_id: str) -> list[RecommendationRisk]:
        return self._list_entities(
            "recommendation_risks",
            RecommendationRisk,
            where="recommendation_candidate_id = ?",
            params=(recommendation_id,),
            order_by="created_at ASC",
            enum_fields={"risk_type": RiskType, "severity": RiskSeverity},
        )

    def list_contradictions(self, recommendation_id: str) -> list[RecommendationContradiction]:
        return self._list_entities("recommendation_contradictions", RecommendationContradiction, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at ASC")

    def list_constraints(self, recommendation_id: str) -> list[RecommendationConstraint]:
        return self._list_entities("recommendation_constraints", RecommendationConstraint, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at ASC", enum_fields={"constraint_type": ConstraintType})

    def list_actions(self, recommendation_id: str) -> list[RecommendationAction]:
        return self._list_entities("recommendation_actions", RecommendationAction, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="sequence_order ASC")

    def list_metrics(self, recommendation_id: str) -> list[RecommendationMetric]:
        return self._list_entities("recommendation_metrics", RecommendationMetric, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at ASC", enum_fields={"metric_role": MetricRole, "availability_status": MetricAvailabilityStatus})

    def list_invalidation_criteria(self, recommendation_id: str) -> list[RecommendationInvalidationCriterion]:
        return self._list_entities("recommendation_invalidation_criteria", RecommendationInvalidationCriterion, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at ASC")

    def list_alternatives(self, recommendation_id: str) -> list[RecommendationAlternative]:
        return self._list_entities("recommendation_alternatives", RecommendationAlternative, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at ASC", enum_fields={"alternative_type": AlternativeType, "confidence_level": ConfidenceLevel})

    def list_reviews(self, recommendation_id: str) -> list[RecommendationReview]:
        return self._list_entities("recommendation_reviews", RecommendationReview, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="reviewed_at DESC", enum_fields={"decision": ReviewDecision})

    def review_recommendation(self, recommendation_id: str, *, decision: str, reason: str, reviewer: str | None = None) -> RecommendationReview:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise RecommendationNotFoundError("La recomendacion no existe.")
        review = RecommendationReview(
            id=str(uuid4()),
            creator_id=recommendation.creator_id,
            recommendation_candidate_id=recommendation.id,
            decision=_normalize_enum(decision, ReviewDecision, ReviewDecision.DEFER),
            previous_status=recommendation.status.value,
            new_status=_recommendation_status_from_decision(decision, recommendation.status),
            reason=reason,
            reviewer=reviewer,
            reviewed_at=utc_now().isoformat(),
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_reviews", review.to_dict())
        updated_status = _recommendation_status_from_decision(decision, recommendation.status)
        updated = replace(recommendation, status=_normalize_enum(updated_status, RecommendationLifecycleStatus, recommendation.status), updated_at=utc_now().isoformat())
        self._upsert("recommendation_candidates", updated.to_dict())
        return review

    def add_feedback(self, recommendation_id: str, *, feedback_type: str, rating: int | None = None, feedback_text: str | None = None, reason_code: str | None = None) -> RecommendationFeedback:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise RecommendationNotFoundError("La recomendacion no existe.")
        feedback = RecommendationFeedback(
            id=str(uuid4()),
            creator_id=recommendation.creator_id,
            recommendation_candidate_id=recommendation.id,
            feedback_type=_normalize_enum(feedback_type, FeedbackType, FeedbackType.NOT_USEFUL),
            rating=rating,
            feedback_text=feedback_text,
            reason_code=reason_code,
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_feedback", feedback.to_dict())
        return feedback

    def list_feedback(self, recommendation_id: str) -> list[RecommendationFeedback]:
        return self._list_entities("recommendation_feedback", RecommendationFeedback, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at DESC", enum_fields={"feedback_type": FeedbackType})

    def list_experiment_links(self, recommendation_id: str) -> list[RecommendationExperimentLink]:
        return self._list_entities("recommendation_experiment_links", RecommendationExperimentLink, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at DESC")

    def convert_to_experiment(self, recommendation_id: str) -> RecommendationExperimentLink:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise RecommendationNotFoundError("La recomendacion no existe.")
        if self.experiment_service is None:
            raise RecommendationValidationError("El servicio de experiments no esta disponible.")
        experiment = self.experiment_service.create_experiment(
            creator_id=recommendation.creator_id,
            name=recommendation.title,
            description=recommendation.summary,
            experiment_type="single_variable_test",
            hypothesis=recommendation.summary,
            rationale="Recommendation converted to experiment.",
            primary_metric_key=self._objective_metric(recommendation.objective_type),
            expected_direction="up",
            minimum_sample_size=1,
            platform=(self._platform_list(recommendation.platform_scope_json)[0] if self._platform_list(recommendation.platform_scope_json) else None),
            content_type=(self._content_type_list(recommendation.content_type_scope_json)[0] if self._content_type_list(recommendation.content_type_scope_json) else None),
        )
        link = RecommendationExperimentLink(
            id=str(uuid4()),
            creator_id=recommendation.creator_id,
            recommendation_candidate_id=recommendation.id,
            experiment_id=experiment.id,
            link_type="converted_to_experiment",
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_experiment_links", link.to_dict())
        return link

    def mark_executed(self, recommendation_id: str, content_id: str) -> RecommendationExecutionRecord:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise RecommendationNotFoundError("La recomendacion no existe.")
        record = RecommendationExecutionRecord(
            id=str(uuid4()),
            creator_id=recommendation.creator_id,
            recommendation_candidate_id=recommendation.id,
            internal_content_id=content_id,
            execution_status="executed",
            platform=self._platform_list(recommendation.platform_scope_json)[0] if self._platform_list(recommendation.platform_scope_json) else None,
            created_at=utc_now().isoformat(),
            updated_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_execution_records", record.to_dict())
        updated = replace(recommendation, status=RecommendationLifecycleStatus.EXECUTED, updated_at=utc_now().isoformat())
        self._upsert("recommendation_candidates", updated.to_dict())
        return record

    def add_outcome(self, recommendation_id: str, file_path: str) -> RecommendationOutcomeSnapshot:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise RecommendationNotFoundError("La recomendacion no existe.")
        path = Path(file_path)
        metrics = {}
        interpretation = {"file": str(path)}
        if path.exists():
            try:
                metrics = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(metrics, dict):
                    metrics = {"raw": metrics}
            except Exception:
                metrics = {"raw_text": path.read_text(encoding="utf-8", errors="replace")}
        snapshot = RecommendationOutcomeSnapshot(
            id=str(uuid4()),
            creator_id=recommendation.creator_id,
            recommendation_candidate_id=recommendation.id,
            experiment_id=self._first_or_none([link.experiment_id for link in self.list_experiment_links(recommendation_id)]),
            period_start=None,
            period_end=None,
            metrics_json=_json_dumps(metrics),
            interpretation_json=_json_dumps(interpretation),
            source_fingerprint=build_recommendation_fingerprint({"recommendation_id": recommendation_id, "file": str(path), "content": metrics}),
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_outcome_snapshots", snapshot.to_dict())
        return snapshot

    def list_snapshots(self, recommendation_id: str) -> list[RecommendationSnapshot]:
        return self._list_entities("recommendation_snapshots", RecommendationSnapshot, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at DESC")

    def list_context_snapshots(self, creator_id: str) -> list[RecommendationContextSnapshot]:
        return self._list_entities("recommendation_context_snapshots", RecommendationContextSnapshot, where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def list_outcomes(self, recommendation_id: str) -> list[RecommendationOutcomeSnapshot]:
        return self._list_entities("recommendation_outcome_snapshots", RecommendationOutcomeSnapshot, where="recommendation_candidate_id = ?", params=(recommendation_id,), order_by="created_at DESC")

    def list_reports(self, creator_id: str) -> list[RecommendationReport]:
        return self._list_entities("recommendation_reports", RecommendationReport, where="creator_id = ?", params=(creator_id,), order_by="created_at DESC")

    def get_report(self, report_id: str) -> RecommendationReport | None:
        return self._fetch_entity("recommendation_reports", RecommendationReport, where="id = ?", params=(report_id,))

    def build_overview(self, creator_id: str) -> dict[str, object]:
        recommendations = self.list_recommendations(creator_id)
        blocked = [
            item
            for item in recommendations
            if item.status == RecommendationLifecycleStatus.BLOCKED or item.priority_level == PriorityLevel.BLOCKED
        ]
        return {
            "creator_id": creator_id,
            "recommendations": len(recommendations),
            "needs_review": sum(1 for item in recommendations if item.status == RecommendationLifecycleStatus.NEEDS_REVIEW),
            "blocked": len(blocked),
            "approved": sum(1 for item in recommendations if item.status == RecommendationLifecycleStatus.APPROVED),
            "expiring": sum(1 for item in recommendations if item.expires_at is not None),
            "stale": sum(1 for item in recommendations if item.freshness_status in {FreshnessStatus.STALE, FreshnessStatus.EXPIRED}),
            "high_risk": sum(1 for item in recommendations if item.copying_risk >= 0.75 or item.overall_risk >= 0.75),
        }

    def build_background_tasks(self, creator_id: str) -> list[dict[str, object]]:
        tasks: list[dict[str, object]] = []
        for run in self.list_runs(creator_id):
            tasks.append(
                {
                    "task_id": run.id,
                    "title": "Recommendation generation",
                    "status": run.status.value,
                    "stage_name": run.status.value,
                    "video_id": None,
                    "video_title": run.request_id or run.context_snapshot_id,
                    "action_id": run.request_id,
                    "progress_percent": 100.0 if run.status in {RecommendationRunStatus.COMPLETED, RecommendationRunStatus.COMPLETED_WITH_WARNINGS} else 0.0,
                    "message": run.error_message or run.status.value,
                    "error": run.error_message,
                    "cancellable": run.status in {RecommendationRunStatus.QUEUED, RecommendationRunStatus.ASSEMBLING_CONTEXT, RecommendationRunStatus.VALIDATING_CONTEXT, RecommendationRunStatus.GATHERING_CANDIDATES, RecommendationRunStatus.AGGREGATING_EVIDENCE, RecommendationRunStatus.EVALUATING_CONSTRAINTS, RecommendationRunStatus.DETECTING_CONTRADICTIONS, RecommendationRunStatus.CALCULATING_FIT, RecommendationRunStatus.CALCULATING_RISK, RecommendationRunStatus.RANKING, RecommendationRunStatus.BUILDING_EXPLANATIONS, RecommendationRunStatus.SELECTING_METRICS, RecommendationRunStatus.BUILDING_ALTERNATIVES, RecommendationRunStatus.SAVING},
                    "created_at": run.created_at,
                    "updated_at": run.completed_at or run.created_at,
                    "interrupted_at": run.completed_at if run.status == RecommendationRunStatus.INTERRUPTED else None,
                    "completed_at": run.completed_at,
                    "payload": {"kind": "recommendation_run", "run": run.to_dict(), "creator_id": creator_id},
                }
            )
        return tasks

    def privacy_summary(self, creator_id: str) -> dict[str, object]:
        return {
            "creator_id": creator_id,
            "read_only": True,
            "no_publication": True,
            "no_scraping": True,
            "no_llm": True,
            "no_ml": True,
            "tokens_in_sqlite": False,
            "evidence_historical": True,
        }

    def export_report(self, report_id: str, format_name: str, *, destination: Path | None = None) -> Path:
        report = self.get_report(report_id)
        if report is None:
            raise RecommendationNotFoundError("El reporte no existe.")
        destination = destination or (self._reports_root / f"{report.id}.{format_name}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if format_name == "json":
            destination.write_text(report.report_json, encoding="utf-8")
        elif format_name == "txt":
            payload = json.loads(report.report_json)
            destination.write_text(self._txt_report(payload), encoding="utf-8")
        elif format_name == "csv":
            payload = json.loads(report.report_json)
            self._write_csv_report(destination, payload)
        else:
            raise RecommendationValidationError("Formato de exportacion no soportado.")
        return destination

    def _write_csv_report(self, destination: Path, payload: dict[str, object]) -> None:
        rows = _safe_list(payload.get("recommendations", []))
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "title", "priority_level", "objective", "status"])
            for item in rows:
                if not isinstance(item, dict):
                    continue
                writer.writerow([
                    _safe_csv_value(item.get("id")),
                    _safe_csv_value(item.get("title")),
                    _safe_csv_value(item.get("priority_level")),
                    _safe_csv_value(item.get("objective_type")),
                    _safe_csv_value(item.get("status")),
                ])

    def _txt_report(self, payload: dict[str, object]) -> str:
        lines = [
            f"Report type: {payload.get('report_type', '')}",
            f"Creator: {payload.get('creator_id', '')}",
            f"Period: {payload.get('period_start', '')} -> {payload.get('period_end', '')}",
            f"Confidence: {payload.get('summary', {}).get('confidence', '') if isinstance(payload.get('summary'), dict) else ''}",
        ]
        for item in _safe_list(payload.get("recommendations", [])):
            if isinstance(item, dict):
                lines.append(f"- {item.get('title')} [{item.get('priority_level')}] {item.get('summary')}")
        return "\n".join(lines)

    def build_report(self, creator_id: str, report_type: str) -> RecommendationReport:
        recommendations = self.list_recommendations(creator_id)
        blocked = [item for item in recommendations if item.priority_level == PriorityLevel.BLOCKED]
        payload = {
            "report_type": report_type,
            "creator_id": creator_id,
            "generated_at": utc_now().isoformat(),
            "summary": {
                "recommendations": len(recommendations),
                "blocked": len(blocked),
                "needs_review": sum(1 for item in recommendations if item.status == RecommendationLifecycleStatus.NEEDS_REVIEW),
                "confidence": "medium" if recommendations else "unknown",
            },
            "recommendations": [item.to_dict() for item in recommendations],
            "privacy": self.privacy_summary(creator_id),
        }
        report = RecommendationReport(
            id=str(uuid4()),
            creator_id=creator_id,
            report_type=report_type,
            recommendation_scope_json=_json_dumps({"creator_id": creator_id, "report_type": report_type}),
            source_fingerprint=build_recommendation_fingerprint(payload),
            report_json=_json_dumps(payload),
            created_at=utc_now().isoformat(),
        )
        self._upsert("recommendation_reports", report.to_dict())
        return report


def _recommendation_status_from_decision(decision: str, current_status: RecommendationLifecycleStatus) -> str:
    mapping = {
        "approve": RecommendationLifecycleStatus.APPROVED.value,
        "reject": RecommendationLifecycleStatus.REJECTED.value,
        "defer": RecommendationLifecycleStatus.DEFERRED.value,
        "needs_more_data": RecommendationLifecycleStatus.NEEDS_MORE_DATA.value,
        "request_alternative": RecommendationLifecycleStatus.NEEDS_REVIEW.value,
        "reduce_scope": RecommendationLifecycleStatus.NEEDS_REVIEW.value,
        "change_platform": RecommendationLifecycleStatus.NEEDS_REVIEW.value,
        "change_objective": RecommendationLifecycleStatus.NEEDS_REVIEW.value,
        "edit_constraints": RecommendationLifecycleStatus.NEEDS_REVIEW.value,
        "convert_to_experiment": RecommendationLifecycleStatus.PLANNED.value,
        "mark_executed": RecommendationLifecycleStatus.EXECUTED.value,
        "mark_inconclusive": RecommendationLifecycleStatus.INCONCLUSIVE.value,
        "archive": RecommendationLifecycleStatus.ARCHIVED.value,
    }
    return mapping.get(decision, current_status.value)


def build_recommendation_engine_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    database: SQLiteDatabase,
    repository: RecommendationRepository,
    catalog_service: CatalogService | None = None,
    analytics_service: AnalyticsQueryService | None = None,
    analytics_lab_service: AnalyticsLabService | None = None,
    creator_memory_service: CreatorMemoryService | None = None,
    creator_language_service: CreatorLanguageService | None = None,
    audience_service: AudienceModelService | None = None,
    market_service: MarketIntelligenceService | None = None,
    platform_service: PlatformIntegrationService | None = None,
    creative_packaging_service: CreativePackagingService | None = None,
    experiment_service: ExperimentService | None = None,
    logger: logging.Logger | None = None,
) -> RecommendationEngineService:
    return RecommendationEngineService(
        settings=settings,
        paths=paths,
        database=database,
        repository=repository,
        catalog_service=catalog_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        market_service=market_service,
        platform_service=platform_service,
        creative_packaging_service=creative_packaging_service,
        experiment_service=experiment_service,
        logger=logger,
    )
