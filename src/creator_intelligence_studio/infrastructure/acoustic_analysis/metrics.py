"""Metricas globales y agregacion para analisis acustico."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

import numpy as np

from creator_intelligence_studio.domain.acoustic_analysis.value_objects import (
    AcousticActivityLabel,
    AcousticEventData,
    AcousticEventType,
    AcousticTimelineWindowData,
)
from creator_intelligence_studio.domain.transcription.entities import TranscriptionSegment
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionSegmentData

from .frame_analyzer import AcousticFrameMetrics
from .voice_activity_detector import classify_activity_label, VoiceActivityResult


@dataclass(frozen=True, slots=True)
class PauseSummary:
    pause_count: int
    average_pause_seconds: float | None
    median_pause_seconds: float | None
    longest_pause_seconds: float | None
    short_pause_count: int
    medium_pause_count: int
    long_pause_count: int
    pauses: tuple[tuple[float, float, float], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "pause_count": self.pause_count,
            "average_pause_seconds": self.average_pause_seconds,
            "median_pause_seconds": self.median_pause_seconds,
            "longest_pause_seconds": self.longest_pause_seconds,
            "short_pause_count": self.short_pause_count,
            "medium_pause_count": self.medium_pause_count,
            "long_pause_count": self.long_pause_count,
            "pauses": [
                {"start_seconds": start, "end_seconds": end, "duration_seconds": duration}
                for start, end, duration in self.pauses
            ],
        }


def _segment_word_count(segment: TranscriptionSegment | TranscriptionSegmentData) -> int:
    return len(re.findall(r"\b[\w']+\b", segment.text, flags=re.UNICODE))


def extract_transcript_windows(
    segments: list[TranscriptionSegment] | list[TranscriptionSegmentData] | tuple[TranscriptionSegment, ...] | tuple[TranscriptionSegmentData, ...] | None,
) -> list[tuple[float, float, int]]:
    if not segments:
        return []
    windows: list[tuple[float, float, int]] = []
    for segment in segments:
        count = _segment_word_count(segment)
        windows.append((float(segment.start_seconds), float(segment.end_seconds), count))
    return windows


def aggregate_windows(
    frames: list[AcousticFrameMetrics],
    activity: VoiceActivityResult,
    *,
    sample_rate_hz: int,
    total_duration_seconds: float,
    window_duration_seconds: float = 1.0,
    rhythm_window_seconds: float = 5.0,
    transcript_segments: list[TranscriptionSegment] | list[TranscriptionSegmentData] | None = None,
) -> list[AcousticTimelineWindowData]:
    if not frames:
        return []
    transcript_windows = extract_transcript_windows(transcript_segments)
    windows: list[AcousticTimelineWindowData] = []
    total_windows = max(1, int(np.ceil(total_duration_seconds / window_duration_seconds)))
    frame_duration = frames[0].duration_seconds
    rhythm_span = max(1, int(round(rhythm_window_seconds / frame_duration)))
    for window_index in range(total_windows):
        start_seconds = window_index * window_duration_seconds
        end_seconds = min(total_duration_seconds, start_seconds + window_duration_seconds)
        window_frames = [
            (frame, idx)
            for idx, frame in enumerate(frames)
            if frame.start_seconds < end_seconds and frame.end_seconds > start_seconds
        ]
        if window_frames:
            frame_values = [frame for frame, _ in window_frames]
            avg_rms = float(np.mean([frame.rms_energy for frame in frame_values]))
            peak = float(np.max([frame.peak_amplitude for frame in frame_values]))
            normalized_energy = float(np.mean([frame.rms_energy for frame in frame_values]))
            max_energy = max(float(np.max([frame.rms_energy for frame in frames])), 1e-6)
            normalized_energy = min(1.0, normalized_energy / max_energy)
            zcr = float(np.mean([frame.zero_crossing_rate for frame in frame_values]))
            probs = np.array([activity.speech_probability[idx] for _, idx in window_frames], dtype=np.float32)
            speech_probability = float(np.mean(probs)) if probs.size else 0.0
            is_speech = bool(np.mean(activity.is_speech[[idx for _, idx in window_frames]]) >= 0.5)
        else:
            avg_rms = 0.0
            peak = 0.0
            normalized_energy = 0.0
            zcr = 0.0
            speech_probability = 0.0
            is_speech = False
        word_count = 0
        if transcript_windows:
            for seg_start, seg_end, count in transcript_windows:
                overlap = max(0.0, min(end_seconds, seg_end) - max(start_seconds, seg_start))
                if overlap <= 0:
                    continue
                segment_duration = max(1e-6, seg_end - seg_start)
                word_count += int(round(count * (overlap / segment_duration)))
        speech_rate_estimate = (word_count / window_duration_seconds) * 60.0 if word_count else None
        pause_duration = window_duration_seconds if not is_speech else 0.0
        windows.append(
            AcousticTimelineWindowData(
                window_index=window_index,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                speech_probability=speech_probability,
                is_speech=is_speech,
                rms_energy=avg_rms,
                peak_amplitude=peak,
                normalized_energy=normalized_energy,
                zero_crossing_rate=zcr,
                speech_rate_estimate=speech_rate_estimate,
                word_count=word_count,
                pause_duration_seconds=pause_duration,
                activity_label=classify_activity_label(
                    speech_probability=speech_probability,
                    normalized_energy=normalized_energy,
                    is_speech=is_speech,
                ),
            )
        )
    return windows


def summarize_pauses(
    windows: list[AcousticTimelineWindowData],
    *,
    pause_micro_max_seconds: float,
    pause_short_max_seconds: float,
    pause_medium_max_seconds: float,
) -> PauseSummary:
    pauses: list[tuple[float, float, float]] = []
    start = None
    for window in windows:
        if window.is_speech:
            if start is not None:
                duration = window.start_seconds - start
                if duration > 0:
                    pauses.append((start, window.start_seconds, duration))
                start = None
            continue
        if start is None:
            start = window.start_seconds
    if start is not None and windows:
        end = windows[-1].end_seconds
        duration = max(0.0, end - start)
        if duration > 0:
            pauses.append((start, end, duration))

    durations = np.array([pause[2] for pause in pauses], dtype=np.float32)
    average = float(np.mean(durations)) if durations.size else None
    median = float(np.median(durations)) if durations.size else None
    longest = float(np.max(durations)) if durations.size else None
    short = int(np.sum((durations > pause_micro_max_seconds) & (durations <= pause_short_max_seconds))) if durations.size else 0
    medium = int(np.sum((durations > pause_short_max_seconds) & (durations <= pause_medium_max_seconds))) if durations.size else 0
    long = int(np.sum(durations > pause_medium_max_seconds)) if durations.size else 0
    return PauseSummary(
        pause_count=len(pauses),
        average_pause_seconds=average,
        median_pause_seconds=median,
        longest_pause_seconds=longest,
        short_pause_count=short,
        medium_pause_count=medium,
        long_pause_count=long,
        pauses=tuple(pauses),
    )


def detect_events(
    windows: list[AcousticTimelineWindowData],
    *,
    pause_summary: PauseSummary,
    transcript_segments: list[TranscriptionSegment] | list[TranscriptionSegmentData] | None = None,
) -> list[AcousticEventData]:
    events: list[AcousticEventData] = []
    if not windows:
        return events
    energies = np.array([window.normalized_energy for window in windows], dtype=np.float32)
    zcr = np.array([window.zero_crossing_rate for window in windows], dtype=np.float32)
    speech_probs = np.array([window.speech_probability for window in windows], dtype=np.float32)
    deltas = np.abs(np.diff(np.r_[energies[:1], energies]))
    transcript_windows = extract_transcript_windows(transcript_segments)
    event_index = 0
    for pause_start, pause_end, duration in pause_summary.pauses:
        if duration >= 2.0:
            events.append(
                AcousticEventData(
                    event_index=event_index,
                    start_seconds=pause_start,
                    end_seconds=pause_end,
                    event_type=AcousticEventType.LONG_SILENCE,
                    confidence=min(0.8, 0.45 + min(0.4, duration / 8.0)),
                    evidence={
                        "duration_seconds": duration,
                        "threshold_seconds": 2.0,
                        "source": "pause_summary",
                    },
                )
            )
            event_index += 1
    for idx, window in enumerate(windows):
        if deltas[idx] >= 0.35:
            events.append(
                AcousticEventData(
                    event_index=event_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    event_type=AcousticEventType.ABRUPT_ENERGY_CHANGE,
                    confidence=min(0.75, 0.35 + float(deltas[idx])),
                    evidence={
                        "energy_delta": float(deltas[idx]),
                        "normalized_energy": window.normalized_energy,
                        "speech_probability": window.speech_probability,
                        "previous_energy": float(energies[idx - 1]) if idx > 0 else None,
                    },
                )
            )
            event_index += 1
        if window.peak_amplitude >= 0.88 and window.normalized_energy >= 0.55:
            events.append(
                AcousticEventData(
                    event_index=event_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    event_type=AcousticEventType.TRANSIENT_PEAK,
                    confidence=min(0.8, 0.5 + window.peak_amplitude * 0.35),
                    evidence={
                        "peak_amplitude": window.peak_amplitude,
                        "normalized_energy": window.normalized_energy,
                        "zero_crossing_rate": window.zero_crossing_rate,
                    },
                )
            )
            event_index += 1
        if not window.is_speech and window.normalized_energy >= 0.25 and window.zero_crossing_rate >= 0.12:
            events.append(
                AcousticEventData(
                    event_index=event_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    event_type=AcousticEventType.SUSTAINED_NON_SPEECH,
                    confidence=min(0.7, 0.3 + window.normalized_energy * 0.5),
                    evidence={
                        "normalized_energy": window.normalized_energy,
                        "zero_crossing_rate": window.zero_crossing_rate,
                        "speech_probability": window.speech_probability,
                    },
                )
            )
            event_index += 1
        if (
            not window.is_speech
            and window.normalized_energy >= 0.18
            and window.normalized_energy <= 0.7
            and window.zero_crossing_rate >= 0.18
            and window.speech_probability < 0.55
        ):
            events.append(
                AcousticEventData(
                    event_index=event_index,
                    start_seconds=window.start_seconds,
                    end_seconds=window.end_seconds,
                    event_type=AcousticEventType.LAUGHTER_CANDIDATE,
                    confidence=min(0.65, 0.25 + float(window.zero_crossing_rate)),
                    evidence={
                        "normalized_energy": window.normalized_energy,
                        "zero_crossing_rate": window.zero_crossing_rate,
                        "speech_probability": window.speech_probability,
                    },
                )
            )
            event_index += 1
    if transcript_windows:
        speech_windows = [window for window in windows if window.is_speech]
        if speech_windows:
            speech_ratio = len(speech_windows) / len(windows)
            if speech_ratio < 0.3 and np.max(speech_probs) < 0.5:
                events.append(
                    AcousticEventData(
                        event_index=event_index,
                        start_seconds=windows[0].start_seconds,
                        end_seconds=windows[-1].end_seconds,
                        event_type=AcousticEventType.SUSTAINED_NON_SPEECH,
                        confidence=0.4,
                        evidence={
                            "speech_ratio": speech_ratio,
                            "max_speech_probability": float(np.max(speech_probs)),
                            "source": "global_window_balance",
                        },
                    )
                )
    return events


def compute_global_metrics(
    windows: list[AcousticTimelineWindowData],
    *,
    total_duration_seconds: float,
    pause_summary: PauseSummary,
    transcript_segments: list[TranscriptionSegment] | list[TranscriptionSegmentData] | None = None,
) -> dict[str, float | None]:
    if not windows:
        return {
            "speech_duration_seconds": 0.0,
            "silence_duration_seconds": total_duration_seconds,
            "speech_ratio": 0.0,
            "silence_ratio": 1.0,
            "words_per_minute": None,
            "voiced_words_per_minute": None,
            "average_energy": 0.0,
            "peak_energy": 0.0,
            "dynamic_range": 0.0,
        }
    speech_windows = [window for window in windows if window.is_speech]
    speech_duration_seconds = float(sum(window.end_seconds - window.start_seconds for window in speech_windows))
    silence_duration_seconds = max(0.0, total_duration_seconds - speech_duration_seconds)
    speech_ratio = speech_duration_seconds / total_duration_seconds if total_duration_seconds else 0.0
    silence_ratio = 1.0 - speech_ratio if total_duration_seconds else 0.0
    energies = np.array([window.normalized_energy for window in windows], dtype=np.float32)
    average_energy = float(np.mean(energies)) if energies.size else 0.0
    peak_energy = float(np.max(energies)) if energies.size else 0.0
    if energies.size:
        low = float(np.percentile(energies, 5))
        high = float(np.percentile(energies, 95))
        dynamic_range = max(0.0, high - low)
    else:
        dynamic_range = 0.0
    word_count = 0
    if transcript_segments:
        for segment in transcript_segments:
            word_count += _segment_word_count(segment)
    words_per_minute = (word_count / total_duration_seconds) * 60.0 if word_count and total_duration_seconds else None
    voiced_words_per_minute = (word_count / speech_duration_seconds) * 60.0 if word_count and speech_duration_seconds else None
    return {
        "speech_duration_seconds": speech_duration_seconds,
        "silence_duration_seconds": silence_duration_seconds,
        "speech_ratio": speech_ratio,
        "silence_ratio": silence_ratio,
        "words_per_minute": words_per_minute,
        "voiced_words_per_minute": voiced_words_per_minute,
        "average_energy": average_energy,
        "peak_energy": peak_energy,
        "dynamic_range": dynamic_range,
    }
