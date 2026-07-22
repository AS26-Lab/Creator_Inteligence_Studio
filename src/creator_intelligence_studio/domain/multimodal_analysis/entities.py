"""Entidades persistidas del analisis multimodal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import MultimodalAnalysisStatus, MultimodalCandidateType


@dataclass(frozen=True, slots=True)
class MultimodalAnalysis:
    """Registro persistido de analisis multimodal."""

    id: str
    video_asset_id: str
    transcription_id: str | None
    acoustic_analysis_id: str | None
    visual_analysis_id: str | None
    status: MultimodalAnalysisStatus
    analyzer_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    duration_seconds: float
    window_size_seconds: float
    window_count: int
    candidate_count: int
    high_activity_candidate_count: int
    transition_candidate_count: int
    silence_candidate_count: int
    started_at: datetime
    completed_at: datetime
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "video_asset_id": self.video_asset_id,
            "transcription_id": self.transcription_id,
            "acoustic_analysis_id": self.acoustic_analysis_id,
            "visual_analysis_id": self.visual_analysis_id,
            "status": self.status.value,
            "analyzer_version": self.analyzer_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "duration_seconds": self.duration_seconds,
            "window_size_seconds": self.window_size_seconds,
            "window_count": self.window_count,
            "candidate_count": self.candidate_count,
            "high_activity_candidate_count": self.high_activity_candidate_count,
            "transition_candidate_count": self.transition_candidate_count,
            "silence_candidate_count": self.silence_candidate_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class MultimodalTimelineWindow:
    """Ventana multimodal persistida."""

    id: str
    multimodal_analysis_id: str
    window_index: int
    start_seconds: float
    end_seconds: float
    transcript_text: str
    word_count: int
    speech_ratio: float
    silence_ratio: float
    speech_rate: float | None
    acoustic_energy: float
    acoustic_change: float
    visual_motion: float
    visual_change: float
    brightness: float
    cut_count: int
    scene_index: int | None
    acoustic_event_count: int
    visual_event_count: int
    combined_activity_score: float
    transition_score: float
    novelty_score: float
    confidence: float
    evidence_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "multimodal_analysis_id": self.multimodal_analysis_id,
            "window_index": self.window_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "transcript_text": self.transcript_text,
            "word_count": self.word_count,
            "speech_ratio": self.speech_ratio,
            "silence_ratio": self.silence_ratio,
            "speech_rate": self.speech_rate,
            "acoustic_energy": self.acoustic_energy,
            "acoustic_change": self.acoustic_change,
            "visual_motion": self.visual_motion,
            "visual_change": self.visual_change,
            "brightness": self.brightness,
            "cut_count": self.cut_count,
            "scene_index": self.scene_index,
            "acoustic_event_count": self.acoustic_event_count,
            "visual_event_count": self.visual_event_count,
            "combined_activity_score": self.combined_activity_score,
            "transition_score": self.transition_score,
            "novelty_score": self.novelty_score,
            "confidence": self.confidence,
            "evidence_json": self.evidence_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class MultimodalMomentCandidate:
    """Candidato de momento multimodal persistido."""

    id: str
    multimodal_analysis_id: str
    candidate_index: int
    start_seconds: float
    end_seconds: float
    candidate_type: MultimodalCandidateType
    score: float
    confidence: float
    title: str
    summary: str
    evidence_json: str
    source_window_start: float | None
    source_window_end: float | None
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "multimodal_analysis_id": self.multimodal_analysis_id,
            "candidate_index": self.candidate_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "candidate_type": self.candidate_type.value,
            "score": self.score,
            "confidence": self.confidence,
            "title": self.title,
            "summary": self.summary,
            "evidence_json": self.evidence_json,
            "source_window_start": self.source_window_start,
            "source_window_end": self.source_window_end,
            "created_at": to_iso_z(self.created_at),
        }

