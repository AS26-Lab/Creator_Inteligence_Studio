"""Metricas por frame para analisis visual."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.domain.visual_analysis.value_objects import (
    VisualActivityLabel,
)

from .frame_sampler import SampledFrame


@dataclass(frozen=True, slots=True)
class VisualFrameMetrics:
    """Metricas calculadas para un frame muestreado."""

    frame_index: int
    timestamp_seconds: float
    brightness: float
    contrast: float
    saturation: float
    motion_score: float
    color_change_score: float
    is_static: bool
    is_black: bool
    is_possible_freeze: bool
    activity_label: VisualActivityLabel


def _luma(frame: np.ndarray) -> np.ndarray:
    rgb = frame.astype(np.float32)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _histogram(luma: np.ndarray, bins: int = 16) -> np.ndarray:
    hist, _ = np.histogram(luma, bins=bins, range=(0.0, 255.0), density=False)
    hist = hist.astype(np.float32)
    total = float(hist.sum()) or 1.0
    return hist / total


def _chi_square(left: np.ndarray, right: np.ndarray) -> float:
    numerator = (left - right) ** 2
    denominator = left + right + 1e-6
    value = float(0.5 * np.sum(numerator / denominator))
    return min(1.0, value * 0.75)


def _label_for(*, brightness: float, motion: float, is_black: bool, is_freeze: bool) -> VisualActivityLabel:
    if is_black:
        return VisualActivityLabel.POSSIBLE_BLACK_FRAME
    if is_freeze:
        return VisualActivityLabel.POSSIBLE_FREEZE
    if motion < 0.03:
        if brightness < 0.18:
            return VisualActivityLabel.DARK
        if brightness > 0.82:
            return VisualActivityLabel.BRIGHT
        return VisualActivityLabel.STATIC
    if motion < 0.08:
        if brightness < 0.18:
            return VisualActivityLabel.DARK
        return VisualActivityLabel.LOW_MOTION
    if motion < 0.2:
        return VisualActivityLabel.MODERATE_MOTION
    return VisualActivityLabel.HIGH_MOTION


def compute_frame_metrics(frames: list[SampledFrame]) -> list[VisualFrameMetrics]:
    if not frames:
        return []
    metrics: list[VisualFrameMetrics] = []
    previous_luma: np.ndarray | None = None
    previous_hist: np.ndarray | None = None
    previous_motion = 0.0
    for frame in frames:
        luma = _luma(frame.rgb_frame)
        brightness = float(np.mean(luma) / 255.0)
        contrast = float(np.std(luma) / 255.0)
        rgb = frame.rgb_frame.astype(np.float32) / 255.0
        channel_max = np.max(rgb, axis=2)
        channel_min = np.min(rgb, axis=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            saturation_map = np.where(channel_max > 0, (channel_max - channel_min) / np.maximum(channel_max, 1e-6), 0.0)
        saturation = float(np.mean(saturation_map))
        hist = _histogram(luma)
        if previous_luma is None or previous_hist is None:
            motion_score = 0.0
            color_change_score = 0.0
        else:
            diff = float(np.mean(np.abs(luma - previous_luma)) / 255.0)
            brightness_delta = abs(brightness - metrics[-1].brightness)
            hist_delta = _chi_square(previous_hist, hist)
            motion_score = min(1.0, 0.65 * diff + 0.2 * hist_delta + 0.15 * brightness_delta)
            color_change_score = min(1.0, 0.7 * hist_delta + 0.3 * brightness_delta)
        is_black = brightness < 0.06 and contrast < 0.04
        is_possible_freeze = (
            not is_black
            and previous_luma is not None
            and motion_score < 0.018
            and previous_motion < 0.03
        )
        activity_label = _label_for(
            brightness=brightness,
            motion=motion_score,
            is_black=is_black,
            is_freeze=is_possible_freeze,
        )
        is_static = motion_score < 0.03 and not is_black
        metrics.append(
            VisualFrameMetrics(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
                motion_score=motion_score,
                color_change_score=color_change_score,
                is_static=is_static,
                is_black=is_black,
                is_possible_freeze=is_possible_freeze,
                activity_label=activity_label,
            )
        )
        previous_luma = luma
        previous_hist = hist
        previous_motion = motion_score
    return metrics
