"""Exportacion de transcripciones a texto, SRT y JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import timedelta

from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def export_txt(transcription: Transcription, segments: list[TranscriptionSegment]) -> str:
    return transcription.full_text.strip() + "\n"


def export_srt(transcription: Transcription, segments: list[TranscriptionSegment]) -> str:
    lines: list[str] = []
    for index, segment in enumerate(sorted(segments, key=lambda item: item.segment_index), start=1):
        lines.extend(
            [
                str(index),
                f"{_format_srt_timestamp(segment.start_seconds)} --> {_format_srt_timestamp(segment.end_seconds)}",
                segment.text.strip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def export_json(transcription: Transcription, segments: list[TranscriptionSegment]) -> str:
    payload = transcription.to_dict()
    payload["segments"] = [segment.to_dict() for segment in sorted(segments, key=lambda item: item.segment_index)]
    return json.dumps(payload, ensure_ascii=False, indent=2)


