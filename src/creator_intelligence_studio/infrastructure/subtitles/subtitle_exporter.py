"""Exportacion de subtitulos a formatos comunes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderSubtitleStyle, SubtitleRenderStylePreset
from creator_intelligence_studio.domain.subtitles.entities import SubtitleCue, SubtitleExport, SubtitleTrack
from creator_intelligence_studio.domain.subtitles.errors import SubtitleExportError
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat
from creator_intelligence_studio.shared.dates import utc_now


@dataclass(frozen=True, slots=True)
class SubtitleExportResult:
    path: Path
    content: str
    fingerprint: str
    verified: bool


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _format_ass_timestamp(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_cs, 3600 * 100)
    minutes, remainder = divmod(remainder, 60 * 100)
    secs, centis = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


class SubtitleExporter:
    def export(
        self,
        track: SubtitleTrack,
        cues: list[SubtitleCue],
        format: SubtitleExportFormat,
        *,
        style: ClipRenderSubtitleStyle | None = None,
    ) -> str:
        if format == SubtitleExportFormat.SRT:
            return self._export_srt(cues)
        if format == SubtitleExportFormat.VTT:
            return self._export_vtt(cues)
        if format == SubtitleExportFormat.ASS:
            return self._export_ass(track, cues, style=style)
        if format == SubtitleExportFormat.TXT:
            return self._export_txt(cues)
        if format == SubtitleExportFormat.JSON:
            return self._export_json(track, cues)
        raise SubtitleExportError("Formato de exportacion no soportado.")

    def _export_srt(self, cues: list[SubtitleCue]) -> str:
        lines: list[str] = []
        for index, cue in enumerate(cues, start=1):
            lines.append(str(index))
            lines.append(f"{_format_srt_timestamp(cue.start_seconds)} --> {_format_srt_timestamp(cue.end_seconds)}")
            lines.extend(cue.text.split("\n"))
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _export_vtt(self, cues: list[SubtitleCue]) -> str:
        lines = ["WEBVTT", ""]
        for cue in cues:
            lines.append(f"{_format_vtt_timestamp(cue.start_seconds)} --> {_format_vtt_timestamp(cue.end_seconds)}")
            lines.extend(cue.text.split("\n"))
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _escape_ass_text(text: str) -> str:
        return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")

    def _export_ass(self, track: SubtitleTrack, cues: list[SubtitleCue], *, style: ClipRenderSubtitleStyle | None = None) -> str:
        style = style or ClipRenderSubtitleStyle(
            preset=SubtitleRenderStylePreset.CLEAN,
            font_family="Arial",
            font_size=48,
            primary_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=2,
            shadow=0,
            bold=False,
            alignment=2,
            margin_left=40,
            margin_right=40,
            margin_vertical=40,
            safe_area=10,
            background_box=False,
            max_lines=2,
        )
        primary_color = style.primary_color
        if not primary_color.startswith("&H"):
            primary_color = "&H00FFFFFF"
        outline_color = style.outline_color if style.outline_color.startswith("&H") else "&H00000000"
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            (
                "Style: Default,"
                f"{style.font_family},{style.font_size},{primary_color},&H000000FF,{outline_color},"
                f"{'&H64000000' if style.background_box else '&H00000000'},{1 if style.bold else 0},0,0,0,100,100,0,0,"
                f"{1 if style.background_box else 1},{max(1, style.outline_width)},{style.shadow},{style.alignment},"
                f"{style.margin_left},{style.margin_right},{style.margin_vertical},1"
            ),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        for cue in cues:
            text = self._escape_ass_text(cue.text)
            lines.append(
                f"Dialogue: 0,{_format_ass_timestamp(cue.start_seconds)},{_format_ass_timestamp(cue.end_seconds)},Default,,0,0,0,,{text}"
            )
        return "\n".join(lines) + "\n"

    def _export_txt(self, cues: list[SubtitleCue]) -> str:
        lines = []
        for cue in cues:
            lines.append(cue.text.replace("\n", " "))
        return "\n".join(lines).strip() + "\n"

    def _export_json(self, track: SubtitleTrack, cues: list[SubtitleCue]) -> str:
        payload = {
            "track": track.to_dict(),
            "cues": [cue.to_dict() for cue in cues],
            "exported_at": utc_now().isoformat(),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
