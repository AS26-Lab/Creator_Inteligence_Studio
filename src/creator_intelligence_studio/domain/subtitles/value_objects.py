"""Objetos de valor para subtitulos locales."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import SubtitleValidationError


class SubtitleTrackStatus(str, Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    EDITING = "editing"
    LOCKED = "locked"
    STALE = "stale"
    FAILED = "failed"
    IMPORTED = "imported"
    ARCHIVED = "archived"


class SubtitleCueValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


class SubtitleSourceType(str, Enum):
    TRANSCRIPTION_GENERATED = "transcription_generated"
    CLIP_GENERATED = "clip_generated"
    IMPORTED_SRT = "imported_srt"
    IMPORTED_VTT = "imported_vtt"
    IMPORTED_ASS = "imported_ass"
    MANUAL = "manual"


class SubtitleTimingSource(str, Enum):
    SEGMENT_EXACT = "segment_exact"
    WORD_TIMESTAMP = "word_timestamp"
    PROPORTIONAL_ESTIMATE = "proportional_estimate"
    MANUAL = "manual"


class SubtitleExportFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    TXT = "txt"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class SubtitleGenerationOptions:
    language: str = "es"
    max_lines: int = 2
    max_chars_per_line: int = 42
    max_chars_per_cue: int = 84
    min_duration_seconds: float = 0.8
    recommended_min_duration_seconds: float = 1.2
    recommended_max_duration_seconds: float = 6.0
    max_duration_seconds: float = 7.0
    min_gap_seconds: float = 0.05
    cps_warning_threshold: float = 22.0
    cps_recommended_min: float = 12.0
    cps_recommended_max: float = 20.0
    generator_version: str = "v1"
    export_format: SubtitleExportFormat = SubtitleExportFormat.SRT

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "max_lines": self.max_lines,
            "max_chars_per_line": self.max_chars_per_line,
            "max_chars_per_cue": self.max_chars_per_cue,
            "min_duration_seconds": self.min_duration_seconds,
            "recommended_min_duration_seconds": self.recommended_min_duration_seconds,
            "recommended_max_duration_seconds": self.recommended_max_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "min_gap_seconds": self.min_gap_seconds,
            "cps_warning_threshold": self.cps_warning_threshold,
            "cps_recommended_min": self.cps_recommended_min,
            "cps_recommended_max": self.cps_recommended_max,
            "generator_version": self.generator_version,
            "export_format": self.export_format.value,
        }


@dataclass(frozen=True, slots=True)
class SubtitleCueDraft:
    start_seconds: float
    end_seconds: float
    text: str
    original_text: str
    source_segment_ids: tuple[str, ...]
    timing_source: SubtitleTimingSource
    absolute_start_seconds: float
    absolute_end_seconds: float
    speaker_label: str | None = None
    warning_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "original_text": self.original_text,
            "source_segment_ids": list(self.source_segment_ids),
            "timing_source": self.timing_source.value,
            "absolute_start_seconds": self.absolute_start_seconds,
            "absolute_end_seconds": self.absolute_end_seconds,
            "speaker_label": self.speaker_label,
            "warning_codes": list(self.warning_codes),
        }


def normalize_generation_options(options: SubtitleGenerationOptions) -> SubtitleGenerationOptions:
    if options.max_lines <= 0:
        raise SubtitleValidationError("max_lines debe ser mayor que cero.")
    if options.max_chars_per_line <= 0:
        raise SubtitleValidationError("max_chars_per_line debe ser mayor que cero.")
    if options.max_chars_per_cue <= 0:
        raise SubtitleValidationError("max_chars_per_cue debe ser mayor que cero.")
    if options.max_chars_per_cue < options.max_chars_per_line:
        raise SubtitleValidationError("max_chars_per_cue debe ser mayor o igual que max_chars_per_line.")
    if options.min_duration_seconds <= 0:
        raise SubtitleValidationError("min_duration_seconds debe ser mayor que cero.")
    if options.recommended_min_duration_seconds < options.min_duration_seconds:
        raise SubtitleValidationError("recommended_min_duration_seconds debe ser mayor o igual que min_duration_seconds.")
    if options.recommended_max_duration_seconds < options.recommended_min_duration_seconds:
        raise SubtitleValidationError("recommended_max_duration_seconds debe ser mayor o igual que recommended_min_duration_seconds.")
    if options.max_duration_seconds < options.recommended_max_duration_seconds:
        raise SubtitleValidationError("max_duration_seconds debe ser mayor o igual que recommended_max_duration_seconds.")
    if options.min_gap_seconds < 0:
        raise SubtitleValidationError("min_gap_seconds no puede ser negativo.")
    if options.cps_warning_threshold <= 0:
        raise SubtitleValidationError("cps_warning_threshold debe ser mayor que cero.")
    if not options.generator_version.strip():
        raise SubtitleValidationError("generator_version no puede estar vacio.")
    return options

