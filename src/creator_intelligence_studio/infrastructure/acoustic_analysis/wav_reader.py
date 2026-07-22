"""Lectura y validacion de WAV preparado."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import wave

import numpy as np


class WavReaderError(RuntimeError):
    """Error al leer o validar un WAV preparado."""


@dataclass(frozen=True, slots=True)
class WavAudioData:
    """Audio WAV normalizado cargado en memoria."""

    path: Path
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    duration_seconds: float
    samples: np.ndarray


def read_wav_audio(path: Path) -> WavAudioData:
    if not path.exists():
        raise WavReaderError(f"No existe el archivo WAV preparado: {path}")
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            raw_frames = wav_file.readframes(frame_count)
    except wave.Error as exc:
        raise WavReaderError(f"El archivo no es un WAV valido: {path}") from exc
    if frame_count <= 0:
        raise WavReaderError("El archivo WAV esta vacio.")
    if channels != 1:
        raise WavReaderError("Se esperaba un WAV mono para analisis acustico.")
    if sample_width != 2:
        raise WavReaderError("Se esperaba un WAV PCM16 (16 bits por muestra).")
    if sample_rate != 16000:
        raise WavReaderError("Se esperaba un WAV a 16000 Hz.")
    samples = np.frombuffer(raw_frames, dtype="<i2").astype(np.float32) / 32768.0
    if samples.size == 0:
        raise WavReaderError("El archivo WAV no contiene muestras utilizables.")
    return WavAudioData(
        path=path,
        sample_rate_hz=sample_rate,
        channels=channels,
        sample_width_bytes=sample_width,
        frame_count=frame_count,
        duration_seconds=frame_count / float(sample_rate),
        samples=samples,
    )
