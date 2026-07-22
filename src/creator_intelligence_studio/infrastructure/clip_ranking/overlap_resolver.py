"""Resolucion de solapamientos entre candidatos de clip."""

from __future__ import annotations

from dataclasses import replace

from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingOptions

from .rule_based_ranker import RankedCandidateDraft


def compute_temporal_iou(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    if end_a <= start_a or end_b <= start_b:
        return 0.0
    intersection = max(0.0, min(end_a, end_b) - max(start_a, start_b))
    if intersection <= 0:
        return 0.0
    union = max(end_a, end_b) - min(start_a, start_b)
    return intersection / union if union > 0 else 0.0


def resolve_overlaps(candidates: list[RankedCandidateDraft], options: ClipRankingOptions) -> list[RankedCandidateDraft]:
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda item: (-item.rank_score, item.adjusted_start_seconds, item.adjusted_end_seconds, item.multimodal_candidate_id))
    resolved: list[RankedCandidateDraft] = []
    for candidate in ordered:
        max_iou = 0.0
        duplicate = False
        for other in resolved:
            iou = compute_temporal_iou(
                candidate.adjusted_start_seconds,
                candidate.adjusted_end_seconds,
                other.adjusted_start_seconds,
                other.adjusted_end_seconds,
            )
            if iou > max_iou:
                max_iou = iou
            if iou >= options.iou_duplicate_threshold or (
                iou >= options.iou_overlap_threshold
                and candidate.candidate_type == other.candidate_type
                and abs(candidate.duration_seconds - other.duration_seconds) <= max(1.0, options.minimum_duration_seconds)
            ):
                duplicate = True
        overlap_penalty = min(1.0, max_iou * 0.85 + (0.20 if duplicate else 0.0))
        rank_score = max(0.0, min(1.0, candidate.rank_score - options.overlap_penalty_weight * overlap_penalty))
        resolved.append(
            replace(
                candidate,
                overlap_penalty=overlap_penalty,
                rank_score=rank_score,
                review_status="duplicate" if duplicate and max_iou >= options.iou_duplicate_threshold else candidate.review_status,
            )
        )
    return sorted(resolved, key=lambda item: (-item.rank_score, item.adjusted_start_seconds, item.adjusted_end_seconds, item.multimodal_candidate_id))
