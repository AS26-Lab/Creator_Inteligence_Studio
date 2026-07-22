"""Repositorio SQLite para analisis visual."""

from __future__ import annotations

import json
import struct
import sqlite3

from creator_intelligence_studio.domain.visual_analysis.entities import (
    VisualAnalysis,
    VisualEvent,
    VisualScene,
    VisualTimelineWindow,
)
from creator_intelligence_studio.domain.visual_analysis.repositories import VisualAnalysisRepository
from creator_intelligence_studio.domain.visual_analysis.value_objects import VisualActivityLabel, VisualAnalysisStatus, VisualEventType
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


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


def _row_to_analysis(row: sqlite3.Row) -> VisualAnalysis:
    return VisualAnalysis(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        source_inspection_id=row["source_inspection_id"],
        status=VisualAnalysisStatus(row["status"]),
        analyzer_version=row["analyzer_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        source_file_size_bytes=int(_coerce_numeric(row["source_file_size_bytes"])) if row["source_file_size_bytes"] is not None else None,
        source_file_modified_at=from_iso_z(row["source_file_modified_at"]),
        duration_seconds=float(_coerce_numeric(row["duration_seconds"])) if row["duration_seconds"] is not None else None,
        sampled_frame_count=int(_coerce_numeric(row["sampled_frame_count"])),
        detected_cut_count=int(_coerce_numeric(row["detected_cut_count"])),
        detected_scene_count=int(_coerce_numeric(row["detected_scene_count"])),
        keyframe_count=int(_coerce_numeric(row["keyframe_count"])),
        static_segment_count=int(_coerce_numeric(row["static_segment_count"])),
        black_frame_event_count=int(_coerce_numeric(row["black_frame_event_count"])),
        freeze_event_count=int(_coerce_numeric(row["freeze_event_count"])),
        average_brightness=float(_coerce_numeric(row["average_brightness"])) if row["average_brightness"] is not None else None,
        brightness_variation=float(_coerce_numeric(row["brightness_variation"])) if row["brightness_variation"] is not None else None,
        average_contrast=float(_coerce_numeric(row["average_contrast"])) if row["average_contrast"] is not None else None,
        average_motion=float(_coerce_numeric(row["average_motion"])) if row["average_motion"] is not None else None,
        peak_motion=float(_coerce_numeric(row["peak_motion"])) if row["peak_motion"] is not None else None,
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]) or utc_now(),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_window(row: sqlite3.Row) -> VisualTimelineWindow:
    return VisualTimelineWindow(
        id=row["id"],
        visual_analysis_id=row["visual_analysis_id"],
        window_index=int(_coerce_numeric(row["window_index"])),
        start_seconds=float(_coerce_numeric(row["start_seconds"])),
        end_seconds=float(_coerce_numeric(row["end_seconds"])),
        sampled_frame_count=int(_coerce_numeric(row["sampled_frame_count"])),
        brightness=float(_coerce_numeric(row["brightness"])),
        contrast=float(_coerce_numeric(row["contrast"])),
        saturation=float(_coerce_numeric(row["saturation"])),
        motion_score=float(_coerce_numeric(row["motion_score"])),
        color_change_score=float(_coerce_numeric(row["color_change_score"])),
        is_static=bool(row["is_static"]),
        is_black=bool(row["is_black"]),
        is_possible_freeze=bool(row["is_possible_freeze"]),
        activity_label=VisualActivityLabel(row["activity_label"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_scene(row: sqlite3.Row) -> VisualScene:
    return VisualScene(
        id=row["id"],
        visual_analysis_id=row["visual_analysis_id"],
        scene_index=int(_coerce_numeric(row["scene_index"])),
        start_seconds=float(_coerce_numeric(row["start_seconds"])),
        end_seconds=float(_coerce_numeric(row["end_seconds"])),
        duration_seconds=float(_coerce_numeric(row["duration_seconds"])),
        representative_keyframe_path=row["representative_keyframe_path"],
        cut_in_score=float(_coerce_numeric(row["cut_in_score"])),
        average_motion=float(_coerce_numeric(row["average_motion"])),
        average_brightness=float(_coerce_numeric(row["average_brightness"])),
        average_contrast=float(_coerce_numeric(row["average_contrast"])),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_event(row: sqlite3.Row) -> VisualEvent:
    return VisualEvent(
        id=row["id"],
        visual_analysis_id=row["visual_analysis_id"],
        event_index=int(_coerce_numeric(row["event_index"])),
        start_seconds=float(_coerce_numeric(row["start_seconds"])),
        end_seconds=float(_coerce_numeric(row["end_seconds"])),
        event_type=VisualEventType(row["event_type"]),
        confidence=float(_coerce_numeric(row["confidence"])),
        evidence_json=row["evidence_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteVisualAnalysisRepository(VisualAnalysisRepository):
    """Repositorio SQLite para analisis visual tecnico."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(
        self,
        analysis: VisualAnalysis,
        windows: list[VisualTimelineWindow],
        scenes: list[VisualScene],
        events: list[VisualEvent],
    ) -> VisualAnalysis:
        payload = analysis.to_dict()
        with self._database.connect() as connection:
            connection.execute("DELETE FROM visual_timeline_windows WHERE visual_analysis_id = ?", (analysis.id,))
            connection.execute("DELETE FROM visual_scenes WHERE visual_analysis_id = ?", (analysis.id,))
            connection.execute("DELETE FROM visual_events WHERE visual_analysis_id = ?", (analysis.id,))
            connection.execute(
                """
                INSERT INTO visual_analyses (
                    id, video_asset_id, source_inspection_id, status, analyzer_version,
                    configuration_fingerprint, source_fingerprint, source_file_size_bytes, source_file_modified_at,
                    duration_seconds, sampled_frame_count, detected_cut_count,
                    detected_scene_count, keyframe_count, static_segment_count,
                    black_frame_event_count, freeze_event_count, average_brightness,
                    brightness_variation, average_contrast, average_motion, peak_motion,
                    started_at, completed_at, warning_code, warning_message, error_code,
                    error_message, created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :source_inspection_id, :status, :analyzer_version,
                    :configuration_fingerprint, :source_fingerprint, :source_file_size_bytes, :source_file_modified_at,
                    :duration_seconds, :sampled_frame_count, :detected_cut_count,
                    :detected_scene_count, :keyframe_count, :static_segment_count,
                    :black_frame_event_count, :freeze_event_count, :average_brightness,
                    :brightness_variation, :average_contrast, :average_motion, :peak_motion,
                    :started_at, :completed_at, :warning_code, :warning_message, :error_code,
                    :error_message, :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    source_inspection_id = excluded.source_inspection_id,
                    status = excluded.status,
                    analyzer_version = excluded.analyzer_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_fingerprint = excluded.source_fingerprint,
                    source_file_size_bytes = excluded.source_file_size_bytes,
                    source_file_modified_at = excluded.source_file_modified_at,
                    duration_seconds = excluded.duration_seconds,
                    sampled_frame_count = excluded.sampled_frame_count,
                    detected_cut_count = excluded.detected_cut_count,
                    detected_scene_count = excluded.detected_scene_count,
                    keyframe_count = excluded.keyframe_count,
                    static_segment_count = excluded.static_segment_count,
                    black_frame_event_count = excluded.black_frame_event_count,
                    freeze_event_count = excluded.freeze_event_count,
                    average_brightness = excluded.average_brightness,
                    brightness_variation = excluded.brightness_variation,
                    average_contrast = excluded.average_contrast,
                    average_motion = excluded.average_motion,
                    peak_motion = excluded.peak_motion,
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
            for window in windows:
                connection.execute(
                    """
                    INSERT INTO visual_timeline_windows (
                        id, visual_analysis_id, window_index, start_seconds, end_seconds,
                        sampled_frame_count, brightness, contrast, saturation, motion_score,
                        color_change_score, is_static, is_black, is_possible_freeze,
                        activity_label, created_at
                    )
                    VALUES (
                        :id, :visual_analysis_id, :window_index, :start_seconds, :end_seconds,
                        :sampled_frame_count, :brightness, :contrast, :saturation, :motion_score,
                        :color_change_score, :is_static, :is_black, :is_possible_freeze,
                        :activity_label, :created_at
                    )
                    """,
                    window.to_dict(),
                )
            for scene in scenes:
                connection.execute(
                    """
                    INSERT INTO visual_scenes (
                        id, visual_analysis_id, scene_index, start_seconds, end_seconds,
                        duration_seconds, representative_keyframe_path, cut_in_score,
                        average_motion, average_brightness, average_contrast, created_at
                    )
                    VALUES (
                        :id, :visual_analysis_id, :scene_index, :start_seconds, :end_seconds,
                        :duration_seconds, :representative_keyframe_path, :cut_in_score,
                        :average_motion, :average_brightness, :average_contrast, :created_at
                    )
                    """,
                    scene.to_dict(),
                )
            for event in events:
                connection.execute(
                    """
                    INSERT INTO visual_events (
                        id, visual_analysis_id, event_index, start_seconds, end_seconds,
                        event_type, confidence, evidence_json, created_at
                    )
                    VALUES (
                        :id, :visual_analysis_id, :event_index, :start_seconds, :end_seconds,
                        :event_type, :confidence, :evidence_json, :created_at
                    )
                    """,
                    event.to_dict(),
                )
            row = connection.execute(
                "SELECT * FROM visual_analyses WHERE video_asset_id = ?",
                (analysis.video_asset_id,),
            ).fetchone()
        return _row_to_analysis(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> VisualAnalysis | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM visual_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
        return _row_to_analysis(row) if row else None

    def list_windows(self, visual_analysis_id: str) -> list[VisualTimelineWindow]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM visual_timeline_windows WHERE visual_analysis_id = ? ORDER BY window_index ASC",
                (visual_analysis_id,),
            ).fetchall()
        return [_row_to_window(row) for row in rows]

    def list_scenes(self, visual_analysis_id: str) -> list[VisualScene]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM visual_scenes WHERE visual_analysis_id = ? ORDER BY scene_index ASC",
                (visual_analysis_id,),
            ).fetchall()
        return [_row_to_scene(row) for row in rows]

    def list_events(self, visual_analysis_id: str) -> list[VisualEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM visual_events WHERE visual_analysis_id = ? ORDER BY event_index ASC",
                (visual_analysis_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM visual_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            ).fetchone()
            if row is None:
                return False
            analysis_id = row["id"]
            connection.execute("DELETE FROM visual_timeline_windows WHERE visual_analysis_id = ?", (analysis_id,))
            connection.execute("DELETE FROM visual_scenes WHERE visual_analysis_id = ?", (analysis_id,))
            connection.execute("DELETE FROM visual_events WHERE visual_analysis_id = ?", (analysis_id,))
            cursor = connection.execute(
                "DELETE FROM visual_analyses WHERE video_asset_id = ?",
                (video_asset_id,),
            )
        return cursor.rowcount > 0
