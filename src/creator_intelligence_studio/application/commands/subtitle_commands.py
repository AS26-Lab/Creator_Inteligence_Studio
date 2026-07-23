"""Comandos de aplicacion para subtitulos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat, SubtitleGenerationOptions


@dataclass(frozen=True, slots=True)
class GenerateVideoSubtitlesCommand:
    video_id: str
    options: SubtitleGenerationOptions


@dataclass(frozen=True, slots=True)
class GenerateClipSubtitlesCommand:
    candidate_id: str
    options: SubtitleGenerationOptions


@dataclass(frozen=True, slots=True)
class RegenerateSubtitleTrackCommand:
    track_id: str
    options: SubtitleGenerationOptions


@dataclass(frozen=True, slots=True)
class ShowSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class ListVideoSubtitleTracksCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ListClipSubtitleTracksCommand:
    candidate_id: str


@dataclass(frozen=True, slots=True)
class ValidateSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class UpdateSubtitleTextCommand:
    cue_id: str
    text: str


@dataclass(frozen=True, slots=True)
class UpdateSubtitleTimeCommand:
    cue_id: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class SplitSubtitleCueCommand:
    cue_id: str
    split_position: int


@dataclass(frozen=True, slots=True)
class MergeSubtitleCuesCommand:
    first_cue_id: str
    second_cue_id: str


@dataclass(frozen=True, slots=True)
class InsertSubtitleCueCommand:
    track_id: str
    index: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True, slots=True)
class DeleteSubtitleCueCommand:
    cue_id: str


@dataclass(frozen=True, slots=True)
class MoveSubtitleCueCommand:
    cue_id: str
    new_index: int


@dataclass(frozen=True, slots=True)
class ShiftSubtitleTrackCommand:
    track_id: str
    offset_seconds: float


@dataclass(frozen=True, slots=True)
class LockSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class UnlockSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class DuplicateSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class ImportSubtitleTrackCommand:
    video_id: str
    file: Path
    format: SubtitleExportFormat | None = None
    options: SubtitleGenerationOptions | None = None


@dataclass(frozen=True, slots=True)
class ExportSubtitleTrackCommand:
    track_id: str
    format: SubtitleExportFormat
    output: Path | None = None


@dataclass(frozen=True, slots=True)
class SubtitleHistoryCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class DeleteSubtitleTrackCommand:
    track_id: str


@dataclass(frozen=True, slots=True)
class ArchiveSubtitleTrackCommand:
    track_id: str

