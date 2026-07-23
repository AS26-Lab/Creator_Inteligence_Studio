"""Extraccion reproducible de features para personalizacion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from statistics import mean
from typing import Any

from creator_intelligence_studio.domain.personalization_data.entities import CreatorFeatureSchema
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment
from creator_intelligence_studio.domain.clip_ranking.entities import ClipRankingRun, RankedClipCandidate
from creator_intelligence_studio.shared.dates import utc_now


CREATOR_FEATURE_SCHEMA_VERSION = "1"
CREATOR_FEATURE_SCHEMA_NAME = "creator_personalization_baseline"
CREATOR_FEATURE_SCHEMA_DESCRIPTION = "Features tecnicas reproducibles para datasets de personalizacion por creador."

CREATOR_FEATURE_NAMES: tuple[str, ...] = (
    "candidate_type",
    "rank_position",
    "profile",
    "source_score",
    "source_confidence",
    "combined_activity_score",
    "transition_score",
    "novelty_score",
    "candidate_duration_seconds",
    "candidate_duration_ratio",
    "relative_start_seconds",
    "relative_end_seconds",
    "distance_to_start_seconds",
    "distance_to_end_seconds",
    "word_count",
    "word_density",
    "has_transcription",
    "transcription_segment_count",
    "nearby_candidate_count",
    "source_available_transcription",
    "source_available_acoustic",
    "source_available_visual",
    "multimodal_window_count",
    "multimodal_window_speech_ratio",
    "multimodal_window_silence_ratio",
    "multimodal_window_speech_rate",
    "multimodal_window_acoustic_energy",
    "multimodal_window_acoustic_change",
    "multimodal_window_visual_motion",
    "multimodal_window_visual_change",
    "multimodal_window_brightness",
    "multimodal_window_cut_count",
    "multimodal_window_acoustic_event_count",
    "multimodal_window_visual_event_count",
    "rank_score",
    "quality_score",
    "diversity_score",
    "overlap_penalty",
    "duration_score",
    "opening_score",
    "closing_score",
    "speech_score",
    "visual_score",
    "acoustic_score",
    "evidence_strength_score",
    "acoustic_average_energy",
    "acoustic_peak_energy",
    "acoustic_dynamic_range",
    "acoustic_pause_count",
    "acoustic_longest_pause_seconds",
    "acoustic_words_per_minute",
    "visual_average_brightness",
    "visual_average_contrast",
    "visual_average_motion",
    "visual_peak_motion",
    "visual_detected_cut_count",
    "visual_detected_scene_count",
    "collections_count",
    "review_event_count",
    "manual_bounds_changed",
    "candidate_conflict_count",
    "current_review_status",
    "current_rating",
)

CREATOR_FEATURE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "candidate_type": {"type": "categorical", "origin": "multimodal_candidate", "missing": None, "normalization": "identity"},
    "rank_position": {"type": "integer", "origin": "ranking", "range": [0, None], "missing": None, "normalization": "identity"},
    "profile": {"type": "categorical", "origin": "ranking", "missing": None, "normalization": "identity"},
    "source_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "source_confidence": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "combined_activity_score": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "transition_score": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "novelty_score": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "candidate_duration_seconds": {"type": "float", "origin": "context", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "candidate_duration_ratio": {"type": "float", "origin": "context", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "relative_start_seconds": {"type": "float", "origin": "context", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "relative_end_seconds": {"type": "float", "origin": "context", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "distance_to_start_seconds": {"type": "float", "origin": "context", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "distance_to_end_seconds": {"type": "float", "origin": "context", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "word_count": {"type": "integer", "origin": "transcription", "range": [0, None], "missing": None, "normalization": "identity"},
    "word_density": {"type": "float", "origin": "transcription", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "has_transcription": {"type": "integer", "origin": "transcription", "range": [0, 1], "missing": 0, "normalization": "identity"},
    "transcription_segment_count": {"type": "integer", "origin": "transcription", "range": [0, None], "missing": 0, "normalization": "identity"},
    "nearby_candidate_count": {"type": "integer", "origin": "multimodal", "range": [0, None], "missing": 0, "normalization": "identity"},
    "source_available_transcription": {"type": "integer", "origin": "source_presence", "range": [0, 1], "missing": 0, "normalization": "identity"},
    "source_available_acoustic": {"type": "integer", "origin": "source_presence", "range": [0, 1], "missing": 0, "normalization": "identity"},
    "source_available_visual": {"type": "integer", "origin": "source_presence", "range": [0, 1], "missing": 0, "normalization": "identity"},
    "multimodal_window_count": {"type": "integer", "origin": "multimodal", "range": [0, None], "missing": 0, "normalization": "identity"},
    "multimodal_window_speech_ratio": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_silence_ratio": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_speech_rate": {"type": "float", "origin": "multimodal", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "multimodal_window_acoustic_energy": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_acoustic_change": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_visual_motion": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_visual_change": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_brightness": {"type": "float", "origin": "multimodal", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "multimodal_window_cut_count": {"type": "integer", "origin": "multimodal", "range": [0, None], "missing": 0, "normalization": "identity"},
    "multimodal_window_acoustic_event_count": {"type": "integer", "origin": "multimodal", "range": [0, None], "missing": 0, "normalization": "identity"},
    "multimodal_window_visual_event_count": {"type": "integer", "origin": "multimodal", "range": [0, None], "missing": 0, "normalization": "identity"},
    "rank_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "quality_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "diversity_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "overlap_penalty": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "duration_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "opening_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "closing_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "speech_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "visual_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "acoustic_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "evidence_strength_score": {"type": "float", "origin": "ranking", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "acoustic_average_energy": {"type": "float", "origin": "acoustic", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "acoustic_peak_energy": {"type": "float", "origin": "acoustic", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "acoustic_dynamic_range": {"type": "float", "origin": "acoustic", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "acoustic_pause_count": {"type": "integer", "origin": "acoustic", "range": [0, None], "missing": None, "normalization": "identity"},
    "acoustic_longest_pause_seconds": {"type": "float", "origin": "acoustic", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "acoustic_words_per_minute": {"type": "float", "origin": "acoustic", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "visual_average_brightness": {"type": "float", "origin": "visual", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "visual_average_contrast": {"type": "float", "origin": "visual", "range": [0.0, None], "missing": None, "normalization": "raw"},
    "visual_average_motion": {"type": "float", "origin": "visual", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "visual_peak_motion": {"type": "float", "origin": "visual", "range": [0.0, 1.0], "missing": None, "normalization": "raw"},
    "visual_detected_cut_count": {"type": "integer", "origin": "visual", "range": [0, None], "missing": 0, "normalization": "identity"},
    "visual_detected_scene_count": {"type": "integer", "origin": "visual", "range": [0, None], "missing": 0, "normalization": "identity"},
    "collections_count": {"type": "integer", "origin": "human_feedback", "range": [0, None], "missing": 0, "normalization": "identity"},
    "review_event_count": {"type": "integer", "origin": "human_feedback", "range": [0, None], "missing": 0, "normalization": "identity"},
    "manual_bounds_changed": {"type": "integer", "origin": "human_feedback", "range": [0, 1], "missing": 0, "normalization": "identity"},
    "candidate_conflict_count": {"type": "integer", "origin": "human_feedback", "range": [0, None], "missing": 0, "normalization": "identity"},
    "current_review_status": {"type": "categorical", "origin": "human_feedback", "missing": None, "normalization": "identity"},
    "current_rating": {"type": "integer", "origin": "human_feedback", "range": [1, 5], "missing": None, "normalization": "identity"},
}


@dataclass(frozen=True, slots=True)
class ExtractedFeatureSet:
    feature_vector: dict[str, Any]
    quality_flags: dict[str, Any]
    missing_feature_count: int
    feature_count: int


def _safe_mean(values: list[float], fallback: float | None = None) -> float | None:
    if not values:
        return fallback
    return float(mean(values))


def _safe_sum(values: list[float | int]) -> float:
    return float(sum(values))


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    left = max(a_start, b_start)
    right = min(a_end, b_end)
    if right <= left:
        return 0.0
    base = max(a_end - a_start, b_end - b_start)
    if base <= 0:
        return 0.0
    return (right - left) / base


def build_feature_schema_entity() -> CreatorFeatureSchema:
    return CreatorFeatureSchema(
        id="creator-feature-schema-1",
        schema_version=CREATOR_FEATURE_SCHEMA_VERSION,
        name=CREATOR_FEATURE_SCHEMA_NAME,
        description=CREATOR_FEATURE_SCHEMA_DESCRIPTION,
        feature_names=CREATOR_FEATURE_NAMES,
        feature_definitions=CREATOR_FEATURE_DEFINITIONS,
        created_at=utc_now(),
    )


def extract_dataset_features(
    *,
    video_duration_seconds: float,
    profile: str,
    multimodal_analysis: MultimodalAnalysis | None,
    multimodal_windows: list[MultimodalTimelineWindow],
    multimodal_candidate: MultimodalMomentCandidate | None,
    ranking_run: ClipRankingRun | None,
    ranked_candidate: RankedClipCandidate,
    transcription: Transcription | None,
    transcription_segments: list[TranscriptionSegment],
    acoustic_analysis: AcousticAnalysis | None,
    visual_analysis: VisualAnalysis | None,
    nearby_candidate_count: int,
    collections_count: int,
    review_event_count: int,
    conflict_count: int,
) -> ExtractedFeatureSet:
    start_seconds = ranked_candidate.adjusted_start_seconds
    end_seconds = ranked_candidate.adjusted_end_seconds
    duration_seconds = max(0.0, end_seconds - start_seconds)
    candidate_windows = [
        window for window in multimodal_windows if _overlap(start_seconds, end_seconds, window.start_seconds, window.end_seconds) > 0.0
    ]
    segment_matches = [
        segment for segment in transcription_segments if _overlap(start_seconds, end_seconds, segment.start_seconds, segment.end_seconds) > 0.0
    ]
    speech_ratios = [window.speech_ratio for window in candidate_windows]
    silence_ratios = [window.silence_ratio for window in candidate_windows]
    speech_rates = [window.speech_rate for window in candidate_windows if window.speech_rate is not None]
    acoustic_energies = [window.acoustic_energy for window in candidate_windows]
    acoustic_changes = [window.acoustic_change for window in candidate_windows]
    visual_motions = [window.visual_motion for window in candidate_windows]
    visual_changes = [window.visual_change for window in candidate_windows]
    brightness_values = [window.brightness for window in candidate_windows]
    cut_counts = [window.cut_count for window in candidate_windows]
    acoustic_event_counts = [window.acoustic_event_count for window in candidate_windows]
    visual_event_counts = [window.visual_event_count for window in candidate_windows]
    combined_scores = [window.combined_activity_score for window in candidate_windows]
    transition_scores = [window.transition_score for window in candidate_windows]
    novelty_scores = [window.novelty_score for window in candidate_windows]
    word_count = sum(window.word_count for window in candidate_windows)
    feature_vector: dict[str, Any] = {
        "candidate_type": ranked_candidate.candidate_type,
        "rank_position": ranked_candidate.rank_position,
        "profile": profile,
        "source_score": ranked_candidate.source_score,
        "source_confidence": ranked_candidate.source_confidence,
        "combined_activity_score": _safe_mean(combined_scores),
        "transition_score": _safe_mean(transition_scores),
        "novelty_score": _safe_mean(novelty_scores),
        "candidate_duration_seconds": duration_seconds,
        "candidate_duration_ratio": duration_seconds / video_duration_seconds if video_duration_seconds > 0 else None,
        "relative_start_seconds": start_seconds / video_duration_seconds if video_duration_seconds > 0 else None,
        "relative_end_seconds": end_seconds / video_duration_seconds if video_duration_seconds > 0 else None,
        "distance_to_start_seconds": max(0.0, start_seconds),
        "distance_to_end_seconds": max(0.0, video_duration_seconds - end_seconds) if video_duration_seconds > 0 else None,
        "word_count": word_count,
        "word_density": (word_count / duration_seconds) if duration_seconds > 0 else None,
        "has_transcription": 1 if transcription is not None else 0,
        "transcription_segment_count": len(segment_matches),
        "nearby_candidate_count": nearby_candidate_count,
        "source_available_transcription": 1 if transcription is not None else 0,
        "source_available_acoustic": 1 if acoustic_analysis is not None else 0,
        "source_available_visual": 1 if visual_analysis is not None else 0,
        "multimodal_window_count": len(candidate_windows),
        "multimodal_window_speech_ratio": _safe_mean(speech_ratios),
        "multimodal_window_silence_ratio": _safe_mean(silence_ratios),
        "multimodal_window_speech_rate": _safe_mean(speech_rates),
        "multimodal_window_acoustic_energy": _safe_mean(acoustic_energies),
        "multimodal_window_acoustic_change": _safe_mean(acoustic_changes),
        "multimodal_window_visual_motion": _safe_mean(visual_motions),
        "multimodal_window_visual_change": _safe_mean(visual_changes),
        "multimodal_window_brightness": _safe_mean(brightness_values),
        "multimodal_window_cut_count": int(_safe_sum(cut_counts)),
        "multimodal_window_acoustic_event_count": int(_safe_sum(acoustic_event_counts)),
        "multimodal_window_visual_event_count": int(_safe_sum(visual_event_counts)),
        "rank_score": ranked_candidate.rank_score,
        "quality_score": ranked_candidate.quality_score,
        "diversity_score": ranked_candidate.diversity_score,
        "overlap_penalty": ranked_candidate.overlap_penalty,
        "duration_score": ranked_candidate.duration_score,
        "opening_score": ranked_candidate.opening_score,
        "closing_score": ranked_candidate.closing_score,
        "speech_score": ranked_candidate.speech_score,
        "visual_score": ranked_candidate.visual_score,
        "acoustic_score": ranked_candidate.acoustic_score,
        "evidence_strength_score": ranked_candidate.evidence_strength_score,
        "acoustic_average_energy": acoustic_analysis.average_energy if acoustic_analysis is not None else None,
        "acoustic_peak_energy": acoustic_analysis.peak_energy if acoustic_analysis is not None else None,
        "acoustic_dynamic_range": acoustic_analysis.dynamic_range if acoustic_analysis is not None else None,
        "acoustic_pause_count": acoustic_analysis.pause_count if acoustic_analysis is not None else None,
        "acoustic_longest_pause_seconds": acoustic_analysis.longest_pause_seconds if acoustic_analysis is not None else None,
        "acoustic_words_per_minute": acoustic_analysis.words_per_minute if acoustic_analysis is not None else None,
        "visual_average_brightness": visual_analysis.average_brightness if visual_analysis is not None else None,
        "visual_average_contrast": visual_analysis.average_contrast if visual_analysis is not None else None,
        "visual_average_motion": visual_analysis.average_motion if visual_analysis is not None else None,
        "visual_peak_motion": visual_analysis.peak_motion if visual_analysis is not None else None,
        "visual_detected_cut_count": visual_analysis.detected_cut_count if visual_analysis is not None else None,
        "visual_detected_scene_count": visual_analysis.detected_scene_count if visual_analysis is not None else None,
        "collections_count": collections_count,
        "review_event_count": review_event_count,
        "manual_bounds_changed": int(
            ranked_candidate.adjusted_start_seconds != ranked_candidate.original_start_seconds
            or ranked_candidate.adjusted_end_seconds != ranked_candidate.original_end_seconds
        ),
        "candidate_conflict_count": conflict_count,
        "current_review_status": ranked_candidate.review_status.value,
        "current_rating": ranked_candidate.user_rating,
    }
    missing_feature_count = sum(1 for value in feature_vector.values() if value is None)
    quality_flags = {
        "feature_schema_version": CREATOR_FEATURE_SCHEMA_VERSION,
        "missing_feature_count": missing_feature_count,
        "candidate_window_count": len(candidate_windows),
        "transcription_segment_count": len(segment_matches),
    }
    return ExtractedFeatureSet(
        feature_vector=feature_vector,
        quality_flags=quality_flags,
        missing_feature_count=missing_feature_count,
        feature_count=len(feature_vector),
    )
