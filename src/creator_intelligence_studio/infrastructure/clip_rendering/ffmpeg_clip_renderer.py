"""Renderer local de clips mediante FFmpeg."""

from __future__ import annotations

import hashlib
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from creator_intelligence_studio.domain.clip_rendering.errors import ClipRenderExecutionError
from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderPlan, SubtitleRenderMode
from creator_intelligence_studio.infrastructure.clip_rendering.subtitle_rendering import escape_ffmpeg_filter_path


class CancelToken(Protocol):
    def cancelled(self) -> bool:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ClipRenderProgress:
    phase: str
    progress_percent: float
    message: str
    speed: str | None = None
    elapsed_seconds: float | None = None
    out_time_seconds: float | None = None
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "speed": self.speed,
            "elapsed_seconds": self.elapsed_seconds,
            "out_time_seconds": self.out_time_seconds,
            "details": self.details or {},
        }


@dataclass(frozen=True, slots=True)
class ClipRenderExecutionResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    output_path: Path
    temporary_output_path: Path
    fingerprint: str | None
    progress_events: tuple[ClipRenderProgress, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "elapsed_seconds": self.elapsed_seconds,
            "output_path": str(self.output_path),
            "temporary_output_path": str(self.temporary_output_path),
            "fingerprint": self.fingerprint,
            "progress_events": [event.to_dict() for event in self.progress_events],
        }


