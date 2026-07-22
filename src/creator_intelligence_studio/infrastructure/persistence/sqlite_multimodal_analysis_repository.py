"""Repositorio SQLite para analisis multimodal."""

from __future__ import annotations

import json
import sqlite3
import struct

from creator_intelligence_studio.domain.multimodal_analysis.entities import (
    MultimodalAnalysis,
    MultimodalMomentCandidate,
    MultimodalTimelineWindow,
)
from creator_intelligence_studio.domain.multimodal_analysis.repositories import MultimodalAnalysisRepository
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import MultimodalAnalysisStatus, MultimodalCandidateType
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _coerce_numeric(value):
    if isinstance(value, (bytes, bytearray)):
        if len(value) == 4:
            return struct.unpack("<f", value)[0]
        if len(value) == 8:
            return struct.unpack("<d", value)[0]
        try:
            return float(value.decode("utf-8", errors="replace"))
        except ValueError:
            return value
    return value


def _row_to_analysis(row: sqlite3.Row) -> MultimodalAnalysis:
    return MultimodalAnalysis(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        transcription_id=row["transcription_id"],
        acoustic_analysis_id=row["acoustic_analysis_id"],
        visual_analysis_id=row["visual_analysis_id"],
        status=MultimodalAnalysisStatus(row["status"]),
        analyzer_version=row["analyzer_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        duration_seconds=float(_coerce_numeric(row["duration_seconds"])),
        window_size_seconds=float(_coerce_numeric(row["window_size_seconds"])),
        window_count=int(_coerce_numeric(row["window_count"])),
        candidate_count=int(_coerce_numeric(row["candidate_count"])),
        high_activity_candidate_count=int(_coerce_numeric(row["high_activity_candidate_count"])),
        transition_candidate_count=int(_coerce_numeric(row["transition_candidate_count"])),
        silence_candidate_count=int(_coerce_numeric(row["silence_candidate_count"])),
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]) or utc_now(),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_window(row: sqlite3.Row) -> MultimodalTimelineWindow:
    return MultimodalTimelineWindow(
        id=row["id"],
        multimodal_analysis_id=row["multimodal_analysis_id"],
        window_index=int(_coerce_numeric(row["window_index"])),
        start_seconds=float(_coerce_numeric(row["start_seconds"])),
        end_seconds=float(_coerce_numeric(row["end_seconds"])),
        transcript_text=row["transcript_text"],
        word_count=int(_coerce_numeric(row["word_count"])),
        speech_ratio=float(_coerce_numeric(row["speech_ratio"])),
        silence_ratio=float(_coerce_numeric(row["silence_ratio"])),
        speech_rate=float(_coerce_numeric(row["speech_rate"])) if row["speech_rate"] is not None else None,
        acoustic_energy=float(_coerce_numeric(row["acoustic_energy"])),
        acoustic_change=float(_coerce_numeric(row["acoustic_change"])),
        visual_motion=float(_coerce_numeric(row["visual_motion"])),
        visual_change=float(_coerce_numeric(row["visual_change"])),
        brightness=float(_coerce_numeric(row["brightness"])),
        cut_count=int(_coerce_numeric(row["cut_count"])),
        scene_index=int(_coerce_numeric(row["scene_index"])) if row["scene_index"] is not None else None,
        acoustic_event_count=int(_coerce_numeric(row["acoustic_event_count"])),
        visual_event_count=int(_coerce_numeric(row["visual_event_count"])),
        combined_activity_score=float(_coerce_numeric(row["combined_activity_score"])),
        transition_score=float(_coerce_numeric(row["transition_score"])),
        novelty_score=float(_coerce_numeric(row["novelty_score"])),
        confidence=float(_coerce_numeric(row["confidence"])),
        evidence_json=row["evidence_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_candidate(row: sqlite3.Row) -> MultimodalMomentCandidate:
    return MultimodalMomentCandidate(
        id=row["id"],
        multimodal_analysis_id=row["multimodal_analysis_id"],
        candidate_index=int(_coerce_numeric(row["candidate_index"])),
        start_seconds=float(_coerce_numeric(row["start_seconds"])),
        end_seconds=float(_coerce_numeric(row["end_seconds"])),
        candidate_type=MultimodalCandidateType(row["candidate_type"]),
        score=float(_coerce_numeric(row["score"])),
        confidence=float(_coerce_numeric(row["confidence"])),
        title=row["title"],
        summary=row["summary"],
        evidence_json=row["evidence_json"],
        source_window_start=float(_coerce_numeric(row["source_window_start"])) if row["source_window_start"] is not None else None,
        source_window_end=float(_coerce_numeric(row["source_window_end"])) if row["source_window_end"] is not None else None,
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteMultimodalAnalysisRepository(MultimodalAnalysisRepository):
    """Repositorio SQLite para analisis multimodal."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(
        self,
        analysis: MultimodalAnalysis,
        windows: list[MultimodalTimelineWindow],
        candidates: list[MultimodalMomentCandidate],
    ) -> MultimodalAnalysis:
        payload = analysis.to_dict()
        with self._database.connect() as connection:
            connection.execute("DELETE FROM multimodal_timeline_windows WHERE multimodal_analysis_id = ?", (analysis.id,))
            connection.execute("DELETE FROM multimodal_moment_candidates WHERE multimodal_analysis_id = ?", (analysis.id,))
            connection.execute(
                """
                INSERT INTO multimodal_analyses (
                    id, video_asset_id, transcription_id, acoustic_analysis_id, visual_analysis_id,
                    status, analyzer_version, configuration_fingerprint, source_fingerprint,
                    duration_seconds, window_size_seconds, window_count, candidate_count,
                    high_activity_candidate_count, transition_candidate_count, silence_candidate_count,
                    started_at, completed_at, warning_code, warning_message, error_code, error_message,
                    created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :transcription_id, :acoustic_analysis_id, :visual_analysis_id,
                    :status, :analyzer_version, :configuration_fingerprint, :source_fingerprint,
                    :duration_seconds, :window_size_seconds, :window_count, :candidate_count,
                    :high_activity_candidate_count, :transition_candidate_count, :silence_candidate_count,
                    :started_at, :completed_at, :warning_code, :warning_message, :error_code, :error_message,
                    :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    transcription_id = excluded.transcription_id,
                    acoustic_analysis_id = excluded.acoustic_analysis_id,
                    visual_analysis_id = excluded.visual_analysis_id,
                    status = excluded.status,
                    analyzer_version = excluded.analyzer_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_fingerprint = excluded.source_fingerprint,
                    duration_seconds = excluded.duration_seconds,
                    window_size_seconds = excluded.window_size_seconds,
                    window_count = excluded.window_count,
                    candidate_count = excluded.candidate_count,
                    high_activity_candidate_count = excluded.high_activity_candidate_count,
                    transition_candidate_count = excluded.transition_candidate_count,
                    silence_candidate_count = excluded.silence_candidate_count,
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
            row = connection.execute("SELECT * FROM multimodal_analyses WHERE video_asset_id = ?", (analysis.video_asset_id,)).fetchone()
            if row is None:
                raise sqlite3.DatabaseError("No se pudo leer el analisis multimodal insertado.")
            analysis_id = row["id"]
            for window in sorted(windows, key=lambda item: item.window_index):
                connection.execute(
                    """
                    INSERT INTO multimodal_timeline_windows (
                        id, multimodal_analysis_id, window_index, start_seconds, end_seconds,
                        transcript_text, word_count, speech_ratio, silence_ratio, speech_rate,
                        acoustic_energy, acoustic_change, visual_motion, visual_change,
                        brightness, cut_count, scene_index, acoustic_event_count, visual_event_count,
                        combined_activity_score, transition_score, novelty_score, confidence,
                        evidence_json, created_at
                    )
                    VALUES (
                        :id, :multimodal_analysis_id, :window_index, :start_seconds, :end_seconds,
                        :transcript_text, :word_count, :speech_ratio, :silence_ratio, :speech_rate,
                        :acoustic_energy, :acoustic_change, :visual_motion, :visual_change,
                        :brightness, :cut_count, :scene_index, :acoustic_event_count, :visual_event_count,
                        :combined_activity_score, :transition_score, :novelty_score, :confidence,
                        :evidence_json, :created_at
                    )
                    """,
                    window.to_dict() | {"multimodal_analysis_id": analysis_id},
                )
            for candidate in sorted(candidates, key=lambda item: item.candidate_index):
                connection.execute(
                    """
                    INSERT INTO multimodal_moment_candidates (
                        id, multimodal_analysis_id, candidate_index, start_seconds, end_seconds,
                        candidate_type, score, confidence, title, summary, evidence_json,
                        source_window_start, source_window_end, created_at
                    )
                    VALUES (
                        :id, :multimodal_analysis_id, :candidate_index, :start_seconds, :end_seconds,
                        :candidate_type, :score, :confidence, :title, :summary, :evidence_json,
                        :source_window_start, :source_window_end, :created_at
                    )
                    """,
                    candidate.to_dict() | {"multimodal_analysis_id": analysis_id},
                )
            row = connection.execute("SELECT * FROM multimodal_analyses WHERE video_asset_id = ?", (analysis.video_asset_id,)).fetchone()
        return _row_to_analysis(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> MultimodalAnalysis | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM multimodal_analyses WHERE video_asset_id = ?", (video_asset_id,)).fetchone()
        return _row_to_analysis(row) if row else None

    def get_by_id(self, multimodal_analysis_id: str) -> MultimodalAnalysis | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM multimodal_analyses WHERE id = ?", (multimodal_analysis_id,)).fetchone()
        return _row_to_analysis(row) if row else None

    def list_windows(self, multimodal_analysis_id: str) -> list[MultimodalTimelineWindow]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM multimodal_timeline_windows WHERE multimodal_analysis_id = ? ORDER BY window_index ASC",
                (multimodal_analysis_id,),
            ).fetchall()
        return [_row_to_window(row) for row in rows]

    def list_candidates(self, multimodal_analysis_id: str) -> list[MultimodalMomentCandidate]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM multimodal_moment_candidates WHERE multimodal_analysis_id = ? ORDER BY candidate_index ASC",
                (multimodal_analysis_id,),
            ).fetchall()
        return [_row_to_candidate(row) for row in rows]

    def get_candidate_by_id(self, candidate_id: str) -> MultimodalMomentCandidate | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM multimodal_moment_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate(row) if row else None

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute("SELECT id FROM multimodal_analyses WHERE video_asset_id = ?", (video_asset_id,)).fetchone()
            if row is None:
                return False
            analysis_id = row["id"]
            connection.execute("DELETE FROM multimodal_timeline_windows WHERE multimodal_analysis_id = ?", (analysis_id,))
            connection.execute("DELETE FROM multimodal_moment_candidates WHERE multimodal_analysis_id = ?", (analysis_id,))
            cursor = connection.execute("DELETE FROM multimodal_analyses WHERE video_asset_id = ?", (video_asset_id,))
        return cursor.rowcount > 0

