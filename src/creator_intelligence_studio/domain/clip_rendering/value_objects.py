"""Objetos de valor para renderizado de clips."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import ClipRenderValidationError


class ClipRenderJobStatus(str, Enum):
    """Estados persistidos de un render individual."""

    QUEUED = "queued"
    VALIDATING = "validating"
    PREPARING = "preparing"
    RENDERING = "rendering"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    STALE = "stale"
    SOURCE_MISSING = "source_missing"
    INVALID_BOUNDS = "invalid_bounds"
    OUTPUT_EXISTS = "output_exists"


class ClipRenderBatchStatus(str, Enum):
    """Estados persistidos de un lote de renders."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ClipRenderProfile(str, Enum):
    """Perfiles iniciales de render."""

    SOURCE_QUALITY = "source_quality"
    BALANCED = "balanced"
    COMPACT = "compact"
    DRAFT = "draft"


class ClipRenderArtifactType(str, Enum):
    """Tipos de artefacto de render."""

    OUTPUT = "output"
    PLAN = "plan"
    MANIFEST = "manifest"
    SUBTITLE_SRT = "subtitle_srt"
    SUBTITLE_VTT = "subtitle_vtt"
    DELIVERY_MANIFEST = "delivery_manifest"
    BURN_IN_SOURCE_ASS = "burn_in_source_ass"
    TECHNICAL_LOG = "technical_log"


class SubtitleRenderMode(str, Enum):
    NONE = "none"
    SIDECAR_SRT = "sidecar_srt"
    SIDECAR_VTT = "sidecar_vtt"
    BURN_IN = "burn_in"


class SubtitleRenderStylePreset(str, Enum):
    CLEAN = "clean"
    HIGH_CONTRAST = "high_contrast"
    COMPACT = "compact"
    SOCIAL_SAFE = "social_safe"


class ClipRenderDeliveryStatus(str, Enum):
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING = "rendering"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    STALE = "stale"
    OUTPUT_EXISTS = "output_exists"
    INVALID_TRACK = "invalid_track"
    SOURCE_MISSING = "source_missing"
    BOUNDS_MISMATCH = "bounds_mismatch"


@dataclass(frozen=True, slots=True)
class ClipRenderProfileConfig:
    """Configuracion reproducible de FFmpeg para un perfil."""

    profile: ClipRenderProfile
    container: str
    video_codec: str
    audio_codec: str
    pixel_format: str
    preset: str
    crf: int
    audio_bitrate_kbps: int
    max_width: int | None
    max_height: int | None
    max_frame_rate: float | None
    faststart: bool
    allow_fast_copy: bool
    hardware_acceleration: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.value,
            "container": self.container,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "pixel_format": self.pixel_format,
            "preset": self.preset,
            "crf": self.crf,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "max_frame_rate": self.max_frame_rate,
            "faststart": self.faststart,
            "allow_fast_copy": self.allow_fast_copy,
            "hardware_acceleration": self.hardware_acceleration,
        }


@dataclass(frozen=True, slots=True)
class ClipRenderSubtitleStyle:
    """Estilo declarativo para render con subtitulos."""

    preset: SubtitleRenderStylePreset
    font_family: str
    font_size: int
    primary_color: str
    outline_color: str
    outline_width: int
    shadow: int
    bold: bool
    alignment: int
    margin_left: int
    margin_right: int
    margin_vertical: int
    safe_area: int
    background_box: bool
    max_lines: int

    def to_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset.value,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "primary_color": self.primary_color,
            "outline_color": self.outline_color,
            "outline_width": self.outline_width,
            "shadow": self.shadow,
            "bold": self.bold,
            "alignment": self.alignment,
            "margin_left": self.margin_left,
            "margin_right": self.margin_right,
            "margin_vertical": self.margin_vertical,
            "safe_area": self.safe_area,
            "background_box": self.background_box,
            "max_lines": self.max_lines,
        }


