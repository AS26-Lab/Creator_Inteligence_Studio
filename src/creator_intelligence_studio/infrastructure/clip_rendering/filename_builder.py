"""Construccion segura de nombres y rutas de render."""

from __future__ import annotations

import re
from pathlib import Path

from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderProfile


_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]+')
_WHITESPACE = re.compile(r"\s+")


def sanitize_filename_component(value: str | None, *, fallback: str = "clip", max_length: int = 60) -> str:
    if not value:
        return fallback
    normalized = _INVALID_CHARS.sub("_", value.strip())
    normalized = _WHITESPACE.sub("_", normalized)
    normalized = normalized.strip("._ ")
    if not normalized:
        normalized = fallback
    return normalized[:max_length]


def build_render_filename(
    *,
    video_title: str,
    clip_title: str | None,
    start_seconds: float,
    end_seconds: float,
    profile: ClipRenderProfile,
    extension: str = "mp4",
    suffix: str | None = None,
) -> str:
    title = sanitize_filename_component(video_title, fallback="video")
    clip = sanitize_filename_component(clip_title, fallback="clip") if clip_title else None
    start_text = f"{start_seconds:.2f}".replace(".", "p")
    end_text = f"{end_seconds:.2f}".replace(".", "p")
    parts = [title]
    if clip:
        parts.append(clip)
    parts.append(f"{start_text}-{end_text}")
    parts.append(profile.value)
    if suffix:
        parts.append(sanitize_filename_component(suffix, fallback="render"))
    stem = "_".join(parts)
    stem = stem[:160].rstrip("._ ")
    return f"{stem}.{extension.lstrip('.')}"


def build_render_output_path(root: Path, *, creator_slug: str, project_slug: str, video_title: str, filename: str) -> Path:
    return root / sanitize_filename_component(creator_slug, fallback="creator") / sanitize_filename_component(project_slug, fallback="project") / sanitize_filename_component(video_title, fallback="video") / filename
