"""Reglas de dominio para analisis visual."""

from __future__ import annotations

from hashlib import sha256
import json

from creator_intelligence_studio.domain.media.entities import VideoInspection
from creator_intelligence_studio.domain.videos.entities import VideoAsset

from .entities import VisualAnalysis
from .value_objects import VisualAnalysisOptions, VisualAnalysisStatus


def normalize_visual_analysis_config(options: VisualAnalysisOptions) -> VisualAnalysisOptions:
    from .value_objects import normalize_visual_analysis_config as _normalize

    return _normalize(options)


def validate_visual_analysis_options(options: VisualAnalysisOptions) -> None:
    normalize_visual_analysis_config(options)


def build_visual_source_fingerprint(
    *,
    video: VideoAsset,
    inspection: VideoInspection | None,
    source_file_size_bytes: int | None = None,
    source_file_modified_at: str | None = None,
) -> str:
    payload = {
        "video_id": video.id,
        "video_source_path": video.source_path,
        "video_file_size_bytes": source_file_size_bytes if source_file_size_bytes is not None else video.file_size_bytes,
        "video_file_modified_at": source_file_modified_at
        if source_file_modified_at is not None
        else (video.file_modified_at.isoformat() if video.file_modified_at else None),
        "inspection_id": inspection.id if inspection else None,
        "inspection_status": inspection.inspection_status.value if inspection else None,
        "inspection_source_file_size_bytes": inspection.source_file_size_bytes if inspection else None,
        "inspection_source_file_modified_at": inspection.source_file_modified_at.isoformat()
        if inspection and inspection.source_file_modified_at
        else None,
        "inspection_duration_seconds": inspection.duration_seconds if inspection else None,
        "inspection_width": inspection.width if inspection else None,
        "inspection_height": inspection.height if inspection else None,
        "inspection_average_frame_rate": inspection.average_frame_rate.to_text() if inspection else None,
        "inspection_frame_rate": inspection.frame_rate.to_text() if inspection else None,
        "inspection_rotation_degrees": inspection.rotation_degrees if inspection else None,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_visual_configuration_fingerprint(options: VisualAnalysisOptions) -> str:
    normalized = normalize_visual_analysis_config(options)
    return sha256(json.dumps(normalized.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def is_visual_analysis_stale(
    visual_analysis: VisualAnalysis | None,
    *,
    video: VideoAsset,
    inspection: VideoInspection | None,
    options: VisualAnalysisOptions,
    source_file_size_bytes: int | None = None,
    source_file_modified_at: str | None = None,
) -> bool:
    if visual_analysis is None:
        return False
    if visual_analysis.status != VisualAnalysisStatus.COMPLETED:
        return True
    if inspection is None:
        return True
    if visual_analysis.source_inspection_id != inspection.id:
        return True
    if visual_analysis.source_fingerprint != build_visual_source_fingerprint(
        video=video,
        inspection=inspection,
        source_file_size_bytes=source_file_size_bytes,
        source_file_modified_at=source_file_modified_at,
    ):
        return True
    if visual_analysis.source_file_size_bytes != (source_file_size_bytes if source_file_size_bytes is not None else video.file_size_bytes):
        return True
    expected_modified = source_file_modified_at if source_file_modified_at is not None else (video.file_modified_at.isoformat() if video.file_modified_at else None)
    current_modified = visual_analysis.source_file_modified_at.isoformat() if visual_analysis.source_file_modified_at else None
    if current_modified != expected_modified:
        return True
    if visual_analysis.configuration_fingerprint != build_visual_configuration_fingerprint(options):
        return True
    if visual_analysis.analyzer_version != options.analyzer_version.strip():
        return True
    return False
