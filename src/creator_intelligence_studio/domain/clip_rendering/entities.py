"""Entidades persistidas de renderizado de clips."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from creator_intelligence_studio.shared.dates import to_iso_z

from .value_objects import (
    ClipRenderArtifactType,
    ClipRenderBatchStatus,
    ClipRenderDeliveryStatus,
    ClipRenderJobStatus,
    ClipRenderProfile,
    SubtitleRenderMode,
    SubtitleRenderStylePreset,
)


@dataclass(frozen=True, slots=True)
class ClipRenderJob:
    id: str
    video_asset_id: str
    ranked_clip_candidate_id: str | None
    collection_id: str | None
    status: ClipRenderJobStatus
    render_profile: ClipRenderProfile
    source_path_snapshot: str
    source_fingerprint: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    output_path: str
    output_container: str
    video_codec: str
    audio_codec: str
    width: int | None
    height: int | None
    frame_rate: float | None
    audio_sample_rate: int | None
    configuration_fingerprint: str
    renderer_version: str
    progress_percent: float
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    retry_count: int
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
            "ranked_clip_candidate_id": self.ranked_clip_candidate_id,
            "collection_id": self.collection_id,
            "status": self.status.value,
            "render_profile": self.render_profile.value,
            "source_path_snapshot": self.source_path_snapshot,
            "source_fingerprint": self.source_fingerprint,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "output_path": self.output_path,
            "output_container": self.output_container,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "width": self.width,
            "height": self.height,
            "frame_rate": self.frame_rate,
            "audio_sample_rate": self.audio_sample_rate,
            "configuration_fingerprint": self.configuration_fingerprint,
            "renderer_version": self.renderer_version,
            "progress_percent": self.progress_percent,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "cancelled_at": to_iso_z(self.cancelled_at),
            "retry_count": self.retry_count,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderArtifact:
    id: str
    render_job_id: str
    artifact_type: ClipRenderArtifactType
    managed_path: str
    fingerprint: str
    size_bytes: int | None
    duration_seconds: float | None
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None
    frame_rate: float | None
    audio_sample_rate: int | None
    verified: bool
    verification_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "render_job_id": self.render_job_id,
            "artifact_type": self.artifact_type.value,
            "managed_path": self.managed_path,
            "fingerprint": self.fingerprint,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "width": self.width,
            "height": self.height,
            "frame_rate": self.frame_rate,
            "audio_sample_rate": self.audio_sample_rate,
            "verified": self.verified,
            "verification_json": self.verification_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderEvent:
    id: str
    render_job_id: str
    event_index: int
    event_type: str
    progress_percent: float
    message: str
    details_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "render_job_id": self.render_job_id,
            "event_index": self.event_index,
            "event_type": self.event_type,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "details_json": self.details_json,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderBatch:
    id: str
    collection_id: str | None
    video_asset_id: str | None
    name: str
    status: ClipRenderBatchStatus
    job_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "video_asset_id": self.video_asset_id,
            "name": self.name,
            "status": self.status.value,
            "job_count": self.job_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "cancelled_count": self.cancelled_count,
            "started_at": to_iso_z(self.started_at),
            "completed_at": to_iso_z(self.completed_at),
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderBatchItem:
    id: str
    batch_id: str
    render_job_id: str
    item_index: int
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "render_job_id": self.render_job_id,
            "item_index": self.item_index,
            "created_at": to_iso_z(self.created_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderDelivery:
    id: str
    render_job_id: str
    subtitle_track_id: str | None
    subtitle_track_version: int | None
    subtitle_track_fingerprint: str | None
    subtitle_mode: SubtitleRenderMode
    subtitle_format: str | None
    style_preset: SubtitleRenderStylePreset | None
    style_json: str
    source_export_path: str | None
    source_export_fingerprint: str | None
    expected_cue_count: int
    rendered_cue_count: int
    output_path: str | None
    manifest_path: str | None
    configuration_fingerprint: str
    status: ClipRenderDeliveryStatus
    progress_percent: float
    warning_code: str | None
    warning_message: str | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "render_job_id": self.render_job_id,
            "subtitle_track_id": self.subtitle_track_id,
            "subtitle_track_version": self.subtitle_track_version,
            "subtitle_track_fingerprint": self.subtitle_track_fingerprint,
            "subtitle_mode": self.subtitle_mode.value,
            "subtitle_format": self.subtitle_format,
            "style_preset": self.style_preset.value if self.style_preset else None,
            "style_json": self.style_json,
            "source_export_path": self.source_export_path,
            "source_export_fingerprint": self.source_export_fingerprint,
            "expected_cue_count": self.expected_cue_count,
            "rendered_cue_count": self.rendered_cue_count,
            "output_path": self.output_path,
            "manifest_path": self.manifest_path,
            "configuration_fingerprint": self.configuration_fingerprint,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "warning_code": self.warning_code,
            "warning_message": self.warning_message,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": to_iso_z(self.created_at),
            "updated_at": to_iso_z(self.updated_at),
            "completed_at": to_iso_z(self.completed_at),
            "cancelled_at": to_iso_z(self.cancelled_at),
        }


@dataclass(frozen=True, slots=True)
class ClipRenderDeliveryArtifact:
    id: str
    delivery_id: str
    artifact_type: ClipRenderArtifactType
    managed_path: str
    fingerprint: str
    size_bytes: int | None
    verified: bool
    verification_json: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "delivery_id": self.delivery_id,
            "artifact_type": self.artifact_type.value,
            "managed_path": self.managed_path,
            "fingerprint": self.fingerprint,
            "size_bytes": self.size_bytes,
            "verified": self.verified,
            "verification_json": self.verification_json,
            "created_at": to_iso_z(self.created_at),
        }
