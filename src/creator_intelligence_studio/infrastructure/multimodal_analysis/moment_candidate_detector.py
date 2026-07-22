"""Deteccion heuristica de candidatos multimodales."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.multimodal_analysis.value_objects import (
    MultimodalAnalysisOptions,
    MultimodalCandidateType,
    MultimodalMomentCandidateData,
    MultimodalTimelineWindowData,
)

from .evidence_builder import build_candidate_summary
from .feature_normalizer import clamp01


@dataclass(frozen=True, slots=True)
class CandidateSeed:
    """Semilla de candidato antes de fusionar."""

    start_seconds: float
    end_seconds: float
    candidate_type: MultimodalCandidateType
    score: float
    confidence: float
    evidence: dict[str, object]


def _window_types(window: MultimodalTimelineWindowData, options: MultimodalAnalysisOptions, *, duration_seconds: float) -> list[tuple[MultimodalCandidateType, float, float]]:
    seeds: list[tuple[MultimodalCandidateType, float, float]] = []
    if window.combined_activity_score >= options.high_activity_threshold:
        seeds.append((MultimodalCandidateType.HIGH_COMBINED_ACTIVITY, window.combined_activity_score, window.confidence))
    if window.transition_score >= options.transition_threshold:
        seeds.append((MultimodalCandidateType.ABRUPT_MULTIMODAL_CHANGE, window.transition_score, window.confidence))
    if window.acoustic_energy >= 0.72 and window.speech_rate is not None and window.speech_rate >= 0.55 and window.speech_ratio >= 0.30:
        score = clamp01((window.acoustic_energy + window.speech_rate + window.speech_ratio) / 3.0)
        seeds.append((MultimodalCandidateType.SPEECH_ENERGY_PEAK, score, window.confidence))
    if window.cut_count > 0 and window.speech_ratio > 0.10:
        score = clamp01(0.5 + 0.5 * min(1.0, window.cut_count / 2.0))
        seeds.append((MultimodalCandidateType.VISUAL_TRANSITION_WITH_SPEECH, score, window.confidence))
    if window.silence_ratio >= 0.75 or window.combined_activity_score <= options.low_activity_threshold:
        score = clamp01(max(window.silence_ratio, 1.0 - window.combined_activity_score))
        seeds.append((MultimodalCandidateType.LOW_ACTIVITY_SEGMENT, score, window.confidence))
    if window.acoustic_event_count > 0 and window.visual_event_count > 0:
        score = clamp01(0.6 + 0.2 * min(1.0, window.acoustic_event_count + window.visual_event_count))
        seeds.append((MultimodalCandidateType.ACOUSTIC_EVENT_WITH_VISUAL_CHANGE, score, window.confidence))
    if window.window_index * options.window_size_seconds <= options.hook_window_seconds and window.combined_activity_score >= 0.55:
        seeds.append((MultimodalCandidateType.POSSIBLE_HOOK_CANDIDATE, clamp01(window.combined_activity_score), window.confidence))
    if window.window_index > 0 and window.transition_score >= options.transition_threshold and window.silence_ratio >= 0.35:
        seeds.append((MultimodalCandidateType.POSSIBLE_REACTION_CANDIDATE, clamp01(window.transition_score), window.confidence))
    if not seeds and window.combined_activity_score >= 0.40:
        seeds.append((MultimodalCandidateType.UNKNOWN_CANDIDATE, clamp01(window.combined_activity_score), window.confidence))
    return seeds


def detect_candidate_seeds(windows: list[MultimodalTimelineWindowData], options: MultimodalAnalysisOptions, *, duration_seconds: float) -> list[CandidateSeed]:
    seeds: list[CandidateSeed] = []
    for window in windows:
        for candidate_type, score, confidence in _window_types(window, options, duration_seconds=duration_seconds):
            evidence = dict(window.evidence)
            evidence["candidate_type"] = candidate_type.value
            evidence["candidate_score"] = score
            evidence["candidate_confidence"] = confidence
            seeds.append(
                CandidateSeed(
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    candidate_type=candidate_type,
                    score=score,
                    confidence=confidence,
                    evidence=evidence,
                )
            )
    return seeds


def _cluster_priority(candidate_type: MultimodalCandidateType) -> int:
    ranking = {
        MultimodalCandidateType.ABRUPT_MULTIMODAL_CHANGE: 0,
        MultimodalCandidateType.HIGH_COMBINED_ACTIVITY: 1,
        MultimodalCandidateType.SPEECH_ENERGY_PEAK: 2,
        MultimodalCandidateType.VISUAL_TRANSITION_WITH_SPEECH: 3,
        MultimodalCandidateType.ACOUSTIC_EVENT_WITH_VISUAL_CHANGE: 4,
        MultimodalCandidateType.POSSIBLE_HOOK_CANDIDATE: 5,
        MultimodalCandidateType.POSSIBLE_REACTION_CANDIDATE: 6,
        MultimodalCandidateType.LOW_ACTIVITY_SEGMENT: 7,
        MultimodalCandidateType.SCENE_OPENING: 8,
        MultimodalCandidateType.SCENE_CLOSING: 9,
        MultimodalCandidateType.UNKNOWN_CANDIDATE: 10,
        MultimodalCandidateType.LONG_SILENCE_OR_PAUSE: 11,
    }
    return ranking.get(candidate_type, 99)


def merge_candidate_seeds(
    seeds: list[CandidateSeed],
    options: MultimodalAnalysisOptions,
) -> list[MultimodalMomentCandidateData]:
    if not seeds:
        return []
    ordered = sorted(seeds, key=lambda seed: (seed.start_seconds, seed.end_seconds, _cluster_priority(seed.candidate_type), -seed.score))
    clusters: list[list[CandidateSeed]] = []
    current: list[CandidateSeed] = [ordered[0]]
    for seed in ordered[1:]:
        previous = current[-1]
        gap = seed.start_seconds - previous.end_seconds
        if gap <= options.candidate_merge_gap_seconds and seed.start_seconds - current[0].start_seconds <= options.candidate_max_duration_seconds:
            current.append(seed)
        else:
            clusters.append(current)
            current = [seed]
    clusters.append(current)

    candidates: list[MultimodalMomentCandidateData] = []
    for index, cluster in enumerate(clusters):
        cluster_start = min(seed.start_seconds for seed in cluster)
        cluster_end = max(seed.end_seconds for seed in cluster)
        merged_types = sorted({seed.candidate_type.value for seed in cluster})
        primary = min(cluster, key=lambda seed: (_cluster_priority(seed.candidate_type), -seed.score, seed.start_seconds))
        score = max(seed.score for seed in cluster)
        confidence = max(seed.confidence for seed in cluster)
        summary = build_candidate_summary(primary.candidate_type.value, score, confidence, primary.evidence)
        evidence = {
            "primary_type": primary.candidate_type.value,
            "merged_types": merged_types,
            "seed_count": len(cluster),
            "seeds": [seed.evidence for seed in cluster],
        }
        candidates.append(
            MultimodalMomentCandidateData(
                candidate_index=index,
                start_seconds=cluster_start,
                end_seconds=cluster_end,
                candidate_type=primary.candidate_type,
                score=score,
                confidence=confidence,
                title=primary.candidate_type.value.replace("_", " ").title(),
                summary=summary,
                evidence=evidence,
                source_window_start=cluster[0].start_seconds,
                source_window_end=cluster[-1].end_seconds,
            )
        )
    return candidates

