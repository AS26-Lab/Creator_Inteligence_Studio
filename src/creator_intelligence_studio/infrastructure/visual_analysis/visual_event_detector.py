"""Deteccion de eventos visuales candidatos."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.domain.visual_analysis.value_objects import (
    VisualAnalysisOptions,
    VisualEventData,
    VisualEventType,
)

from .frame_metrics import VisualFrameMetrics
from .scene_detector import DetectedCut


def _confidence(base: float, modifier: float) -> float:
    return max(0.1, min(0.9, base + modifier))


def detect_visual_events(
    metrics: list[VisualFrameMetrics],
    cuts: list[DetectedCut],
    options: VisualAnalysisOptions,
) -> list[VisualEventData]:
    events: list[VisualEventData] = []
    event_index = 0
    for cut in cuts:
        events.append(
            VisualEventData(
                event_index=event_index,
                start_seconds=cut.start_seconds,
                end_seconds=cut.end_seconds,
                event_type=cut.cut_type,
                confidence=_confidence(0.45 if cut.cut_type == VisualEventType.GRADUAL_TRANSITION else 0.62, cut.score * 0.25),
                evidence={
                    **cut.evidence,
                    "cut_score": cut.score,
                    "source": "cut_detector",
                },
            )
        )
        event_index += 1

    if not metrics:
        return events

    brightness = np.array([metric.brightness for metric in metrics], dtype=np.float32)
    motion = np.array([metric.motion_score for metric in metrics], dtype=np.float32)
    deltas_brightness = np.abs(np.diff(np.r_[brightness[:1], brightness]))
    deltas_motion = np.abs(np.diff(np.r_[motion[:1], motion]))

    freeze_start = None
    for index, metric in enumerate(metrics):
        if metric.is_black:
            events.append(
                VisualEventData(
                    event_index=event_index,
                    start_seconds=metric.timestamp_seconds,
                    end_seconds=metric.timestamp_seconds,
                    event_type=VisualEventType.BLACK_FRAME_CANDIDATE,
                    confidence=_confidence(0.55, 0.2 if metric.brightness < options.black_brightness_threshold / 2 else 0.0),
                    evidence={
                        "brightness": metric.brightness,
                        "contrast": metric.contrast,
                        "label": metric.activity_label.value,
                    },
                )
            )
            event_index += 1
        if metric.brightness >= options.bright_brightness_threshold and deltas_brightness[index] >= 0.18:
            events.append(
                VisualEventData(
                    event_index=event_index,
                    start_seconds=metric.timestamp_seconds,
                    end_seconds=metric.timestamp_seconds,
                    event_type=VisualEventType.FLASH_CANDIDATE,
                    confidence=_confidence(0.4, min(0.35, deltas_brightness[index])),
                    evidence={
                        "brightness": metric.brightness,
                        "brightness_delta": float(deltas_brightness[index]),
                        "motion_score": metric.motion_score,
                    },
                )
            )
            event_index += 1
        if index > 0 and deltas_motion[index] >= 0.22:
            events.append(
                VisualEventData(
                    event_index=event_index,
                    start_seconds=metrics[index - 1].timestamp_seconds,
                    end_seconds=metric.timestamp_seconds,
                    event_type=VisualEventType.ABRUPT_MOTION_CHANGE,
                    confidence=_confidence(0.45, min(0.3, deltas_motion[index])),
                    evidence={
                        "motion_delta": float(deltas_motion[index]),
                        "previous_motion": float(motion[index - 1]),
                        "current_motion": float(motion[index]),
                    },
                )
            )
            event_index += 1
        if index > 0 and deltas_brightness[index] >= 0.18:
            events.append(
                VisualEventData(
                    event_index=event_index,
                    start_seconds=metrics[index - 1].timestamp_seconds,
                    end_seconds=metric.timestamp_seconds,
                    event_type=VisualEventType.ABRUPT_BRIGHTNESS_CHANGE,
                    confidence=_confidence(0.45, min(0.3, deltas_brightness[index])),
                    evidence={
                        "brightness_delta": float(deltas_brightness[index]),
                        "previous_brightness": float(brightness[index - 1]),
                        "current_brightness": float(brightness[index]),
                    },
                )
            )
            event_index += 1
        if metric.is_possible_freeze:
            if freeze_start is None:
                freeze_start = metric.timestamp_seconds
        else:
            if freeze_start is not None:
                events.append(
                    VisualEventData(
                        event_index=event_index,
                        start_seconds=freeze_start,
                        end_seconds=metric.timestamp_seconds,
                        event_type=VisualEventType.FREEZE_CANDIDATE,
                        confidence=_confidence(0.5, 0.15),
                        evidence={
                            "duration_seconds": float(metric.timestamp_seconds - freeze_start),
                            "motion_score": float(metric.motion_score),
                            "label": metric.activity_label.value,
                        },
                    )
                )
                event_index += 1
                freeze_start = None
    if freeze_start is not None:
        events.append(
            VisualEventData(
                event_index=event_index,
                start_seconds=freeze_start,
                end_seconds=metrics[-1].timestamp_seconds,
                event_type=VisualEventType.FREEZE_CANDIDATE,
                confidence=_confidence(0.5, 0.15),
                evidence={
                    "duration_seconds": float(metrics[-1].timestamp_seconds - freeze_start),
                    "motion_score": float(metrics[-1].motion_score),
                    "label": metrics[-1].activity_label.value,
                },
            )
        )
    return events
