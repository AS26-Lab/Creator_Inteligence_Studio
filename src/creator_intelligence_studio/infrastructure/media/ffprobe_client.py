"""Cliente seguro para obtener metadatos con ffprobe."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFprobeError(RuntimeError):
    """Error al consultar ffprobe."""


class FFprobeTimeoutError(FFprobeError):
    """ffprobe excedio el tiempo permitido."""


@dataclass(frozen=True, slots=True)
class FFprobeResult:
    """Salida estructurada de ffprobe."""

    raw_json: str
    payload: dict[str, object]


class FFprobeClient:
    """Ejecutor encapsulado de ffprobe."""

    def __init__(self, executable_path: Path, *, timeout_seconds: float = 30.0, output_limit_bytes: int = 2_000_000) -> None:
        self.executable_path = executable_path
        self.timeout_seconds = timeout_seconds
        self.output_limit_bytes = output_limit_bytes

    def version(self) -> str | None:
        try:
            completed = subprocess.run(
                [str(self.executable_path), "-version"],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            raise FFprobeError(f"No se pudo ejecutar ffprobe: {exc}") from exc
        if completed.returncode != 0:
            raise FFprobeError(completed.stderr.strip() or "ffprobe devolvio un error.")
        return completed.stdout.splitlines()[0].strip() if completed.stdout else None

    def inspect(self, media_path: Path) -> FFprobeResult:
        try:
            completed = subprocess.run(
                [
                    str(self.executable_path),
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    "-show_chapters",
                    str(media_path),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise FFprobeTimeoutError(
                f"ffprobe excedio el tiempo permitido inspeccionando {media_path}."
            ) from exc
        except (FileNotFoundError, OSError) as exc:
            raise FFprobeError(f"No se pudo ejecutar ffprobe: {exc}") from exc

        if completed.stdout and len(completed.stdout.encode("utf-8")) > self.output_limit_bytes:
            raise FFprobeError("ffprobe devolvio una salida demasiado grande.")
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "ffprobe fallo."
            raise FFprobeError(message)
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise FFprobeError("ffprobe no devolvio JSON valido.") from exc
        if not isinstance(payload, dict):
            raise FFprobeError("ffprobe devolvio un objeto JSON inesperado.")
        return FFprobeResult(raw_json=completed.stdout or "{}", payload=payload)

