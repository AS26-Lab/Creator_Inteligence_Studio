"""Repositorio SQLite para transcripciones locales."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
import sqlite3

from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.repositories import TranscriptionRepository
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _bool_to_db(value: bool) -> int:
    return 1 if value else 0


def _row_to_transcription(row: sqlite3.Row) -> Transcription:
    return Transcription(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        prepared_audio_asset_id=row["prepared_audio_asset_id"],
        status=TranscriptionStatus(row["status"]),
        engine=row["engine"],
        model_name=row["model_name"],
        device=row["device"],
        compute_type=row["compute_type"],
        requested_language=row["requested_language"],
        detected_language=row["detected_language"],
        language_probability=row["language_probability"],
        full_text=row["full_text"],
        duration_seconds=row["duration_seconds"],
        processing_time_seconds=row["processing_time_seconds"],
        real_time_factor=row["real_time_factor"],
        segment_count=row["segment_count"],
        word_timestamps_enabled=bool(row["word_timestamps_enabled"]),
        vad_enabled=bool(row["vad_enabled"]),
        source_audio_size_bytes=row["source_audio_size_bytes"],
        source_audio_modified_at=from_iso_z(row["source_audio_modified_at"]),
        source_audio_fingerprint=row["source_audio_fingerprint"],
        configuration_fingerprint=row["configuration_fingerprint"],
        engine_version=row["engine_version"],
        model_version=row["model_version"],
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_segment(row: sqlite3.Row) -> TranscriptionSegment:
    return TranscriptionSegment(
        id=row["id"],
        transcription_id=row["transcription_id"],
        segment_index=row["segment_index"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        text=row["text"],
        confidence=row["confidence"],
        no_speech_probability=row["no_speech_probability"],
        temperature=row["temperature"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteTranscriptionRepository(TranscriptionRepository):
    """Repositorio SQLite de transcripciones."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(self, transcription: Transcription, segments: list[TranscriptionSegment]) -> Transcription:
        payload = transcription.to_dict()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO transcriptions (
                    id, video_asset_id, prepared_audio_asset_id, status, engine,
                    model_name, device, compute_type, requested_language,
                    detected_language, language_probability, full_text,
                    duration_seconds, processing_time_seconds, real_time_factor,
                    segment_count, word_timestamps_enabled, vad_enabled,
                    source_audio_size_bytes, source_audio_modified_at,
                    source_audio_fingerprint, configuration_fingerprint,
                    engine_version, model_version, warning_code, warning_message,
                    error_code, error_message, started_at, completed_at,
                    created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :prepared_audio_asset_id, :status, :engine,
                    :model_name, :device, :compute_type, :requested_language,
                    :detected_language, :language_probability, :full_text,
                    :duration_seconds, :processing_time_seconds, :real_time_factor,
                    :segment_count, :word_timestamps_enabled, :vad_enabled,
                    :source_audio_size_bytes, :source_audio_modified_at,
                    :source_audio_fingerprint, :configuration_fingerprint,
                    :engine_version, :model_version, :warning_code, :warning_message,
                    :error_code, :error_message, :started_at, :completed_at,
                    :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    prepared_audio_asset_id = excluded.prepared_audio_asset_id,
                    status = excluded.status,
                    engine = excluded.engine,
                    model_name = excluded.model_name,
                    device = excluded.device,
                    compute_type = excluded.compute_type,
                    requested_language = excluded.requested_language,
                    detected_language = excluded.detected_language,
                    language_probability = excluded.language_probability,
                    full_text = excluded.full_text,
                    duration_seconds = excluded.duration_seconds,
                    processing_time_seconds = excluded.processing_time_seconds,
                    real_time_factor = excluded.real_time_factor,
                    segment_count = excluded.segment_count,
                    word_timestamps_enabled = excluded.word_timestamps_enabled,
                    vad_enabled = excluded.vad_enabled,
                    source_audio_size_bytes = excluded.source_audio_size_bytes,
                    source_audio_modified_at = excluded.source_audio_modified_at,
                    source_audio_fingerprint = excluded.source_audio_fingerprint,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    engine_version = excluded.engine_version,
                    model_version = excluded.model_version,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            transcription_row = connection.execute(
                "SELECT * FROM transcriptions WHERE video_asset_id = ?",
                (transcription.video_asset_id,),
            ).fetchone()
            if transcription_row is None:
                raise sqlite3.DatabaseError("No se pudo leer la transcripcion insertada.")
            transcription_id = transcription_row["id"]
            connection.execute(
                "DELETE FROM transcription_segments WHERE transcription_id = ?",
                (transcription_id,),
            )
            for segment in sorted(segments, key=lambda item: item.segment_index):
                segment_payload = segment.to_dict()
                connection.execute(
                    """
                    INSERT INTO transcription_segments (
                        id, transcription_id, segment_index, start_seconds,
                        end_seconds, text, confidence, no_speech_probability,
                        temperature, created_at
                    )
                    VALUES (
                        :id, :transcription_id, :segment_index, :start_seconds,
                        :end_seconds, :text, :confidence, :no_speech_probability,
                        :temperature, :created_at
                    )
                    """,
                    segment_payload,
                )
            row = connection.execute(
                "SELECT * FROM transcriptions WHERE video_asset_id = ?",
                (transcription.video_asset_id,),
            ).fetchone()
        return _row_to_transcription(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> Transcription | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM transcriptions WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
        return _row_to_transcription(row) if row else None

    def get_by_id(self, transcription_id: str) -> Transcription | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM transcriptions WHERE id = ?",
                (transcription_id,),
            ).fetchone()
        return _row_to_transcription(row) if row else None

    def list_segments(self, transcription_id: str) -> list[TranscriptionSegment]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transcription_segments WHERE transcription_id = ? ORDER BY segment_index ASC",
                (transcription_id,),
            ).fetchall()
        return [_row_to_segment(row) for row in rows]

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM transcriptions WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
            if row is None:
                return False
            transcription_id = row["id"]
            connection.execute(
                "DELETE FROM transcription_segments WHERE transcription_id = ?",
                (transcription_id,),
            )
            cursor = connection.execute(
                "DELETE FROM transcriptions WHERE video_asset_id = ?",
                (video_asset_id,),
            )
        return cursor.rowcount > 0

