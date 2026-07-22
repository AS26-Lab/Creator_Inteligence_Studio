"""Extraccion segura de audio normalizado con ffmpeg."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class FFmpegAudioExtractionError(RuntimeError):
    """Error al extraer audio con ffmpeg."""


@dataclass(frozen=True, slots=True)
class FFmpegAudioExtractionResult:
    """Resultado de una extraccion de audio."""

    path: Path
    stderr: str | None


def _limit_text(text: str | None, limit_bytes: int) -> str | None:
    if text is None:
        return None
    if len(text.encode("utf-8")) <= limit_bytes:
        return text.strip() or None
    return text.encode("utf-8")[:limit_bytes].decode("utf-8", errors="ignore").strip() or None


def extract_normalized_audio(
    *,
    ffmpeg_path: Path,
    source_path: Path,
    selected_stream_index: int,
    destination_path: Path,
    sample_rate_hz: int,
    channels: int = 1,
    timeout_seconds: float = 60.0,
    output_limit_bytes: int = 2_000_000,
) -> FFmpegAudioExtractionResult:
    """Genera un WAV normalizado sin modificar el video original."""

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        prefix=f"{destination_path.stem}.",
        suffix=f".tmp{destination_path.suffix}",
        dir=destination_path.parent,
        delete=False,
    )
    temp_file_path = Path(temp_file.name)
    temp_file.close()
    args = [
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source_path),
        "-map",
        f"0:{selected_stream_index}",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate_hz),
        str(temp_file_path),
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
        if temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        raise FFmpegAudioExtractionError("ffmpeg excedio el tiempo permitido para preparar el audio.") from exc
    except (FileNotFoundError, OSError) as exc:
        if temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        raise FFmpegAudioExtractionError(f"No se pudo ejecutar ffmpeg: {exc}") from exc

    stderr = _limit_text(completed.stderr, output_limit_bytes)
    stdout = _limit_text(completed.stdout, output_limit_bytes)
    if completed.returncode != 0:
        if temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        message = stderr or stdout or "ffmpeg fallo al preparar el audio."
        raise FFmpegAudioExtractionError(message)
    if not temp_file_path.exists() or temp_file_path.stat().st_size <= 0:
        if temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)
        raise FFmpegAudioExtractionError("ffmpeg no genero el archivo WAV esperado.")
    temp_file_path.replace(destination_path)
    return FFmpegAudioExtractionResult(path=destination_path, stderr=stderr)


class FFmpegAudioExtractor:
    """Envoltorio orientado a objeto para la extraccion de audio."""

    def __init__(self, ffmpeg_path: Path, *, timeout_seconds: float = 60.0) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.timeout_seconds = timeout_seconds

    def extract(
        self,
        *,
        source_path: Path,
        selected_stream_index: int,
        destination_path: Path,
        sample_rate_hz: int,
        channels: int = 1,
    ) -> FFmpegAudioExtractionResult:
        return extract_normalized_audio(
            ffmpeg_path=self.ffmpeg_path,
            source_path=source_path,
            selected_stream_index=selected_stream_index,
            destination_path=destination_path,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            timeout_seconds=self.timeout_seconds,
        )
