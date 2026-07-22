"""Validador de WAV basado en la biblioteca estandar."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path


class WavInspectionError(RuntimeError):
    """Error al verificar un archivo WAV."""


@dataclass(frozen=True, slots=True)
class WavInspectionResult:
    """Resumen tecnico de un WAV preparado."""

    path: Path
    format_name: str | None
    codec_name: str | None
    sample_rate_hz: int | None
    channels: int | None
    bit_depth: int | None
    duration_seconds: float | None
    file_size_bytes: int | None
    valid: bool
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "format_name": self.format_name,
            "codec_name": self.codec_name,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "valid": self.valid,
            "error_message": self.error_message,
        }


def inspect_wav_file(path: Path) -> WavInspectionResult:
    """Comprueba que el archivo tenga el encabezado y el formato esperados."""

    if not path.exists() or not path.is_file():
        raise WavInspectionError(f"No existe el archivo WAV: {path}")
    file_size = path.stat().st_size
    if file_size <= 0:
        raise WavInspectionError("El archivo WAV esta vacio.")
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate_hz = wav_file.getframerate()
            bit_depth = wav_file.getsampwidth() * 8
            frame_count = wav_file.getnframes()
            comptype = wav_file.getcomptype()
    except wave.Error as exc:
        raise WavInspectionError(f"El archivo no es un WAV valido: {exc}") from exc

    if comptype != "NONE":
        raise WavInspectionError("El WAV no usa PCM sin compresion.")
    if channels <= 0:
        raise WavInspectionError("El WAV no tiene canales validos.")
    if sample_rate_hz <= 0:
        raise WavInspectionError("El WAV no tiene una frecuencia de muestreo valida.")
    if bit_depth <= 0:
        raise WavInspectionError("El WAV no tiene una profundidad de bits valida.")
    if frame_count <= 0:
        raise WavInspectionError("El WAV no contiene muestras de audio.")
    duration_seconds = frame_count / float(sample_rate_hz)
    return WavInspectionResult(
        path=path,
        format_name="wav",
        codec_name="pcm_s16le" if bit_depth == 16 else None,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        bit_depth=bit_depth,
        duration_seconds=duration_seconds,
        file_size_bytes=file_size,
        valid=channels == 1 and sample_rate_hz == 16000 and bit_depth == 16,
        error_message=None,
    )
