"""Reglas del dominio de analisis acustico."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionStatus

from .errors import AcousticAnalysisValidationError
from .entities import AcousticAnalysis
from .value_objects import AcousticAnalysisStatus
from .value_objects import AcousticAnalysisOptions


def normalize_acoustic_analysis_config(options: AcousticAnalysisOptions) -> AcousticAnalysisOptions:
    if options.frame_duration_ms < 10 or options.frame_duration_ms > 100:
        raise AcousticAnalysisValidationError("frame_duration_ms fuera de rango razonable.")
    if options.frame_hop_ms <= 0 or options.frame_hop_ms > options.frame_duration_ms:
        raise AcousticAnalysisValidationError("frame_hop_ms debe ser mayor que cero y menor o igual al frame.")
    if options.window_duration_seconds <= 0:
        raise AcousticAnalysisValidationError("window_duration_seconds debe ser mayor que cero.")
    if options.rhythm_window_seconds <= 0:
        raise AcousticAnalysisValidationError("rhythm_window_seconds debe ser mayor que cero.")
    if options.speech_energy_multiplier <= 0:
        raise AcousticAnalysisValidationError("speech_energy_multiplier debe ser mayor que cero.")
    if options.silence_energy_multiplier <= 0:
        raise AcousticAnalysisValidationError("silence_energy_multiplier debe ser mayor que cero.")
    if options.minimum_speech_seconds < 0:
        raise AcousticAnalysisValidationError("minimum_speech_seconds no puede ser negativo.")
    if options.pause_micro_max_seconds <= 0:
        raise AcousticAnalysisValidationError("pause_micro_max_seconds debe ser mayor que cero.")
    if options.pause_short_max_seconds <= options.pause_micro_max_seconds:
        raise AcousticAnalysisValidationError("pause_short_max_seconds debe ser mayor que pause_micro_max_seconds.")
    if options.pause_medium_max_seconds <= options.pause_short_max_seconds:
        raise AcousticAnalysisValidationError("pause_medium_max_seconds debe ser mayor que pause_short_max_seconds.")
    if not options.cache_version.strip():
        raise AcousticAnalysisValidationError("cache_version no puede estar vacio.")
    if not options.analyzer_version.strip():
        raise AcousticAnalysisValidationError("analyzer_version no puede estar vacio.")
    return replace(
        options,
        cache_version=options.cache_version.strip(),
        analyzer_version=options.analyzer_version.strip(),
    )


def validate_acoustic_analysis_options(options: AcousticAnalysisOptions) -> None:
    normalize_acoustic_analysis_config(options)


def build_acoustic_source_fingerprint(
    *,
    prepared_audio: PreparedAudioAsset,
    transcription: Transcription | None,
    audio_file_size_bytes: int | None = None,
    audio_file_modified_at: str | None = None,
) -> str:
    payload = {
        "prepared_audio_asset_id": prepared_audio.id,
        "prepared_audio_status": prepared_audio.status.value,
        "prepared_audio_relative_cache_path": prepared_audio.relative_cache_path,
        "prepared_audio_file_size_bytes": prepared_audio.file_size_bytes,
        "prepared_audio_source_file_size_bytes": prepared_audio.source_file_size_bytes,
        "prepared_audio_source_file_modified_at": prepared_audio.source_file_modified_at.isoformat()
        if prepared_audio.source_file_modified_at
        else None,
        "prepared_audio_cache_version": prepared_audio.cache_version,
        "prepared_audio_normalization_sample_rate_hz": prepared_audio.normalization_sample_rate_hz,
        "prepared_audio_normalization_channels": prepared_audio.normalization_channels,
        "audio_file_size_bytes": audio_file_size_bytes,
        "audio_file_modified_at": audio_file_modified_at,
        "transcription_id": transcription.id if transcription else None,
        "transcription_status": transcription.status.value if transcription else None,
        "transcription_configuration_fingerprint": transcription.configuration_fingerprint if transcription else None,
        "transcription_source_audio_fingerprint": transcription.source_audio_fingerprint if transcription else None,
        "transcription_model_name": transcription.model_name if transcription else None,
        "transcription_device": transcription.device if transcription else None,
        "transcription_compute_type": transcription.compute_type if transcription else None,
        "transcription_requested_language": transcription.requested_language if transcription else None,
        "transcription_detected_language": transcription.detected_language if transcription else None,
        "transcription_engine_version": transcription.engine_version if transcription else None,
        "transcription_model_version": transcription.model_version if transcription else None,
        "transcription_full_text": transcription.full_text if transcription else None,
        "transcription_segment_count": transcription.segment_count if transcription else None,
        "transcription_word_timestamps_enabled": transcription.word_timestamps_enabled if transcription else None,
        "transcription_vad_enabled": transcription.vad_enabled if transcription else None,
        "transcription_updated_at": transcription.updated_at.isoformat() if transcription and transcription.updated_at else None,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_acoustic_configuration_fingerprint(options: AcousticAnalysisOptions, *, transcription: Transcription | None) -> str:
    normalized = normalize_acoustic_analysis_config(options)
    payload = {
        **normalized.to_dict(),
        "transcription_id": transcription.id if transcription else None,
        "transcription_configuration_fingerprint": transcription.configuration_fingerprint if transcription else None,
        "transcription_model_version": transcription.model_version if transcription else None,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def is_acoustic_analysis_stale(
    acoustic_analysis: AcousticAnalysis | None,
    *,
    prepared_audio: PreparedAudioAsset,
    transcription: Transcription | None,
    options: AcousticAnalysisOptions,
    audio_file_size_bytes: int | None = None,
    audio_file_modified_at: str | None = None,
) -> bool:
    if acoustic_analysis is None:
        return False
    if acoustic_analysis.status != AcousticAnalysisStatus.COMPLETED:
        return True
    if prepared_audio.status != PreparedAudioStatus.COMPLETED:
        return True
    if acoustic_analysis.prepared_audio_asset_id != prepared_audio.id:
        return True
    if acoustic_analysis.source_audio_fingerprint != build_acoustic_source_fingerprint(
        prepared_audio=prepared_audio,
        transcription=transcription,
        audio_file_size_bytes=audio_file_size_bytes,
        audio_file_modified_at=audio_file_modified_at,
    ):
        return True
    if acoustic_analysis.configuration_fingerprint != build_acoustic_configuration_fingerprint(
        options,
        transcription=transcription,
    ):
        return True
    if transcription is not None and transcription.status != TranscriptionStatus.COMPLETED:
        return True
    return False
