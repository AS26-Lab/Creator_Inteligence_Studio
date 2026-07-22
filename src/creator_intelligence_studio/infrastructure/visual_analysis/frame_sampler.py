"""Muestreador ligero de frames para analisis visual."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


class FrameSamplingError(RuntimeError):
    """Error al muestrear frames con ffmpeg."""


@dataclass(frozen=True, slots=True)
class SampledFrame:
    """Frame muestreado del video."""

    frame_index: int
    timestamp_seconds: float
    width: int
    height: int
    rgb_frame: np.ndarray


def _fit_dimensions(source_width: int | None, source_height: int | None, target_width: int, target_height: int) -> tuple[int, int]:
    if not source_width or not source_height:
        return target_width, target_height
    scale = min(target_width / float(source_width), target_height / float(source_height), 1.0)
    width = max(2, int(round(source_width * scale)))
    height = max(2, int(round(source_height * scale)))
    width -= width % 2
    height -= height % 2
    return max(2, width), max(2, height)


def _effective_sample_fps(*, duration_seconds: float | None, sample_fps: float, max_sample_frames: int) -> float:
    if duration_seconds is None or duration_seconds <= 0:
        return sample_fps
    estimated_frames = max(1, int(round(duration_seconds * sample_fps)))
    capped_frames = min(max_sample_frames, estimated_frames)
    return max(0.25, capped_frames / duration_seconds)


def sample_frames(
    *,
    ffmpeg_path: Path,
    source_path: Path,
    duration_seconds: float | None,
    source_width: int | None,
    source_height: int | None,
    sample_fps: float,
    max_sample_frames: int,
    target_width: int,
    target_height: int,
    start_seconds: float = 0.0,
    window_duration_seconds: float | None = None,
    timeout_seconds: float = 120.0,
) -> list[SampledFrame]:
    """Extrae frames RGB24 a baja frecuencia sin usar OpenCV."""

    effective_fps = _effective_sample_fps(
        duration_seconds=window_duration_seconds if window_duration_seconds is not None else duration_seconds,
        sample_fps=sample_fps,
        max_sample_frames=max_sample_frames,
    )
    width, height = _fit_dimensions(source_width, source_height, target_width, target_height)
    args = [
        str(ffmpeg_path),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, start_seconds):.3f}",
        "-i",
        str(source_path),
        "-an",
        "-sn",
        "-dn",
        "-vf",
        f"fps={effective_fps:.6f},scale={width}:{height}:flags=bicubic,format=rgb24",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-",
    ]
    if window_duration_seconds is not None and window_duration_seconds > 0:
        args[args.index("-i"):args.index("-i")] = ["-t", f"{window_duration_seconds:.3f}"]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FrameSamplingError("ffmpeg excedio el tiempo permitido para muestrear frames.") from exc
    except (FileNotFoundError, OSError) as exc:
        raise FrameSamplingError(f"No se pudo ejecutar ffmpeg: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        message = stderr or stdout or "ffmpeg fallo al muestrear frames."
        raise FrameSamplingError(message[:2000])
    raw_bytes = completed.stdout or b""
    frame_size = width * height * 3
    if frame_size <= 0:
        return []
    frame_count = len(raw_bytes) // frame_size
    if frame_count <= 0:
        return []
    if len(raw_bytes) % frame_size != 0:
        raise FrameSamplingError("ffmpeg devolvio un flujo de frames incompleto.")
    frames_array = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((frame_count, height, width, 3))
    result: list[SampledFrame] = []
    for index in range(frame_count):
        timestamp_seconds = start_seconds + (index / effective_fps if effective_fps > 0 else 0.0)
        result.append(
            SampledFrame(
                frame_index=index,
                timestamp_seconds=timestamp_seconds,
                width=width,
                height=height,
                rgb_frame=frames_array[index],
            )
        )
    return result
