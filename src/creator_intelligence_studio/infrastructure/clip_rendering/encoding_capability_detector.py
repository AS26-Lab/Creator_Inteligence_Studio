"""Deteccion no destructiva de capacidades de codificacion."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EncodingCapabilityReport:
    ffmpeg_path: str | None
    available: bool
    libx264: bool
    aac: bool
    h264_nvenc: bool
    hevc_nvenc: bool
    scale_filter: bool
    subtitles_filter: bool
    ass_filter: bool
    libass_available: bool
    fontconfig_available: bool
    burn_in_available: bool
    sidecar_available: bool
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "ffmpeg_path": self.ffmpeg_path,
            "available": self.available,
            "libx264": self.libx264,
            "aac": self.aac,
            "h264_nvenc": self.h264_nvenc,
            "hevc_nvenc": self.hevc_nvenc,
            "scale_filter": self.scale_filter,
            "subtitles_filter": self.subtitles_filter,
            "ass_filter": self.ass_filter,
            "libass_available": self.libass_available,
            "fontconfig_available": self.fontconfig_available,
            "burn_in_available": self.burn_in_available,
            "sidecar_available": self.sidecar_available,
            "errors": list(self.errors),
        }


class EncodingCapabilityDetector:
    """Detecta codecs y filtros disponibles sin modificar el sistema."""

    def __init__(self, ffmpeg_path: Path | None) -> None:
        self.ffmpeg_path = ffmpeg_path

    def detect(self) -> EncodingCapabilityReport:
        if self.ffmpeg_path is None:
            return EncodingCapabilityReport(
                ffmpeg_path=None,
                available=False,
                libx264=False,
                aac=False,
                h264_nvenc=False,
                hevc_nvenc=False,
                scale_filter=False,
                subtitles_filter=False,
                ass_filter=False,
                libass_available=False,
                fontconfig_available=False,
                burn_in_available=False,
                sidecar_available=False,
                errors=("ffmpeg no disponible.",),
            )
        try:
            completed = subprocess.run(
                [str(self.ffmpeg_path), "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            filters = subprocess.run(
                [str(self.ffmpeg_path), "-hide_banner", "-filters"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            buildconf = subprocess.run(
                [str(self.ffmpeg_path), "-hide_banner", "-buildconf"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
            return EncodingCapabilityReport(
                ffmpeg_path=str(self.ffmpeg_path),
                available=False,
                libx264=False,
                aac=False,
                h264_nvenc=False,
                hevc_nvenc=False,
                scale_filter=False,
                subtitles_filter=False,
                ass_filter=False,
                libass_available=False,
                fontconfig_available=False,
                burn_in_available=False,
                sidecar_available=False,
                errors=(str(exc),),
            )
        output = f"{completed.stdout}\n{completed.stderr}"
        filters_output = f"{filters.stdout}\n{filters.stderr}"
        buildconf_output = f"{buildconf.stdout}\n{buildconf.stderr}"
        subtitles_filter = " subtitles " in filters_output or "\n subtitles " in filters_output or "subtitles" in filters_output
        ass_filter = " ass " in filters_output or "\n ass " in filters_output or "ass" in filters_output
        libass_available = "libass" in buildconf_output or "enable-libass" in buildconf_output
        fontconfig_available = "fontconfig" in buildconf_output or "enable-libfontconfig" in buildconf_output
        return EncodingCapabilityReport(
            ffmpeg_path=str(self.ffmpeg_path),
            available=completed.returncode == 0,
            libx264="libx264" in output,
            aac="aac " in output or "\naac" in output,
            h264_nvenc="h264_nvenc" in output,
            hevc_nvenc="hevc_nvenc" in output,
            scale_filter=" scale " in filters_output or "\n scale " in filters_output or "scale" in filters_output,
            subtitles_filter=subtitles_filter,
            ass_filter=ass_filter,
            libass_available=libass_available,
            fontconfig_available=fontconfig_available,
            burn_in_available=subtitles_filter and ass_filter and libass_available,
            sidecar_available=True,
            errors=(),
        )
