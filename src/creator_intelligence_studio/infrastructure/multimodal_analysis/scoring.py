"""Puntuacion tecnica de ventanas multimodales."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.multimodal_analysis.value_objects import MultimodalAnalysisOptions

from .feature_normalizer import clamp01


@dataclass(frozen=True, slots=True)
class MultimodalScoreResult:
    combined_activity_score: float
    transition_score: float
    novelty_score: float
    confidence: float


def compute_scores(
    *,
    acoustic_energy: float,
    speech_rate: float | None,
    visual_motion: float,
    cut_count: int,
    acoustic_event_count: int,
    visual_event_count: int,
    acoustic_change: float,
    visual_change: float,
    speech_ratio: float,
    silence_ratio: float,
    context_activity: float,
    options: MultimodalAnalysisOptions,
    coverage: float,
    agreement: float,
) -> MultimodalScoreResult:
    speech_rate_value = float(speech_rate or 0.0)
    event_signal = clamp01((acoustic_event_count + visual_event_count) / 3.0)
    cut_signal = clamp01(cut_count / 2.0)
    combined_raw = (
        options.acoustic_energy_weight * clamp01(acoustic_energy)
        + options.speech_rate_weight * clamp01(speech_rate_value)
        + options.visual_motion_weight * clamp01(visual_motion)
        + options.cut_weight * cut_signal
        + options.event_weight * event_signal
    )
    combined_activity = clamp01(combined_raw)
    transition = clamp01(
        0.45 * clamp01(acoustic_change)
        + 0.35 * clamp01(visual_change)
        + 0.20 * cut_signal
    )
    novelty = clamp01(abs(combined_activity - clamp01(context_activity)))
    confidence = clamp01(
        0.40 * clamp01(coverage)
        + 0.35 * clamp01(agreement)
        + 0.25 * clamp01(max(combined_activity, transition, 1.0 - silence_ratio + speech_ratio * 0.2))
    )
    return MultimodalScoreResult(
        combined_activity_score=combined_activity,
        transition_score=transition,
        novelty_score=novelty,
        confidence=confidence,
    )

