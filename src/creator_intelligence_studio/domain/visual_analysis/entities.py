"""Entidades de analisis visual tecnico."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .value_objects import (
    VisualActivityLabel,
    VisualAnalysisStatus,
    VisualEventType,
)


@dataclass(frozen=True, slots=True)
class VisualAnalysis:
    """Registro persistido de analisis visual."""

    id: str
    video_asset_id: str
    source_inspection_id: str | None
    status: VisualAnalysisStatus
    analyzer_version: str
    configuration_fingerprint: str
    source_fingerprint: str
    source_file_size_bytes: int | None
    source_file_modified_at: datetime | None
    duration_seconds: float | None
    sampled_frame_count: int
    detected_cut_count: int
    detected_scene_count: int
    keyframe_count: int
    static_segment_count: int
    black_frame_event_count: int
    freeze_event_count: int
    average_brightness: float | None
    brightness_variation: float | None
    average_contrast: float | None
    average_motion: float | None
    peak_motion: float | None
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
            "source_inspection_id": self.source_inspection_id,
            "status": self.status.value,
            "analyzer_version": self.analyzer_version,
            "configuration_fingerprint": self.configuration_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "source_file_size_bytes": self.source_file_size_bytes,
            "source_file_modified_at": self.source_file_modified_at.isoformat() if self.source_file_modified_at else None,
            "duration_seconds": self.duration_seconds,
            "sampled_frame_count": self.sampled_frame_count,
            "detected_cut_count": self.detected_cut_count,
            "detected_scene_count": self.detected_scene_count,
            "keyframe_count": self.keyframe_count,
            "static_segment_count": self.static_segment_count,
            "black_frame_event_count": self.black_frame_event_count,
            "freeze_event_count": self.freeze_event_count,
            "average_brightness": self.average_brightness,
            "brightness_variation": self.brightness_variation,
            "average_contrast": self.average_contrast,
            "average_motion": self.average_motion,
            "peak_motion": self.peak_motion,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class VisualTimelineWindow:
    """Ventana temporal persistida del analisis visual."""

    id: str
    visual_analysis_id: str
    window_index: int
    start_seconds: float
    end_seconds: float
    sampled_frame_count: int
    brightness: float
    contrast: float
    saturation: float
    motion_score: float
    color_change_score: float
    is_static: bool
    is_black: bool
    is_possible_freeze: bool
    activity_label: VisualActivityLabel
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "visual_analysis_id": self.visual_analysis_id,
            "window_index": self.window_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "sampled_frame_count": self.sampled_frame_count,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "motion_score": self.motion_score,
            "color_change_score": self.color_change_score,
            "is_static": self.is_static,
            "is_black": self.is_black,
            "is_possible_freeze": self.is_possible_freeze,
            "activity_label": self.activity_label.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class VisualScene:
    """Escena persistida."""

    id: str
    visual_analysis_id: str
    scene_index: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    representative_keyframe_path: str | None
    cut_in_score: float
    average_motion: float
    average_brightness: float
    average_contrast: float
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "visual_analysis_id": self.visual_analysis_id,
            "scene_index": self.scene_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "representative_keyframe_path": self.representative_keyframe_path,
            "cut_in_score": self.cut_in_score,
            "average_motion": self.average_motion,
            "average_brightness": self.average_brightness,
            "average_contrast": self.average_contrast,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class VisualEvent:
    """Evento candidato persistido."""

    id: str
    visual_analysis_id: str
    event_index: int
    start_seconds: float
    end_seconds: float
    event_type: VisualEventType
    confidence: float
    evidence_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "visual_analysis_id": self.visual_analysis_id,
            "event_index": self.event_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "event_type": self.event_type.value,
            "confidence": self.confidence,
            "evidence_json": self.evidence_json,
            "created_at": self.created_at.isoformat(),
        }
