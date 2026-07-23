"""Entidades persistidas para datasets de personalizacion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    PersonalizationDatasetStatus,
    PersonalizationLabel,
    PersonalizationReadinessStatus,
    PersonalizationSplitName,
)


@dataclass(frozen=True, slots=True)
class CreatorFeatureSchema:
    id: str
    schema_version: str
    name: str
    description: str | None
    feature_names: tuple[str, ...]
    feature_definitions: dict[str, Any]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "name": self.name,
            "description": self.description,
            "feature_names": list(self.feature_names),
            "feature_definitions": dict(self.feature_definitions),
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorDatasetSnapshot:
    id: str
    creator_id: str
    project_id: str | None
    name: str
    status: PersonalizationDatasetStatus
    dataset_version: str
    feature_schema_version: str
    label_schema_version: str
    source_fingerprint: str
    configuration_fingerprint: str
    example_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    excluded_count: int
    conflict_count: int
    train_count: int
    validation_count: int
    test_count: int
    readiness_status: PersonalizationReadinessStatus
    readiness_score: float
    started_at: datetime
    completed_at: datetime
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value,
            "dataset_version": self.dataset_version,
            "feature_schema_version": self.feature_schema_version,
            "label_schema_version": self.label_schema_version,
            "source_fingerprint": self.source_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "example_count": self.example_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "excluded_count": self.excluded_count,
            "conflict_count": self.conflict_count,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "readiness_status": self.readiness_status.value,
            "readiness_score": self.readiness_score,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorDatasetExample:
    id: str
    snapshot_id: str
    creator_id: str
    video_asset_id: str
    ranking_run_id: str | None
    ranked_clip_candidate_id: str | None
    multimodal_candidate_id: str | None
    group_key: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    label: PersonalizationLabel
    label_source: tuple[str, ...]
    label_confidence: float
    human_review_status: str | None
    human_rating: int | None
    human_tags: tuple[str, ...]
    feature_vector: dict[str, Any]
    feature_schema_version: str
    quality_flags: dict[str, Any]
    exclusion_reason: str | None
    split_name: PersonalizationSplitName
    sample_weight: float
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "creator_id": self.creator_id,
            "video_asset_id": self.video_asset_id,
            "ranking_run_id": self.ranking_run_id,
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "multimodal_candidate_id": self.multimodal_candidate_id,
            "group_key": self.group_key,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "label": self.label.value,
            "label_source": list(self.label_source),
            "label_confidence": self.label_confidence,
            "human_review_status": self.human_review_status,
            "human_rating": self.human_rating,
            "human_tags": list(self.human_tags),
            "feature_vector": dict(self.feature_vector),
            "feature_schema_version": self.feature_schema_version,
            "quality_flags": dict(self.quality_flags),
            "exclusion_reason": self.exclusion_reason,
            "split_name": self.split_name.value,
            "sample_weight": self.sample_weight,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class CreatorDatasetConflict:
    id: str
    snapshot_id: str
    creator_id: str
    conflict_type: str
    candidate_a_id: str | None
    candidate_b_id: str | None
    description: str
    evidence_json: dict[str, Any]
    resolution_status: str
    created_at: datetime
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "creator_id": self.creator_id,
            "conflict_type": self.conflict_type,
            "candidate_a_id": self.candidate_a_id,
            "candidate_b_id": self.candidate_b_id,
            "description": self.description,
            "evidence_json": dict(self.evidence_json),
            "resolution_status": self.resolution_status,
            "created_at": to_iso_z(self.created_at),
            "resolved_at": to_iso_z(self.resolved_at) if self.resolved_at else None,
        }


@dataclass(frozen=True, slots=True)
class CreatorDatasetQualityReport:
    id: str
    snapshot_id: str
    report_version: str
    duplicate_ratio: float
    overlap_ratio: float
    missing_feature_ratio: float
    class_balance_score: float
    creator_coverage_score: float
    temporal_coverage_score: float
    source_diversity_score: float
    label_consistency_score: float
    leakage_risk_score: float
    readiness_score: float
    readiness_status: PersonalizationReadinessStatus
    recommendations: tuple[str, ...]
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "report_version": self.report_version,
            "duplicate_ratio": self.duplicate_ratio,
            "overlap_ratio": self.overlap_ratio,
            "missing_feature_ratio": self.missing_feature_ratio,
            "class_balance_score": self.class_balance_score,
            "creator_coverage_score": self.creator_coverage_score,
            "temporal_coverage_score": self.temporal_coverage_score,
            "source_diversity_score": self.source_diversity_score,
            "label_consistency_score": self.label_consistency_score,
            "leakage_risk_score": self.leakage_risk_score,
            "readiness_score": self.readiness_score,
            "readiness_status": self.readiness_status.value,
            "recommendations": list(self.recommendations),
            "created_at": to_iso_z(self.created_at),
        }
