"""Analisis de calidad para datasets de personalizacion."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from creator_intelligence_studio.domain.personalization_data.entities import CreatorDatasetConflict, CreatorDatasetExample, CreatorDatasetQualityReport, CreatorDatasetSnapshot
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationReadinessStatus
from creator_intelligence_studio.shared.dates import utc_now


@dataclass(frozen=True, slots=True)
class QualityStats:
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


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def analyze_dataset_quality(
    *,
    snapshot: CreatorDatasetSnapshot,
    examples: list[CreatorDatasetExample],
    conflicts: list[CreatorDatasetConflict],
    total_videos: int,
    total_duration_seconds: float,
) -> QualityStats:
    if not examples:
        return QualityStats(
            duplicate_ratio=0.0,
            overlap_ratio=0.0,
            missing_feature_ratio=1.0,
            class_balance_score=0.0,
            creator_coverage_score=0.0,
            temporal_coverage_score=0.0,
            source_diversity_score=0.0,
            label_consistency_score=0.0,
            leakage_risk_score=1.0,
            readiness_score=0.0,
            readiness_status=PersonalizationReadinessStatus.NOT_READY,
            recommendations=("No hay ejemplos utilizable.",),
        )
    total = len(examples)
    positive = sum(1 for example in examples if example.label.value == "positive")
    negative = sum(1 for example in examples if example.label.value == "negative")
    neutral = sum(1 for example in examples if example.label.value == "neutral_or_uncertain")
    excluded = sum(1 for example in examples if example.label.value == "excluded")
    reviewed = total - neutral - excluded
    feature_ratios = [
        float(example.quality_flags.get("missing_feature_count", 0)) / max(1, int(example.quality_flags.get("feature_count", len(example.feature_vector))))
        for example in examples
    ]
    duplicate_pairs = 0
    overlap_pairs = 0
    for left_index, left in enumerate(examples):
        for right in examples[left_index + 1 :]:
            if left.video_asset_id != right.video_asset_id:
                continue
            overlap_start = max(left.start_seconds, right.start_seconds)
            overlap_end = min(left.end_seconds, right.end_seconds)
            if overlap_end > overlap_start:
                overlap_pairs += 1
                left_span = max(left.duration_seconds, 1e-9)
                right_span = max(right.duration_seconds, 1e-9)
                iou = (overlap_end - overlap_start) / max(left_span, right_span)
                if iou >= 0.8:
                    duplicate_pairs += 1
    pair_total = max(1, total * (total - 1) / 2)
    duplicate_ratio = _ratio(duplicate_pairs, pair_total)
    overlap_ratio = _ratio(overlap_pairs, pair_total)
    missing_feature_ratio = _ratio(sum(feature_ratios), len(feature_ratios))
    balance_base = max(positive, negative, reviewed, 1)
    class_balance_score = 1.0 - abs(positive - negative) / balance_base
    creator_coverage_score = _ratio(len({example.video_asset_id for example in examples}), max(total_videos, 1))
    temporal_coverage_score = _ratio(sum(example.duration_seconds for example in examples), max(total_duration_seconds, 1e-9))
    source_diversity_score = _ratio(len({example.ranking_run_id for example in examples if example.ranking_run_id}), total)
    label_consistency_score = 1.0 - _ratio(len(conflicts), total)
    leakage_risk_score = 1.0 if len({example.video_asset_id for example in examples}) == 1 and total >= 4 else 0.0

    readiness_score = max(
        0.0,
        min(
            1.0,
            (
                0.24 * class_balance_score
                + 0.18 * creator_coverage_score
                + 0.14 * temporal_coverage_score
                + 0.14 * source_diversity_score
                + 0.16 * label_consistency_score
                + 0.14 * (1.0 - leakage_risk_score)
            ),
        ),
    )
    recommendations: list[str] = []
    if duplicate_ratio > 0.2:
        recommendations.append("Reducir duplicados o candidatos casi identicos.")
    if missing_feature_ratio > 0.2:
        recommendations.append("Completar features faltantes antes de entrenar.")
    if positive == 0 or negative == 0:
        recommendations.append("Necesita ejemplos positivos y negativos.")
    if len({example.video_asset_id for example in examples}) < 3:
        recommendations.append("Aumentar cobertura de videos independientes.")
    if len(conflicts) > 0:
        recommendations.append("Resolver conflictos humanos antes de usar el dataset.")
    if not recommendations:
        recommendations.append("Dataset utilizable para una linea base, sujeto a validacion posterior.")
    if len({example.video_asset_id for example in examples}) < 3:
        readiness_status = PersonalizationReadinessStatus.LIMITED
    elif len(examples) >= 50 and positive > 0 and negative > 0 and len(conflicts) == 0 and leakage_risk_score == 0.0:
        readiness_status = PersonalizationReadinessStatus.READY_FOR_PERSONALIZED_TRAINING
    elif len(examples) >= 20 and positive > 0 and negative > 0 and len(conflicts) == 0:
        readiness_status = PersonalizationReadinessStatus.READY_FOR_EVALUATION
    elif reviewed >= 8 and positive > 0 and negative > 0 and len(conflicts) == 0:
        readiness_status = PersonalizationReadinessStatus.READY_FOR_BASELINE
    elif reviewed > 0:
        readiness_status = PersonalizationReadinessStatus.COLLECTING_FEEDBACK
    else:
        readiness_status = PersonalizationReadinessStatus.NOT_READY
    if len(conflicts) > 0:
        readiness_status = PersonalizationReadinessStatus.BLOCKED_BY_CONFLICTS
    elif missing_feature_ratio > 0.4 or duplicate_ratio > 0.4:
        readiness_status = PersonalizationReadinessStatus.BLOCKED_BY_QUALITY
    return QualityStats(
        duplicate_ratio=duplicate_ratio,
        overlap_ratio=overlap_ratio,
        missing_feature_ratio=missing_feature_ratio,
        class_balance_score=class_balance_score,
        creator_coverage_score=creator_coverage_score,
        temporal_coverage_score=temporal_coverage_score,
        source_diversity_score=source_diversity_score,
        label_consistency_score=label_consistency_score,
        leakage_risk_score=leakage_risk_score,
        readiness_score=readiness_score,
        readiness_status=readiness_status,
        recommendations=tuple(recommendations),
    )
