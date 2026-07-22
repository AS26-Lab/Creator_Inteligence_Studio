"""Detector heuristico de voz y silencio."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticActivityLabel, AcousticTimelineWindowData

from .frame_analyzer import AcousticFrameMetrics


@dataclass(frozen=True, slots=True)
class VoiceActivityResult:
    """Resultado de actividad de voz por frame."""

    speech_probability: np.ndarray
    is_speech: np.ndarray
    noise_floor: float
    speech_threshold: float


def detect_voice_activity(
    frames: list[AcousticFrameMetrics],
    *,
    transcript_windows: list[tuple[float, float]] | None = None,
    minimum_speech_seconds: float = 0.2,
    speech_energy_multiplier: float = 2.5,
    silence_energy_multiplier: float = 1.2,
) -> VoiceActivityResult:
    if not frames:
        empty = np.array([], dtype=np.float32)
        return VoiceActivityResult(empty, empty.astype(bool), 0.0, 0.0)

    rms_values = np.array([frame.rms_energy for frame in frames], dtype=np.float32)
    peak_values = np.array([frame.peak_amplitude for frame in frames], dtype=np.float32)
    zcr_values = np.array([frame.zero_crossing_rate for frame in frames], dtype=np.float32)
    low_slice = rms_values[np.argsort(rms_values)[: max(1, int(len(rms_values) * 0.2))]]
    noise_floor = float(np.median(low_slice)) if low_slice.size else 0.0
    quiet_reference = float(np.percentile(rms_values, 70)) if rms_values.size else 0.0
    speech_threshold = max(noise_floor * speech_energy_multiplier, quiet_reference * 0.25, 1e-6)
    silence_threshold = max(noise_floor * silence_energy_multiplier, 1e-6)
    peak_reference = float(np.percentile(peak_values, 90)) if peak_values.size else 0.0

    speech_probability = np.zeros(len(frames), dtype=np.float32)
    for index, frame in enumerate(frames):
        energy_score = 0.0
        if frame.rms_energy > speech_threshold:
            energy_score = min(1.0, (frame.rms_energy - speech_threshold) / max(1e-6, peak_reference - speech_threshold))
        zcr_penalty = 1.0 - min(1.0, frame.zero_crossing_rate * 2.2)
        peak_score = min(1.0, frame.peak_amplitude / max(1e-6, peak_reference or frame.peak_amplitude or 1.0))
        probability = 0.55 * energy_score + 0.25 * peak_score + 0.2 * max(0.0, zcr_penalty)
        if frame.rms_energy <= silence_threshold:
            probability *= 0.2
        if transcript_windows:
            overlap = any(frame.start_seconds < end and frame.end_seconds > start for start, end in transcript_windows)
            if overlap:
                probability = min(1.0, probability + 0.25)
        speech_probability[index] = float(np.clip(probability, 0.0, 1.0))

    smoothed = _smooth_probability(speech_probability, minimum_speech_seconds, frames)
    is_speech = smoothed >= 0.5
    if transcript_windows:
        for index, frame in enumerate(frames):
            overlap = any(frame.start_seconds < end and frame.end_seconds > start for start, end in transcript_windows)
            if overlap:
                is_speech[index] = True
                smoothed[index] = max(smoothed[index], 0.65)
    return VoiceActivityResult(smoothed.astype(np.float32), is_speech.astype(bool), noise_floor, speech_threshold)


def _smooth_probability(
    probability: np.ndarray,
    minimum_speech_seconds: float,
    frames: list[AcousticFrameMetrics],
) -> np.ndarray:
    if probability.size == 0:
        return probability
    frame_duration = max(1e-6, frames[0].duration_seconds)
    window = max(1, int(round(minimum_speech_seconds / frame_duration)))
    if window <= 1:
        return probability
    kernel = np.ones(window, dtype=np.float32) / float(window)
    padded = np.pad(probability, (window // 2, window - 1 - window // 2), mode="edge")
    smoothed = np.convolve(padded, kernel, mode="valid")
    return np.asarray(smoothed, dtype=np.float32)


def classify_activity_label(*, speech_probability: float, normalized_energy: float, is_speech: bool) -> AcousticActivityLabel:
    if speech_probability < 0.12 and normalized_energy < 0.08:
        return AcousticActivityLabel.SILENCE
    if speech_probability < 0.28 and normalized_energy < 0.22:
        return AcousticActivityLabel.LOW_ACTIVITY
    if is_speech and normalized_energy < 0.28:
        return AcousticActivityLabel.SPEECH_LOW
    if is_speech and normalized_energy < 0.62:
        return AcousticActivityLabel.SPEECH_NORMAL
    if is_speech:
        return AcousticActivityLabel.SPEECH_HIGH
    if normalized_energy >= 0.22:
        return AcousticActivityLabel.NON_SPEECH_ACTIVITY
    return AcousticActivityLabel.UNKNOWN
