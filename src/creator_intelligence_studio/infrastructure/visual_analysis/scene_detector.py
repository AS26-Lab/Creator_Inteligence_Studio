"""Deteccion tecnica de cortes y escenas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.domain.visual_analysis.value_objects import (
    VisualActivityLabel,
    VisualAnalysisOptions,
    VisualEventData,
    VisualEventType,
    VisualSceneData,
)

from .frame_metrics import VisualFrameMetrics


@dataclass(frozen=True, slots=True)
class DetectedCut:
    """Corte o transicion candidata."""

    frame_index: int
    start_seconds: float
    end_seconds: float
    score: float
    cut_type: VisualEventType
    evidence: dict[str, object]


@dataclass(frozen=True, slots=True)
class DetectedScene:
    """Escena tecnica derivada de cortes."""

    scene_index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    representative_timestamp_seconds: float
    cut_in_score: float
    average_motion: float
    average_brightness: float
    average_contrast: float


def _cut_score(previous: VisualFrameMetrics, current: VisualFrameMetrics) -> float:
    brightness_delta = abs(current.brightness - previous.brightness)
    motion = current.motion_score
    color = current.color_change_score
    score = min(1.0, 0.6 * motion + 0.25 * color + 0.15 * brightness_delta)
    return score


def detect_cut_candidates(
    metrics: list[VisualFrameMetrics],
    options: VisualAnalysisOptions,
) -> list[DetectedCut]:
    if len(metrics) < 2:
        return []
    candidates: list[DetectedCut] = []
    deltas = [_cut_score(metrics[index - 1], metrics[index]) for index in range(1, len(metrics))]
    for index, score in enumerate(deltas, start=1):
        previous = metrics[index - 1]
        current = metrics[index]
        if score < options.cut_threshold:
            continue
        if index > 1 and score < deltas[index - 2]:
            continue
        if index < len(deltas) and score < deltas[index]:
            continue
        cut_type = VisualEventType.GRADUAL_TRANSITION
        if score >= options.hard_cut_threshold:
            cut_type = VisualEventType.HARD_CUT
        elif score >= options.cut_threshold * 1.15 and abs(current.brightness - previous.brightness) >= 0.12:
            cut_type = VisualEventType.HARD_CUT
        candidates.append(
            DetectedCut(
                frame_index=index,
                start_seconds=previous.timestamp_seconds,
                end_seconds=current.timestamp_seconds,
                score=score,
                cut_type=cut_type,
                evidence={
                    "motion_score": current.motion_score,
                    "color_change_score": current.color_change_score,
                    "brightness_delta": abs(current.brightness - previous.brightness),
                    "previous_brightness": previous.brightness,
                    "current_brightness": current.brightness,
                },
            )
        )
    return candidates


def build_scenes(
    metrics: list[VisualFrameMetrics],
    cuts: list[DetectedCut],
    *,
    duration_seconds: float,
    min_scene_duration_seconds: float,
) -> list[DetectedScene]:
    if not metrics:
        return []
    boundaries = [0.0]
    for cut in cuts:
        if cut.cut_type == VisualEventType.GRADUAL_TRANSITION and cut.score < 0.45:
            continue
        if cut.start_seconds - boundaries[-1] < min_scene_duration_seconds:
            continue
        boundaries.append(max(cut.start_seconds, boundaries[-1]))
    if boundaries[-1] < duration_seconds:
        boundaries.append(duration_seconds)
    scenes: list[DetectedScene] = []
    scene_index = 0
    for start_seconds, end_seconds in zip(boundaries, boundaries[1:]):
        if end_seconds <= start_seconds:
            continue
        scene_metrics = [metric for metric in metrics if start_seconds <= metric.timestamp_seconds < end_seconds]
        if not scene_metrics:
            continue
        representative = max(scene_metrics, key=lambda metric: (metric.contrast + metric.motion_score * 0.5, -metric.timestamp_seconds))
        scenes.append(
            DetectedScene(
                scene_index=scene_index,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                duration_seconds=end_seconds - start_seconds,
                representative_timestamp_seconds=representative.timestamp_seconds,
                cut_in_score=max((cut.score for cut in cuts if start_seconds <= cut.start_seconds < end_seconds), default=0.0),
                average_motion=float(np.mean([metric.motion_score for metric in scene_metrics])),
                average_brightness=float(np.mean([metric.brightness for metric in scene_metrics])),
                average_contrast=float(np.mean([metric.contrast for metric in scene_metrics])),
            )
        )
        scene_index += 1
    if not scenes:
        scenes.append(
            DetectedScene(
                scene_index=0,
                start_seconds=0.0,
                end_seconds=duration_seconds,
                duration_seconds=duration_seconds,
                representative_timestamp_seconds=metrics[len(metrics) // 2].timestamp_seconds,
                cut_in_score=0.0,
                average_motion=float(np.mean([metric.motion_score for metric in metrics])),
                average_brightness=float(np.mean([metric.brightness for metric in metrics])),
                average_contrast=float(np.mean([metric.contrast for metric in metrics])),
            )
        )
    return scenes
