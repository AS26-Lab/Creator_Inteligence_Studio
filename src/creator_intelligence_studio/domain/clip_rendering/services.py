"""Servicios de dominio para renderizado de clips."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from creator_intelligence_studio.domain.clip_ranking.entities import RankedClipCandidate
from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingReviewStatus
from creator_intelligence_studio.domain.videos.entities import VideoAsset

from .errors import ClipRenderStateError, ClipRenderValidationError
from .value_objects import (
    ClipRenderProfile,
    ClipRenderProfileConfig,
    ClipRenderJobStatus,
    ClipRenderBatchStatus,
    ClipRenderSubtitleStyle,
    ClipRenderSubtitleConfig,
    SubtitleRenderMode,
    SubtitleRenderStylePreset,
    validate_render_bounds,
)


def _json_dumps(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_render_profile(profile: str) -> ClipRenderProfile:
    normalized = profile.strip().lower().replace("-", "_")
    aliases = {
        "source_quality": ClipRenderProfile.SOURCE_QUALITY,
        "sourcequality": ClipRenderProfile.SOURCE_QUALITY,
        "balanced": ClipRenderProfile.BALANCED,
        "compact": ClipRenderProfile.COMPACT,
        "draft": ClipRenderProfile.DRAFT,
    }
    if normalized not in aliases:
        raise ClipRenderValidationError("Perfil de render no reconocido.")
    return aliases[normalized]


def render_profile_config(profile: ClipRenderProfile) -> ClipRenderProfileConfig:
    if profile == ClipRenderProfile.SOURCE_QUALITY:
        return ClipRenderProfileConfig(
            profile=profile,
            container="mp4",
            video_codec="libx264",
            audio_codec="aac",
            pixel_format="yuv420p",
            preset="slow",
            crf=18,
            audio_bitrate_kbps=192,
            max_width=None,
            max_height=None,
            max_frame_rate=None,
            faststart=True,
            allow_fast_copy=False,
            hardware_acceleration=False,
        )
    if profile == ClipRenderProfile.COMPACT:
        return ClipRenderProfileConfig(
            profile=profile,
            container="mp4",
            video_codec="libx264",
            audio_codec="aac",
            pixel_format="yuv420p",
            preset="veryfast",
            crf=28,
            audio_bitrate_kbps=96,
            max_width=1280,
            max_height=720,
            max_frame_rate=30.0,
            faststart=True,
            allow_fast_copy=False,
            hardware_acceleration=False,
        )
    if profile == ClipRenderProfile.DRAFT:
        return ClipRenderProfileConfig(
            profile=profile,
            container="mp4",
            video_codec="libx264",
            audio_codec="aac",
            pixel_format="yuv420p",
            preset="ultrafast",
            crf=32,
            audio_bitrate_kbps=64,
            max_width=854,
            max_height=480,
            max_frame_rate=24.0,
            faststart=True,
            allow_fast_copy=False,
            hardware_acceleration=False,
        )
    return ClipRenderProfileConfig(
        profile=profile,
        container="mp4",
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        preset="medium",
        crf=23,
        audio_bitrate_kbps=128,
        max_width=1920,
        max_height=1080,
        max_frame_rate=60.0,
        faststart=True,
        allow_fast_copy=True,
        hardware_acceleration=False,
    )


def build_render_configuration_fingerprint(
    *,
    profile: ClipRenderProfile,
    profile_config: ClipRenderProfileConfig,
    expected_width: int | None,
    expected_height: int | None,
    expected_audio: bool,
    renderer_version: str,
    subtitle_config: ClipRenderSubtitleConfig | None = None,
) -> str:
    payload = {
        "profile": profile.value,
        "profile_config": profile_config.to_dict(),
        "expected_width": expected_width,
        "expected_height": expected_height,
        "expected_audio": expected_audio,
        "renderer_version": renderer_version,
    }
    if subtitle_config is not None and subtitle_config.mode != SubtitleRenderMode.NONE:
        payload["subtitle_config"] = subtitle_config.to_dict()
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def build_subtitle_style_fingerprint(style: ClipRenderSubtitleStyle | None) -> str | None:
    if style is None:
        return None
    return hashlib.sha256(_json_dumps(style.to_dict()).encode("utf-8")).hexdigest()


def build_source_fingerprint(video: VideoAsset, candidate: RankedClipCandidate | None, *, collection_id: str | None = None) -> str:
    payload = {
        "video_id": video.id,
        "source_path": video.source_path,
        "source_file_size_bytes": video.file_size_bytes,
        "source_file_modified_at": video.file_modified_at.isoformat() if video.file_modified_at else None,
        "candidate_id": candidate.id if candidate else None,
        "candidate_status": candidate.review_status.value if candidate else None,
        "candidate_bounds": (
            candidate.adjusted_start_seconds,
            candidate.adjusted_end_seconds,
        )
        if candidate
        else None,
        "collection_id": collection_id,
    }
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def candidate_is_eligible_for_render(candidate: RankedClipCandidate, *, explicit: bool = False) -> bool:
    if candidate.review_status in {ClipRankingReviewStatus.APPROVED, ClipRankingReviewStatus.SHORTLISTED}:
        return True
    if candidate.review_status == ClipRankingReviewStatus.NEEDS_REVIEW:
        return explicit
    return False


def render_state_label(status: ClipRenderJobStatus) -> str:
    labels = {
        ClipRenderJobStatus.QUEUED: "queued",
        ClipRenderJobStatus.VALIDATING: "validating",
        ClipRenderJobStatus.PREPARING: "preparing",
        ClipRenderJobStatus.RENDERING: "rendering",
        ClipRenderJobStatus.VERIFYING: "verifying",
        ClipRenderJobStatus.COMPLETED: "completed",
        ClipRenderJobStatus.COMPLETED_WITH_WARNINGS: "completed_with_warnings",
        ClipRenderJobStatus.FAILED: "failed",
        ClipRenderJobStatus.CANCELLED: "cancelled",
        ClipRenderJobStatus.INTERRUPTED: "interrupted",
        ClipRenderJobStatus.STALE: "stale",
        ClipRenderJobStatus.SOURCE_MISSING: "source_missing",
        ClipRenderJobStatus.INVALID_BOUNDS: "invalid_bounds",
        ClipRenderJobStatus.OUTPUT_EXISTS: "output_exists",
    }
    return labels[status]


def validate_render_job_state(job_status: ClipRenderJobStatus) -> None:
    if job_status not in {
        ClipRenderJobStatus.QUEUED,
        ClipRenderJobStatus.VALIDATING,
        ClipRenderJobStatus.PREPARING,
        ClipRenderJobStatus.RENDERING,
        ClipRenderJobStatus.VERIFYING,
        ClipRenderJobStatus.COMPLETED,
        ClipRenderJobStatus.COMPLETED_WITH_WARNINGS,
        ClipRenderJobStatus.FAILED,
        ClipRenderJobStatus.CANCELLED,
        ClipRenderJobStatus.INTERRUPTED,
        ClipRenderJobStatus.STALE,
        ClipRenderJobStatus.SOURCE_MISSING,
        ClipRenderJobStatus.INVALID_BOUNDS,
        ClipRenderJobStatus.OUTPUT_EXISTS,
    }:
        raise ClipRenderStateError("Estado de render no reconocido.")
