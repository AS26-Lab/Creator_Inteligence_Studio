"""Repositorio SQLite para analisis acustico."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
import sqlite3

from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.repositories import AcousticAnalysisRepository
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticActivityLabel, AcousticAnalysisStatus, AcousticEventType
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _row_to_analysis(row: sqlite3.Row) -> AcousticAnalysis:
    return AcousticAnalysis(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        prepared_audio_asset_id=row["prepared_audio_asset_id"],
        transcription_id=row["transcription_id"],
        status=AcousticAnalysisStatus(row["status"]),
        analyzer_version=row["analyzer_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_audio_fingerprint=row["source_audio_fingerprint"],
        duration_seconds=row["duration_seconds"],
        speech_duration_seconds=row["speech_duration_seconds"],
        silence_duration_seconds=row["silence_duration_seconds"],
        speech_ratio=row["speech_ratio"],
        silence_ratio=row["silence_ratio"],
        words_per_minute=row["words_per_minute"],
        voiced_words_per_minute=row["voiced_words_per_minute"],
        average_energy=row["average_energy"],
        peak_energy=row["peak_energy"],
        dynamic_range=row["dynamic_range"],
        pause_count=row["pause_count"],
        average_pause_seconds=row["average_pause_seconds"],
        longest_pause_seconds=row["longest_pause_seconds"],
        short_pause_count=row["short_pause_count"],
        medium_pause_count=row["medium_pause_count"],
        long_pause_count=row["long_pause_count"],
        low_activity_segment_count=row["low_activity_segment_count"],
        abrupt_change_count=row["abrupt_change_count"],
        event_candidate_count=row["event_candidate_count"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_window(row: sqlite3.Row) -> AcousticTimelineWindow:
    return AcousticTimelineWindow(
        id=row["id"],
        acoustic_analysis_id=row["acoustic_analysis_id"],
        window_index=row["window_index"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        speech_probability=row["speech_probability"],
        is_speech=bool(row["is_speech"]),
        rms_energy=row["rms_energy"],
        peak_amplitude=row["peak_amplitude"],
        normalized_energy=row["normalized_energy"],
        zero_crossing_rate=row["zero_crossing_rate"],
        speech_rate_estimate=row["speech_rate_estimate"],
        word_count=row["word_count"],
        pause_duration_seconds=row["pause_duration_seconds"],
        activity_label=AcousticActivityLabel(row["activity_label"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_event(row: sqlite3.Row) -> AcousticEvent:
    return AcousticEvent(
        id=row["id"],
        acoustic_analysis_id=row["acoustic_analysis_id"],
        event_index=row["event_index"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        event_type=AcousticEventType(row["event_type"]),
        confidence=row["confidence"],
        evidence_json=row["evidence_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteAcousticAnalysisRepository(AcousticAnalysisRepository):
    """Repositorio SQLite para analisis acustico persistido."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(
        self,
        analysis: AcousticAnalysis,
        windows: list[AcousticTimelineWindow],
        events: list[AcousticEvent],
    ) -> AcousticAnalysis:
        payload = analysis.to_dict()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO acoustic_analyses (
                    id, video_asset_id, prepared_audio_asset_id, transcription_id,
                    status, analyzer_version, configuration_fingerprint,
                    source_audio_fingerprint, duration_seconds,
                    speech_duration_seconds, silence_duration_seconds,
                    speech_ratio, silence_ratio, words_per_minute,
                    voiced_words_per_minute, average_energy, peak_energy,
                    dynamic_range, pause_count, average_pause_seconds,
                    longest_pause_seconds, short_pause_count,
                    medium_pause_count, long_pause_count,
                    low_activity_segment_count, abrupt_change_count,
                    event_candidate_count, started_at, completed_at,
                    warning_code, warning_message, error_code, error_message,
                    created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :prepared_audio_asset_id, :transcription_id,
                    :status, :analyzer_version, :configuration_fingerprint,
                    :source_audio_fingerprint, :duration_seconds,
                    :speech_duration_seconds, :silence_duration_seconds,
                    :speech_ratio, :silence_ratio, :words_per_minute,
                    :voiced_words_per_minute, :average_energy, :peak_energy,
                    :dynamic_range, :pause_count, :average_pause_seconds,
                    :longest_pause_seconds, :short_pause_count,
                    :medium_pause_count, :long_pause_count,
                    :low_activity_segment_count, :abrupt_change_count,
                    :event_candidate_count, :started_at, :completed_at,
                    :warning_code, :warning_message, :error_code, :error_message,
                    :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    prepared_audio_asset_id = excluded.prepared_audio_asset_id,
                    transcription_id = excluded.transcription_id,
                    status = excluded.status,
                    analyzer_version = excluded.analyzer_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_audio_fingerprint = excluded.source_audio_fingerprint,
                    duration_seconds = excluded.duration_seconds,
                    speech_duration_seconds = excluded.speech_duration_seconds,
                    silence_duration_seconds = excluded.silence_duration_seconds,
                    speech_ratio = excluded.speech_ratio,
                    silence_ratio = excluded.silence_ratio,
                    words_per_minute = excluded.words_per_minute,
                    voiced_words_per_minute = excluded.voiced_words_per_minute,
                    average_energy = excluded.average_energy,
                    peak_energy = excluded.peak_energy,
                    dynamic_range = excluded.dynamic_range,
                    pause_count = excluded.pause_count,
                    average_pause_seconds = excluded.average_pause_seconds,
                    longest_pause_seconds = excluded.longest_pause_seconds,
                    short_pause_count = excluded.short_pause_count,
                    medium_pause_count = excluded.medium_pause_count,
                    long_pause_count = excluded.long_pause_count,
                    low_activity_segment_count = excluded.low_activity_segment_count,
                    abrupt_change_count = excluded.abrupt_change_count,
                    event_candidate_count = excluded.event_candidate_count,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            row = connection.execute(
                "SELECT * FROM acoustic_analyses WHERE video_asset_id = ?",
                (analysis.video_asset_id,),
            ).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("No se pudo leer el analisis insertado.")
            acoustic_analysis_id = row["id"]
            connection.execute("DELETE FROM acoustic_timeline_windows WHERE acoustic_analysis_id = ?", (acoustic_analysis_id,))
            connection.execute("DELETE FROM acoustic_events WHERE acoustic_analysis_id = ?", (acoustic_analysis_id,))
            for window in sorted(windows, key=lambda item: item.window_index):
                connection.execute(
                    """
                    INSERT INTO acoustic_timeline_windows (
                        id, acoustic_analysis_id, window_index, start_seconds,
                        end_seconds, speech_probability, is_speech, rms_energy,
                        peak_amplitude, normalized_energy, zero_crossing_rate,
                        speech_rate_estimate, word_count, pause_duration_seconds,
                        activity_label, created_at
                    )
                    VALUES (
                        :id, :acoustic_analysis_id, :window_index, :start_seconds,
                        :end_seconds, :speech_probability, :is_speech, :rms_energy,
                        :peak_amplitude, :normalized_energy, :zero_crossing_rate,
                        :speech_rate_estimate, :word_count, :pause_duration_seconds,
                        :activity_label, :created_at
                    )
                    """,
                    window.to_dict(),
                )
            for event in sorted(events, key=lambda item: item.event_index):
                connection.execute(
                    """
                    INSERT INTO acoustic_events (
                        id, acoustic_analysis_id, event_index, start_seconds,
                        end_seconds, event_type, confidence, evidence_json,
                        created_at
                    )
                    VALUES (
                        :id, :acoustic_analysis_id, :event_index, :start_seconds,
                        :end_seconds, :event_type, :confidence, :evidence_json,
                        :created_at
                    )
                    """,
                    event.to_dict(),
                )
            row = connection.execute(
                "SELECT * FROM acoustic_analyses WHERE video_asset_id = ?",
                (analysis.video_asset_id,),
            ).fetchone()
        return _row_to_analysis(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> AcousticAnalysis | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM acoustic_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
        return _row_to_analysis(row) if row else None

    def get_by_id(self, acoustic_analysis_id: str) -> AcousticAnalysis | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM acoustic_analyses WHERE id = ?",
                (acoustic_analysis_id,),
            ).fetchone()
        return _row_to_analysis(row) if row else None

    def list_windows(self, acoustic_analysis_id: str) -> list[AcousticTimelineWindow]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM acoustic_timeline_windows WHERE acoustic_analysis_id = ? ORDER BY window_index ASC",
                (acoustic_analysis_id,),
            ).fetchall()
        return [_row_to_window(row) for row in rows]

    def list_events(self, acoustic_analysis_id: str) -> list[AcousticEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM acoustic_events WHERE acoustic_analysis_id = ? ORDER BY event_index ASC",
                (acoustic_analysis_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM acoustic_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
            if row is None:
                return False
            acoustic_analysis_id = row["id"]
            connection.execute("DELETE FROM acoustic_timeline_windows WHERE acoustic_analysis_id = ?", (acoustic_analysis_id,))
            connection.execute("DELETE FROM acoustic_events WHERE acoustic_analysis_id = ?", (acoustic_analysis_id,))
            cursor = connection.execute(
                "DELETE FROM acoustic_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            )
        return cursor.rowcount > 0
