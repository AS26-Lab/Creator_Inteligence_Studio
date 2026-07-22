"""Extraccion controlada de keyframes visuales."""

from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import UUID


class KeyframeExtractionError(RuntimeError):
    """Error al extraer un keyframe."""


def build_keyframe_path(cache_root: Path, video_id: str, analysis_fingerprint: str, scene_index: int, extension: str = "jpg") -> Path:
    normalized_video_id = str(UUID(video_id))
    return cache_root / "videos" / normalized_video_id / "visual" / "keyframes" / analysis_fingerprint / f"scene-{scene_index:04d}.{extension}"


def extract_keyframe(
    *,
    ffmpeg_path: Path,
    source_path: Path,
    destination_path: Path,
    timestamp_seconds: float,
    width: int = 640,
    timeout_seconds: float = 30.0,
) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, timestamp_seconds):.3f}",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-2:flags=bicubic",
        "-q:v",
        "3",
        "-y",
        str(destination_path),
    ]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise KeyframeExtractionError("ffmpeg excedio el tiempo permitido para generar el keyframe.") from exc
    except (FileNotFoundError, OSError) as exc:
        raise KeyframeExtractionError(f"No se pudo ejecutar ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        message = stderr or stdout or "ffmpeg fallo al generar el keyframe."
        raise KeyframeExtractionError(message[:2000])
    if not destination_path.exists():
        raise KeyframeExtractionError("ffmpeg no genero el keyframe esperado.")
    return destination_path
