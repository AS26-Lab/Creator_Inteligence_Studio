"""Reglas puras del dominio de transcripcion."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus

from .errors import TranscriptionValidationError
from .entities import TranscriptionStatus
from .value_objects import TranscriptionOptions

DEFAULT_TRANSCRIPTION_MODELS = ("base", "small", "medium")
PROFILE_TO_MODEL = {
    "fast": "base",
    "balanced": "small",
    "quality": "medium",
}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_COMPUTE_TYPES = {"auto", "float16", "int8_float16", "int8", "default"}


def normalize_profile(profile: str | None) -> str:
    value = (profile or "balanced").strip().lower()
    if value == "rapid":
        value = "fast"
    if value not in PROFILE_TO_MODEL:
        raise TranscriptionValidationError(
            "El perfil de transcripcion debe ser fast, balanced o quality."
        )
    return value


def normalize_model_name(model_name: str | None) -> str:
    value = (model_name or "small").strip().lower()
    if value not in DEFAULT_TRANSCRIPTION_MODELS:
        raise TranscriptionValidationError(
            f"Modelo no soportado: '{value}'. Valores permitidos: {list(DEFAULT_TRANSCRIPTION_MODELS)}"
        )
    return value


def normalize_device(device: str | None) -> str:
    value = (device or "auto").strip().lower()
    if value not in ALLOWED_DEVICES:
        raise TranscriptionValidationError(
            f"Device no soportado: '{value}'. Valores permitidos: {sorted(ALLOWED_DEVICES)}"
        )
    return value


def normalize_requested_compute_type(compute_type: str | None) -> str | None:
    if compute_type is None:
        return None
    value = compute_type.strip().lower()
    if value not in ALLOWED_COMPUTE_TYPES:
        raise TranscriptionValidationError(
            f"Compute type no soportado: '{value}'. Valores permitidos: {sorted(ALLOWED_COMPUTE_TYPES)}"
        )
    return None if value == "auto" else value


def normalize_language(language: str | None) -> str | None:
    if language is None:
        return None
    value = language.strip().lower()
    if not value or value == "auto":
        return None
    return value


def validate_transcription_options(options: TranscriptionOptions) -> None:
    if options.beam_size <= 0:
        raise TranscriptionValidationError("beam_size debe ser mayor que cero.")
    normalize_profile(options.profile)
    normalize_model_name(options.model_name)
    normalize_device(options.device)
    normalize_requested_compute_type(options.compute_type)
    normalize_language(options.language)
    if not options.cache_version.strip():
        raise TranscriptionValidationError("cache_version no puede estar vacio.")


def build_source_audio_fingerprint(
    *,
    prepared_audio: PreparedAudioAsset,
) -> str:
    payload = {
        "prepared_audio_asset_id": prepared_audio.id,
        "video_asset_id": prepared_audio.video_asset_id,
        "relative_cache_path": prepared_audio.relative_cache_path,
        "file_size_bytes": prepared_audio.file_size_bytes,
        "source_file_size_bytes": prepared_audio.source_file_size_bytes,
        "source_file_modified_at": prepared_audio.source_file_modified_at.isoformat()
        if prepared_audio.source_file_modified_at
        else None,
        "selected_stream_index": prepared_audio.selected_stream_index,
        "selected_stream_codec_name": prepared_audio.selected_stream_codec_name,
        "selected_stream_channels": prepared_audio.selected_stream_channels,
        "selected_stream_channel_layout": prepared_audio.selected_stream_channel_layout,
        "selected_stream_sample_rate_hz": prepared_audio.selected_stream_sample_rate_hz,
        "selected_stream_language": prepared_audio.selected_stream_language,
        "selected_stream_is_default": prepared_audio.selected_stream_is_default,
        "cache_version": prepared_audio.cache_version,
        "normalization_sample_rate_hz": prepared_audio.normalization_sample_rate_hz,
        "normalization_channels": prepared_audio.normalization_channels,
        "status": prepared_audio.status.value,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return digest


def build_configuration_fingerprint(options: TranscriptionOptions, *, engine_version: str | None, model_version: str | None) -> str:
    payload = {
        "profile": normalize_profile(options.profile),
        "model_name": normalize_model_name(options.model_name),
        "device": normalize_device(options.device),
        "compute_type": normalize_requested_compute_type(options.compute_type),
        "language": normalize_language(options.language),
        "beam_size": options.beam_size,
        "vad_filter": options.vad_filter,
        "word_timestamps": options.word_timestamps,
        "cache_version": options.cache_version,
        "engine_version": engine_version,
        "model_version": model_version,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def is_transcription_stale(
    transcription,
    *,
    prepared_audio: PreparedAudioAsset,
    options: TranscriptionOptions,
    cache_version: str,
    engine_version: str | None = None,
    model_version: str | None = None,
) -> bool:
    if transcription is None:
        return False
    if transcription.status != TranscriptionStatus.COMPLETED:
        return True
    if prepared_audio.status != PreparedAudioStatus.COMPLETED:
        return True
    if transcription.prepared_audio_asset_id != prepared_audio.id:
        return True
    if transcription.source_audio_fingerprint != build_source_audio_fingerprint(prepared_audio=prepared_audio):
        return True
    normalized_options = replace(
        options,
        profile=normalize_profile(options.profile),
        model_name=normalize_model_name(options.model_name),
        device=normalize_device(options.device),
        compute_type=normalize_requested_compute_type(options.compute_type),
        language=normalize_language(options.language),
    )
    if transcription.configuration_fingerprint != build_configuration_fingerprint(
        normalized_options,
        engine_version=engine_version,
        model_version=model_version,
    ):
        return True
    return False
