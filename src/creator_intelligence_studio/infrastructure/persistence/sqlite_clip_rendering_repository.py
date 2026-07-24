"""Repositorio SQLite para renderizado de clips."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from uuid import uuid4

from creator_intelligence_studio.domain.clip_rendering.entities import (
    ClipRenderArtifact,
    ClipRenderBatch,
    ClipRenderBatchItem,
    ClipRenderDelivery,
    ClipRenderDeliveryArtifact,
    ClipRenderEvent,
    ClipRenderJob,
)
from creator_intelligence_studio.domain.clip_rendering.repositories import ClipRenderRepository
from creator_intelligence_studio.domain.clip_rendering.value_objects import (
    ClipRenderArtifactType,
    ClipRenderBatchStatus,
    ClipRenderDeliveryStatus,
    ClipRenderJobStatus,
    ClipRenderProfile,
    SubtitleRenderMode,
    SubtitleRenderStylePreset,
)
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


def _row_to_job(row: sqlite3.Row) -> ClipRenderJob:
    return ClipRenderJob(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        ranked_clip_candidate_id=row["ranked_clip_candidate_id"],
        collection_id=row["collection_id"],
        status=ClipRenderJobStatus(row["status"]),
        render_profile=ClipRenderProfile(row["render_profile"]),
        source_path_snapshot=row["source_path_snapshot"],
        source_fingerprint=row["source_fingerprint"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        duration_seconds=row["duration_seconds"],
        output_path=row["output_path"],
        output_container=row["output_container"],
        video_codec=row["video_codec"],
        audio_codec=row["audio_codec"],
        width=row["width"],
        height=row["height"],
        frame_rate=row["frame_rate"],
        audio_sample_rate=row["audio_sample_rate"],
        configuration_fingerprint=row["configuration_fingerprint"],
        renderer_version=row["renderer_version"],
        progress_percent=row["progress_percent"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        cancelled_at=from_iso_z(row["cancelled_at"]),
        retry_count=row["retry_count"],
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_artifact(row: sqlite3.Row) -> ClipRenderArtifact:
    return ClipRenderArtifact(
        id=row["id"],
        render_job_id=row["render_job_id"],
        artifact_type=ClipRenderArtifactType(row["artifact_type"]),
        managed_path=row["managed_path"],
        fingerprint=row["fingerprint"],
        size_bytes=row["size_bytes"],
        duration_seconds=row["duration_seconds"],
        video_codec=row["video_codec"],
        audio_codec=row["audio_codec"],
        width=row["width"],
        height=row["height"],
        frame_rate=row["frame_rate"],
        audio_sample_rate=row["audio_sample_rate"],
        verified=bool(row["verified"]),
        verification_json=row["verification_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_event(row: sqlite3.Row) -> ClipRenderEvent:
    return ClipRenderEvent(
        id=row["id"],
        render_job_id=row["render_job_id"],
        event_index=row["event_index"],
        event_type=row["event_type"],
        progress_percent=row["progress_percent"],
        message=row["message"],
        details_json=row["details_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_delivery(row: sqlite3.Row) -> ClipRenderDelivery:
    return ClipRenderDelivery(
        id=row["id"],
        render_job_id=row["render_job_id"],
        subtitle_track_id=row["subtitle_track_id"],
        subtitle_track_version=row["subtitle_track_version"],
        subtitle_track_fingerprint=row["subtitle_track_fingerprint"],
        subtitle_mode=SubtitleRenderMode(row["subtitle_mode"]),
        subtitle_format=row["subtitle_format"],
        style_preset=SubtitleRenderStylePreset(row["style_preset"]) if row["style_preset"] else None,
        style_json=row["style_json"],
        source_export_path=row["source_export_path"],
        source_export_fingerprint=row["source_export_fingerprint"],
        expected_cue_count=row["expected_cue_count"],
        rendered_cue_count=row["rendered_cue_count"],
        output_path=row["output_path"],
        manifest_path=row["manifest_path"],
        configuration_fingerprint=row["configuration_fingerprint"],
        status=ClipRenderDeliveryStatus(row["status"]),
        progress_percent=row["progress_percent"],
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        retry_count=row["retry_count"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        cancelled_at=from_iso_z(row["cancelled_at"]),
    )


def _row_to_delivery_artifact(row: sqlite3.Row) -> ClipRenderDeliveryArtifact:
    return ClipRenderDeliveryArtifact(
        id=row["id"],
        delivery_id=row["delivery_id"],
        artifact_type=ClipRenderArtifactType(row["artifact_type"]),
        managed_path=row["managed_path"],
        fingerprint=row["fingerprint"],
        size_bytes=row["size_bytes"],
        verified=bool(row["verified"]),
        verification_json=row["verification_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_batch(row: sqlite3.Row) -> ClipRenderBatch:
    return ClipRenderBatch(
        id=row["id"],
        collection_id=row["collection_id"],
        video_asset_id=row["video_asset_id"],
        name=row["name"],
        status=ClipRenderBatchStatus(row["status"]),
        job_count=row["job_count"],
        completed_count=row["completed_count"],
        failed_count=row["failed_count"],
        cancelled_count=row["cancelled_count"],
        started_at=from_iso_z(row["started_at"]),
        completed_at=from_iso_z(row["completed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_batch_item(row: sqlite3.Row) -> ClipRenderBatchItem:
    return ClipRenderBatchItem(
        id=row["id"],
        batch_id=row["batch_id"],
        render_job_id=row["render_job_id"],
        item_index=row["item_index"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteClipRenderingRepository(ClipRenderRepository):
    """Persistencia SQLite para jobs de render."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_job(self, job: ClipRenderJob) -> ClipRenderJob:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_jobs (
                    id, video_asset_id, ranked_clip_candidate_id, collection_id, status,
                    render_profile, source_path_snapshot, source_fingerprint,
                    start_seconds, end_seconds, duration_seconds, output_path,
                    output_container, video_codec, audio_codec, width, height,
                    frame_rate, audio_sample_rate, configuration_fingerprint,
                    renderer_version, progress_percent, started_at, completed_at,
                    cancelled_at, retry_count, warning_code, warning_message,
                    error_code, error_message, created_at, updated_at
                ) VALUES (
                    :id, :video_asset_id, :ranked_clip_candidate_id, :collection_id, :status,
                    :render_profile, :source_path_snapshot, :source_fingerprint,
                    :start_seconds, :end_seconds, :duration_seconds, :output_path,
                    :output_container, :video_codec, :audio_codec, :width, :height,
                    :frame_rate, :audio_sample_rate, :configuration_fingerprint,
                    :renderer_version, :progress_percent, :started_at, :completed_at,
                    :cancelled_at, :retry_count, :warning_code, :warning_message,
                    :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    render_profile = excluded.render_profile,
                    source_path_snapshot = excluded.source_path_snapshot,
                    source_fingerprint = excluded.source_fingerprint,
                    start_seconds = excluded.start_seconds,
                    end_seconds = excluded.end_seconds,
                    duration_seconds = excluded.duration_seconds,
                    output_path = excluded.output_path,
                    output_container = excluded.output_container,
                    video_codec = excluded.video_codec,
                    audio_codec = excluded.audio_codec,
                    width = excluded.width,
                    height = excluded.height,
                    frame_rate = excluded.frame_rate,
                    audio_sample_rate = excluded.audio_sample_rate,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    renderer_version = excluded.renderer_version,
                    progress_percent = excluded.progress_percent,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    cancelled_at = excluded.cancelled_at,
                    retry_count = excluded.retry_count,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                job.to_dict() | {
                    "status": job.status.value,
                    "render_profile": job.render_profile.value,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "cancelled_at": job.cancelled_at.isoformat() if job.cancelled_at else None,
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM clip_render_jobs WHERE id = ?", (job.id,)).fetchone()
        return _row_to_job(row)

    def get_job_by_id(self, job_id: str) -> ClipRenderJob | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_render_jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_job(row) if row else None

    def list_jobs(self) -> list[ClipRenderJob]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM clip_render_jobs ORDER BY created_at DESC, updated_at DESC").fetchall()
        return [_row_to_job(row) for row in rows]

    def get_job_by_candidate_id(self, candidate_id: str) -> ClipRenderJob | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM clip_render_jobs WHERE ranked_clip_candidate_id = ? ORDER BY created_at DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
        return _row_to_job(row) if row else None

    def list_jobs_for_candidate(self, candidate_id: str) -> list[ClipRenderJob]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_jobs WHERE ranked_clip_candidate_id = ? ORDER BY created_at DESC",
                (candidate_id,),
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def list_jobs_for_collection(self, collection_id: str) -> list[ClipRenderJob]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_jobs WHERE collection_id = ? ORDER BY created_at DESC",
                (collection_id,),
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def list_jobs_for_video(self, video_asset_id: str) -> list[ClipRenderJob]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_jobs WHERE video_asset_id = ? ORDER BY created_at DESC",
                (video_asset_id,),
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def upsert_artifact(self, artifact: ClipRenderArtifact) -> ClipRenderArtifact:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_artifacts (
                    id, render_job_id, artifact_type, managed_path, fingerprint,
                    size_bytes, duration_seconds, video_codec, audio_codec,
                    width, height, frame_rate, audio_sample_rate, verified,
                    verification_json, created_at
                ) VALUES (
                    :id, :render_job_id, :artifact_type, :managed_path, :fingerprint,
                    :size_bytes, :duration_seconds, :video_codec, :audio_codec,
                    :width, :height, :frame_rate, :audio_sample_rate, :verified,
                    :verification_json, :created_at
                )
                ON CONFLICT(render_job_id, artifact_type) DO UPDATE SET
                    managed_path = excluded.managed_path,
                    fingerprint = excluded.fingerprint,
                    size_bytes = excluded.size_bytes,
                    duration_seconds = excluded.duration_seconds,
                    video_codec = excluded.video_codec,
                    audio_codec = excluded.audio_codec,
                    width = excluded.width,
                    height = excluded.height,
                    frame_rate = excluded.frame_rate,
                    audio_sample_rate = excluded.audio_sample_rate,
                    verified = excluded.verified,
                    verification_json = excluded.verification_json
                """,
                artifact.to_dict() | {
                    "artifact_type": artifact.artifact_type.value,
                    "created_at": artifact.created_at.isoformat(),
                    "verified": 1 if artifact.verified else 0,
                },
            )
            row = connection.execute(
                "SELECT * FROM clip_render_artifacts WHERE render_job_id = ? AND artifact_type = ?",
                (artifact.render_job_id, artifact.artifact_type.value),
            ).fetchone()
        return _row_to_artifact(row)

    def list_artifacts_for_job(self, render_job_id: str) -> list[ClipRenderArtifact]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_artifacts WHERE render_job_id = ? ORDER BY created_at ASC",
                (render_job_id,),
            ).fetchall()
        return [_row_to_artifact(row) for row in rows]

    def get_artifact_for_job(self, render_job_id: str) -> ClipRenderArtifact | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM clip_render_artifacts WHERE render_job_id = ? ORDER BY created_at DESC LIMIT 1",
                (render_job_id,),
            ).fetchone()
        return _row_to_artifact(row) if row else None

    def delete_artifact_for_job(self, render_job_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM clip_render_artifacts WHERE render_job_id = ?",
                (render_job_id,),
            )
        return cursor.rowcount > 0

    def upsert_delivery(self, delivery: ClipRenderDelivery) -> ClipRenderDelivery:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_deliveries (
                    id, render_job_id, subtitle_track_id, subtitle_track_version,
                    subtitle_track_fingerprint, subtitle_mode, subtitle_format,
                    style_preset, style_json, source_export_path,
                    source_export_fingerprint, expected_cue_count, rendered_cue_count,
                    output_path, manifest_path, configuration_fingerprint, status,
                    progress_percent, warning_code, warning_message, error_code,
                    error_message, retry_count, created_at, updated_at,
                    completed_at, cancelled_at
                ) VALUES (
                    :id, :render_job_id, :subtitle_track_id, :subtitle_track_version,
                    :subtitle_track_fingerprint, :subtitle_mode, :subtitle_format,
                    :style_preset, :style_json, :source_export_path,
                    :source_export_fingerprint, :expected_cue_count, :rendered_cue_count,
                    :output_path, :manifest_path, :configuration_fingerprint, :status,
                    :progress_percent, :warning_code, :warning_message, :error_code,
                    :error_message, :retry_count, :created_at, :updated_at,
                    :completed_at, :cancelled_at
                )
                ON CONFLICT(configuration_fingerprint) DO UPDATE SET
                    subtitle_track_version = excluded.subtitle_track_version,
                    subtitle_track_fingerprint = excluded.subtitle_track_fingerprint,
                    subtitle_format = excluded.subtitle_format,
                    style_preset = excluded.style_preset,
                    style_json = excluded.style_json,
                    source_export_path = excluded.source_export_path,
                    source_export_fingerprint = excluded.source_export_fingerprint,
                    expected_cue_count = excluded.expected_cue_count,
                    rendered_cue_count = excluded.rendered_cue_count,
                    output_path = excluded.output_path,
                    manifest_path = excluded.manifest_path,
                    status = excluded.status,
                    progress_percent = excluded.progress_percent,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    retry_count = excluded.retry_count,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at,
                    cancelled_at = excluded.cancelled_at
                """,
                delivery.to_dict() | {
                    "subtitle_mode": delivery.subtitle_mode.value,
                    "style_preset": delivery.style_preset.value if delivery.style_preset else None,
                    "status": delivery.status.value,
                    "created_at": delivery.created_at.isoformat(),
                    "updated_at": delivery.updated_at.isoformat(),
                    "completed_at": delivery.completed_at.isoformat() if delivery.completed_at else None,
                    "cancelled_at": delivery.cancelled_at.isoformat() if delivery.cancelled_at else None,
                },
            )
            row = connection.execute("SELECT * FROM clip_render_deliveries WHERE configuration_fingerprint = ?", (delivery.configuration_fingerprint,)).fetchone()
        return _row_to_delivery(row)

    def get_delivery_by_id(self, delivery_id: str) -> ClipRenderDelivery | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_render_deliveries WHERE id = ?", (delivery_id,)).fetchone()
        return _row_to_delivery(row) if row else None

    def list_deliveries_for_job(self, render_job_id: str) -> list[ClipRenderDelivery]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_deliveries WHERE render_job_id = ? ORDER BY created_at DESC",
                (render_job_id,),
            ).fetchall()
        return [_row_to_delivery(row) for row in rows]

    def list_deliveries_for_candidate(self, candidate_id: str) -> list[ClipRenderDelivery]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.*
                FROM clip_render_deliveries d
                JOIN clip_render_jobs j ON j.id = d.render_job_id
                WHERE j.ranked_clip_candidate_id = ?
                ORDER BY d.created_at DESC
                """,
                (candidate_id,),
            ).fetchall()
        return [_row_to_delivery(row) for row in rows]

    def list_deliveries_for_video(self, video_asset_id: str) -> list[ClipRenderDelivery]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.*
                FROM clip_render_deliveries d
                JOIN clip_render_jobs j ON j.id = d.render_job_id
                WHERE j.video_asset_id = ?
                ORDER BY d.created_at DESC
                """,
                (video_asset_id,),
            ).fetchall()
        return [_row_to_delivery(row) for row in rows]

    def upsert_delivery_artifact(self, artifact: ClipRenderDeliveryArtifact) -> ClipRenderDeliveryArtifact:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_delivery_artifacts (
                    id, delivery_id, artifact_type, managed_path, fingerprint,
                    size_bytes, verified, verification_json, created_at
                ) VALUES (
                    :id, :delivery_id, :artifact_type, :managed_path, :fingerprint,
                    :size_bytes, :verified, :verification_json, :created_at
                )
                ON CONFLICT(delivery_id, artifact_type) DO UPDATE SET
                    managed_path = excluded.managed_path,
                    fingerprint = excluded.fingerprint,
                    size_bytes = excluded.size_bytes,
                    verified = excluded.verified,
                    verification_json = excluded.verification_json
                """,
                artifact.to_dict() | {
                    "artifact_type": artifact.artifact_type.value,
                    "verified": 1 if artifact.verified else 0,
                    "created_at": artifact.created_at.isoformat(),
                },
            )
            row = connection.execute(
                "SELECT * FROM clip_render_delivery_artifacts WHERE delivery_id = ? AND artifact_type = ?",
                (artifact.delivery_id, artifact.artifact_type.value),
            ).fetchone()
        return _row_to_delivery_artifact(row)

    def list_delivery_artifacts_for_delivery(self, delivery_id: str) -> list[ClipRenderDeliveryArtifact]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_delivery_artifacts WHERE delivery_id = ? ORDER BY created_at ASC",
                (delivery_id,),
            ).fetchall()
        return [_row_to_delivery_artifact(row) for row in rows]

    def get_delivery_artifact_for_delivery(self, delivery_id: str, artifact_type: str) -> ClipRenderDeliveryArtifact | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM clip_render_delivery_artifacts WHERE delivery_id = ? AND artifact_type = ?",
                (delivery_id, artifact_type),
            ).fetchone()
        return _row_to_delivery_artifact(row) if row else None

    def delete_delivery_artifacts_for_delivery(self, delivery_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute("DELETE FROM clip_render_delivery_artifacts WHERE delivery_id = ?", (delivery_id,))
        return cursor.rowcount > 0

    def delete_delivery(self, delivery_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute("DELETE FROM clip_render_deliveries WHERE id = ?", (delivery_id,))
        return cursor.rowcount > 0

    def append_event(self, event: ClipRenderEvent) -> ClipRenderEvent:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_events (
                    id, render_job_id, event_index, event_type, progress_percent,
                    message, details_json, created_at
                ) VALUES (
                    :id, :render_job_id, :event_index, :event_type, :progress_percent,
                    :message, :details_json, :created_at
                )
                """,
                event.to_dict() | {"created_at": event.created_at.isoformat()},
            )
            row = connection.execute("SELECT * FROM clip_render_events WHERE id = ?", (event.id,)).fetchone()
        return _row_to_event(row)

    def list_events_for_job(self, render_job_id: str) -> list[ClipRenderEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_events WHERE render_job_id = ? ORDER BY event_index ASC",
                (render_job_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def upsert_batch(self, batch: ClipRenderBatch) -> ClipRenderBatch:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_batches (
                    id, collection_id, video_asset_id, name, status, job_count,
                    completed_count, failed_count, cancelled_count, started_at,
                    completed_at, created_at, updated_at
                ) VALUES (
                    :id, :collection_id, :video_asset_id, :name, :status, :job_count,
                    :completed_count, :failed_count, :cancelled_count, :started_at,
                    :completed_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    job_count = excluded.job_count,
                    completed_count = excluded.completed_count,
                    failed_count = excluded.failed_count,
                    cancelled_count = excluded.cancelled_count,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    updated_at = excluded.updated_at
                """,
                batch.to_dict() | {
                    "status": batch.status.value,
                    "started_at": batch.started_at.isoformat() if batch.started_at else None,
                    "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                    "created_at": batch.created_at.isoformat(),
                    "updated_at": batch.updated_at.isoformat(),
                },
            )
            row = connection.execute("SELECT * FROM clip_render_batches WHERE id = ?", (batch.id,)).fetchone()
        return _row_to_batch(row)

    def get_batch_by_id(self, batch_id: str) -> ClipRenderBatch | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_render_batches WHERE id = ?", (batch_id,)).fetchone()
        return _row_to_batch(row) if row else None

    def list_batches_for_collection(self, collection_id: str) -> list[ClipRenderBatch]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_batches WHERE collection_id = ? ORDER BY created_at DESC",
                (collection_id,),
            ).fetchall()
        return [_row_to_batch(row) for row in rows]

    def list_batches_for_video(self, video_asset_id: str) -> list[ClipRenderBatch]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_batches WHERE video_asset_id = ? ORDER BY created_at DESC",
                (video_asset_id,),
            ).fetchall()
        return [_row_to_batch(row) for row in rows]

    def add_batch_item(self, item: ClipRenderBatchItem) -> ClipRenderBatchItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_render_batch_items (
                    id, batch_id, render_job_id, item_index, created_at
                ) VALUES (
                    :id, :batch_id, :render_job_id, :item_index, :created_at
                )
                """,
                item.to_dict() | {"created_at": item.created_at.isoformat()},
            )
            row = connection.execute("SELECT * FROM clip_render_batch_items WHERE id = ?", (item.id,)).fetchone()
        return _row_to_batch_item(row)

    def list_batch_items(self, batch_id: str) -> list[ClipRenderBatchItem]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_render_batch_items WHERE batch_id = ? ORDER BY item_index ASC",
                (batch_id,),
            ).fetchall()
        return [_row_to_batch_item(row) for row in rows]

    def delete_job(self, job_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute("DELETE FROM clip_render_jobs WHERE id = ?", (job_id,))
            connection.execute("DELETE FROM clip_render_artifacts WHERE render_job_id = ?", (job_id,))
            connection.execute("DELETE FROM clip_render_events WHERE render_job_id = ?", (job_id,))
        return cursor.rowcount > 0
