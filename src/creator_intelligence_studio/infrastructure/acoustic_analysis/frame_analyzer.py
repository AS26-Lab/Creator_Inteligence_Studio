"""Analisis de frames acusticos deterministas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class AcousticFrameMetrics:
    """Metricas calculadas por frame corto."""

    frame_index: int
    start_seconds: float
    end_seconds: float
    rms_energy: float
    peak_amplitude: float
    zero_crossing_rate: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def analyze_frames(
    samples: np.ndarray,
    *,
    sample_rate_hz: int,
    frame_duration_ms: int = 25,
    hop_duration_ms: int = 10,
) -> list[AcousticFrameMetrics]:
    if samples.size == 0:
        return []
    frame_size = max(1, int(sample_rate_hz * frame_duration_ms / 1000))
    hop_size = max(1, int(sample_rate_hz * hop_duration_ms / 1000))
    if frame_size > samples.size:
        frame_size = samples.size
    frame_metrics: list[AcousticFrameMetrics] = []
    frame_index = 0
    for start in range(0, samples.size, hop_size):
        end = min(start + frame_size, samples.size)
        if end <= start:
            break
        frame = samples[start:end]
        rms = float(np.sqrt(np.mean(frame * frame))) if frame.size else 0.0
        peak = float(np.max(np.abs(frame))) if frame.size else 0.0
        if frame.size > 1:
            zero_crossings = np.count_nonzero(np.diff(np.signbit(frame)))
            zcr = float(zero_crossings / (frame.size - 1))
        else:
            zcr = 0.0
        frame_metrics.append(
            AcousticFrameMetrics(
                frame_index=frame_index,
                start_seconds=start / sample_rate_hz,
                end_seconds=end / sample_rate_hz,
                rms_energy=rms,
                peak_amplitude=peak,
                zero_crossing_rate=zcr,
            )
        )
        frame_index += 1
        if end == samples.size:
            break
    return frame_metrics