@dataclass(frozen=True, slots=True)
class ClipRenderSubtitleConfig:
    """Bloque inmutable de subtitulos para un render o delivery."""

    mode: SubtitleRenderMode
    track_id: str | None
    track_version: int | None
    fingerprint: str | None
    format: str | None
    style_preset: SubtitleRenderStylePreset | None
    style: ClipRenderSubtitleStyle | None
    expected_cue_count: int | None
    stale_acknowledged: bool
    temporary_ass_path: str | None
    sidecar_output_path: str | None
    source_export_path: str | None
    source_export_fingerprint: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "track_id": self.track_id,
            "track_version": self.track_version,
            "fingerprint": self.fingerprint,
            "format": self.format,
            "style_preset": self.style_preset.value if self.style_preset else None,
            "style": self.style.to_dict() if self.style else None,
            "expected_cue_count": self.expected_cue_count,
            "stale_acknowledged": self.stale_acknowledged,
            "temporary_ass_path": self.temporary_ass_path,
            "sidecar_output_path": self.sidecar_output_path,
            "source_export_path": self.source_export_path,
            "source_export_fingerprint": self.source_export_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ClipRenderPlan:
    """Plan inmutable para ejecutar un render."""

    job_id: str
    video_asset_id: str
    creator_slug: str
    project_slug: str
    ranked_clip_candidate_id: str | None
    collection_id: str | None
    source_path: str
    source_path_snapshot: str
    source_fingerprint: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    profile: ClipRenderProfile
    output_path: str
    temporary_output_path: str
    container: str
    video_codec: str
    audio_codec: str
    pixel_format: str
    preset: str
    crf: int
    audio_bitrate_kbps: int
    max_width: int | None
    max_height: int | None
    max_frame_rate: float | None
    faststart: bool
    allow_fast_copy: bool
    hardware_acceleration: bool
    expected_width: int | None
    expected_height: int | None
    expected_audio: bool
    subtitle_config: ClipRenderSubtitleConfig | None
    configuration_fingerprint: str
    renderer_version: str
    custom_name: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "video_asset_id": self.video_asset_id,
            "creator_slug": self.creator_slug,
            "project_slug": self.project_slug,
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "collection_id": self.collection_id,
            "source_path": self.source_path,
            "source_path_snapshot": self.source_path_snapshot,
            "source_fingerprint": self.source_fingerprint,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "profile": self.profile.value,
            "output_path": self.output_path,
            "temporary_output_path": self.temporary_output_path,
            "container": self.container,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "pixel_format": self.pixel_format,
            "preset": self.preset,
            "crf": self.crf,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "max_frame_rate": self.max_frame_rate,
            "faststart": self.faststart,
            "allow_fast_copy": self.allow_fast_copy,
            "hardware_acceleration": self.hardware_acceleration,
            "expected_width": self.expected_width,
            "expected_height": self.expected_height,
            "expected_audio": self.expected_audio,
            "subtitle_config": self.subtitle_config.to_dict() if self.subtitle_config else None,
            "configuration_fingerprint": self.configuration_fingerprint,
            "renderer_version": self.renderer_version,
            "custom_name": self.custom_name,
        }


@dataclass(frozen=True, slots=True)
class RenderOutputVerification:
    """Resultado de verificacion del archivo de salida."""

    verified: bool
    output_path: str
    size_bytes: int | None
    duration_seconds: float | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: float | None
    audio_sample_rate: int | None
    fingerprint: str | None
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "verified": self.verified,
            "output_path": self.output_path,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "width": self.width,
            "height": self.height,
            "frame_rate": self.frame_rate,
            "audio_sample_rate": self.audio_sample_rate,
            "fingerprint": self.fingerprint,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "details": self.details or {},
        }


def build_render_configuration_fingerprint(payload: dict[str, object]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_render_bounds(start_seconds: float, end_seconds: float, duration_seconds: float | None, *, minimum_duration_seconds: float, maximum_duration_seconds: float) -> float:
    if start_seconds < 0:
        raise ClipRenderValidationError("start_seconds no puede ser negativo.")
    if end_seconds <= start_seconds:
        raise ClipRenderValidationError("end_seconds debe ser mayor que start_seconds.")
    clip_duration = end_seconds - start_seconds
    if clip_duration < minimum_duration_seconds:
        raise ClipRenderValidationError("La duracion del clip es menor que el minimo configurado.")
    if clip_duration > maximum_duration_seconds:
        raise ClipRenderValidationError("La duracion del clip excede el maximo configurado.")
    if duration_seconds is not None and end_seconds > duration_seconds + 0.001:
        raise ClipRenderValidationError("Los bordes exceden la duracion del video fuente.")
    return clip_duration
