"""Reglas y politicas del dominio de audio."""

from __future__ import annotations

from creator_intelligence_studio.domain.audio.errors import AudioValidationError
from creator_intelligence_studio.domain.audio.value_objects import AudioPreparationConfig, AudioStreamCandidate
from creator_intelligence_studio.domain.media.value_objects import MediaStreamInfo


def build_audio_candidates(streams: list[MediaStreamInfo]) -> list[AudioStreamCandidate]:
    """Convierte streams tipados de ffprobe en candidatos de audio."""

    candidates: list[AudioStreamCandidate] = []
    for stream in streams:
        if stream.codec_type != "audio":
            continue
        language = None
        if "language" in stream.tags and stream.tags["language"]:
            language = stream.tags["language"].strip().lower()
        candidates.append(
            AudioStreamCandidate(
                index=stream.index,
                codec_name=stream.codec_name,
                codec_long_name=stream.codec_long_name,
                channels=stream.channels,
                channel_layout=stream.channel_layout,
                sample_rate_hz=stream.sample_rate,
                language=language,
                is_default=bool(stream.disposition.get("default", 0)),
                tags=dict(stream.tags),
            )
        )
    return candidates


def select_audio_stream(
    candidates: list[AudioStreamCandidate],
    *,
    preferred_language: str | None = None,
) -> AudioStreamCandidate:
    """Selecciona un stream de audio siguiendo la politica documentada."""

    valid = [candidate for candidate in candidates if candidate.index >= 0]
    if not valid:
        raise AudioValidationError("No existe un stream de audio valido para preparar.")
    if preferred_language:
        language = preferred_language.strip().lower()
        matched = next((candidate for candidate in valid if candidate.language == language), None)
        if matched is not None:
            return matched
    default_candidate = next((candidate for candidate in valid if candidate.is_default), None)
    if default_candidate is not None:
        return default_candidate
    by_channels = sorted(
        valid,
        key=lambda candidate: (
            candidate.channels if candidate.channels is not None else -1,
            candidate.sample_rate_hz if candidate.sample_rate_hz is not None else -1,
        ),
        reverse=True,
    )
    return by_channels[0]


def validate_audio_preparation_config(config: AudioPreparationConfig) -> None:
    """Valida la configuracion de normalizacion."""

    if config.sample_rate_hz <= 0:
        raise AudioValidationError("sample_rate_hz debe ser mayor que cero.")
    if config.channels <= 0:
        raise AudioValidationError("channels debe ser mayor que cero.")
    if config.bit_depth <= 0:
        raise AudioValidationError("bit_depth debe ser mayor que cero.")
    if not config.cache_version.strip():
        raise AudioValidationError("cache_version no puede estar vacio.")
