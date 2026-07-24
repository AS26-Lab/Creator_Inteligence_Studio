"""Servicio central para Analytics Lab."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.application.services.analytics_import_service import AnalyticsQueryService
from creator_intelligence_studio.domain.analytics.entities import AnalyticsMetricSnapshot, AnalyticsPublication
from creator_intelligence_studio.domain.analytics_lab.cohort_definitions import SYSTEM_COHORT_PRESETS
from creator_intelligence_studio.domain.analytics_lab.entities import (
    AnalyticsAnalysisRun,
    AnalyticsCohortDefinition,
    AnalyticsComparisonResult,
    AnalyticsFinding,
    AnalyticsReportItem,
    AnalyticsReportRun,
)
from creator_intelligence_studio.domain.analytics_lab.errors import AnalyticsLabNotFoundError, AnalyticsLabStateError, AnalyticsLabValidationError
from creator_intelligence_studio.domain.analytics_lab.repositories import AnalyticsLabRepository
from creator_intelligence_studio.domain.analytics_lab.services import (
    build_analytics_lab_fingerprint,
    comparison_status_from_sample,
    confidence_from_sample,
    system_cohort_payloads,
)
from creator_intelligence_studio.domain.analytics_lab.value_objects import (
    AnalyticsAnalysisRunStatus,
    AnalyticsConfidenceLevel,
    AnalyticsComparisonStatus,
    AnalyticsFindingStatus,
    AnalyticsFindingType,
    AnalyticsLabRunType,
    AnalyticsReportStatus,
)
from creator_intelligence_studio.infrastructure.analytics_lab.anomaly_detector import detect_anomalies
from creator_intelligence_studio.infrastructure.analytics_lab.cohort_builder import CohortSelectionResult, select_publications
from creator_intelligence_studio.infrastructure.analytics_lab.finding_generator import generate_findings_from_anomalies
from creator_intelligence_studio.infrastructure.analytics_lab.metric_aggregator import (
    derived_completion_gap,
    derived_metric_payloads,
    summarize_metric,
)
from creator_intelligence_studio.infrastructure.analytics_lab.percentile_calculator import calculate_percentile, robust_z_score
from creator_intelligence_studio.infrastructure.analytics_lab.report_builder import build_report_payload, write_report
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(payload: str | None) -> dict[str, object]:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _publication_latest_metrics(service: AnalyticsQueryService, publication: AnalyticsPublication) -> dict[str, AnalyticsMetricSnapshot]:
    return service.get_latest_metrics(publication.id)


def _snapshot_numeric_map(snapshots: dict[str, AnalyticsMetricSnapshot]) -> dict[str, float | None]:
    metrics: dict[str, float | None] = {}
    for metric_key, snapshot in snapshots.items():
        metrics[metric_key] = snapshot.numeric_value
    return metrics


def _publication_topic_format_language(service: AnalyticsQueryService, publication: AnalyticsPublication) -> dict[str, str | None]:
    metrics = service.get_latest_metrics(publication.id)
    return {
        "topic": metrics.get("topic").text_value if metrics.get("topic") else None,
        "format": metrics.get("format").text_value if metrics.get("format") else None,
        "language": metrics.get("language").text_value if metrics.get("language") else None,
    }


def _count_value_positions(values: list[float], observed: float | None) -> float | None:
    if observed is None or not values:
        return None
    ordered = sorted(float(value) for value in values)
    less = sum(1 for value in ordered if value < observed)
    equal = sum(1 for value in ordered if value == observed)
    return 100.0 * ((less + 0.5 * equal) / len(ordered))


class AnalyticsLabService:
    def __init__(
        self,
        *,
        analytics_service: AnalyticsQueryService,
        repository: AnalyticsLabRepository,
        paths: ProjectPaths,
        logger: logging.Logger | None = None,
    ) -> None:
        self.analytics_service = analytics_service
        self.repository = repository
        self.paths = paths
        self.logger = logger or logging.getLogger("creator_intelligence_studio.analytics_lab")
        self._reports_root = self.paths.data_directory / "analytics_lab" / "reports"

    def _ensure_system_cohorts(self, creator_id: str) -> None:
        existing = self.repository.list_cohorts(creator_id)
        existing_names = {cohort.name for cohort in existing}
        if existing_names:
            return
        publications = self.analytics_service.list_publications(creator_id)
        if not publications:
            for preset in system_cohort_payloads():
                self.repository.upsert_cohort(
                    AnalyticsCohortDefinition(
                        id=str(uuid4()),
                        creator_id=creator_id,
                        name=str(preset["name"]),
                        description=str(preset["description"]),
                        platform=None,
                        content_type=None,
                        date_from=None,
                        date_to=None,
                        duration_min_seconds=None,
                        duration_max_seconds=None,
                        topic=None,
                        format=None,
                        language=None,
                        filters_json=_json_dumps(preset.get("filters", {})),
                        is_system=True,
                        is_active=True,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
            return
        platform_counts: dict[str, int] = {}
        content_counts: dict[str, int] = {}
        format_counts: dict[str, int] = {}
        topic_counts: dict[str, int] = {}
        durations: list[float] = []
        dates = [publication.published_at for publication in publications]
        latest_metrics_cache = {publication.id: self.analytics_service.get_latest_metrics(publication.id) for publication in publications}
        for publication in publications:
            platform_counts[publication.platform] = platform_counts.get(publication.platform, 0) + 1
            content_counts[publication.content_type.value] = content_counts.get(publication.content_type.value, 0) + 1
            if publication.duration_seconds is not None:
                durations.append(float(publication.duration_seconds))
            topic = latest_metrics_cache[publication.id].get("topic")
            if topic and topic.text_value:
                topic_counts[topic.text_value] = topic_counts.get(topic.text_value, 0) + 1
            fmt = latest_metrics_cache[publication.id].get("format")
            if fmt and fmt.text_value:
                format_counts[fmt.text_value] = format_counts.get(fmt.text_value, 0) + 1
        dominant_platform = max(platform_counts, key=platform_counts.get)
        dominant_content_type = max(content_counts, key=content_counts.get)
        dominant_format = max(format_counts, key=format_counts.get) if format_counts else None
        dominant_topic = max(topic_counts, key=topic_counts.get) if topic_counts else None
        q1 = calculate_percentile(durations, 25.0) if durations else None
        q3 = calculate_percentile(durations, 75.0) if durations else None
        recent_start = (max(dates) - timedelta(days=90)).date().isoformat() if dates else None
        seed_payloads = [
            {
                "name": "same_platform_same_content_type",
                "description": "Publicaciones de la misma plataforma y tipo de contenido.",
                "platform": dominant_platform,
                "content_type": dominant_content_type,
                "date_from": None,
                "date_to": None,
                "duration_min_seconds": None,
                "duration_max_seconds": None,
                "topic": None,
                "format": None,
                "language": None,
                "filters_json": {"platform": dominant_platform, "content_type": dominant_content_type},
            },
            {
                "name": "same_platform_duration_band",
                "description": "Publicaciones de la misma plataforma dentro de un rango de duracion comparable.",
                "platform": dominant_platform,
                "content_type": None,
                "date_from": None,
                "date_to": None,
                "duration_min_seconds": q1,
                "duration_max_seconds": q3,
                "topic": None,
                "format": None,
                "language": None,
                "filters_json": {"platform": dominant_platform, "duration_min_seconds": q1, "duration_max_seconds": q3},
            },
            {
                "name": "same_platform_topic",
                "description": "Publicaciones de la misma plataforma y tema.",
                "platform": dominant_platform,
                "content_type": None,
                "date_from": None,
                "date_to": None,
                "duration_min_seconds": None,
                "duration_max_seconds": None,
                "topic": dominant_topic,
                "format": None,
                "language": None,
                "filters_json": {"platform": dominant_platform, "topic": dominant_topic},
            },
            {
                "name": "same_platform_recent_period",
                "description": "Publicaciones de la misma plataforma en un periodo reciente.",
                "platform": dominant_platform,
                "content_type": None,
                "date_from": recent_start,
                "date_to": None,
                "duration_min_seconds": None,
                "duration_max_seconds": None,
                "topic": None,
                "format": None,
                "language": None,
                "filters_json": {"platform": dominant_platform, "date_from": recent_start},
            },
            {
                "name": "creator_all_same_format",
                "description": "Publicaciones del creador con el mismo formato.",
                "platform": None,
                "content_type": None,
                "date_from": None,
                "date_to": None,
                "duration_min_seconds": None,
                "duration_max_seconds": None,
                "topic": None,
                "format": dominant_format,
                "language": None,
                "filters_json": {"format": dominant_format},
            },
        ]
        for payload in seed_payloads:
            self.repository.upsert_cohort(
                AnalyticsCohortDefinition(
                    id=str(uuid4()),
                    creator_id=creator_id,
                    name=payload["name"],
                    description=payload["description"],
                    platform=payload["platform"],
                    content_type=payload["content_type"],
                    date_from=payload["date_from"],
                    date_to=payload["date_to"],
                    duration_min_seconds=payload["duration_min_seconds"],
                    duration_max_seconds=payload["duration_max_seconds"],
                    topic=payload["topic"],
                    format=payload["format"],
                    language=payload["language"],
                    filters_json=_json_dumps(payload["filters_json"]),
                    is_system=True,
                    is_active=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )

    def list_cohorts(self, creator_id: str) -> list[AnalyticsCohortDefinition]:
        self._ensure_system_cohorts(creator_id)
        return self.repository.list_cohorts(creator_id)

    def create_cohort(
        self,
        *,
        creator_id: str,
        name: str,
        description: str,
        platform: str | None = None,
        content_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        duration_min_seconds: float | None = None,
        duration_max_seconds: float | None = None,
        topic: str | None = None,
        format: str | None = None,
        language: str | None = None,
        channel_id: str | None = None,
        linked: bool | None = None,
        filters: dict[str, object] | None = None,
        is_system: bool = False,
        is_active: bool = True,
    ) -> AnalyticsCohortDefinition:
        payload = filters.copy() if filters else {}
        for key, value in {
            "platform": platform,
            "content_type": content_type,
            "date_from": date_from,
            "date_to": date_to,
            "duration_min_seconds": duration_min_seconds,
            "duration_max_seconds": duration_max_seconds,
            "topic": topic,
            "format": format,
            "language": language,
            "channel_id": channel_id,
            "linked": linked,
        }.items():
            if value is not None:
                payload[key] = value
        cohort = AnalyticsCohortDefinition(
            id=str(uuid4()),
            creator_id=creator_id,
            name=name,
            description=description,
            platform=platform,
            content_type=content_type,
            date_from=date_from,
            date_to=date_to,
            duration_min_seconds=duration_min_seconds,
            duration_max_seconds=duration_max_seconds,
            topic=topic,
            format=format,
            language=language,
            filters_json=_json_dumps(payload),
            is_system=is_system,
            is_active=is_active,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_cohort(cohort)

    def update_cohort(self, cohort_id: str, **changes) -> AnalyticsCohortDefinition:
        cohort = self.repository.get_cohort_by_id(cohort_id)
        if cohort is None:
            raise AnalyticsLabNotFoundError("La cohorte no existe.")
        payload = _json_loads(cohort.filters_json)
        for key, value in changes.items():
            if hasattr(cohort, key):
                payload[key] = value
        updated = replace(
            cohort,
            name=changes.get("name", cohort.name),
            description=changes.get("description", cohort.description),
            platform=changes.get("platform", cohort.platform),
            content_type=changes.get("content_type", cohort.content_type),
            date_from=changes.get("date_from", cohort.date_from),
            date_to=changes.get("date_to", cohort.date_to),
            duration_min_seconds=changes.get("duration_min_seconds", cohort.duration_min_seconds),
            duration_max_seconds=changes.get("duration_max_seconds", cohort.duration_max_seconds),
            topic=changes.get("topic", cohort.topic),
            format=changes.get("format", cohort.format),
            language=changes.get("language", cohort.language),
            filters_json=_json_dumps(payload),
            is_active=changes.get("is_active", cohort.is_active),
            updated_at=utc_now(),
        )
        return self.repository.upsert_cohort(updated)

    def archive_cohort(self, cohort_id: str) -> AnalyticsCohortDefinition:
        cohort = self.repository.get_cohort_by_id(cohort_id)
        if cohort is None:
            raise AnalyticsLabNotFoundError("La cohorte no existe.")
        return self.repository.upsert_cohort(replace(cohort, is_active=False, updated_at=utc_now()))

    def get_cohort(self, cohort_id: str) -> AnalyticsCohortDefinition | None:
        return self.repository.get_cohort_by_id(cohort_id)

    def _cohort_publications(self, cohort: AnalyticsCohortDefinition) -> tuple[list[AnalyticsPublication], CohortSelectionResult, dict[str, dict[str, AnalyticsMetricSnapshot]]]:
        publications = self.analytics_service.list_publications(cohort.creator_id)
        latest_metrics_by_publication = {
            publication.id: self.analytics_service.get_latest_metrics(publication.id)
            for publication in publications
        }
        filters = _json_loads(cohort.filters_json)
        filters.update(
            {
                "platform": cohort.platform,
                "content_type": cohort.content_type,
                "date_from": cohort.date_from,
                "date_to": cohort.date_to,
                "duration_min_seconds": cohort.duration_min_seconds,
                "duration_max_seconds": cohort.duration_max_seconds,
                "topic": cohort.topic,
                "format": cohort.format,
                "language": cohort.language,
            }
        )
        selection = select_publications(publications, latest_metrics_by_publication, filters)
        selected_publications = [publication for publication in publications if publication.id in selection.publication_ids]
        return selected_publications, selection, latest_metrics_by_publication

    def _analysis_fingerprint(
        self,
        *,
        creator_id: str,
        run_type: AnalyticsLabRunType,
        cohort: AnalyticsCohortDefinition | None,
        publication_ids: list[str],
        publication_fingerprints: list[str],
        configuration: dict[str, object],
    ) -> str:
        payload = {
            "creator_id": creator_id,
            "run_type": run_type.value,
            "cohort_id": cohort.id if cohort else None,
            "publication_ids": publication_ids,
            "publication_fingerprints": publication_fingerprints,
            "configuration": configuration,
            "analyzer_version": "v1",
        }
        return build_analytics_lab_fingerprint(payload)

    def _build_comparison_results(
        self,
        *,
        run_id: str,
        cohort: AnalyticsCohortDefinition,
        publications: list[AnalyticsPublication],
        latest_metrics_by_publication: dict[str, dict[str, AnalyticsMetricSnapshot]],
    ) -> list[AnalyticsComparisonResult]:
        comparison_results: list[AnalyticsComparisonResult] = []
        metric_keys = sorted(
            {
                metric_key
                for publication in publications
                for metric_key, snapshot in latest_metrics_by_publication.get(publication.id, {}).items()
                if snapshot.numeric_value is not None
            }
        )
        for metric_key in metric_keys:
            peer_values = [
                float(latest_metrics_by_publication[publication.id][metric_key].numeric_value)
                for publication in publications
                if metric_key in latest_metrics_by_publication.get(publication.id, {})
                and latest_metrics_by_publication[publication.id][metric_key].numeric_value is not None
            ]
            for publication in publications:
                snapshot = latest_metrics_by_publication.get(publication.id, {}).get(metric_key)
                if snapshot is None or snapshot.numeric_value is None:
                    comparison_results.append(
                        AnalyticsComparisonResult(
                            id=str(uuid4()),
                            analysis_run_id=run_id,
                            publication_id=publication.id,
                            cohort_id=cohort.id,
                            metric_key=metric_key,
                            observed_value=None,
                            cohort_count=len(peer_values),
                            cohort_min=min(peer_values) if peer_values else None,
                            cohort_max=max(peer_values) if peer_values else None,
                            cohort_mean=None,
                            cohort_median=None,
                            percentile=None,
                            lower_quartile=None,
                            upper_quartile=None,
                            robust_z_score=None,
                            comparison_status=AnalyticsComparisonStatus.NO_DATA,
                            warning_codes_json=_json_dumps(["missing_expected_metric"]),
                            created_at=utc_now(),
                        )
                    )
                    continue
                values = [value for value in peer_values if value is not None]
                if publication.id in latest_metrics_by_publication and metric_key in latest_metrics_by_publication[publication.id]:
                    values = [
                        float(other_snapshot.numeric_value)
                        for other_publication, other_snapshot_map in (
                            (pub, latest_metrics_by_publication.get(pub.id, {})) for pub in publications if pub.id != publication.id
                        )
                        for other_snapshot_key, other_snapshot in other_snapshot_map.items()
                        if other_snapshot_key == metric_key and other_snapshot.numeric_value is not None
                    ]
                percentile = _count_value_positions(values, float(snapshot.numeric_value)) if values else None
                summary = summarize_metric(metric_key, values)
                comparison_status = comparison_status_from_sample(len(values), comparable=cohort.platform is not None and cohort.content_type is not None, outlier_dominated=bool(snapshot.numeric_value is not None and values and abs(robust_z_score(float(snapshot.numeric_value), values) or 0.0) > 3.0))
                warnings = []
                if len(values) < 4:
                    warnings.append("insufficient_sample")
                if comparison_status == AnalyticsComparisonStatus.OUTLIER_DOMINATED:
                    warnings.append("outlier_dominated")
                comparison_results.append(
                    AnalyticsComparisonResult(
                        id=str(uuid4()),
                        analysis_run_id=run_id,
                        publication_id=publication.id,
                        cohort_id=cohort.id,
                        metric_key=metric_key,
                        observed_value=float(snapshot.numeric_value),
                        cohort_count=len(values),
                        cohort_min=summary.minimum,
                        cohort_max=summary.maximum,
                        cohort_mean=summary.mean,
                        cohort_median=summary.median,
                        percentile=percentile,
                        lower_quartile=summary.lower_quartile,
                        upper_quartile=summary.upper_quartile,
                        robust_z_score=robust_z_score(float(snapshot.numeric_value), values),
                        comparison_status=comparison_status,
                        warning_codes_json=_json_dumps(warnings),
                        created_at=utc_now(),
                    )
                )
        return comparison_results

    def _build_findings(
        self,
        *,
        run_id: str,
        creator_id: str,
        cohort: AnalyticsCohortDefinition,
        publications: list[AnalyticsPublication],
        latest_metrics_by_publication: dict[str, dict[str, AnalyticsMetricSnapshot]],
        comparison_results: list[AnalyticsComparisonResult],
        selection: CohortSelectionResult,
    ) -> list[AnalyticsFinding]:
        findings: list[AnalyticsFinding] = []
        summary_metrics = {}
        all_anomalies = []
        for metric_key in ("views", "share_rate", "completion_rate", "subscriber_conversion_rate", "follower_conversion_rate"):
            values = []
            for publication in publications:
                snapshots = latest_metrics_by_publication.get(publication.id, {})
                if metric_key in snapshots and snapshots[metric_key].numeric_value is not None:
                    values.append(float(snapshots[metric_key].numeric_value))
                else:
                    derived, _ = derived_metric_payloads(
                        _snapshot_numeric_map(snapshots),
                        published_at=publication.published_at,
                    ).get(metric_key, (None, ()))
                    if derived is not None:
                        values.append(float(derived))
            if values:
                summary_metrics[metric_key] = summarize_metric(metric_key, values)
        for metric_key, summary in summary_metrics.items():
            findings.append(
                AnalyticsFinding(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    creator_id=creator_id,
                    publication_id=None,
                    cohort_id=cohort.id,
                    finding_type=AnalyticsFindingType.FACT,
                    category="cohort_summary",
                    title=f"Mediana de {metric_key}",
                    summary=f"La mediana de {metric_key} en la cohorte fue {summary.median}.",
                    evidence_json=_json_dumps(summary.to_dict()),
                    confidence_level=AnalyticsConfidenceLevel.MEDIUM if summary.count >= 4 else AnalyticsConfidenceLevel.LOW,
                    confidence_score=0.55 if summary.count >= 4 else 0.35,
                    sample_size=summary.count,
                    contradiction_count=0,
                    status=AnalyticsFindingStatus.DRAFT,
                    is_confirmed=False,
                    confirmed_at=None,
                    rejected_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        by_publication: dict[str, list[AnalyticsComparisonResult]] = {}
        for item in comparison_results:
            if item.publication_id is None:
                continue
            by_publication.setdefault(item.publication_id, []).append(item)
        for publication in publications:
            pub_results = by_publication.get(publication.id, [])
            top_result = next(
                (item for item in sorted(pub_results, key=lambda item: abs((item.percentile or 0.0) - 50.0), reverse=True) if item.percentile is not None),
                None,
            )
            if top_result and (top_result.percentile is not None and (top_result.percentile >= 80.0 or top_result.percentile <= 20.0)):
                label = "alto" if top_result.percentile >= 80.0 else "bajo"
                findings.append(
                    AnalyticsFinding(
                        id=str(uuid4()),
                        analysis_run_id=run_id,
                        creator_id=creator_id,
                        publication_id=publication.id,
                        cohort_id=cohort.id,
                        finding_type=AnalyticsFindingType.COMPARISON,
                        category="publication_comparison",
                        title=f"{top_result.metric_key} {label} en su cohorte",
                        summary=f"La publicacion quedo en el percentil {top_result.percentile:.0f} para {top_result.metric_key}.",
                        evidence_json=_json_dumps(top_result.to_dict()),
                        confidence_level=confidence_from_sample(top_result.cohort_count),
                        confidence_score=0.75 if top_result.cohort_count >= 4 else 0.45,
                        sample_size=top_result.cohort_count,
                        contradiction_count=0,
                        status=AnalyticsFindingStatus.DRAFT,
                        is_confirmed=False,
                        confirmed_at=None,
                        rejected_at=None,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
        for publication in publications:
            snapshots = latest_metrics_by_publication.get(publication.id, {})
            numeric_map = _snapshot_numeric_map(snapshots)
            derived_map = derived_metric_payloads(numeric_map, published_at=publication.published_at)
            merged_metrics = {**numeric_map}
            for key, (value, warnings) in derived_map.items():
                if value is not None:
                    merged_metrics[key] = value
            publication_anomalies = detect_anomalies(
                publication_id=publication.id,
                metrics=merged_metrics,
                cohort_percentiles={},
                warnings=list(selection.warnings),
            )
            all_anomalies.extend(publication_anomalies)
            for anomaly in publication_anomalies:
                findings.append(
                    AnalyticsFinding(
                        id=str(uuid4()),
                        analysis_run_id=run_id,
                        creator_id=creator_id,
                        publication_id=publication.id,
                        cohort_id=cohort.id,
                        finding_type=AnalyticsFindingType.ANOMALY,
                        category="anomaly",
                        title=anomaly.anomaly_type.replace("_", " ").title(),
                        summary=anomaly.message,
                        evidence_json=_json_dumps(anomaly.evidence),
                        confidence_level=AnalyticsConfidenceLevel.MEDIUM,
                        confidence_score=0.65,
                        sample_size=len(publications),
                        contradiction_count=0,
                        status=AnalyticsFindingStatus.DRAFT,
                        is_confirmed=False,
                        confirmed_at=None,
                        rejected_at=None,
                        created_at=utc_now(),
                        updated_at=utc_now(),
                    )
                )
        if len(publications) >= 4:
            findings.append(
                AnalyticsFinding(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    creator_id=creator_id,
                    publication_id=None,
                    cohort_id=cohort.id,
                    finding_type=AnalyticsFindingType.PATTERN,
                    category="general_pattern",
                    title="Patron preliminar de compartidos y conversion",
                    summary="La cohorte muestra una relacion preliminar entre compartidos y conversion, sin afirmar causalidad.",
                    evidence_json=_json_dumps({"cohort_size": len(publications), "limitations": list(selection.limitations)}),
                    confidence_level=AnalyticsConfidenceLevel.LOW if len(publications) < 10 else AnalyticsConfidenceLevel.MEDIUM,
                    confidence_score=0.4 if len(publications) < 10 else 0.6,
                    sample_size=len(publications),
                    contradiction_count=0,
                    status=AnalyticsFindingStatus.DRAFT,
                    is_confirmed=False,
                    confirmed_at=None,
                    rejected_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if selection.warnings:
            findings.append(
                AnalyticsFinding(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    creator_id=creator_id,
                    publication_id=None,
                    cohort_id=cohort.id,
                    finding_type=AnalyticsFindingType.DATA_QUALITY_WARNING,
                    category="quality",
                    title="Advertencias de comparabilidad",
                    summary="La cohorte contiene advertencias de comparabilidad o muestra insuficiente.",
                    evidence_json=_json_dumps({"warnings": list(selection.warnings), "limitations": list(selection.limitations)}),
                    confidence_level=AnalyticsConfidenceLevel.LOW,
                    confidence_score=0.25,
                    sample_size=len(publications),
                    contradiction_count=0,
                    status=AnalyticsFindingStatus.DRAFT,
                    is_confirmed=False,
                    confirmed_at=None,
                    rejected_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if any(item.anomaly_type in {"strong_ctr_weak_retention", "weak_ctr_strong_retention"} for item in all_anomalies):
            findings.append(
                AnalyticsFinding(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    creator_id=creator_id,
                    publication_id=None,
                    cohort_id=cohort.id,
                    finding_type=AnalyticsFindingType.HYPOTHESIS,
                    category="hypothesis",
                    title="Revisar inicio y retencion",
                    summary="Probar ajustes de arranque y comparar completion_rate en proximas publicaciones.",
                    evidence_json=_json_dumps({"trigger": "anomaly_detected", "requirement": "futuras muestras"}),
                    confidence_level=AnalyticsConfidenceLevel.LOW,
                    confidence_score=0.3,
                    sample_size=len(publications),
                    contradiction_count=0,
                    status=AnalyticsFindingStatus.DRAFT,
                    is_confirmed=False,
                    confirmed_at=None,
                    rejected_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        if summary_metrics:
            top_metric = max(summary_metrics.values(), key=lambda item: item.count)
            findings.append(
                AnalyticsFinding(
                    id=str(uuid4()),
                    analysis_run_id=run_id,
                    creator_id=creator_id,
                    publication_id=None,
                    cohort_id=cohort.id,
                    finding_type=AnalyticsFindingType.INFERENCE,
                    category="inference",
                    title=f"Interpretacion provisional de {top_metric.metric_key}",
                    summary="La tendencia observada parece consistente dentro de la muestra, pero no implica causalidad.",
                    evidence_json=_json_dumps(top_metric.to_dict()),
                    confidence_level=confidence_from_sample(top_metric.count),
                    confidence_score=0.5 if top_metric.count < 4 else 0.7,
                    sample_size=top_metric.count,
                    contradiction_count=0,
                    status=AnalyticsFindingStatus.DRAFT,
                    is_confirmed=False,
                    confirmed_at=None,
                    rejected_at=None,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
        return findings

    def _persist_analysis(
        self,
        *,
        run: AnalyticsAnalysisRun,
        cohort: AnalyticsCohortDefinition,
        publications: list[AnalyticsPublication],
        latest_metrics_by_publication: dict[str, dict[str, AnalyticsMetricSnapshot]],
        selection: CohortSelectionResult,
        comparison_results: list[AnalyticsComparisonResult],
        findings: list[AnalyticsFinding],
    ) -> AnalyticsAnalysisRun:
        run = self.repository.upsert_analysis_run(run)
        self.repository.upsert_comparison_results(run.id, comparison_results)
        persisted_findings = [self.repository.upsert_finding(finding) for finding in findings]
        warning_count = len(selection.warnings) + len(selection.limitations)
        completed_status = AnalyticsAnalysisRunStatus.COMPLETED_WITH_WARNINGS if warning_count else AnalyticsAnalysisRunStatus.COMPLETED
        completed = replace(
            run,
            status=completed_status,
            publication_count=len(publications),
            metric_count=len(comparison_results),
            warning_count=warning_count,
            completed_at=utc_now(),
        )
        return self.repository.upsert_analysis_run(completed)

    def analyze_cohort(self, cohort_id: str) -> AnalyticsAnalysisRun:
        cohort = self.repository.get_cohort_by_id(cohort_id)
        if cohort is None:
            raise AnalyticsLabNotFoundError("La cohorte no existe.")
        publications, selection, latest_metrics_by_publication = self._cohort_publications(cohort)
        publication_ids = [publication.id for publication in publications]
        publication_fingerprints = [publication.source_fingerprint for publication in publications]
        configuration = {
            "cohort": cohort.to_dict(),
            "publication_ids": publication_ids,
            "selection": selection.to_dict(),
        }
        fingerprint = self._analysis_fingerprint(
            creator_id=cohort.creator_id,
            run_type=AnalyticsLabRunType.COHORT_ANALYSIS,
            cohort=cohort,
            publication_ids=publication_ids,
            publication_fingerprints=publication_fingerprints,
            configuration=configuration,
        )
        existing = self.repository.get_analysis_run_by_fingerprint(fingerprint, AnalyticsLabRunType.COHORT_ANALYSIS.value)
        if existing and existing.status in {AnalyticsAnalysisRunStatus.COMPLETED, AnalyticsAnalysisRunStatus.COMPLETED_WITH_WARNINGS}:
            return existing
        run = AnalyticsAnalysisRun(
            id=str(uuid4()),
            creator_id=cohort.creator_id,
            run_type=AnalyticsLabRunType.COHORT_ANALYSIS,
            cohort_id=cohort.id,
            status=AnalyticsAnalysisRunStatus.RUNNING,
            configuration_json=_json_dumps(configuration),
            source_fingerprint=fingerprint,
            publication_count=len(publications),
            metric_count=0,
            warning_count=0,
            started_at=utc_now(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=utc_now(),
        )
        comparison_results = self._build_comparison_results(run_id=run.id, cohort=cohort, publications=publications, latest_metrics_by_publication=latest_metrics_by_publication)
        findings = self._build_findings(
            run_id=run.id,
            creator_id=cohort.creator_id,
            cohort=cohort,
            publications=publications,
            latest_metrics_by_publication=latest_metrics_by_publication,
            comparison_results=comparison_results,
            selection=selection,
        )
        return self._persist_analysis(
            run=run,
            cohort=cohort,
            publications=publications,
            latest_metrics_by_publication=latest_metrics_by_publication,
            selection=selection,
            comparison_results=comparison_results,
            findings=findings,
        )

    def compare_publication(self, publication_id: str, cohort_id: str) -> AnalyticsAnalysisRun:
        cohort = self.repository.get_cohort_by_id(cohort_id)
        if cohort is None:
            raise AnalyticsLabNotFoundError("La cohorte no existe.")
        publication = self.analytics_service.get_publication(publication_id)
        if publication is None:
            raise AnalyticsLabNotFoundError("La publicacion no existe.")
        publications, selection, latest_metrics_by_publication = self._cohort_publications(cohort)
        publications = [item for item in publications if item.id == publication.id]
        selection = CohortSelectionResult(
            publication_ids=tuple(pub.id for pub in publications),
            warnings=selection.warnings,
            limitations=selection.limitations,
            comparable=selection.comparable,
            available_metrics=selection.available_metrics,
        )
        publication_ids = [publication.id for publication in publications]
        publication_fingerprints = [publication.source_fingerprint for publication in publications]
        configuration = {
            "cohort": cohort.to_dict(),
            "publication_id": publication.id,
            "selection": selection.to_dict(),
        }
        fingerprint = self._analysis_fingerprint(
            creator_id=cohort.creator_id,
            run_type=AnalyticsLabRunType.PUBLICATION_COMPARISON,
            cohort=cohort,
            publication_ids=publication_ids,
            publication_fingerprints=publication_fingerprints,
            configuration=configuration,
        )
        existing = self.repository.get_analysis_run_by_fingerprint(fingerprint, AnalyticsLabRunType.PUBLICATION_COMPARISON.value)
        if existing and existing.status in {AnalyticsAnalysisRunStatus.COMPLETED, AnalyticsAnalysisRunStatus.COMPLETED_WITH_WARNINGS}:
            return existing
        run = AnalyticsAnalysisRun(
            id=str(uuid4()),
            creator_id=cohort.creator_id,
            run_type=AnalyticsLabRunType.PUBLICATION_COMPARISON,
            cohort_id=cohort.id,
            status=AnalyticsAnalysisRunStatus.RUNNING,
            configuration_json=_json_dumps(configuration),
            source_fingerprint=fingerprint,
            publication_count=len(publications),
            metric_count=0,
            warning_count=0,
            started_at=utc_now(),
            completed_at=None,
            error_code=None,
            error_message=None,
            created_at=utc_now(),
        )
        comparison_results = self._build_comparison_results(run_id=run.id, cohort=cohort, publications=publications, latest_metrics_by_publication=latest_metrics_by_publication)
        findings = self._build_findings(
            run_id=run.id,
            creator_id=cohort.creator_id,
            cohort=cohort,
            publications=publications,
            latest_metrics_by_publication=latest_metrics_by_publication,
            comparison_results=comparison_results,
            selection=selection,
        )
        return self._persist_analysis(
            run=run,
            cohort=cohort,
            publications=publications,
            latest_metrics_by_publication=latest_metrics_by_publication,
            selection=selection,
            comparison_results=comparison_results,
            findings=findings,
        )

    def get_analysis_run(self, run_id: str) -> AnalyticsAnalysisRun | None:
        return self.repository.get_analysis_run_by_id(run_id)

    def list_analysis_runs(self, creator_id: str, *, run_type: str | None = None) -> list[AnalyticsAnalysisRun]:
        return self.repository.list_analysis_runs(creator_id, run_type=run_type)

    def get_analysis_detail(self, run_id: str) -> dict[str, object]:
        run = self.repository.get_analysis_run_by_id(run_id)
        if run is None:
            raise AnalyticsLabNotFoundError("La corrida de analisis no existe.")
        return {
            "run": run.to_dict(),
            "comparisons": [item.to_dict() for item in self.repository.list_comparison_results(run_id)],
            "findings": [item.to_dict() for item in self.repository.list_findings(run.creator_id, filters={"analysis_run_id": run_id})],
        }

    def list_findings(self, creator_id: str, *, filters: dict[str, object] | None = None) -> list[AnalyticsFinding]:
        return self.repository.list_findings(creator_id, filters=filters)

    def get_finding(self, finding_id: str) -> AnalyticsFinding | None:
        return self.repository.get_finding_by_id(finding_id)

    def confirm_finding(self, finding_id: str) -> AnalyticsFinding:
        finding = self.repository.get_finding_by_id(finding_id)
        if finding is None:
            raise AnalyticsLabNotFoundError("El finding no existe.")
        updated = replace(
            finding,
            status=AnalyticsFindingStatus.CONFIRMED,
            is_confirmed=True,
            confirmed_at=utc_now(),
            rejected_at=None,
            updated_at=utc_now(),
        )
        return self.repository.upsert_finding(updated)

    def reject_finding(self, finding_id: str) -> AnalyticsFinding:
        finding = self.repository.get_finding_by_id(finding_id)
        if finding is None:
            raise AnalyticsLabNotFoundError("El finding no existe.")
        updated = replace(
            finding,
            status=AnalyticsFindingStatus.REJECTED,
            is_confirmed=False,
            rejected_at=utc_now(),
            confirmed_at=None,
            updated_at=utc_now(),
        )
        return self.repository.upsert_finding(updated)

    def generate_weekly_report(self, *, creator_id: str, period_start: str, period_end: str) -> AnalyticsReportRun:
        date_start = datetime.fromisoformat(period_start).date()
        date_end = datetime.fromisoformat(period_end).date()
        publications = self.analytics_service.list_publications(
            creator_id,
            filters={"date_from": period_start, "date_to": period_end},
        )
        latest_runs = self.list_analysis_runs(creator_id)
        relevant_runs = [run for run in latest_runs if date_start <= run.created_at.date() <= date_end]
        relevant_run_ids = {run.id for run in relevant_runs}
        findings = [finding for finding in self.list_findings(creator_id) if finding.analysis_run_id in relevant_run_ids]
        configuration = {
            "creator_id": creator_id,
            "period_start": period_start,
            "period_end": period_end,
            "publication_ids": [publication.id for publication in publications],
            "analysis_run_ids": [run.id for run in relevant_runs],
            "finding_ids": [finding.id for finding in findings],
        }
        fingerprint = build_analytics_lab_fingerprint(configuration | {"report_version": "v1"})
        existing = self.repository.get_report_run_by_fingerprint(fingerprint, "weekly")
        if existing and existing.status in {AnalyticsReportStatus.COMPLETED, AnalyticsReportStatus.COMPLETED_WITH_WARNINGS}:
            return existing
        report = AnalyticsReportRun(
            id=str(uuid4()),
            creator_id=creator_id,
            report_type="weekly",
            period_start=period_start,
            period_end=period_end,
            status=AnalyticsReportStatus.RUNNING,
            title=f"Weekly report {period_start} to {period_end}",
            summary="Reporte semanal reproducible de Analytics Lab.",
            configuration_json=_json_dumps(configuration),
            source_fingerprint=fingerprint,
            finding_count=len(findings),
            warning_count=0,
            output_json_path=None,
            output_txt_path=None,
            output_csv_path=None,
            created_at=utc_now(),
            completed_at=None,
        )
        report = self.repository.upsert_report_run(report)
        sections = [
            {"name": "Resumen del periodo", "title": "Resumen", "body": f"Publicaciones: {len(publications)} | Findings: {len(findings)}"},
            {"name": "Datos disponibles", "title": "Datos", "body": ", ".join(sorted({publication.platform for publication in publications})) or "Sin datos"},
            {"name": "Publicaciones nuevas", "title": "Nuevas", "body": "\n".join(publication.title for publication in publications) or "Sin publicaciones"},
            {"name": "Rendimiento por plataforma", "title": "Plataformas", "body": self._build_platform_summary(publications)},
            {"name": "Hallazgos destacados", "title": "Hallazgos", "body": "\n".join(finding.title for finding in findings) or "Sin hallazgos"},
            {"name": "Anomalias", "title": "Anomalias", "body": self._build_anomaly_summary(findings)},
            {"name": "Patrones preliminares", "title": "Patrones", "body": self._build_pattern_summary(findings)},
            {"name": "Hipotesis para revisar", "title": "Hipotesis", "body": self._build_hypothesis_summary(findings)},
            {"name": "Datos faltantes", "title": "Faltantes", "body": self._build_missing_data_summary(publications)},
            {"name": "Limitaciones", "title": "Limitaciones", "body": "No se infiere causalidad ni se generan recomendaciones."},
        ]
        items: list[AnalyticsReportItem] = []
        for index, section in enumerate(sections, start=1):
            items.append(
                AnalyticsReportItem(
                    id=str(uuid4()),
                    report_run_id=report.id,
                    item_index=index,
                    section=section["name"],
                    finding_id=None,
                    item_type="section",
                    title=section["title"],
                    body=section["body"],
                    evidence_json=_json_dumps({"section": section["name"]}),
                    created_at=utc_now(),
                )
            )
        persisted_items = self.repository.upsert_report_items(report.id, items)
        payload = build_report_payload(
            report,
            persisted_items,
            [finding.to_dict() for finding in findings],
            sections=sections,
            warnings=[],
            confidence=[],
            limitations=["no_causality", "no_recommendations"],
        )
        json_path = self._reports_root / f"{report.id}.json"
        txt_path = self._reports_root / f"{report.id}.txt"
        csv_path = self._reports_root / f"{report.id}.csv"
        write_report(json_path, payload, format_name="json")
        write_report(txt_path, payload, format_name="txt")
        write_report(csv_path, payload, format_name="csv")
        completed = replace(
            report,
            status=AnalyticsReportStatus.COMPLETED,
            finding_count=len(findings),
            warning_count=0,
            output_json_path=str(json_path),
            output_txt_path=str(txt_path),
            output_csv_path=str(csv_path),
            completed_at=utc_now(),
        )
        return self.repository.upsert_report_run(completed)

    def list_reports(self, creator_id: str) -> list[AnalyticsReportRun]:
        return self.repository.list_report_runs(creator_id)

    def get_report(self, report_id: str) -> AnalyticsReportRun | None:
        return self.repository.get_report_run_by_id(report_id)

    def get_report_detail(self, report_id: str) -> dict[str, object]:
        report = self.repository.get_report_run_by_id(report_id)
        if report is None:
            raise AnalyticsLabNotFoundError("El reporte no existe.")
        return {
            "report": report.to_dict(),
            "items": [item.to_dict() for item in self.repository.list_report_items(report_id)],
        }

    def export_report(self, report_id: str, format_name: str) -> Path:
        report = self.repository.get_report_run_by_id(report_id)
        if report is None:
            raise AnalyticsLabNotFoundError("El reporte no existe.")
        output_path = {
            "json": report.output_json_path,
            "txt": report.output_txt_path,
            "csv": report.output_csv_path,
        }.get(format_name)
        if not output_path:
            raise AnalyticsLabStateError("El reporte no tiene una salida de ese formato.")
        return Path(output_path)

    def _build_platform_summary(self, publications: list[AnalyticsPublication]) -> str:
        counts: dict[str, int] = {}
        for publication in publications:
            counts[publication.platform] = counts.get(publication.platform, 0) + 1
        return "\n".join(f"{platform}: {count}" for platform, count in sorted(counts.items())) or "Sin datos"

    def _build_anomaly_summary(self, findings: list[AnalyticsFinding]) -> str:
        anomalies = [finding for finding in findings if finding.finding_type == AnalyticsFindingType.ANOMALY]
        return "\n".join(finding.title for finding in anomalies) or "Sin anomalias"

    def _build_pattern_summary(self, findings: list[AnalyticsFinding]) -> str:
        patterns = [finding for finding in findings if finding.finding_type == AnalyticsFindingType.PATTERN]
        return "\n".join(finding.title for finding in patterns) or "Sin patrones"

    def _build_hypothesis_summary(self, findings: list[AnalyticsFinding]) -> str:
        hypotheses = [finding for finding in findings if finding.finding_type == AnalyticsFindingType.HYPOTHESIS]
        return "\n".join(finding.title for finding in hypotheses) or "Sin hipotesis"

    def _build_missing_data_summary(self, publications: list[AnalyticsPublication]) -> str:
        if not publications:
            return "Sin publicaciones."
        missing_metrics = []
        for publication in publications:
            metrics = self.analytics_service.get_latest_metrics(publication.id)
            for expected in ("views", "completion_rate", "share_rate"):
                if expected not in metrics:
                    missing_metrics.append(f"{publication.title}: {expected}")
        return "\n".join(missing_metrics) or "Sin datos faltantes relevantes."


def build_analytics_lab_services(
    *,
    analytics_service: AnalyticsQueryService,
    repository: AnalyticsLabRepository,
    paths: ProjectPaths,
    logger: logging.Logger | None = None,
):
    lab_service = AnalyticsLabService(
        analytics_service=analytics_service,
        repository=repository,
        paths=paths,
        logger=logger,
    )
    from creator_intelligence_studio.application.services.analytics_cohort_service import AnalyticsCohortService
    from creator_intelligence_studio.application.services.analytics_comparison_service import AnalyticsComparisonService
    from creator_intelligence_studio.application.services.analytics_finding_service import AnalyticsFindingService
    from creator_intelligence_studio.application.services.analytics_report_service import AnalyticsReportService

    return (
        lab_service,
        AnalyticsCohortService(lab_service),
        AnalyticsComparisonService(lab_service),
        AnalyticsFindingService(lab_service),
        AnalyticsReportService(lab_service),
    )
