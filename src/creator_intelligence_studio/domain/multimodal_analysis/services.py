"""Servicios de dominio para analisis multimodal."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis
from creator_intelligence_studio.domain.transcription.entities import Transcription
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis

from .errors import MultimodalAnalysisValidationError
from .value_objects import MultimodalAnalysisOptions, normalize_multimodal_analysis_config


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def build_multimodal_configuration_fingerprint(options: MultimodalAnalysisOptions) -> str:
    normalized = normalize_multimodal_analysis_config(options)
    digest = hashlib.sha256(_json_dumps(normalized.to_dict()).encode("utf-8")).hexdigest()
    return digest


def build_multimodal_source_fingerprint(
    *,
    transcription: Transcription | None,
    acoustic_analysis: AcousticAnalysis | None,
    visual_analysis: VisualAnalysis | None,
    duration_seconds: float | None,
) -> str:
    payload = {
        "transcription": transcription.configuration_fingerprint if transcription else None,
        "transcription_id": transcription.id if transcription else None,
        "transcription_status": transcription.status.value if transcription else None,
        "acoustic": acoustic_analysis.configuration_fingerprint if acoustic_analysis else None,
        "acoustic_id": acoustic_analysis.id if acoustic_analysis else None,
        "acoustic_status": acoustic_analysis.status.value if acoustic_analysis else None,
        "visual": visual_analysis.configuration_fingerprint if visual_analysis else None,
        "visual_id": visual_analysis.id if visual_analysis else None,
        "visual_status": visual_analysis.status.value if visual_analysis else None,
        "duration_seconds": duration_seconds,
    }
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def is_multimodal_analysis_stale(
    analysis,
    *,
    transcription: Transcription | None,
    acoustic_analysis: AcousticAnalysis | None,
    visual_analysis: VisualAnalysis | None,
    options: MultimodalAnalysisOptions | None = None,
    duration_seconds: float | None = None,
) -> bool:
    if analysis is None:
        return False
    if analysis.status.value != "completed":
        return True
    if options is not None:
        expected = build_multimodal_configuration_fingerprint(options)
        if analysis.configuration_fingerprint != expected:
            return True
    expected_source = build_multimodal_source_fingerprint(
        transcription=transcription,
        acoustic_analysis=acoustic_analysis,
        visual_analysis=visual_analysis,
        duration_seconds=duration_seconds,
    )
    return analysis.source_fingerprint != expected_source

