"""Lectura de metadatos y pixeles de miniaturas locales."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class ThumbnailFileMetadata:
    path: Path
    width: int | None
    height: int | None
    file_size_bytes: int | None
    file_fingerprint: str | None
    warnings: tuple[str, ...]


def _probe_dimensions(path: Path, *, ffprobe_path: Path | None) -> tuple[int | None, int | None]:
    executable = str(ffprobe_path or "ffprobe")
    args = [
        executable,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None, None
    if completed.returncode != 0:
        return None, None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None, None
    streams = payload.get("streams") or []
    if not streams:
        return None, None
    stream = streams[0] or {}
    return stream.get("width"), stream.get("height")


def probe_thumbnail_file(path: Path, *, ffprobe_path: Path | None = None) -> ThumbnailFileMetadata:
    warnings: list[str] = []
    if not path.exists() or not path.is_file():
        warnings.append("missing_thumbnail")
        return ThumbnailFileMetadata(path=path, width=None, height=None, file_size_bytes=None, file_fingerprint=None, warnings=tuple(warnings))
    stat = path.stat()
    width, height = _probe_dimensions(path, ffprobe_path=ffprobe_path)
    if width is None or height is None:
        warnings.append("unsupported_format")
    file_fingerprint = hashlib.sha256(path.read_bytes()).hexdigest() if stat.st_size > 0 else None
    return ThumbnailFileMetadata(
        path=path,
        width=width,
        height=height,
        file_size_bytes=stat.st_size,
        file_fingerprint=file_fingerprint,
        warnings=tuple(warnings),
    )


def read_thumbnail_pixels(path: Path, *, ffmpeg_path: Path | None = None, ffprobe_path: Path | None = None, max_width: int = 96) -> tuple[ThumbnailFileMetadata, np.ndarray | None]:
    metadata = probe_thumbnail_file(path, ffprobe_path=ffprobe_path)
    if metadata.width is None or metadata.height is None or not path.exists():
        return metadata, None
    target_width = min(max_width, metadata.width)
    if target_width % 2 == 1:
        target_width -= 1
    target_width = max(2, target_width)
    target_height = max(2, int(round(metadata.height * (target_width / float(metadata.width)))))
    if target_height % 2 == 1:
        target_height -= 1
    executable = str(ffmpeg_path or "ffmpeg")
    args = [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={target_width}:{target_height}:flags=bicubic,format=rgb24",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    try:
        completed = subprocess.run(args, capture_output=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return metadata, None
    if completed.returncode != 0 or not completed.stdout:
        return metadata, None
    frame_size = target_width * target_height * 3
    if frame_size <= 0 or len(completed.stdout) < frame_size:
        return metadata, None
    raw = np.frombuffer(completed.stdout[:frame_size], dtype=np.uint8).reshape((target_height, target_width, 3))
    return metadata, raw

