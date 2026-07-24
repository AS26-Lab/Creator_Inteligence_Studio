"""Utilidades de subtitulos para deliveries locales."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderSubtitleStyle, SubtitleRenderStylePreset


def resolve_subtitle_style(
    preset: SubtitleRenderStylePreset,
    *,
    font_family: str | None = None,
    font_size: int | None = None,
) -> ClipRenderSubtitleStyle:
    base_styles = {
        SubtitleRenderStylePreset.CLEAN: ClipRenderSubtitleStyle(
            preset=preset,
            font_family=font_family or "Arial",
            font_size=font_size or 48,
            primary_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=2,
            shadow=0,
            bold=False,
            alignment=2,
            margin_left=40,
            margin_right=40,
            margin_vertical=48,
            safe_area=10,
            background_box=False,
            max_lines=2,
        ),
        SubtitleRenderStylePreset.HIGH_CONTRAST: ClipRenderSubtitleStyle(
            preset=preset,
            font_family=font_family or "Arial",
            font_size=font_size or 48,
            primary_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=3,
            shadow=1,
            bold=True,
            alignment=2,
            margin_left=32,
            margin_right=32,
            margin_vertical=52,
            safe_area=10,
            background_box=True,
            max_lines=2,
        ),
        SubtitleRenderStylePreset.COMPACT: ClipRenderSubtitleStyle(
            preset=preset,
            font_family=font_family or "Arial",
            font_size=font_size or 42,
            primary_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=2,
            shadow=0,
            bold=False,
            alignment=2,
            margin_left=28,
            margin_right=28,
            margin_vertical=34,
            safe_area=8,
            background_box=False,
            max_lines=2,
        ),
        SubtitleRenderStylePreset.SOCIAL_SAFE: ClipRenderSubtitleStyle(
            preset=preset,
            font_family=font_family or "Arial",
            font_size=font_size or 44,
            primary_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=3,
            shadow=1,
            bold=True,
            alignment=2,
            margin_left=36,
            margin_right=36,
            margin_vertical=76,
            safe_area=18,
            background_box=True,
            max_lines=2,
        ),
    }
    return base_styles[preset]


def escape_ass_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def escape_ffmpeg_filter_path(path: Path) -> str:
    resolved = path.resolve(strict=False).as_posix()
    return resolved.replace(":", r"\:")


def build_delivery_manifest(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
