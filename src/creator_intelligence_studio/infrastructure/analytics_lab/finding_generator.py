"""Generacion de findings trazables para Analytics Lab."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.analytics_lab.value_objects import AnalyticsConfidenceLevel, AnalyticsFindingType

from .anomaly_detector import AnomalyRecord


@dataclass(frozen=True, slots=True)
class GeneratedFinding:
    finding_type: AnalyticsFindingType
    category: str
    title: str
    summary: str
    evidence: dict[str, object]
    confidence_level: AnalyticsConfidenceLevel
    confidence_score: float | None
    sample_size: int
    contradiction_count: int
    status: str
    is_confirmed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "finding_type": self.finding_type.value,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "sample_size": self.sample_size,
            "contradiction_count": self.contradiction_count,
            "status": self.status,
            "is_confirmed": self.is_confirmed,
        }


def generate_findings_from_anomalies(anomalies: list[AnomalyRecord], *, sample_size: int) -> list[GeneratedFinding]:
    findings: list[GeneratedFinding] = []
    for anomaly in anomalies:
        findings.append(
            GeneratedFinding(
                finding_type=AnalyticsFindingType.ANOMALY,
                category="anomaly",
                title=anomaly.anomaly_type.replace("_", " ").title(),
                summary=anomaly.message,
                evidence=anomaly.evidence,
                confidence_level=AnalyticsConfidenceLevel.MEDIUM if sample_size >= 4 else AnalyticsConfidenceLevel.LOW,
                confidence_score=0.65 if sample_size >= 4 else 0.35,
                sample_size=sample_size,
                contradiction_count=0,
                status="draft",
                is_confirmed=False,
            )
        )
    return findings

