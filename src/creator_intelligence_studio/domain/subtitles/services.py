"""Reglas de dominio para subtitulos."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, replace
from typing import Any

from creator_intelligence_studio.domain.clip_ranking.entities import RankedClipCandidate
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment
from creator_intelligence_studio.shared.dates import to_iso_z

from .errors import SubtitleValidationError
from .value_objects import (
    SubtitleCueDraft,
    SubtitleCueValidationStatus,
    SubtitleGenerationOptions,
    SubtitleSourceType,
    SubtitleTimingSource,
    SubtitleTrackStatus,
    normalize_generation_options,
)

_WHITESPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")
_BREAK_SENTENCE = re.compile(r"(?<=[.!?…。])\s+")


def normalize_subtitle_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n")]
    normalized = " ".join(part for part in lines if part)
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = _SPACE_BEFORE_PUNCT.sub(r"\1", normalized)
    return normalized.strip()


def wrap_subtitle_text(text: str, *, max_lines: int, max_chars_per_line: int) -> tuple[str, ...]:
    normalized = normalize_subtitle_text(text)
    if not normalized:
        return ()
    words = normalized.split(" ")
    if len(words) == 1:
        return (normalized,)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars_per_line:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    if len(lines) <= max_lines:
        return tuple(lines)
    merged = " ".join(lines)
    midpoint = max(1, len(merged) // 2)
    left = merged[:midpoint].rsplit(" ", 1)[0] if " " in merged[:midpoint] else merged[:midpoint]
    right = merged[len(left):].strip()
    wrapped = [part.strip() for part in (left, right) if part.strip()]
    return tuple(wrapped[:max_lines]) if wrapped else (merged[:max_chars_per_line],)


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_subtitle_configuration_fingerprint(options: SubtitleGenerationOptions) -> str:
    return _fingerprint_payload({"options": options.to_dict()})


def build_subtitle_source_fingerprint(
    transcription: Transcription,
    *,
    candidate: RankedClipCandidate | None = None,
    render_job_id: str | None = None,
    source_type: SubtitleSourceType,
    source_start_seconds: float = 0.0,
    source_end_seconds: float | None = None,
) -> str:
    payload: dict[str, Any] = {
        "transcription_id": transcription.id,
        "video_asset_id": transcription.video_asset_id,
        "transcription_configuration_fingerprint": transcription.configuration_fingerprint,
        "transcription_updated_at": to_iso_z(transcription.updated_at),
        "source_type": source_type.value,
        "source_start_seconds": round(source_start_seconds, 6),
        "source_end_seconds": round(source_end_seconds if source_end_seconds is not None else transcription.duration_seconds, 6),
    }
    if candidate is not None:
        payload.update(
            {
                "candidate_id": candidate.id,
                "candidate_multimodal_id": candidate.multimodal_candidate_id,
                "candidate_review_status": candidate.review_status.value,
                "candidate_adjusted_start_seconds": candidate.adjusted_start_seconds,
                "candidate_adjusted_end_seconds": candidate.adjusted_end_seconds,
                "candidate_rank_score": candidate.rank_score,
            }
        )
    if render_job_id is not None:
        payload["render_job_id"] = render_job_id
    return _fingerprint_payload(payload)


def validate_subtitle_bounds(start_seconds: float, end_seconds: float, duration_seconds: float | None) -> None:
    if start_seconds < 0:
        raise SubtitleValidationError("El inicio del subtitulo no puede ser negativo.")
    if end_seconds <= start_seconds:
        raise SubtitleValidationError("El fin del subtitulo debe ser mayor que el inicio.")
    if duration_seconds is not None and end_seconds > duration_seconds + 0.05:
        raise SubtitleValidationError("El subtitulo excede la duracion disponible.")


def validate_subtitle_cue(
    cue: SubtitleCueDraft,
    *,
    options: SubtitleGenerationOptions,
    source_duration_seconds: float | None = None,
    previous_end_seconds: float | None = None,
) -> tuple[SubtitleCueValidationStatus, tuple[str, ...]]:
    warnings: list[str] = list(cue.warning_codes)
    status = SubtitleCueValidationStatus.VALID
    text = normalize_subtitle_text(cue.text)
    if not text:
        warnings.append("empty_text")
        return SubtitleCueValidationStatus.INVALID, tuple(dict.fromkeys(warnings))
    if len(wrap_subtitle_text(text, max_lines=options.max_lines, max_chars_per_line=options.max_chars_per_line)) > options.max_lines:
        warnings.append("too_many_lines")
        status = SubtitleCueValidationStatus.INVALID
    if any(len(line) > options.max_chars_per_line for line in wrap_subtitle_text(text, max_lines=options.max_lines, max_chars_per_line=options.max_chars_per_line)):
        warnings.append("too_many_characters")
        status = SubtitleCueValidationStatus.INVALID
    duration = cue.end_seconds - cue.start_seconds
    if cue.start_seconds < 0 or cue.end_seconds <= cue.start_seconds:
        warnings.append("out_of_bounds")
        status = SubtitleCueValidationStatus.INVALID
    if source_duration_seconds is not None and cue.end_seconds > source_duration_seconds + 0.05:
        warnings.append("out_of_bounds")
        status = SubtitleCueValidationStatus.INVALID
    if previous_end_seconds is not None and cue.start_seconds < previous_end_seconds - 0.001:
        warnings.append("overlap")
        status = SubtitleCueValidationStatus.INVALID
    if duration < options.min_duration_seconds:
        warnings.append("too_short")
        status = SubtitleCueValidationStatus.WARNING if status != SubtitleCueValidationStatus.INVALID else status
    if duration > options.max_duration_seconds:
        warnings.append("too_long")
        status = SubtitleCueValidationStatus.WARNING if status != SubtitleCueValidationStatus.INVALID else status
    cps = len(text) / duration if duration > 0 else float("inf")
    if cps > options.cps_warning_threshold:
        warnings.append("high_cps")
        status = SubtitleCueValidationStatus.WARNING if status != SubtitleCueValidationStatus.INVALID else status
    return status, tuple(dict.fromkeys(warnings))


def validate_subtitle_track(track) -> None:
    if track.source_end_seconds <= track.source_start_seconds:
        raise SubtitleValidationError("source_end_seconds debe ser mayor que source_start_seconds.")
    if track.track_version <= 0:
        raise SubtitleValidationError("track_version debe ser mayor que cero.")
    if not track.language.strip():
        raise SubtitleValidationError("language no puede estar vacio.")
    if not track.name.strip():
        raise SubtitleValidationError("name no puede estar vacio.")


def is_subtitle_track_stale(
    track,
    *,
    current_source_fingerprint: str,
    current_configuration_fingerprint: str,
    current_source_start_seconds: float,
    current_source_end_seconds: float,
) -> bool:
    return (
        track.source_fingerprint != current_source_fingerprint
        or track.configuration_fingerprint != current_configuration_fingerprint
        or abs(track.source_start_seconds - current_source_start_seconds) > 0.001
        or abs(track.source_end_seconds - current_source_end_seconds) > 0.001
        or track.status == SubtitleTrackStatus.STALE
    )

