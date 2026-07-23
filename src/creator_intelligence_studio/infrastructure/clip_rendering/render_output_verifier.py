"""Verificacion local de salidas de render."""

from __future__ import annotations

import hashlib
from pathlib import Path

from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderPlan, RenderOutputVerification
from creator_intelligence_studio.infrastructure.media.ffprobe_client import FFprobeClient


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RenderOutputVerifier:
    """Verifica salidas renderizadas con ffprobe."""

    def __init__(self, ffprobe_path: Path | None, *, duration_tolerance_seconds: float = 1.0) -> None:
        self.ffprobe_path = ffprobe_path
        self.duration_tolerance_seconds = duration_tolerance_seconds

    def verify(self, plan: ClipRenderPlan, output_path: Path) -> RenderOutputVerification:
        if not output_path.exists():
            return RenderOutputVerification(
                verified=False,
                output_path=str(output_path),
                size_bytes=None,
                duration_seconds=None,
                video_codec=None,
                audio_codec=None,
                width=None,
                height=None,
                frame_rate=None,
                audio_sample_rate=None,
                fingerprint=None,
                errors=("La salida no existe.",),
                details={"expected_duration_seconds": plan.duration_seconds},
            )
        size_bytes = output_path.stat().st_size
        if size_bytes <= 0:
            return RenderOutputVerification(
                verified=False,
                output_path=str(output_path),
                size_bytes=size_bytes,
                duration_seconds=None,
                video_codec=None,
                audio_codec=None,
                width=None,
                height=None,
                frame_rate=None,
                audio_sample_rate=None,
                fingerprint=_file_fingerprint(output_path),
                errors=("La salida esta vacia.",),
                details={"expected_duration_seconds": plan.duration_seconds},
            )
        if self.ffprobe_path is None:
            return RenderOutputVerification(
                verified=False,
                output_path=str(output_path),
                size_bytes=size_bytes,
                duration_seconds=None,
                video_codec=None,
                audio_codec=None,
                width=None,
                height=None,
                frame_rate=None,
                audio_sample_rate=None,
                fingerprint=_file_fingerprint(output_path),
                errors=("ffprobe no esta disponible.",),
                details={"expected_duration_seconds": plan.duration_seconds},
            )
        client = FFprobeClient(self.ffprobe_path, timeout_seconds=30.0)
        result = client.inspect(output_path)
        payload = result.payload
        format_payload = payload.get("format") if isinstance(payload, dict) else None
        streams = payload.get("streams") if isinstance(payload, dict) else None
        video_stream = next((stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"), None) if isinstance(streams, list) else None
        audio_stream = next((stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"), None) if isinstance(streams, list) else None
        duration_seconds = None
        if isinstance(format_payload, dict) and format_payload.get("duration") is not None:
            try:
                duration_seconds = float(format_payload["duration"])
            except (TypeError, ValueError):
                duration_seconds = None
        warnings: list[str] = []
        errors: list[str] = []
        if duration_seconds is None or abs(duration_seconds - plan.duration_seconds) > self.duration_tolerance_seconds:
            warnings.append("Duracion fuera de la tolerancia esperada.")
        if video_stream is None:
            errors.append("La salida no contiene stream de video.")
        if plan.expected_audio and audio_stream is None:
            errors.append("La salida no contiene stream de audio esperado.")
        frame_rate = None
        if isinstance(video_stream, dict):
            raw_rate = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
            if isinstance(raw_rate, str) and raw_rate not in {"", "N/A", "0/0"} and "/" in raw_rate:
                numerator, denominator = raw_rate.split("/", 1)
                try:
                    denominator_value = float(denominator)
                    if denominator_value:
                        frame_rate = float(numerator) / denominator_value
                except (TypeError, ValueError):
                    frame_rate = None
        verified = not errors
        return RenderOutputVerification(
            verified=verified,
            output_path=str(output_path),
            size_bytes=size_bytes,
            duration_seconds=duration_seconds,
            video_codec=video_stream.get("codec_name") if isinstance(video_stream, dict) else None,
            audio_codec=audio_stream.get("codec_name") if isinstance(audio_stream, dict) else None,
            width=int(video_stream["width"]) if isinstance(video_stream, dict) and video_stream.get("width") is not None else None,
            height=int(video_stream["height"]) if isinstance(video_stream, dict) and video_stream.get("height") is not None else None,
            frame_rate=frame_rate,
            audio_sample_rate=int(audio_stream["sample_rate"]) if isinstance(audio_stream, dict) and audio_stream.get("sample_rate") is not None else None,
            fingerprint=_file_fingerprint(output_path),
            warnings=tuple(warnings),
            errors=tuple(errors),
            details={"ffprobe": result.payload, "expected_duration_seconds": plan.duration_seconds},
        )
