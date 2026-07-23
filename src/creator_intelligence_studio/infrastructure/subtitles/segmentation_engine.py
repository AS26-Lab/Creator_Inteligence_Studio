"""Segmentacion determinista para subtitulos."""

from __future__ import annotations

import re
from dataclasses import dataclass

from creator_intelligence_studio.domain.subtitles.services import normalize_subtitle_text, wrap_subtitle_text
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueDraft, SubtitleGenerationOptions, SubtitleTimingSource
from creator_intelligence_studio.domain.transcription.entities import TranscriptionSegment


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…。])\s+")


@dataclass(frozen=True, slots=True)
class SubtitleSegmentationResult:
    cues: tuple[SubtitleCueDraft, ...]
    warnings: tuple[str, ...] = ()


class SubtitleSegmentationEngine:
    def segment(
        self,
        segments: list[TranscriptionSegment],
        *,
        options: SubtitleGenerationOptions,
        clip_start_seconds: float = 0.0,
        clip_end_seconds: float | None = None,
    ) -> SubtitleSegmentationResult:
        cues: list[SubtitleCueDraft] = []
        warnings: list[str] = []
        for segment in segments:
            text = normalize_subtitle_text(segment.text)
            if not text:
                warnings.append("empty_text")
                continue
            seg_start = max(segment.start_seconds, clip_start_seconds)
            seg_end = min(segment.end_seconds, clip_end_seconds) if clip_end_seconds is not None else segment.end_seconds
            if seg_end <= seg_start:
                continue
            relative_start = seg_start - clip_start_seconds
            relative_end = seg_end - clip_start_seconds
            chunk_texts = self._split_text(text, options=options)
            if not chunk_texts:
                continue
            durations = self._allocate_durations(relative_start, relative_end, chunk_texts)
            cursor = relative_start
            for index, chunk_text in enumerate(chunk_texts):
                duration = durations[index]
                end = cursor + duration
                wrapped = wrap_subtitle_text(chunk_text, max_lines=options.max_lines, max_chars_per_line=options.max_chars_per_line)
                warnings_for_chunk: list[str] = []
                if len(chunk_text) > options.max_chars_per_cue:
                    warnings_for_chunk.append("too_many_characters")
                if len(wrapped) > options.max_lines:
                    warnings_for_chunk.append("too_many_lines")
                cues.append(
                    SubtitleCueDraft(
                        start_seconds=round(cursor, 3),
                        end_seconds=round(end, 3),
                        text="\n".join(wrapped),
                        original_text=chunk_text,
                        source_segment_ids=(segment.id,),
                        timing_source=SubtitleTimingSource.SEGMENT_EXACT if len(chunk_texts) == 1 and seg_start == segment.start_seconds and seg_end == segment.end_seconds else SubtitleTimingSource.PROPORTIONAL_ESTIMATE,
                        absolute_start_seconds=round(seg_start, 3),
                        absolute_end_seconds=round(seg_end, 3),
                        warning_codes=tuple(dict.fromkeys(warnings_for_chunk)),
                    )
                )
                cursor = end
        return SubtitleSegmentationResult(cues=tuple(cues), warnings=tuple(dict.fromkeys(warnings)))

    def _split_text(self, text: str, *, options: SubtitleGenerationOptions) -> list[str]:
        parts = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
        if not parts:
            parts = [text]
        chunks: list[str] = []
        for part in parts:
            if len(part) <= options.max_chars_per_cue:
                chunks.append(part)
                continue
            words = part.split()
            current: list[str] = []
            current_len = 0
            for word in words:
                needed = len(word) + (1 if current else 0)
                if current and current_len + needed > options.max_chars_per_cue:
                    chunks.append(" ".join(current))
                    current = [word]
                    current_len = len(word)
                else:
                    current.append(word)
                    current_len += needed
            if current:
                chunks.append(" ".join(current))
        return [chunk for chunk in chunks if chunk.strip()]

    def _allocate_durations(self, start: float, end: float, chunk_texts: list[str]) -> list[float]:
        duration = max(0.05, end - start)
        weights = [max(1, len(chunk)) for chunk in chunk_texts]
        total = sum(weights) or 1
        durations = [duration * weight / total for weight in weights]
        if len(durations) == 1:
            durations[0] = duration
        return durations

