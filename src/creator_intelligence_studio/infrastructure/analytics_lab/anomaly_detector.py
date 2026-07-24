"""Deteccion simple y explicable de anomalias para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .metric_aggregator import derived_share_rate


@dataclass(frozen=True, slots=True)
class AnomalyRecord:
    publication_id: str | None
    metric_key: str
    anomaly_type: str
    severity: str
    message: str
    evidence: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "publication_id": self.publication_id,
            "metric_key": self.metric_key,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }


def detect_anomalies(
    *,
    publication_id: str,
    metrics: dict[str, float | None],
    cohort_percentiles: dict[str, float | None],
    warnings: list[str],
) -> list[AnomalyRecord]:
    anomalies: list[AnomalyRecord] = []
    ctr = metrics.get("ctr")
    completion = metrics.get("completion_rate")
    views = metrics.get("views")
    share_rate, _ = derived_share_rate(metrics)
    if ctr is not None and completion is not None:
        if ctr >= 0.75 and completion <= 0.35:
            anomalies.append(
                AnomalyRecord(
                    publication_id=publication_id,
                    metric_key="ctr/completion_rate",
                    anomaly_type="strong_ctr_weak_retention",
                    severity="warning",
                    message="CTR alto con retencion baja relativa a la cohorte.",
                    evidence={"ctr": ctr, "completion_rate": completion},
                )
            )
        if ctr <= 0.35 and completion >= 0.75:
            anomalies.append(
                AnomalyRecord(
                    publication_id=publication_id,
                    metric_key="ctr/completion_rate",
                    anomaly_type="weak_ctr_strong_retention",
                    severity="info",
                    message="CTR bajo con retencion alta relativa a la cohorte.",
                    evidence={"ctr": ctr, "completion_rate": completion},
                )
            )
    if views is not None and share_rate is not None and share_rate > 0.1:
        anomalies.append(
            AnomalyRecord(
                publication_id=publication_id,
                metric_key="share_rate",
                anomaly_type="high_engagement_low_reach",
                severity="info",
                message="El contenido muestra engagement fuerte relativo al alcance observado.",
                evidence={"views": views, "share_rate": share_rate},
            )
        )
    if warnings:
        anomalies.append(
            AnomalyRecord(
                publication_id=publication_id,
                metric_key="quality",
                anomaly_type="missing_expected_metric",
                severity="warning",
                message="Faltan metricas esperadas o se detectaron advertencias.",
                evidence={"warnings": warnings},
            )
        )
    return anomalies
