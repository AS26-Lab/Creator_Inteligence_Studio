"""Repositorio SQLite para audio preparado."""

from __future__ import annotations

import sqlite3

from creator_intelligence_studio.domain.audio.entities import PreparedAudioAsset, PreparedAudioStatus
from creator_intelligence_studio.domain.audio.repositories import PreparedAudioRepository
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _bool_from_db(value: object) -> bool | None:
    if value is None:
        return None
    return bool(int(value))


def _row_to_asset(row: sqlite3.Row) -> PreparedAudioAsset:
    return PreparedAudioAsset(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        source_inspection_id=row["source_inspection_id"],
        status=PreparedAudioStatus(row["status"]),
        relative_cache_path=row["relative_cache_path"],
        metadata_relative_path=row["metadata_relative_path"],
        format_name=row["format_name"],
        codec_name=row["codec_name"],
        sample_rate_hz=row["sample_rate_hz"],
        channels=row["channels"],
        channel_layout=row["channel_layout"],
        bit_depth=row["bit_depth"],
        duration_seconds=row["duration_seconds"],
        file_size_bytes=row["file_size_bytes"],
        source_file_size_bytes=row["source_file_size_bytes"],
        source_file_modified_at=from_iso_z(row["source_file_modified_at"]),
        selected_stream_index=row["selected_stream_index"],
        selected_stream_codec_name=row["selected_stream_codec_name"],
        selected_stream_channels=row["selected_stream_channels"],
        selected_stream_channel_layout=row["selected_stream_channel_layout"],
        selected_stream_sample_rate_hz=row["selected_stream_sample_rate_hz"],
        selected_stream_language=row["selected_stream_language"],
        selected_stream_is_default=_bool_from_db(row["selected_stream_is_default"]),
        extraction_started_at=from_iso_z(row["extraction_started_at"]),
        extraction_completed_at=from_iso_z(row["extraction_completed_at"]),
        ffmpeg_version=row["ffmpeg_version"],
        cache_version=row["cache_version"],
        normalization_sample_rate_hz=row["normalization_sample_rate_hz"],
        normalization_channels=row["normalization_channels"],
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


class SQLitePreparedAudioRepository(PreparedAudioRepository):
    """Repositorio de audio preparado sobre SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(self, asset: PreparedAudioAsset) -> PreparedAudioAsset:
        payload = asset.to_dict()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO prepared_audio_assets (
                    id, video_asset_id, source_inspection_id, status,
                    relative_cache_path, metadata_relative_path, format_name, codec_name,
                    sample_rate_hz, channels, channel_layout, bit_depth, duration_seconds,
                    file_size_bytes, source_file_size_bytes, source_file_modified_at,
                    selected_stream_index, selected_stream_codec_name,
                    selected_stream_channels, selected_stream_channel_layout,
                    selected_stream_sample_rate_hz, selected_stream_language,
                    selected_stream_is_default, extraction_started_at,
                    extraction_completed_at, ffmpeg_version, cache_version,
                    normalization_sample_rate_hz, normalization_channels,
                    warning_code, warning_message, error_code, error_message,
                    created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :source_inspection_id, :status,
                    :relative_cache_path, :metadata_relative_path, :format_name, :codec_name,
                    :sample_rate_hz, :channels, :channel_layout, :bit_depth, :duration_seconds,
                    :file_size_bytes, :source_file_size_bytes, :source_file_modified_at,
                    :selected_stream_index, :selected_stream_codec_name,
                    :selected_stream_channels, :selected_stream_channel_layout,
                    :selected_stream_sample_rate_hz, :selected_stream_language,
                    :selected_stream_is_default, :extraction_started_at,
                    :extraction_completed_at, :ffmpeg_version, :cache_version,
                    :normalization_sample_rate_hz, :normalization_channels,
                    :warning_code, :warning_message, :error_code, :error_message,
                    :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    source_inspection_id = excluded.source_inspection_id,
                    status = excluded.status,
                    relative_cache_path = excluded.relative_cache_path,
                    metadata_relative_path = excluded.metadata_relative_path,
                    format_name = excluded.format_name,
                    codec_name = excluded.codec_name,
                    sample_rate_hz = excluded.sample_rate_hz,
                    channels = excluded.channels,
                    channel_layout = excluded.channel_layout,
                    bit_depth = excluded.bit_depth,
                    duration_seconds = excluded.duration_seconds,
                    file_size_bytes = excluded.file_size_bytes,
                    source_file_size_bytes = excluded.source_file_size_bytes,
                    source_file_modified_at = excluded.source_file_modified_at,
                    selected_stream_index = excluded.selected_stream_index,
                    selected_stream_codec_name = excluded.selected_stream_codec_name,
                    selected_stream_channels = excluded.selected_stream_channels,
                    selected_stream_channel_layout = excluded.selected_stream_channel_layout,
                    selected_stream_sample_rate_hz = excluded.selected_stream_sample_rate_hz,
                    selected_stream_language = excluded.selected_stream_language,
                    selected_stream_is_default = excluded.selected_stream_is_default,
                    extraction_started_at = excluded.extraction_started_at,
                    extraction_completed_at = excluded.extraction_completed_at,
                    ffmpeg_version = excluded.ffmpeg_version,
                    cache_version = excluded.cache_version,
                    normalization_sample_rate_hz = excluded.normalization_sample_rate_hz,
                    normalization_channels = excluded.normalization_channels,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM prepared_audio_assets WHERE video_asset_id = ?",
                (asset.video_asset_id,),
            ).fetchone()
        return _row_to_asset(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> PreparedAudioAsset | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM prepared_audio_assets WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
        return _row_to_asset(row) if row else None

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM prepared_audio_assets WHERE video_asset_id = ?",
                (video_asset_id,),
            )
        return cursor.rowcount > 0
