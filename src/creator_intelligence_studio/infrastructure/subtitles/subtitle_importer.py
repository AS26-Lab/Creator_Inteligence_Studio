"""Importacion de subtitulos SRT, VTT y ASS basicos."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.domain.subtitles.errors import SubtitleImportError
from creator_intelligence_studio.domain.subtitles.services import normalize_subtitle_text
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueDraft, SubtitleExportFormat, SubtitleGenerationOptions, SubtitleSourceType, SubtitleTimingSource


_SRT_TIME = re.compile(r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})")
_VTT_TIME = re.compile(r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})")


@dataclass(frozen=True, slots=True)
class SubtitleImportResult:
    cues: tuple[SubtitleCueDraft, ...]
    format: SubtitleExportFormat
    warnings: tuple[str, ...] = ()


def _to_seconds(value: str) -> float:
    clean = value.replace(",", ".")
    hours, minutes, rest = clean.split(":")
    seconds, millis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def _strip_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", re.sub(r"\{[^}]+\}", "", text)).strip()


class SubtitleImporter:
    def import_file(self, path: Path, *, format: SubtitleExportFormat | None = None, options: SubtitleGenerationOptions) -> SubtitleImportResult:
        if not path.exists() or not path.is_file():
            raise SubtitleImportError("El archivo de subtitulos no existe.")
        raw = path.read_bytes()
        if b"\x00" in raw[:1024]:
            raise SubtitleImportError("El archivo de subtitulos parece binario.")
        text = raw.decode("utf-8-sig", errors="strict")
        detected = format or self._detect_format(path, text)
        if detected == SubtitleExportFormat.SRT:
            return SubtitleImportResult(cues=tuple(self._parse_srt(text, options=options)), format=detected)
        if detected == SubtitleExportFormat.VTT:
            return SubtitleImportResult(cues=tuple(self._parse_vtt(text, options=options)), format=detected)
        if detected == SubtitleExportFormat.ASS:
            return SubtitleImportResult(cues=tuple(self._parse_ass(text, options=options)), format=detected)
        if detected == SubtitleExportFormat.JSON:
            payload = json.loads(text)
            cues = []
            for item in payload.get("cues", []):
                cues.append(
                    SubtitleCueDraft(
                        start_seconds=float(item["start_seconds"]),
                        end_seconds=float(item["end_seconds"]),
                        text=normalize_subtitle_text(str(item["text"])),
                        original_text=normalize_subtitle_text(str(item.get("original_text") or item["text"])),
                        source_segment_ids=tuple(item.get("source_segment_ids") or ()),
                        timing_source=SubtitleTimingSource.MANUAL,
                        absolute_start_seconds=float(item.get("absolute_start_seconds", item["start_seconds"])),
                        absolute_end_seconds=float(item.get("absolute_end_seconds", item["end_seconds"])),
                        speaker_label=item.get("speaker_label"),
                    )
                )
            return SubtitleImportResult(cues=tuple(cues), format=detected, warnings=tuple(payload.get("warnings", ())))
        raise SubtitleImportError("Formato de subtitulos no soportado.")

    def _detect_format(self, path: Path, text: str) -> SubtitleExportFormat:
        suffix = path.suffix.lower().lstrip(".")
        if suffix == "srt":
            return SubtitleExportFormat.SRT
        if suffix == "vtt":
            return SubtitleExportFormat.VTT
        if suffix == "ass":
            return SubtitleExportFormat.ASS
        if suffix == "json":
            return SubtitleExportFormat.JSON
        if text.lstrip().startswith("WEBVTT"):
            return SubtitleExportFormat.VTT
        if "[Script Info]" in text and "[Events]" in text:
            return SubtitleExportFormat.ASS
        return SubtitleExportFormat.SRT

    def _parse_srt(self, text: str, *, options: SubtitleGenerationOptions) -> list[SubtitleCueDraft]:
        cues: list[SubtitleCueDraft] = []
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")) if block.strip()]
        for block in blocks:
            lines = [line.rstrip() for line in block.split("\n") if line.strip()]
            if len(lines) < 2:
                continue
            match = _SRT_TIME.search(lines[1] if lines[0].isdigit() and len(lines) > 1 else lines[0])
            if match is None:
                raise SubtitleImportError("Timestamp SRT invalido.")
            body_lines = lines[2:] if lines[0].isdigit() and len(lines) > 2 else lines[1:]
            body = _strip_markup("\n".join(body_lines))
            cues.append(
                SubtitleCueDraft(
                    start_seconds=_to_seconds(match.group("start")),
                    end_seconds=_to_seconds(match.group("end")),
                    text=normalize_subtitle_text(body),
                    original_text=normalize_subtitle_text(body),
                    source_segment_ids=(),
                    timing_source=SubtitleTimingSource.MANUAL,
                    absolute_start_seconds=_to_seconds(match.group("start")),
                    absolute_end_seconds=_to_seconds(match.group("end")),
                    warning_codes=("markup_stripped",) if body != "\n".join(body_lines) else (),
                )
            )
        return cues

    def _parse_vtt(self, text: str, *, options: SubtitleGenerationOptions) -> list[SubtitleCueDraft]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.lstrip().startswith("WEBVTT"):
            raise SubtitleImportError("El archivo VTT no tiene encabezado WEBVTT.")
        cues: list[SubtitleCueDraft] = []
        for block in [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()][1:]:
            lines = [line.rstrip() for line in block.split("\n") if line.strip()]
            match = _VTT_TIME.search(lines[0] if "-->" in lines[0] else lines[1] if len(lines) > 1 else "")
            if match is None:
                continue
            body = _strip_markup("\n".join(lines[1:])) if "-->" in lines[0] else _strip_markup("\n".join(lines[2:]))
            cues.append(
                SubtitleCueDraft(
                    start_seconds=_to_seconds(match.group("start")),
                    end_seconds=_to_seconds(match.group("end")),
                    text=normalize_subtitle_text(body),
                    original_text=normalize_subtitle_text(body),
                    source_segment_ids=(),
                    timing_source=SubtitleTimingSource.MANUAL,
                    absolute_start_seconds=_to_seconds(match.group("start")),
                    absolute_end_seconds=_to_seconds(match.group("end")),
                    warning_codes=("markup_stripped",) if body != "\n".join(lines[1:]) else (),
                )
            )
        return cues

    def _parse_ass(self, text: str, *, options: SubtitleGenerationOptions) -> list[SubtitleCueDraft]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if "[Events]" not in normalized:
            raise SubtitleImportError("El archivo ASS no contiene la seccion Events.")
        cues: list[SubtitleCueDraft] = []
        in_events = False
        for line in normalized.split("\n"):
            if line.strip().startswith("[Events]"):
                in_events = True
                continue
            if not in_events or not line.startswith("Dialogue:"):
                continue
            payload = line[len("Dialogue:"):].lstrip()
            parts = payload.split(",", 9)
            if len(parts) < 10:
                continue
            start, end = parts[1], parts[2]
            body = _strip_markup(parts[9])
            cues.append(
                SubtitleCueDraft(
                    start_seconds=_ass_to_seconds(start),
                    end_seconds=_ass_to_seconds(end),
                    text=normalize_subtitle_text(body),
                    original_text=normalize_subtitle_text(body),
                    source_segment_ids=(),
                    timing_source=SubtitleTimingSource.MANUAL,
                    absolute_start_seconds=_ass_to_seconds(start),
                    absolute_end_seconds=_ass_to_seconds(end),
                    warning_codes=("markup_stripped",) if body != parts[9] else (),
                )
            )
        return cues


def _ass_to_seconds(value: str) -> float:
    hours, minutes, rest = value.strip().split(":")
    seconds, centis = rest.split(".")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100.0

