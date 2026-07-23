"""Construccion de planes de render reproducibles."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_studio.domain.clip_ranking.entities import ClipCollectionItem, RankedClipCandidate
from creator_intelligence_studio.domain.clip_rendering.services import (
    build_render_configuration_fingerprint,
    build_source_fingerprint,
    render_profile_config,
)
from creator_intelligence_studio.domain.clip_rendering.value_objects import ClipRenderPlan, ClipRenderProfile, validate_render_bounds
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.infrastructure.clip_rendering.filename_builder import build_render_filename, build_render_output_path


def _clip_bounds(candidate: RankedClipCandidate) -> tuple[float, float]:
    return candidate.adjusted_start_seconds, candidate.adjusted_end_seconds


def build_render_plan(
    *,
    job_id: str,
    video: VideoAsset,
    creator_slug: str,
    project_slug: str,
    candidate: RankedClipCandidate | None,
    collection_item: ClipCollectionItem | None,
    profile: ClipRenderProfile,
    source_duration_seconds: float | None,
    output_root: Path,
    output_path: Path | None = None,
    custom_name: str | None = None,
    renderer_version: str = "v1",
) -> ClipRenderPlan:
    if candidate is not None:
        start_seconds, end_seconds = _clip_bounds(candidate)
        clip_title = candidate.explanation.get("title") if isinstance(candidate.explanation, dict) else None
        expected_audio = True
    elif collection_item is not None:
        raise ValueError("La version inicial requiere un candidato para el plan.")
    else:
        raise ValueError("Se requiere un candidato o item de coleccion.")
    duration_seconds = validate_render_bounds(
        start_seconds,
        end_seconds,
        source_duration_seconds,
        minimum_duration_seconds=1.0,
        maximum_duration_seconds=90.0,
    )
    config = render_profile_config(profile)
    filename = build_render_filename(
        video_title=video.title,
        clip_title=clip_title,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        profile=profile,
        extension=config.container,
        suffix=custom_name,
    )
    final_path = output_path or build_render_output_path(
        output_root,
        creator_slug=creator_slug,
        project_slug=project_slug,
        video_title=video.title,
        filename=filename,
    )
    temporary_output_path = final_path.with_name(f"{final_path.stem}.part{final_path.suffix}")
    source_fingerprint = build_source_fingerprint(video, candidate, collection_id=collection_item.collection_id if collection_item else None)
    configuration_fingerprint = build_render_configuration_fingerprint(
        profile=profile,
        profile_config=config,
        expected_width=getattr(video, "width", None),
        expected_height=getattr(video, "height", None),
        expected_audio=expected_audio,
        renderer_version=renderer_version,
    )
    return ClipRenderPlan(
        job_id=job_id,
        video_asset_id=video.id,
        creator_slug=creator_slug,
        project_slug=project_slug,
        ranked_clip_candidate_id=candidate.id if candidate else None,
        collection_id=collection_item.collection_id if collection_item else None,
        source_path=video.source_path,
        source_path_snapshot=video.source_path,
        source_fingerprint=source_fingerprint,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        profile=profile,
        output_path=str(final_path),
        temporary_output_path=str(temporary_output_path),
        container=config.container,
        video_codec=config.video_codec,
        audio_codec=config.audio_codec,
        pixel_format=config.pixel_format,
        preset=config.preset,
        crf=config.crf,
        audio_bitrate_kbps=config.audio_bitrate_kbps,
        max_width=config.max_width,
        max_height=config.max_height,
        max_frame_rate=config.max_frame_rate,
        faststart=config.faststart,
        allow_fast_copy=config.allow_fast_copy,
        hardware_acceleration=config.hardware_acceleration,
        expected_width=getattr(video, "width", None),
        expected_height=getattr(video, "height", None),
        expected_audio=expected_audio,
        configuration_fingerprint=configuration_fingerprint,
        renderer_version=renderer_version,
        custom_name=custom_name,
    )