class FFmpegClipRenderer:
    """Ejecuta FFmpeg con corte preciso y salida atomica."""

    def __init__(self, ffmpeg_path: Path | None, *, renderer_version: str = "v1") -> None:
        self.ffmpeg_path = ffmpeg_path
        self.renderer_version = renderer_version

    def _fingerprint_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _build_args(self, plan: ClipRenderPlan) -> list[str]:
        args = [
            str(self.ffmpeg_path),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-progress",
            "pipe:1",
            "-i",
            plan.source_path,
            "-ss",
            f"{plan.start_seconds:.3f}",
            "-t",
            f"{plan.duration_seconds:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map_metadata",
            "0",
            "-c:v",
            plan.video_codec,
            "-preset",
            plan.preset,
            "-crf",
            str(plan.crf),
            "-pix_fmt",
            plan.pixel_format,
            "-c:a",
            plan.audio_codec,
            "-b:a",
            f"{plan.audio_bitrate_kbps}k",
            "-avoid_negative_ts",
            "make_zero",
            "-sn",
            "-dn",
        ]
        if plan.faststart:
            args.extend(["-movflags", "+faststart"])
        filters: list[str] = []
        if plan.max_width is not None or plan.max_height is not None:
            max_width = plan.max_width or -2
            max_height = plan.max_height or -2
            filters.append(f"scale='min(iw,{max_width})':'min(ih,{max_height})':force_original_aspect_ratio=decrease")
        subtitle_config = plan.subtitle_config
        if subtitle_config is not None and subtitle_config.mode == SubtitleRenderMode.BURN_IN:
            if not subtitle_config.temporary_ass_path:
                raise ClipRenderExecutionError("No se definio un archivo ASS temporal para el burn-in.")
            filters.append(f"ass='{escape_ffmpeg_filter_path(Path(subtitle_config.temporary_ass_path))}'")
        if filters:
            args.extend(["-vf", ",".join(filters)])
        if plan.max_frame_rate is not None:
            args.extend(["-r", f"{plan.max_frame_rate:.3f}"])
        args.append(str(plan.temporary_output_path))
        return args

    def render(
        self,
        plan: ClipRenderPlan,
        *,
        cancellation_token: CancelToken | None = None,
        progress_callback=None,
        timeout_seconds: float | None = None,
    ) -> ClipRenderExecutionResult:
        if self.ffmpeg_path is None:
            raise ClipRenderExecutionError("ffmpeg no esta disponible.")
        plan_output = Path(plan.output_path)
        temp_output = Path(plan.temporary_output_path)
        temp_output.parent.mkdir(parents=True, exist_ok=True)
        if plan_output.exists():
            raise ClipRenderExecutionError("La salida final ya existe.")
        args = self._build_args(plan)
        start = time.monotonic()
        progress_events: list[ClipRenderProgress] = []
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        completed_event = threading.Event()
        progress_state = {"percent": 0.0, "speed": None, "out_time_seconds": 0.0}

        def emit(phase: str, percent: float, message: str, *, speed: str | None = None, out_time_seconds: float | None = None) -> None:
            event = ClipRenderProgress(
                phase=phase,
                progress_percent=max(0.0, min(100.0, percent)),
                message=message,
                speed=speed,
                elapsed_seconds=round(time.monotonic() - start, 3),
                out_time_seconds=out_time_seconds,
                details={"plan": plan.job_id},
            )
            progress_events.append(event)
            if progress_callback is not None:
                progress_callback(event.phase, event.progress_percent / 100.0, event.to_dict())

        emit("preparing", 0.0, "Preparando render")
        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
        except (FileNotFoundError, OSError) as exc:
            raise ClipRenderExecutionError(f"No se pudo ejecutar ffmpeg: {exc}") from exc

        def read_stdout() -> None:
            if process.stdout is None:
                return
            current: dict[str, str] = {}
            for line in process.stdout:
                if not line:
                    continue
                stdout_chunks.append(line)
                stripped = line.strip()
                if "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                current[key] = value
                if key == "out_time_ms":
                    try:
                        out_time = float(value) / 1_000_000.0
                    except ValueError:
                        continue
                    progress_state["out_time_seconds"] = out_time
                    percent = 0.0 if plan.duration_seconds <= 0 else min(100.0, (out_time / plan.duration_seconds) * 100.0)
                    emit("rendering", percent, "Renderizando", speed=progress_state.get("speed"), out_time_seconds=out_time)
                elif key == "speed":
                    progress_state["speed"] = value
                elif key == "progress" and value == "end":
                    emit("rendering", 99.0, "Finalizando")
            completed_event.set()

        def read_stderr() -> None:
            if process.stderr is None:
                return
            for line in process.stderr:
                if line:
                    stderr_chunks.append(line)

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        cancelled = False
        try:
            while process.poll() is None:
                if cancellation_token is not None and cancellation_token.cancelled():
                    cancelled = True
                    process.terminate()
                    try:
                        process.wait(timeout=3.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3.0)
                    break
                if timeout_seconds is not None and (time.monotonic() - start) > timeout_seconds:
                    process.terminate()
                    try:
                        process.wait(timeout=3.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3.0)
                    raise ClipRenderExecutionError("FFmpeg excedio el tiempo permitido para el render.")
                time.sleep(0.05)
            stdout_thread.join(timeout=2.0)
            stderr_thread.join(timeout=2.0)
            returncode = process.returncode if process.returncode is not None else -1
            if cancelled:
                if temp_output.exists():
                    temp_output.unlink(missing_ok=True)
                emit("cancelled", progress_events[-1].progress_percent if progress_events else 0.0, "Render cancelado")
                return ClipRenderExecutionResult(
                    returncode=returncode,
                    stdout="".join(stdout_chunks),
                    stderr="".join(stderr_chunks),
                    elapsed_seconds=round(time.monotonic() - start, 3),
                    output_path=plan_output,
                    temporary_output_path=temp_output,
                    fingerprint=None,
                    progress_events=tuple(progress_events),
                )
            if returncode != 0:
                message = "".join(stderr_chunks).strip() or "".join(stdout_chunks).strip() or "ffmpeg fallo."
                raise ClipRenderExecutionError(message)
            if not temp_output.exists():
                raise ClipRenderExecutionError("FFmpeg no genero la salida temporal esperada.")
            if plan_output.exists():
                raise ClipRenderExecutionError("La salida final ya existe.")
            temp_output.replace(plan_output)
            fingerprint = self._fingerprint_file(plan_output)
            emit("completed", 100.0, "Render completado")
            return ClipRenderExecutionResult(
                returncode=returncode,
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
                elapsed_seconds=round(time.monotonic() - start, 3),
                output_path=plan_output,
                temporary_output_path=temp_output,
                fingerprint=fingerprint,
                progress_events=tuple(progress_events),
            )
        except Exception:
            if temp_output.exists():
                try:
                    temp_output.unlink()
                except Exception:
                    pass
            raise
