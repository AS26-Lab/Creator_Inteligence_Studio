"""Servicios de dominio para ranking de clips."""

from __future__ import annotations

import hashlib
import json

from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate

from .errors import ClipRankingValidationError
from .value_objects import ClipRankingOptions, ClipRankingProfile, normalize_clip_ranking_config


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def build_clip_ranking_configuration_fingerprint(options: ClipRankingOptions) -> str:
    normalized = normalize_clip_ranking_config(options)
    return hashlib.sha256(_json_dumps(normalized.to_dict()).encode("utf-8")).hexdigest()


def build_clip_ranking_source_fingerprint(
    *,
    multimodal_analysis: MultimodalAnalysis,
    multimodal_candidates: list[MultimodalMomentCandidate],
    options: ClipRankingOptions,
) -> str:
    payload = {
        "analysis_id": multimodal_analysis.id,
        "analysis_configuration_fingerprint": multimodal_analysis.configuration_fingerprint,
        "analysis_source_fingerprint": multimodal_analysis.source_fingerprint,
        "candidate_count": len(multimodal_candidates),
        "candidate_signatures": [
            {
                "source_id": candidate.multimodal_analysis_id,
                "candidate_id": candidate.id,
                "candidate_type": candidate.candidate_type.value,
                "start_seconds": candidate.start_seconds,
                "end_seconds": candidate.end_seconds,
                "score": candidate.score,
                "confidence": candidate.confidence,
            }
            for candidate in sorted(multimodal_candidates, key=lambda item: (item.start_seconds, item.end_seconds, item.id))
        ],
        "profile": options.profile.value,
    }
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def is_clip_ranking_stale(
    run,
    *,
    multimodal_analysis: MultimodalAnalysis | None,
    multimodal_candidates: list[MultimodalMomentCandidate] | None = None,
    options: ClipRankingOptions | None = None,
) -> bool:
    if run is None:
        return False
    if run.status.value != "completed":
        return True
    if multimodal_analysis is None:
        return True
    if options is not None:
        expected_config = build_clip_ranking_configuration_fingerprint(options)
        if run.configuration_fingerprint != expected_config:
            return True
    if multimodal_candidates is None:
        multimodal_candidates = []
    expected_source = build_clip_ranking_source_fingerprint(
        multimodal_analysis=multimodal_analysis,
        multimodal_candidates=multimodal_candidates,
        options=options or ClipRankingOptions(),
    )
    return run.source_fingerprint != expected_source


def profile_weight_multipliers(profile: ClipRankingProfile) -> dict[str, float]:
    if profile == ClipRankingProfile.SPEECH_FOCUSED:
        return {
            "speech_weight": 1.35,
            "evidence_weight": 1.10,
            "activity_weight": 1.10,
            "visual_weight": 0.90,
        }
    if profile == ClipRankingProfile.VISUAL_FOCUSED:
        return {
            "visual_weight": 1.35,
            "transition_weight": 1.15,
            "novelty_weight": 1.10,
            "speech_weight": 0.90,
        }
    if profile == ClipRankingProfile.HIGH_ENERGY:
        return {
            "acoustic_weight": 1.30,
            "activity_weight": 1.20,
            "transition_weight": 1.10,
            "speech_weight": 0.95,
        }
    if profile == ClipRankingProfile.STORY_BEATS:
        return {
            "transition_weight": 1.20,
            "novelty_weight": 1.15,
            "duration_weight": 1.05,
            "opening_bias": 1.10,
            "closing_bias": 1.10,
        }
    return {}


def apply_profile_weights(options: ClipRankingOptions) -> ClipRankingOptions:
    normalized = normalize_clip_ranking_config(options)
    multipliers = profile_weight_multipliers(normalized.profile)
    payload = normalized.to_dict()
    for field, factor in multipliers.items():
        if field.endswith("_bias"):
            continue
        if field in payload:
            payload[field] = float(payload[field]) * factor
    if normalized.profile == ClipRankingProfile.STORY_BEATS:
        payload["duration_weight"] = float(payload["duration_weight"]) * 1.05
    return ClipRankingOptions(
        profile=ClipRankingProfile(payload["profile"]),
        minimum_duration_seconds=float(payload["minimum_duration_seconds"]),
        recommended_duration_seconds=float(payload["recommended_duration_seconds"]),
        target_short_duration_seconds=float(payload["target_short_duration_seconds"]),
        target_medium_duration_seconds=float(payload["target_medium_duration_seconds"]),
        maximum_duration_seconds=float(payload["maximum_duration_seconds"]),
        iou_duplicate_threshold=float(payload["iou_duplicate_threshold"]),
        iou_overlap_threshold=float(payload["iou_overlap_threshold"]),
        diversity_min_gap_seconds=float(payload["diversity_min_gap_seconds"]),
        diversity_window_seconds=float(payload["diversity_window_seconds"]),
        ranker_version=str(payload["ranker_version"]),
        source_fingerprint_version=str(payload["source_fingerprint_version"]),
        base_score_weight=float(payload["base_score_weight"]),
        confidence_weight=float(payload["confidence_weight"]),
        activity_weight=float(payload["activity_weight"]),
        novelty_weight=float(payload["novelty_weight"]),
        transition_weight=float(payload["transition_weight"]),
        evidence_weight=float(payload["evidence_weight"]),
        speech_weight=float(payload["speech_weight"]),
        visual_weight=float(payload["visual_weight"]),
        acoustic_weight=float(payload["acoustic_weight"]),
        duration_weight=float(payload["duration_weight"]),
        overlap_penalty_weight=float(payload["overlap_penalty_weight"]),
        silence_penalty_weight=float(payload["silence_penalty_weight"]),
        low_activity_penalty_weight=float(payload["low_activity_penalty_weight"]),
        missing_source_penalty_weight=float(payload["missing_source_penalty_weight"]),
        duplicate_penalty_weight=float(payload["duplicate_penalty_weight"]),
        diversity_weight=float(payload["diversity_weight"]),
    )
