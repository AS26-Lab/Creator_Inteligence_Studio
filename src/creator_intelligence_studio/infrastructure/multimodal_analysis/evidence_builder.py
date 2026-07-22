"""Construccion de evidencia tecnica multimodal."""

from __future__ import annotations

from typing import Iterable

from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalMomentCandidate, MultimodalTimelineWindow


def _join_non_empty(parts: Iterable[str]) -> str:
    return " | ".join(part for part in parts if part)


def build_window_evidence(window: dict[str, object]) -> dict[str, object]:
    return {
        "signals": {
            "speech_ratio": window.get("speech_ratio"),
            "silence_ratio": window.get("silence_ratio"),
            "speech_rate": window.get("speech_rate"),
            "acoustic_energy": window.get("acoustic_energy"),
            "acoustic_change": window.get("acoustic_change"),
            "visual_motion": window.get("visual_motion"),
            "visual_change": window.get("visual_change"),
            "brightness": window.get("brightness"),
            "cut_count": window.get("cut_count"),
            "scene_index": window.get("scene_index"),
            "acoustic_event_count": window.get("acoustic_event_count"),
            "visual_event_count": window.get("visual_event_count"),
        },
        "scores": {
            "combined_activity_score": window.get("combined_activity_score"),
            "transition_score": window.get("transition_score"),
            "novelty_score": window.get("novelty_score"),
            "confidence": window.get("confidence"),
        },
        "transcript_text": window.get("transcript_text") or "",
    }


def build_candidate_summary(candidate_type: str, score: float, confidence: float, evidence: dict[str, object]) -> str:
    signals = evidence.get("signals", {})
    parts = [
        candidate_type,
        f"score={score:.3f}",
        f"confidence={confidence:.3f}",
    ]
    if signals.get("cut_count"):
        parts.append(f"cuts={signals['cut_count']}")
    if signals.get("speech_ratio") is not None:
        parts.append(f"speech={float(signals['speech_ratio']):.3f}")
    if signals.get("visual_motion") is not None:
        parts.append(f"motion={float(signals['visual_motion']):.3f}")
    if signals.get("acoustic_energy") is not None:
        parts.append(f"energy={float(signals['acoustic_energy']):.3f}")
    transcript = evidence.get("transcript_text")
    if transcript:
        parts.append(f"text={str(transcript)[:80]}")
    return _join_non_empty(parts)


def build_candidate_evidence(
    *,
    windows: list[MultimodalTimelineWindow],
    candidate_type: str,
    merged_types: list[str],
    source_window_start: float | None,
    source_window_end: float | None,
) -> dict[str, object]:
    return {
        "candidate_type": candidate_type,
        "merged_types": merged_types,
        "source_window_start": source_window_start,
        "source_window_end": source_window_end,
        "window_count": len(windows),
        "window_indexes": [window.window_index for window in windows],
        "signals": [window.evidence_json for window in windows],
    }

