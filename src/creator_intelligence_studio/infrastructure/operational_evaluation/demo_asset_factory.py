"""Generacion de assets de demostracion para evaluacion operativa."""

from __future__ import annotations

import math
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator


@dataclass(frozen=True, slots=True)
class DemoAssetBundle:
    audio_path: Path
    video_path: Path
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "audio_path": str(self.audio_path),
            "video_path": str(self.video_path),
            "notes": list(self.notes),
        }


def _powershell_quote(value: str) -> str:
    return value.replace("'", "''")


def _build_sine_wav(destination: Path, *, duration_seconds: float = 4.0, sample_rate: int = 16000) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_samples = max(1, int(duration_seconds * sample_rate))
    amplitude = 12000
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for index in range(total_samples):
            if index < sample_rate * 0.5:
                sample = 0
            else:
                frequency = 220 + ((index // sample_rate) % 3) * 110
                sample = int(amplitude * math.sin(2 * math.pi * frequency * (index / sample_rate)))
            frames.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def _try_windows_tts(destination: Path, text: str) -> str | None:
    quoted_destination = _powershell_quote(str(destination))
    quoted_text = _powershell_quote(text)
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SetOutputToWaveFile('{quoted_destination}'); "
        f"$s.Speak('{quoted_text}'); "
        "$s.Dispose();"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return str(exc)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "TTS local no disponible."
        return stderr
    return None


def create_demo_audio(destination: Path, *, text: str, duration_seconds: float = 4.0) -> tuple[Path, tuple[str, ...]]:
    notes: list[str] = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    tts_error = _try_windows_tts(destination, text)
    if tts_error:
        notes.append(f"TTS local no disponible: {tts_error}")
        _build_sine_wav(destination, duration_seconds=duration_seconds)
        notes.append("Audio sintetico generado con onda senoidal controlada.")
    else:
        notes.append("Audio generado con Windows Speech API local.")
    return destination, tuple(notes)


def _ffmpeg_color_source(color: str, duration_seconds: float, size: str = "854x480", rate: int = 30) -> str:
    return f"color=c={color}:s={size}:r={rate}:d={duration_seconds}"


def create_demo_video(
    *,
    ffmpeg_path: Path,
    destination: Path,
    audio_path: Path,
    style: str,
    duration_seconds: float = 4.0,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    input_args: list[str] = []
    video_map = "0:v"
    video_filter: str | None = None
    if style == "cut":
        input_args = [
            "-f",
            "lavfi",
            "-i",
            _ffmpeg_color_source("darkred", duration_seconds / 2),
            "-f",
            "lavfi",
            "-i",
            _ffmpeg_color_source("darkblue", duration_seconds / 2),
        ]
        video_map = "[v]"
    elif style == "fade":
        input_args = [
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=854x480:rate=30:duration={duration_seconds}",
        ]
        video_filter = f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(duration_seconds - 0.5, 0.5)}:d=0.5"
    elif style == "static":
        input_args = [
            "-f",
            "lavfi",
            "-i",
            _ffmpeg_color_source("gray", duration_seconds),
        ]
    else:
        input_args = [
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=854x480:rate=30:duration={duration_seconds}",
        ]
    audio_input_index = 2 if style == "cut" else 1
    if style == "cut":
        input_args.extend([
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        ])
    args = [
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        *input_args,
        "-i",
        str(audio_path),
        "-map",
        video_map,
        "-map",
        f"{audio_input_index}:a",
        *(["-vf", video_filter] if video_filter else []),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(destination),
    ]
    completed = subprocess.run(args, capture_output=True, text=True, check=False, timeout=60)
    if completed.returncode != 0 or not destination.exists():
        message = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg no pudo crear el video de demostracion."
        raise RuntimeError(message)
    return destination


def create_demo_assets(
    *,
    project_root: Path,
    scenario_id: str,
    run_id: str,
    style: str,
    narration_text: str,
    duration_seconds: float = 4.0,
    asset_index: int = 0,
) -> DemoAssetBundle:
    locator = MediaToolLocator(project_root=project_root)
    ffmpeg = locator.locate("ffmpeg")
    if not ffmpeg.available or ffmpeg.path is None:
        raise RuntimeError(ffmpeg.error_message or "ffmpeg no disponible.")
    base_dir = project_root / "temp" / "evaluations" / scenario_id / run_id / f"asset_{asset_index + 1}"
    audio_path = base_dir / "demo_audio.wav"
    video_path = base_dir / "demo_video.mp4"
    notes: list[str] = []
    _, audio_notes = create_demo_audio(audio_path, text=narration_text, duration_seconds=duration_seconds)
    notes.extend(audio_notes)
    create_demo_video(
        ffmpeg_path=Path(ffmpeg.path),
        destination=video_path,
        audio_path=audio_path,
        style=style,
        duration_seconds=duration_seconds,
    )
    notes.append(f"Video demo generado con estilo '{style}'.")
    return DemoAssetBundle(audio_path=audio_path, video_path=video_path, notes=tuple(notes))
