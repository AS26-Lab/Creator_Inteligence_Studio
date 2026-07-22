"""Repositorio SQLite para inspecciones tecnicas de video."""

from __future__ import annotations

import sqlite3

from creator_intelligence_studio.domain.media.entities import VideoInspection, VideoInspectionStatus
from creator_intelligence_studio.domain.media.repositories import VideoInspectionRepository
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _row_to_inspection(row: sqlite3.Row) -> VideoInspection:
    return VideoInspection(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        inspection_status=VideoInspectionStatus(row["inspection_status"]),
        inspected_at=from_iso_z(row["inspected_at"]) or utc_now(),
        source_file_size_bytes=row["source_file_size_bytes"],
        source_file_modified_at=from_iso_z(row["source_file_modified_at"]),
        duration_seconds=row["duration_seconds"],
        format_name=row["format_name"],
        format_long_name=row["format_long_name"],
        overall_bitrate=row["overall_bitrate"],
        stream_count=row["stream_count"],
        video_stream_count=row["video_stream_count"],
        audio_stream_count=row["audio_stream_count"],
        subtitle_stream_count=row["subtitle_stream_count"],
        width=row["width"],
        height=row["height"],
        display_aspect_ratio=row["display_aspect_ratio"],
        pixel_aspect_ratio=row["pixel_aspect_ratio"],
        frame_rate_numerator=row["frame_rate_numerator"],
        frame_rate_denominator=row["frame_rate_denominator"],
        average_frame_rate_numerator=row["average_frame_rate_numerator"],
        average_frame_rate_denominator=row["average_frame_rate_denominator"],
        video_codec=row["video_codec"],
        video_codec_profile=row["video_codec_profile"],
        pixel_format=row["pixel_format"],
        video_bitrate=row["video_bitrate"],
        audio_codec=row["audio_codec"],
        audio_sample_rate=row["audio_sample_rate"],
        audio_channels=row["audio_channels"],
        audio_channel_layout=row["audio_channel_layout"],
        audio_bitrate=row["audio_bitrate"],
        rotation_degrees=row["rotation_degrees"],
        metadata_json=row["metadata_json"],
        ffprobe_version=row["ffprobe_version"],
        ffprobe_path=row["ffprobe_path"],
        ffmpeg_version=row["ffmpeg_version"],
        ffmpeg_path=row["ffmpeg_path"],
        thumbnail_relative_path=row["thumbnail_relative_path"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLiteVideoInspectionRepository(VideoInspectionRepository):
    """Repositorio de inspecciones tecnicas sobre SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(self, inspection: VideoInspection) -> VideoInspection:
        payload = inspection.to_dict()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO video_inspections (
                    id, video_asset_id, inspection_status, inspected_at,
                    source_file_size_bytes, source_file_modified_at, duration_seconds,
                    format_name, format_long_name, overall_bitrate, stream_count,
                    video_stream_count, audio_stream_count, subtitle_stream_count,
                    width, height, display_aspect_ratio, pixel_aspect_ratio,
                    frame_rate_numerator, frame_rate_denominator,
                    average_frame_rate_numerator, average_frame_rate_denominator,
                    video_codec, video_codec_profile, pixel_format, video_bitrate,
                    audio_codec, audio_sample_rate, audio_channels, audio_channel_layout,
                    audio_bitrate, rotation_degrees, metadata_json, ffprobe_version,
                    ffprobe_path, ffmpeg_version, ffmpeg_path, thumbnail_relative_path,
                    error_code, error_message, created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :inspection_status, :inspected_at,
                    :source_file_size_bytes, :source_file_modified_at, :duration_seconds,
                    :format_name, :format_long_name, :overall_bitrate, :stream_count,
                    :video_stream_count, :audio_stream_count, :subtitle_stream_count,
                    :width, :height, :display_aspect_ratio, :pixel_aspect_ratio,
                    :frame_rate_numerator, :frame_rate_denominator,
                    :average_frame_rate_numerator, :average_frame_rate_denominator,
                    :video_codec, :video_codec_profile, :pixel_format, :video_bitrate,
                    :audio_codec, :audio_sample_rate, :audio_channels, :audio_channel_layout,
                    :audio_bitrate, :rotation_degrees, :metadata_json, :ffprobe_version,
                    :ffprobe_path, :ffmpeg_version, :ffmpeg_path, :thumbnail_relative_path,
                    :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    inspection_status = excluded.inspection_status,
                    inspected_at = excluded.inspected_at,
                    source_file_size_bytes = excluded.source_file_size_bytes,
                    source_file_modified_at = excluded.source_file_modified_at,
                    duration_seconds = excluded.duration_seconds,
                    format_name = excluded.format_name,
                    format_long_name = excluded.format_long_name,
                    overall_bitrate = excluded.overall_bitrate,
                    stream_count = excluded.stream_count,
                    video_stream_count = excluded.video_stream_count,
                    audio_stream_count = excluded.audio_stream_count,
                    subtitle_stream_count = excluded.subtitle_stream_count,
                    width = excluded.width,
                    height = excluded.height,
                    display_aspect_ratio = excluded.display_aspect_ratio,
                    pixel_aspect_ratio = excluded.pixel_aspect_ratio,
                    frame_rate_numerator = excluded.frame_rate_numerator,
                    frame_rate_denominator = excluded.frame_rate_denominator,
                    average_frame_rate_numerator = excluded.average_frame_rate_numerator,
                    average_frame_rate_denominator = excluded.average_frame_rate_denominator,
                    video_codec = excluded.video_codec,
                    video_codec_profile = excluded.video_codec_profile,
                    pixel_format = excluded.pixel_format,
                    video_bitrate = excluded.video_bitrate,
                    audio_codec = excluded.audio_codec,
                    audio_sample_rate = excluded.audio_sample_rate,
                    audio_channels = excluded.audio_channels,
                    audio_channel_layout = excluded.audio_channel_layout,
                    audio_bitrate = excluded.audio_bitrate,
                    rotation_degrees = excluded.rotation_degrees,
                    metadata_json = excluded.metadata_json,
                    ffprobe_version = excluded.ffprobe_version,
                    ffprobe_path = excluded.ffprobe_path,
                    ffmpeg_version = excluded.ffmpeg_version,
                    ffmpeg_path = excluded.ffmpeg_path,
                    thumbnail_relative_path = excluded.thumbnail_relative_path,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM video_inspections WHERE video_asset_id = ?",
                (inspection.video_asset_id,),
            ).fetchone()
        return _row_to_inspection(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> VideoInspection | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM video_inspections WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
        return _row_to_inspection(row) if row else None
