"""Extraccion de candidates de frame para miniaturas."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.creative_packaging.entities import ThumbnailFrameCandidate
from creator_intelligence_studio.domain.creative_packaging.value_objects import PackagingAssetStatus
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
from creator_intelligence_studio.infrastructure.visual_analysis.frame_metrics import compute_frame_metrics
from creator_intelligence_studio.infrastructure.visual_analysis.frame_sampler import sample_frames
from creator_intelligence_studio.shared.dates import utc_now


def _fingerprint(path: Path, timestamp_seconds: float) -> str:
    payload = f"{path.resolve()}|{timestamp_seconds:.3f}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_frame_candidates(
    *,
    creator_id: str,
    video_asset_id: str,
    video_path: Path,
    duration_seconds: float | None = None,
    ffmpeg_path: Path | None = None,
    ffprobe_path: Path | None = None,
    timestamps: list[float] | None = None,
) -> tuple[ThumbnailFrameCandidate, ...]:
    locator = MediaToolLocator()
    ffmpeg = ffmpeg_path or Path(locator.locate("ffmpeg").path or "ffmpeg")
    frames = sample_frames(
        ffmpeg_path=ffmpeg,
        source_path=video_path,
        duration_seconds=duration_seconds,
        source_width=None,
        source_height=None,
        sample_fps=0.5,
        max_sample_frames=6,
        target_width=160,
        target_height=90,
        timeout_seconds=30.0,
    )
    metrics = compute_frame_metrics(frames)
    result: list[ThumbnailFrameCandidate] = []
    for frame, metric in zip(frames, metrics):
        frame_path = video_path.with_suffix("")
        candidate = ThumbnailFrameCandidate(
            id=str(uuid4()),
            creator_id=creator_id,
            video_asset_id=video_asset_id,
            timestamp_seconds=frame.timestamp_seconds,
            frame_path=str(frame_path),
            frame_fingerprint=_fingerprint(video_path, frame.timestamp_seconds),
            width=frame.width,
            height=frame.height,
            sharpness_score=float(metric.motion_score),
            brightness_score=float(metric.brightness),
            contrast_score=float(metric.contrast),
            face_presence=None,
            motion_blur_score=float(metric.motion_score),
            quality_status=metric.activity_label.value,
            warning_codes_json="[]",
            creator_decision=None,
            created_at=utc_now(),
        )
        result.append(candidate)
    return tuple(result)

