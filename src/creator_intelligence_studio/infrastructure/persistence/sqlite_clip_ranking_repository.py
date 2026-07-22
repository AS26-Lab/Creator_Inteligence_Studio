"""Repositorio SQLite para ranking de clips."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from creator_intelligence_studio.domain.clip_ranking.entities import (
    ClipCollection,
    ClipCollectionItem,
    ClipRankingRun,
    ClipReviewEvent,
    RankedClipCandidate,
)
from creator_intelligence_studio.domain.clip_ranking.repositories import ClipRankingRepository
from creator_intelligence_studio.domain.clip_ranking.value_objects import ClipRankingReviewStatus, ClipRankingRunStatus
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


def _row_to_run(row: sqlite3.Row) -> ClipRankingRun:
    return ClipRankingRun(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        multimodal_analysis_id=row["multimodal_analysis_id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        status=ClipRankingRunStatus(row["status"]),
        ranker_version=row["ranker_version"],
        configuration_fingerprint=row["configuration_fingerprint"],
        source_fingerprint=row["source_fingerprint"],
        candidate_count=row["candidate_count"],
        ranked_candidate_count=row["ranked_candidate_count"],
        selected_count=row["selected_count"],
        rejected_count=row["rejected_count"],
        review_count=row["review_count"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]) or utc_now(),
        warning_code=row["warning_code"],
        warning_message=row["warning_message"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_candidate(row: sqlite3.Row) -> RankedClipCandidate:
    return RankedClipCandidate(
        id=row["id"],
        ranking_run_id=row["ranking_run_id"],
        multimodal_candidate_id=row["multimodal_candidate_id"],
        rank_position=row["rank_position"],
        original_start_seconds=row["original_start_seconds"],
        original_end_seconds=row["original_end_seconds"],
        adjusted_start_seconds=row["adjusted_start_seconds"],
        adjusted_end_seconds=row["adjusted_end_seconds"],
        duration_seconds=row["duration_seconds"],
        candidate_type=row["candidate_type"],
        source_score=row["source_score"],
        source_confidence=row["source_confidence"],
        rank_score=row["rank_score"],
        quality_score=row["quality_score"],
        diversity_score=row["diversity_score"],
        overlap_penalty=row["overlap_penalty"],
        duration_score=row["duration_score"],
        opening_score=row["opening_score"],
        closing_score=row["closing_score"],
        speech_score=row["speech_score"],
        visual_score=row["visual_score"],
        acoustic_score=row["acoustic_score"],
        transition_score=row["transition_score"],
        novelty_score=row["novelty_score"],
        evidence_strength_score=row["evidence_strength_score"],
        review_status=ClipRankingReviewStatus(row["review_status"]),
        user_rating=row["user_rating"],
        user_note=row["user_note"],
        explanation=_json_loads(row["explanation_json"], {}),
        tags=tuple(_json_loads(row["tags_json"], [])),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_event(row: sqlite3.Row) -> ClipReviewEvent:
    return ClipReviewEvent(
        id=row["id"],
        ranked_clip_candidate_id=row["ranked_clip_candidate_id"],
        event_index=row["event_index"],
        action=row["action"],
        previous_status=ClipRankingReviewStatus(row["previous_status"]) if row["previous_status"] else None,
        new_status=ClipRankingReviewStatus(row["new_status"]) if row["new_status"] else None,
        previous_start_seconds=row["previous_start_seconds"],
        previous_end_seconds=row["previous_end_seconds"],
        new_start_seconds=row["new_start_seconds"],
        new_end_seconds=row["new_end_seconds"],
        rating=row["rating"],
        note=row["note"],
        tags=tuple(_json_loads(row["tags_json"], [])),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_collection(row: sqlite3.Row) -> ClipCollection:
    return ClipCollection(
        id=row["id"],
        video_asset_id=row["video_asset_id"],
        name=row["name"],
        description=row["description"],
        status=row["status"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_collection_item(row: sqlite3.Row) -> ClipCollectionItem:
    return ClipCollectionItem(
        id=row["id"],
        collection_id=row["collection_id"],
        ranked_clip_candidate_id=row["ranked_clip_candidate_id"],
        item_index=row["item_index"],
        custom_title=row["custom_title"],
        custom_note=row["custom_note"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _persist_candidate(connection: sqlite3.Connection, candidate: RankedClipCandidate) -> sqlite3.Row:
    existing = connection.execute(
        """
        SELECT id
        FROM ranked_clip_candidates
        WHERE ranking_run_id = ? AND multimodal_candidate_id = ?
        """,
        (candidate.ranking_run_id, candidate.multimodal_candidate_id),
    ).fetchone()
    payload = candidate.to_dict() | {
        "review_status": candidate.review_status.value,
        "explanation_json": json.dumps(candidate.explanation, ensure_ascii=False, sort_keys=True),
        "tags_json": json.dumps(list(candidate.tags), ensure_ascii=False),
    }
    if existing is None:
        connection.execute(
            """
            INSERT INTO ranked_clip_candidates (
                id, ranking_run_id, multimodal_candidate_id, rank_position,
                original_start_seconds, original_end_seconds, adjusted_start_seconds,
                adjusted_end_seconds, duration_seconds, candidate_type, source_score,
                source_confidence, rank_score, quality_score, diversity_score,
                overlap_penalty, duration_score, opening_score, closing_score,
                speech_score, visual_score, acoustic_score, transition_score,
                novelty_score, evidence_strength_score, review_status, user_rating,
                user_note, explanation_json, tags_json, created_at, updated_at
            )
            VALUES (
                :id, :ranking_run_id, :multimodal_candidate_id, :rank_position,
                :original_start_seconds, :original_end_seconds, :adjusted_start_seconds,
                :adjusted_end_seconds, :duration_seconds, :candidate_type, :source_score,
                :source_confidence, :rank_score, :quality_score, :diversity_score,
                :overlap_penalty, :duration_score, :opening_score, :closing_score,
                :speech_score, :visual_score, :acoustic_score, :transition_score,
                :novelty_score, :evidence_strength_score, :review_status, :user_rating,
                :user_note, :explanation_json, :tags_json, :created_at, :updated_at
            )
            """,
            payload,
        )
        candidate_id = candidate.id
    else:
        candidate_id = existing["id"]
        connection.execute(
            """
            UPDATE ranked_clip_candidates
            SET
                rank_position = :rank_position,
                original_start_seconds = :original_start_seconds,
                original_end_seconds = :original_end_seconds,
                adjusted_start_seconds = :adjusted_start_seconds,
                adjusted_end_seconds = :adjusted_end_seconds,
                duration_seconds = :duration_seconds,
                candidate_type = :candidate_type,
                source_score = :source_score,
                source_confidence = :source_confidence,
                rank_score = :rank_score,
                quality_score = :quality_score,
                diversity_score = :diversity_score,
                overlap_penalty = :overlap_penalty,
                duration_score = :duration_score,
                opening_score = :opening_score,
                closing_score = :closing_score,
                speech_score = :speech_score,
                visual_score = :visual_score,
                acoustic_score = :acoustic_score,
                transition_score = :transition_score,
                novelty_score = :novelty_score,
                evidence_strength_score = :evidence_strength_score,
                review_status = :review_status,
                user_rating = :user_rating,
                user_note = :user_note,
                explanation_json = :explanation_json,
                tags_json = :tags_json,
                updated_at = :updated_at
            WHERE ranking_run_id = :ranking_run_id AND multimodal_candidate_id = :multimodal_candidate_id
            """,
            payload,
        )
    row = connection.execute("SELECT * FROM ranked_clip_candidates WHERE id = ?", (candidate_id,)).fetchone()
    if row is None:
        raise sqlite3.DatabaseError("No se pudo persistir el candidato rankeado.")
    return row


class SQLiteClipRankingRepository(ClipRankingRepository):
    """Repositorio SQLite para ranking de clips."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert(self, run: ClipRankingRun, candidates: list[RankedClipCandidate]) -> ClipRankingRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_ranking_runs (
                    id, video_asset_id, multimodal_analysis_id, creator_id, project_id,
                    status, ranker_version, configuration_fingerprint, source_fingerprint,
                    candidate_count, ranked_candidate_count, selected_count, rejected_count,
                    review_count, started_at, completed_at, warning_code, warning_message,
                    error_code, error_message, created_at, updated_at
                )
                VALUES (
                    :id, :video_asset_id, :multimodal_analysis_id, :creator_id, :project_id,
                    :status, :ranker_version, :configuration_fingerprint, :source_fingerprint,
                    :candidate_count, :ranked_candidate_count, :selected_count, :rejected_count,
                    :review_count, :started_at, :completed_at, :warning_code, :warning_message,
                    :error_code, :error_message, :created_at, :updated_at
                )
                ON CONFLICT(video_asset_id) DO UPDATE SET
                    multimodal_analysis_id = excluded.multimodal_analysis_id,
                    creator_id = excluded.creator_id,
                    project_id = excluded.project_id,
                    status = excluded.status,
                    ranker_version = excluded.ranker_version,
                    configuration_fingerprint = excluded.configuration_fingerprint,
                    source_fingerprint = excluded.source_fingerprint,
                    candidate_count = excluded.candidate_count,
                    ranked_candidate_count = excluded.ranked_candidate_count,
                    selected_count = excluded.selected_count,
                    rejected_count = excluded.rejected_count,
                    review_count = excluded.review_count,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    warning_code = excluded.warning_code,
                    warning_message = excluded.warning_message,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
                """,
                run.to_dict(),
            )
            current = connection.execute(
                "SELECT id FROM clip_ranking_runs WHERE video_asset_id = ?",
                (run.video_asset_id,),
            ).fetchone()
            if current is None:
                raise sqlite3.DatabaseError("No se pudo leer el ranking de clips insertado.")
            keep_ids = tuple(candidate.id for candidate in candidates)
            if keep_ids:
                placeholders = ",".join("?" for _ in keep_ids)
                connection.execute(
                    f"DELETE FROM ranked_clip_candidates WHERE ranking_run_id = ? AND id NOT IN ({placeholders})",
                    (current["id"], *keep_ids),
                )
            else:
                connection.execute("DELETE FROM ranked_clip_candidates WHERE ranking_run_id = ?", (current["id"],))
            for candidate in sorted(candidates, key=lambda item: item.rank_position):
                _persist_candidate(
                    connection,
                    replace(candidate, ranking_run_id=current["id"]) if candidate.ranking_run_id != current["id"] else candidate,
                )
            row = connection.execute("SELECT * FROM clip_ranking_runs WHERE id = ?", (current["id"],)).fetchone()
        return _row_to_run(row)

    def get_by_video_asset_id(self, video_asset_id: str) -> ClipRankingRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_ranking_runs WHERE video_asset_id = ?", (video_asset_id,)).fetchone()
        return _row_to_run(row) if row else None

    def get_by_id(self, ranking_run_id: str) -> ClipRankingRun | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_ranking_runs WHERE id = ?", (ranking_run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def list_candidates(self, ranking_run_id: str) -> list[RankedClipCandidate]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ranked_clip_candidates WHERE ranking_run_id = ? ORDER BY rank_position ASC",
                (ranking_run_id,),
            ).fetchall()
        return [_row_to_candidate(row) for row in rows]

    def get_candidate_by_id(self, candidate_id: str) -> RankedClipCandidate | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM ranked_clip_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _row_to_candidate(row) if row else None

    def upsert_candidate(self, candidate: RankedClipCandidate) -> RankedClipCandidate:
        with self._database.connect() as connection:
            row = _persist_candidate(connection, candidate)
        return _row_to_candidate(row)

    def append_review_event(self, event: ClipReviewEvent) -> ClipReviewEvent:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_review_events (
                    id, ranked_clip_candidate_id, event_index, action, previous_status,
                    new_status, previous_start_seconds, previous_end_seconds, new_start_seconds,
                    new_end_seconds, rating, note, tags_json, created_at
                )
                VALUES (
                    :id, :ranked_clip_candidate_id, :event_index, :action, :previous_status,
                    :new_status, :previous_start_seconds, :previous_end_seconds, :new_start_seconds,
                    :new_end_seconds, :rating, :note, :tags_json, :created_at
                )
                """,
                event.to_dict()
                | {
                    "previous_status": event.previous_status.value if event.previous_status else None,
                    "new_status": event.new_status.value if event.new_status else None,
                    "tags_json": json.dumps(list(event.tags), ensure_ascii=False),
                },
            )
            row = connection.execute("SELECT * FROM clip_review_events WHERE id = ?", (event.id,)).fetchone()
        return _row_to_event(row)

    def list_review_events(self, ranked_clip_candidate_id: str) -> list[ClipReviewEvent]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_review_events WHERE ranked_clip_candidate_id = ? ORDER BY event_index ASC",
                (ranked_clip_candidate_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def get_collection_by_id(self, collection_id: str) -> ClipCollection | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM clip_collections WHERE id = ?", (collection_id,)).fetchone()
        return _row_to_collection(row) if row else None

    def list_collections(self, video_asset_id: str) -> list[ClipCollection]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM clip_collections WHERE video_asset_id = ? ORDER BY created_at ASC", (video_asset_id,)).fetchall()
        return [_row_to_collection(row) for row in rows]

    def list_collection_items(self, collection_id: str) -> list[ClipCollectionItem]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM clip_collection_items WHERE collection_id = ? ORDER BY item_index ASC",
                (collection_id,),
            ).fetchall()
        return [_row_to_collection_item(row) for row in rows]

    def upsert_collection(self, collection: ClipCollection) -> ClipCollection:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_collections (
                    id, video_asset_id, name, description, status, created_at, updated_at
                ) VALUES (
                    :id, :video_asset_id, :name, :description, :status, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                collection.to_dict(),
            )
            row = connection.execute("SELECT * FROM clip_collections WHERE id = ?", (collection.id,)).fetchone()
        return _row_to_collection(row)

    def add_collection_item(self, item: ClipCollectionItem) -> ClipCollectionItem:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_collection_items (
                    id, collection_id, ranked_clip_candidate_id, item_index, custom_title, custom_note, created_at
                ) VALUES (
                    :id, :collection_id, :ranked_clip_candidate_id, :item_index, :custom_title, :custom_note, :created_at
                )
                ON CONFLICT(collection_id, ranked_clip_candidate_id) DO UPDATE SET
                    item_index = excluded.item_index,
                    custom_title = excluded.custom_title,
                    custom_note = excluded.custom_note
                """,
                item.to_dict(),
            )
            row = connection.execute("SELECT * FROM clip_collection_items WHERE id = ?", (item.id,)).fetchone()
        return _row_to_collection_item(row)

    def remove_collection_item(self, collection_id: str, ranked_clip_candidate_id: str) -> bool:
        with self._database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM clip_collection_items WHERE collection_id = ? AND ranked_clip_candidate_id = ?",
                (collection_id, ranked_clip_candidate_id),
            )
        return cursor.rowcount > 0

    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute("SELECT id FROM clip_ranking_runs WHERE video_asset_id = ?", (video_asset_id,)).fetchone()
            if row is None:
                return False
            run_id = row["id"]
            connection.execute("DELETE FROM clip_collections WHERE video_asset_id = ?", (video_asset_id,))
            connection.execute("DELETE FROM ranked_clip_candidates WHERE ranking_run_id = ?", (run_id,))
            cursor = connection.execute("DELETE FROM clip_ranking_runs WHERE video_asset_id = ?", (video_asset_id,))
        return cursor.rowcount > 0
