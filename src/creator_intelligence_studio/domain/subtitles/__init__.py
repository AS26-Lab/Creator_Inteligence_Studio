"""Dominio de subtitulos locales."""

from .entities import SubtitleCue, SubtitleEditEvent, SubtitleExport, SubtitleTrack
from .errors import SubtitleError, SubtitleExportError, SubtitleImportError, SubtitleStateError, SubtitleValidationError
from .repositories import SubtitleRepository
from .services import (
    build_subtitle_configuration_fingerprint,
    build_subtitle_source_fingerprint,
    is_subtitle_track_stale,
    normalize_subtitle_text,
    normalize_generation_options,
    validate_subtitle_bounds,
    validate_subtitle_cue,
    validate_subtitle_track,
    wrap_subtitle_text,
)
from .value_objects import (
    SubtitleCueDraft,
    SubtitleCueValidationStatus,
    SubtitleExportFormat,
    SubtitleGenerationOptions,
    SubtitleSourceType,
    SubtitleTimingSource,
    SubtitleTrackStatus,
)
