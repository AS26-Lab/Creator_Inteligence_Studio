"""Cliente seguro para generar miniaturas tecnicas con ffmpeg."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


class FFmpegError(RuntimeError):
    """Error al ejecutar ffmpeg."""


@dataclass(frozen=True, slots=True)
class ThumbnailResult:
    """Resultado de generacion de miniatura."""

    path: Path
    timestamp_seconds: float


def build_thumbnail_path(cache_root: Path, video_id: str, version: str = "v1") -> Path:
    """Construye una ruta determinista para miniaturas tecnicas."""

    normalized_video_id = str(UUID(video_id))
    return cache_root / "videos" / normalized_video_id / "thumbnails" / f"thumbnail-{version}.jpg"


def _safe_thumbnail_timestamp(duration_seconds: float | None) -> float:
    if duration_seconds is None or duration_seconds <= 0:
        return 1.0
    if duration_seconds < 2.0:
        return max(duration_seconds / 2.0, 0.5)
    return min(max(duration_seconds * 0.10, 1.0), max(duration_seconds - 0.5, 1.0))


def generate_initial_thumbnail(
    *,
    ffmpeg_path: Path,
    source_path: Path,
    destination_path: Path,
    duration_seconds: float | None,
    timeout_seconds: float = 30.0,
) -> ThumbnailResult:
    """Genera una unica miniatura sin modificar el video original."""

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _safe_thumbnail_timestamp(duration_seconds)
    args = [
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        "-vf",
        "scale=640:-2",
        "-q:v",
        "3",
        str(destination_path),
    ]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("ffmpeg excedio el tiempo permitido para generar la miniatura.") from exc
    except (FileNotFoundError, OSError) as exc:
        raise FFmpegError(f"No se pudo ejecutar ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg fallo."
        raise FFmpegError(message)
    if not destination_path.exists():
        raise FFmpegError("ffmpeg no genero la miniatura esperada.")
    return ThumbnailResult(path=destination_path, timestamp_seconds=timestamp)
