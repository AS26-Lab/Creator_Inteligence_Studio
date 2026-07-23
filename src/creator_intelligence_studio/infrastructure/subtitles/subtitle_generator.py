"""Generacion de subtitulos desde transcripciones."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueDraft, SubtitleGenerationOptions, SubtitleSourceType
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment
from creator_intelligence_studio.infrastructure.subtitles.segmentation_engine import SubtitleSegmentationEngine


@dataclass(frozen=True, slots=True)
class SubtitleGenerationResult:
    cues: tuple[SubtitleCueDraft, ...]
    warnings: tuple[str, ...]


class SubtitleGenerator:
    def __init__(self) -> None:
        self._segmentation = SubtitleSegmentationEngine()

    def generate(
        self,
        *,
        transcription: Transcription,
        segments: list[TranscriptionSegment],
        options: SubtitleGenerationOptions,
        source_type: SubtitleSourceType,
        clip_start_seconds: float = 0.0,
        clip_end_seconds: float | None = None,
    ) -> SubtitleGenerationResult:
        result = self._segmentation.segment(
            segments,
            options=options,
            clip_start_seconds=clip_start_seconds,
            clip_end_seconds=clip_end_seconds,
        )
        warnings = list(result.warnings)
        if source_type == SubtitleSourceType.CLIP_GENERATED and clip_end_seconds is not None:
            warnings.append("clip_relative_timing")
        return SubtitleGenerationResult(cues=result.cues, warnings=tuple(dict.fromkeys(warnings)))

