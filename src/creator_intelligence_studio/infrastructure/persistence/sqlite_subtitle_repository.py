"""Repositorio SQLite para subtitulos locales."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from uuid import uuid4

from creator_intelligence_studio.domain.subtitles.entities import SubtitleCue, SubtitleEditEvent, SubtitleExport, SubtitleTrack
from creator_intelligence_studio.domain.subtitles.repositories import SubtitleRepository
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleCueValidationStatus, SubtitleExportFormat, SubtitleSourceType, SubtitleTrackStatus
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except json.JSONDecodeError:
        return fallback


def _row_to_track(row: sqlite3.Row) -> SubtitleTrack:
    return SubtitleTrack(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        transcription_id=row["transcription_id"],
        ranked_clip_candidate_id=row["ranked_clip_candidate_id"],
        render_job_id=row["render_job_id"],
        language=row["language"],
        name=row["name"],
        status=SubtitleTrackStatus(row["status"]),
        source_type=SubtitleSourceType(row["source_type"]),
        track_version=row["track_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        source_start_seconds=row["source_start_seconds"],
        source_end_seconds=row["source_end_seconds"],
        cue_count=row["cue_count"],
        total_text_length=row["total_text_length"],
        is_default=bool(row["is_default"]),
        is_locked=bool(row["is_locked"]),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
    )


def _row_to_cue(row: sqlite3.Row) -> SubtitleCue:
    return SubtitleCue(
        id=row["id"],
        subtitle_track_id=row["subtitle_track_id"],
        cue_index=row["cue_index"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        text=row["text"],
        original_text=row["original_text"],
        source_segment_ids_json=row["source_segment_ids_json"],
        speaker_label=row["speaker_label"],
        line_count=row["line_count"],
        character_count=row["character_count"],
        characters_per_second=row["characters_per_second"],
        words_per_minute=row["words_per_minute"],
        validation_status=SubtitleCueValidationStatus(row["validation_status"]),
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_event(row: sqlite3.Row) -> SubtitleEditEvent:
    return SubtitleEditEvent(
        id=row["id"],
        subtitle_track_id=row["subtitle_track_id"],
        subtitle_cue_id=row["subtitle_cue_id"],
        event_index=row["event_index"],
        action=row["action"],
        previous_json=row["previous_json"],
        new_json=row["new_json"],
        note=row["note"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_export(row: sqlite3.Row) -> SubtitleExport:
    return SubtitleExport(
        id=row["id"],
        subtitle_track_id=row["subtitle_track_id"],
        format=SubtitleExportFormat(row["format"]),
        output_path=row["output_path"],
        fingerprint=row["fingerprint"],
        size_bytes=row["size_bytes"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        verified_at=from_iso_z(row["verified_at"]),
    )


class SQLiteSubtitleRepository(SubtitleRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_track(self, track: SubtitleTrack) -> SubtitleTrack:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO subtitle_tracks (
                    id, video_asset_id, transcription_id, ranked_clip_candidate_id, render_job_id,
                    language, name, status, source_type, track_version,
                    configuration_fingerprint, source_fingerprint, source_start_seconds, source_end_seconds,
                    cue_count, total_text_length, is_default, is_locked,
                    warning_code, warning_message, error_code, error_message,
                    created_at, updated_at, completed_at
                ) VALUES (
                    :id, :video_asset_id, :transcription_id, :ranked_clip_candidate_id, :render_job_id,
                    :language, :name, :status, :source_type, :track_version,
                    :configuration_fingerprint, :source_fingerprint, :source_start_seconds, :source_end_seconds,
                    :cue_count, :total_text_length, :is_default, :is_locked,
                    :warning_code, :warning_message, :error_code, :error_message,
                    :created_at, :updated_at, :completed_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    language = excluded.language,
                    name = excluded.name,
                    status = excluded.status,
                    source_type = excluded.source_type,
                    track_version = excluded.track_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_fingerprint = excluded.source_fingerprint,
                    source_start_seconds = excluded.source_start_seconds,
                    source_end_seconds = excluded.source_end_seconds,
                    cue_count = excluded.cue_count,
                    total_text_length = excluded.total_text_length,
                    is_default = excluded.is_default,
                    is_locked = excluded.is_locked,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at
                """,
                {
                    **track.to_dict(),
                    "status": track.status.value,
                    "source_type": track.source_type.value,
                    "created_at": track.created_at.isoformat(),
                    "updated_at": track.updated_at.isoformat(),
                    "completed_at": track.completed_at.isoformat() if track.completed_at else None,
                },
            )
            row = connection.execute("SELECT * FROM subtitle_tracks WHERE id = ?", (track.id,)).fetchone()
        return _row_to_track(row)

    def get_track_by_id(self, track_id: str) -> SubtitleTrack | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM subtitle_tracks WHERE id = ?", (track_id,)).fetchone()
        return _row_to_track(row) if row else None

    def get_track_by_video_asset_id(self, video_asset_id: str) -> SubtitleTrack | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE video_asset_id = ? ORDER BY track_version DESC, created_at DESC LIMIT 1",
                (video_asset_id,),
            ).fetchone()
        return _row_to_track(row) if row else None

    def get_track_by_candidate_id(self, candidate_id: str) -> SubtitleTrack | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE ranked_clip_candidate_id = ? ORDER BY track_version DESC, created_at DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        return _row_to_track(row) if row else None

    def get_track_by_render_job_id(self, render_job_id: str) -> SubtitleTrack | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE render_job_id = ? ORDER BY track_version DESC, created_at DESC LIMIT 1",
                (render_job_id,),
            ).fetchone()
        return _row_to_track(row) if row else None

    def list_tracks_for_video(self, video_asset_id: str) -> list[SubtitleTrack]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE video_asset_id = ? ORDER BY track_version DESC, created_at DESC",
                (video_asset_id,),
            ).fetchall()
        return [_row_to_track(row) for row in rows]

    def list_tracks_for_candidate(self, candidate_id: str) -> list[SubtitleTrack]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE ranked_clip_candidate_id = ? ORDER BY track_version DESC, created_at DESC",
                (candidate_id,),
            ).fetchall()
        return [_row_to_track(row) for row in rows]

    def list_tracks_for_render_job(self, render_job_id: str) -> list[SubtitleTrack]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_tracks WHERE render_job_id = ? ORDER BY track_version DESC, created_at DESC",
                (render_job_id,),
            ).fetchall()
        return [_row_to_track(row) for row in rows]

    def upsert_cues(self, track_id: str, cues: list[SubtitleCue]) -> list[SubtitleCue]:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM subtitle_cues WHERE subtitle_track_id = ?", (track_id,))
            for cue in sorted(cues, key=lambda item: item.cue_index):
                connection.execute(
                    """
                    INSERT INTO subtitle_cues (
                        id, subtitle_track_id, cue_index, start_seconds, end_seconds,
                        text, original_text, source_segment_ids_json, speaker_label,
                        line_count, character_count, characters_per_second, words_per_minute,
                        validation_status, warning_codes_json, created_at, updated_at
                    ) VALUES (
                        :id, :subtitle_track_id, :cue_index, :start_seconds, :end_seconds,
                        :text, :original_text, :source_segment_ids_json, :speaker_label,
                        :line_count, :character_count, :characters_per_second, :words_per_minute,
                        :validation_status, :warning_codes_json, :created_at, :updated_at
                    )
                    """,
                    {
                        **cue.to_dict(),
                        "validation_status": cue.validation_status.value,
                        "created_at": cue.created_at.isoformat(),
                        "updated_at": cue.updated_at.isoformat(),
                    },
                )
            rows = connection.execute(
                "SELECT * FROM subtitle_cues WHERE subtitle_track_id = ? ORDER BY cue_index ASC",
                (track_id,),
            ).fetchall()
        return [_row_to_cue(row) for row in rows]

    def list_cues(self, track_id: str) -> list[SubtitleCue]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_cues WHERE subtitle_track_id = ? ORDER BY cue_index ASC",
                (track_id,),
            ).fetchall()
        return [_row_to_cue(row) for row in rows]

    def get_cue_by_id(self, cue_id: str) -> SubtitleCue | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM subtitle_cues WHERE id = ?", (cue_id,)).fetchone()
        return _row_to_cue(row) if row else None

    def delete_cues_for_track(self, track_id: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM subtitle_cues WHERE subtitle_track_id = ?", (track_id,))

    def append_event(self, event: SubtitleEditEvent) -> SubtitleEditEvent:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO subtitle_edit_events (
                    id, subtitle_track_id, subtitle_cue_id, event_index, action,
                    previous_json, new_json, note, created_at
                ) VALUES (
                    :id, :subtitle_track_id, :subtitle_cue_id, :event_index, :action,
                    :previous_json, :new_json, :note, :created_at
                )
                """,
                {
                    **event.to_dict(),
                    "created_at": event.created_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM subtitle_edit_events WHERE id = ?", (event.id,)).fetchone()
        return _row_to_event(row)

    def list_events_for_track(self, track_id: str) -> list[SubtitleEditEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_edit_events WHERE subtitle_track_id = ? ORDER BY event_index ASC",
                (track_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def list_events_for_cue(self, cue_id: str) -> list[SubtitleEditEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_edit_events WHERE subtitle_cue_id = ? ORDER BY event_index ASC",
                (cue_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def upsert_export(self, export: SubtitleExport) -> SubtitleExport:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO subtitle_exports (
                    id, subtitle_track_id, format, output_path, fingerprint, size_bytes,
                    status, created_at, verified_at
                ) VALUES (
                    :id, :subtitle_track_id, :format, :output_path, :fingerprint, :size_bytes,
                    :status, :created_at, :verified_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    format = excluded.format,
                    output_path = excluded.output_path,
                    fingerprint = excluded.fingerprint,
                    size_bytes = excluded.size_bytes,
                    status = excluded.status,
                    verified_at = excluded.verified_at
                """,
                {
                    **export.to_dict(),
                    "format": export.format.value,
                    "created_at": export.created_at.isoformat(),
                    "verified_at": export.verified_at.isoformat() if export.verified_at else None,
                },
            )
            row = connection.execute("SELECT * FROM subtitle_exports WHERE id = ?", (export.id,)).fetchone()
        return _row_to_export(row)

    def list_exports(self, track_id: str) -> list[SubtitleExport]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subtitle_exports WHERE subtitle_track_id = ? ORDER BY created_at DESC",
                (track_id,),
            ).fetchall()
        return [_row_to_export(row) for row in rows]

    def archive_track(self, track_id: str) -> SubtitleTrack | None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE subtitle_tracks SET status = ?, updated_at = ? WHERE id = ?",
                (SubtitleTrackStatus.ARCHIVED.value, utc_now().isoformat(), track_id),
            )
            row = connection.execute("SELECT * FROM subtitle_tracks WHERE id = ?", (track_id,)).fetchone()
        return _row_to_track(row) if row else None

    def delete_track(self, track_id: str) -> bool:
        archived = self.archive_track(track_id)
        return archived is not None

