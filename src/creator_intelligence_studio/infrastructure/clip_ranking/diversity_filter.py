"""Filtro de diversidad para candidatos de clip."""

from __future__ import annotations

from dataclasses import replace
from statistics import mean

from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingOptions

from .overlap_resolver import compute_temporal_iou
from .rule_based_ranker import RankedCandidateDraft


def compute_diversity_score(candidate: RankedCandidateDraft, selected: list[RankedCandidateDraft], options: ClipRankingOptions) -> float:
    if not selected:
        return 1.0
    distance_scores = []
    type_bonus = 0.0
    scene_bonus = 0.0
    for other in selected:
        iou = compute_temporal_iou(
            candidate.adjusted_start_seconds,
            candidate.adjusted_end_seconds,
            other.adjusted_start_seconds,
            other.adjusted_end_seconds,
        )
        center_distance = abs(
            ((candidate.adjusted_start_seconds + candidate.adjusted_end_seconds) / 2.0)
            - ((other.adjusted_start_seconds + other.adjusted_end_seconds) / 2.0)
        )
        distance_scores.append(max(0.0, min(1.0, center_distance / max(1.0, options.diversity_window_seconds))) * (1.0 - iou))
        if candidate.candidate_type != other.candidate_type:
            type_bonus += 0.05
        if candidate.scene_index is not None and candidate.scene_index != other.scene_index:
            scene_bonus += 0.05
    separation = mean(distance_scores) if distance_scores else 0.0
    diversity = max(0.0, min(1.0, 0.45 * separation + 0.30 * type_bonus + 0.25 * scene_bonus))
    return diversity


def diversify_candidates(candidates: list[RankedCandidateDraft], options: ClipRankingOptions) -> list[RankedCandidateDraft]:
    if not candidates:
        return []
    ordered = sorted(candidates, key=lambda item: (-item.rank_score, item.adjusted_start_seconds, item.adjusted_end_seconds, item.multimodal_candidate_id))
    selected: list[RankedCandidateDraft] = []
    output: list[RankedCandidateDraft] = []
    for candidate in ordered:
        diversity_score = compute_diversity_score(candidate, selected, options)
        rank_score = max(0.0, min(1.0, candidate.rank_score + options.diversity_weight * (diversity_score - 0.5)))
        adjusted = replace(candidate, diversity_score=diversity_score, rank_score=rank_score)
        selected.append(adjusted)
        output.append(adjusted)
    return sorted(output, key=lambda item: (-item.rank_score, item.adjusted_start_seconds, item.adjusted_end_seconds, item.multimodal_candidate_id))
