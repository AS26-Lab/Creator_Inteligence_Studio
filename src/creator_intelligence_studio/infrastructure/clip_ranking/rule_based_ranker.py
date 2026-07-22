"""Ranker basado en reglas para candidatos de clip."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingOptions
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.transcription.entities import TranscriptionSegment


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _duration_score(duration_seconds: float, options: ClipRankingOptions) -> float:
    if duration_seconds < options.minimum_duration_seconds:
        return _clamp01(duration_seconds / options.minimum_duration_seconds * 0.4)
    if duration_seconds <= options.recommended_duration_seconds:
        return _clamp01(0.55 + 0.45 * (duration_seconds - options.minimum_duration_seconds) / max(1.0, options.recommended_duration_seconds - options.minimum_duration_seconds))
    if duration_seconds <= options.target_medium_duration_seconds:
        return _clamp01(1.0 - (duration_seconds - options.recommended_duration_seconds) / max(1.0, options.target_medium_duration_seconds - options.recommended_duration_seconds) * 0.2)
    if duration_seconds <= options.maximum_duration_seconds:
        return _clamp01(0.8 - (duration_seconds - options.target_medium_duration_seconds) / max(1.0, options.maximum_duration_seconds - options.target_medium_duration_seconds) * 0.45)
    return _clamp01(0.35 - (duration_seconds - options.maximum_duration_seconds) / max(1.0, options.maximum_duration_seconds) * 0.35)


def _window_mean(windows: list[MultimodalTimelineWindow], attr: str, default: float = 0.0) -> float:
    values = [float(getattr(window, attr)) for window in windows if getattr(window, attr, None) is not None]
    return float(median(values)) if values else float(default)


def _window_sum(windows: list[MultimodalTimelineWindow], attr: str) -> float:
    return float(sum(float(getattr(window, attr, 0.0)) for window in windows))


def _transcript_density(segments: list[TranscriptionSegment], start_seconds: float, end_seconds: float) -> float:
    if not segments or end_seconds <= start_seconds:
        return 0.0
    overlap_words = 0
    overlap_seconds = 0.0
    for segment in segments:
        if segment.end_seconds <= start_seconds or segment.start_seconds >= end_seconds:
            continue
        overlap = min(end_seconds, segment.end_seconds) - max(start_seconds, segment.start_seconds)
        if overlap <= 0:
            continue
        overlap_seconds += overlap
        overlap_words += max(1, len(segment.text.split()))
    if overlap_seconds <= 0:
        return 0.0
    words_per_second = overlap_words / overlap_seconds
    return _clamp01(words_per_second / 4.0)


@dataclass(frozen=True, slots=True)
class RankedCandidateDraft:
    multimodal_candidate_id: str
    original_start_seconds: float
    original_end_seconds: float
    adjusted_start_seconds: float
    adjusted_end_seconds: float
    duration_seconds: float
    candidate_type: str
    source_score: float
    source_confidence: float
    rank_score: float
    quality_score: float
    diversity_score: float
    overlap_penalty: float
    duration_score: float
    opening_score: float
    closing_score: float
    speech_score: float
    visual_score: float
    acoustic_score: float
    transition_score: float
    novelty_score: float
    evidence_strength_score: float
    review_status: str
    user_rating: int | None
    user_note: str | None
    explanation: dict[str, object]
    tags: tuple[str, ...]
    transcript_text: str
    scene_index: int | None
    source_window_start: float | None
    source_window_end: float | None


def score_clip_candidate(
    candidate: MultimodalMomentCandidate,
    *,
    windows: list[MultimodalTimelineWindow],
    transcription_segments: list[TranscriptionSegment],
    options: ClipRankingOptions,
) -> RankedCandidateDraft:
    duration_seconds = max(0.0, candidate.end_seconds - candidate.start_seconds)
    duration_score = _duration_score(duration_seconds, options)
    speech_score = _clamp01(_window_mean(windows, "speech_ratio") * 0.7 + _transcript_density(transcription_segments, candidate.start_seconds, candidate.end_seconds) * 0.3)
    visual_score = _clamp01(_window_mean(windows, "visual_motion"))
    acoustic_score = _clamp01(_window_mean(windows, "acoustic_energy"))
    transition_score = _clamp01(_window_mean(windows, "transition_score"))
    novelty_score = _clamp01(_window_mean(windows, "novelty_score"))
    evidence_strength_score = _clamp01(
        0.20 * min(1.0, len(windows) / 5.0)
        + 0.20 * min(1.0, _window_sum(windows, "acoustic_event_count") / 3.0)
        + 0.20 * min(1.0, _window_sum(windows, "visual_event_count") / 3.0)
        + 0.20 * min(1.0, _window_sum(windows, "cut_count") / 2.0)
        + 0.20 * candidate.confidence
    )
    opening_score = _clamp01(max(0.0, 1.0 - candidate.start_seconds / max(1.0, options.target_short_duration_seconds)))
    closing_score = _clamp01(max(0.0, candidate.end_seconds / max(1.0, candidate.end_seconds + options.target_short_duration_seconds / 2.0) - 0.5))
    activity_score = _clamp01(0.45 * candidate.score + 0.35 * candidate.confidence + 0.20 * _window_mean(windows, "combined_activity_score"))
    quality_score = _clamp01(
        options.base_score_weight * candidate.score
        + options.confidence_weight * candidate.confidence
        + options.activity_weight * activity_score
        + options.novelty_weight * novelty_score
        + options.transition_weight * transition_score
        + options.evidence_weight * evidence_strength_score
        + options.speech_weight * speech_score
        + options.visual_weight * visual_score
        + options.acoustic_weight * acoustic_score
        + options.duration_weight * duration_score
    )
    rank_score = _clamp01(quality_score + 0.20 * evidence_strength_score + 0.10 * novelty_score)
    evidence = {
        "source_candidate_id": candidate.id,
        "candidate_type": candidate.candidate_type.value,
        "source_score": candidate.score,
        "source_confidence": candidate.confidence,
        "duration_seconds": duration_seconds,
        "speech_ratio": _window_mean(windows, "speech_ratio"),
        "silence_ratio": _window_mean(windows, "silence_ratio"),
        "acoustic_energy": _window_mean(windows, "acoustic_energy"),
        "visual_motion": _window_mean(windows, "visual_motion"),
        "transition_score": transition_score,
        "novelty_score": novelty_score,
        "window_count": len(windows),
        "cut_count": int(_window_sum(windows, "cut_count")),
        "acoustic_event_count": int(_window_sum(windows, "acoustic_event_count")),
        "visual_event_count": int(_window_sum(windows, "visual_event_count")),
    }
    transcript_text = " ".join(
        segment.text.strip()
        for segment in transcription_segments
        if not (segment.end_seconds <= candidate.start_seconds or segment.start_seconds >= candidate.end_seconds)
    ).strip()
    scene_index = None
    scene_windows = [window for window in windows if window.scene_index is not None]
    if scene_windows:
        scene_index = scene_windows[0].scene_index
    return RankedCandidateDraft(
        multimodal_candidate_id=candidate.id,
        original_start_seconds=candidate.start_seconds,
        original_end_seconds=candidate.end_seconds,
        adjusted_start_seconds=candidate.start_seconds,
        adjusted_end_seconds=candidate.end_seconds,
        duration_seconds=duration_seconds,
        candidate_type=candidate.candidate_type.value,
        source_score=candidate.score,
        source_confidence=candidate.confidence,
        rank_score=rank_score,
        quality_score=quality_score,
        diversity_score=1.0,
        overlap_penalty=0.0,
        duration_score=duration_score,
        opening_score=opening_score,
        closing_score=closing_score,
        speech_score=speech_score,
        visual_score=visual_score,
        acoustic_score=acoustic_score,
        transition_score=transition_score,
        novelty_score=novelty_score,
        evidence_strength_score=evidence_strength_score,
        review_status="unreviewed",
        user_rating=None,
        user_note=None,
        explanation=evidence,
        tags=(),
        transcript_text=transcript_text,
        scene_index=scene_index,
        source_window_start=windows[0].start_seconds if windows else candidate.start_seconds,
        source_window_end=windows[-1].end_seconds if windows else candidate.end_seconds,
    )
