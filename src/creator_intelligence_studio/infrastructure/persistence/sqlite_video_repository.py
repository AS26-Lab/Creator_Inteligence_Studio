"""Repositorio SQLite para videos."""

from __future__ import annotations

import sqlite3

from creator_intelligence_studio.domain.errors import ConflictError
from creator_intelligence_studio.domain.videos.entities import (
    VideoAsset,
    VideoProcessingStatus,
    VideoSourceType,
)
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.shared.dates import from_iso_z, to_iso_z
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase


def _row_to_video(row: sqlite3.Row) -> VideoAsset:
    return VideoAsset(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        source_path=row["source_path"],
        original_filename=row["original_filename"],
        extension=row["extension"],
        file_size_bytes=int(row["file_size_bytes"]),
        file_modified_at=from_iso_z(row["file_modified_at"]),
        source_type=VideoSourceType(row["source_type"]),
        processing_status=VideoProcessingStatus(row["processing_status"]),
        registered_at=from_iso_z(row["registered_at"]),
        updated_at=from_iso_z(row["updated_at"]),
        notes=row["notes"],
        file_available=bool(row["file_available"]),
    )


class SQLiteVideoRepository(VideoRepository):
    """Repositorio de videos sobre SQLite."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def create(self, video: VideoAsset) -> VideoAsset:
        try:
            with self._database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO video_assets (
                        id, project_id, title, source_path, original_filename, extension,
                        file_size_bytes, file_modified_at, source_type, processing_status,
                        registered_at, updated_at, notes, file_available
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        video.id,
                        video.project_id,
                        video.title,
                        video.source_path,
                        video.original_filename,
                        video.extension,
                        video.file_size_bytes,
                        to_iso_z(video.file_modified_at),
                        video.source_type.value,
                        video.processing_status.value,
                        to_iso_z(video.registered_at),
                        to_iso_z(video.updated_at),
                        video.notes,
                        1 if video.file_available else 0,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("No se pudo registrar el video. Verifica el proyecto.") from exc
        return video

    def list_by_project(self, project_id: str) -> list[VideoAsset]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM video_assets WHERE project_id = ? ORDER BY registered_at ASC",
                (project_id,),
            ).fetchall()
        return [_row_to_video(row) for row in rows]

    def get_by_id(self, video_id: str) -> VideoAsset | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM video_assets WHERE id = ?",
                (video_id,),
            ).fetchone()
        return _row_to_video(row) if row else None

