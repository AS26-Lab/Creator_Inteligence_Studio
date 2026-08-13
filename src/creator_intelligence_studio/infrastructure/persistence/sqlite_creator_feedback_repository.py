"""SQLite repository for creator feedback and learning signals."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.creator_feedback import (
    CreatorFeedbackEvent,
    CreatorFeedbackRepository,
    CreatorLearningSignal,
    CreatorLearningSignalEvidence,
)
from creator_intelligence_studio.domain.creator_feedback.value_objects import (
    CreatorFeedbackEventSource,
    CreatorFeedbackEventType,
    CreatorFeedbackExplicitness,
    CreatorFeedbackScope,
    CreatorLearningSignalConfidence,
    CreatorLearningSignalPolarity,
    CreatorLearningSignalStatus,
    CreatorLearningSignalType,
)
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _event_from_row(row: sqlite3.Row) -> CreatorFeedbackEvent:
    return CreatorFeedbackEvent(
        id=row["id"],
        dedupe_key=row["dedupe_key"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        workflow_type=row["workflow_type"],
        artifact_type=row["artifact_type"],
        artifact_id=row["artifact_id"],
        source_version_id=row["source_version_id"],
        result_version_id=row["result_version_id"],
        ai_execution_id=row["ai_execution_id"],
        event_type=CreatorFeedbackEventType(row["event_type"]),
        event_source=CreatorFeedbackEventSource(row["event_source"]),
        signal_explicitness=CreatorFeedbackExplicitness(row["signal_explicitness"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        metadata_json=row["metadata_json"] or "{}",
    )


def _signal_from_row(row: sqlite3.Row) -> CreatorLearningSignal:
    return CreatorLearningSignal(
        id=row["id"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        workflow_type=row["workflow_type"],
        scope=CreatorFeedbackScope(row["scope"]),
        signal_type=CreatorLearningSignalType(row["signal_type"]),
        signal_value=row["signal_value"],
        polarity=CreatorLearningSignalPolarity(row["polarity"]),
        strength=row["strength"],
        confidence=CreatorLearningSignalConfidence(row["confidence"]),
        evidence_count=row["evidence_count"],
        supporting_event_count=row["supporting_event_count"],
        contradicting_event_count=row["contradicting_event_count"],
        status=CreatorLearningSignalStatus(row["status"]),
        first_observed_at=from_iso_z(row["first_observed_at"]) or utc_now(),
        last_observed_at=from_iso_z(row["last_observed_at"]) or utc_now(),
        algorithm_version=row["algorithm_version"],
        metadata_json=row["metadata_json"] or "{}",
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _evidence_from_row(row: sqlite3.Row) -> CreatorLearningSignalEvidence:
    return CreatorLearningSignalEvidence(
        id=row["id"],
        signal_id=row["signal_id"],
        feedback_event_id=row["feedback_event_id"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _signal_key(signal: CreatorLearningSignal) -> str:
    return "|".join(
        [
            signal.creator_id,
            signal.project_id or "",
            signal.workflow_type or "",
            signal.scope.value,
            signal.signal_type.value,
            signal.signal_value,
            signal.polarity.value,
        ]
    )


class SQLiteCreatorFeedbackRepository(CreatorFeedbackRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_feedback_event(self, event: CreatorFeedbackEvent) -> CreatorFeedbackEvent:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_feedback_events (
                    id, dedupe_key, creator_id, project_id, workflow_type, artifact_type,
                    artifact_id, source_version_id, result_version_id, ai_execution_id,
                    event_type, event_source, signal_explicitness, created_at, metadata_json
                ) VALUES (
                    :id, :dedupe_key, :creator_id, :project_id, :workflow_type, :artifact_type,
                    :artifact_id, :source_version_id, :result_version_id, :ai_execution_id,
                    :event_type, :event_source, :signal_explicitness, :created_at, :metadata_json
                )
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    creator_id = excluded.creator_id,
                    project_id = excluded.project_id,
                    workflow_type = excluded.workflow_type,
                    artifact_type = excluded.artifact_type,
                    artifact_id = excluded.artifact_id,
                    source_version_id = excluded.source_version_id,
                    result_version_id = excluded.result_version_id,
                    ai_execution_id = excluded.ai_execution_id,
                    event_type = excluded.event_type,
                    event_source = excluded.event_source,
                    signal_explicitness = excluded.signal_explicitness,
                    metadata_json = excluded.metadata_json
                """,
                event.to_dict(),
            )
            row = connection.execute("SELECT * FROM creator_feedback_events WHERE dedupe_key = ?", (event.dedupe_key,)).fetchone()
        return _event_from_row(row)

    def get_feedback_event_by_id(self, event_id: str) -> CreatorFeedbackEvent | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_feedback_events WHERE id = ?", (event_id,)).fetchone()
        return _event_from_row(row) if row else None

    def get_feedback_event_by_dedupe_key(self, dedupe_key: str) -> CreatorFeedbackEvent | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_feedback_events WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
        return _event_from_row(row) if row else None

    def list_feedback_events(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorFeedbackEvent]:
        clauses = ["creator_id = ?"]
        params: list[object] = [creator_id]
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if workflow_type is not None:
            clauses.append("workflow_type = ?")
            params.append(workflow_type)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        sql = f"SELECT * FROM creator_feedback_events WHERE {' AND '.join(clauses)} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        with self._database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [_event_from_row(row) for row in rows]

    def upsert_learning_signal(self, signal: CreatorLearningSignal) -> CreatorLearningSignal:
        signal_payload = signal.to_dict() | {"signal_key": _signal_key(signal)}
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_learning_signals (
                    id, signal_key, creator_id, project_id, workflow_type, scope, signal_type,
                    signal_value, polarity, strength, confidence, evidence_count,
                    supporting_event_count, contradicting_event_count, status,
                    first_observed_at, last_observed_at, algorithm_version,
                    metadata_json, created_at, updated_at
                ) VALUES (
                    :id, :signal_key, :creator_id, :project_id, :workflow_type, :scope, :signal_type,
                    :signal_value, :polarity, :strength, :confidence, :evidence_count,
                    :supporting_event_count, :contradicting_event_count, :status,
                    :first_observed_at, :last_observed_at, :algorithm_version,
                    :metadata_json, :created_at, :updated_at
                )
                ON CONFLICT(signal_key) DO UPDATE SET
                    strength = excluded.strength,
                    confidence = excluded.confidence,
                    evidence_count = excluded.evidence_count,
                    supporting_event_count = excluded.supporting_event_count,
                    contradicting_event_count = excluded.contradicting_event_count,
                    status = excluded.status,
                    first_observed_at = excluded.first_observed_at,
                    last_observed_at = excluded.last_observed_at,
                    algorithm_version = excluded.algorithm_version,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                signal_payload,
            )
            row = connection.execute("SELECT * FROM creator_learning_signals WHERE id = ?", (signal.id,)).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT * FROM creator_learning_signals
                    WHERE creator_id = ?
                      AND signal_key = ?
                    """,
                    (signal.creator_id, _signal_key(signal)),
                ).fetchone()
        return _signal_from_row(row)

    def get_learning_signal_by_id(self, signal_id: str) -> CreatorLearningSignal | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_learning_signals WHERE id = ?", (signal_id,)).fetchone()
        return _signal_from_row(row) if row else None

    def get_learning_signal_by_key(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str | None,
        scope: str,
        signal_type: str,
        signal_value: str,
        polarity: str,
    ) -> CreatorLearningSignal | None:
        signal = CreatorLearningSignal(
            id="",
            creator_id=creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            scope=CreatorFeedbackScope(scope),
            signal_type=CreatorLearningSignalType(signal_type),
            signal_value=signal_value,
            polarity=CreatorLearningSignalPolarity(polarity),
            strength=0.0,
            confidence=CreatorLearningSignalConfidence.LOW,
            evidence_count=0,
            supporting_event_count=0,
            contradicting_event_count=0,
            status=CreatorLearningSignalStatus.OBSERVED,
            first_observed_at=utc_now(),
            last_observed_at=utc_now(),
            algorithm_version="",
            metadata_json="{}",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_learning_signals WHERE signal_key = ? AND creator_id = ?",
                (_signal_key(signal), creator_id),
            ).fetchone()
        return _signal_from_row(row) if row else None

    def list_learning_signals(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
        signal_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorLearningSignal]:
        clauses = ["creator_id = ?"]
        params: list[object] = [creator_id]
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if workflow_type is not None:
            clauses.append("workflow_type = ?")
            params.append(workflow_type)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if signal_type is not None:
            clauses.append("signal_type = ?")
            params.append(signal_type)
        sql = f"SELECT * FROM creator_learning_signals WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        with self._database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [_signal_from_row(row) for row in rows]

    def upsert_learning_signal_evidence(self, evidence: CreatorLearningSignalEvidence) -> CreatorLearningSignalEvidence:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_learning_signal_evidence (
                    id, signal_id, feedback_event_id, created_at
                ) VALUES (
                    :id, :signal_id, :feedback_event_id, :created_at
                )
                ON CONFLICT(signal_id, feedback_event_id) DO NOTHING
                """,
                evidence.to_dict(),
            )
            row = connection.execute("SELECT * FROM creator_learning_signal_evidence WHERE signal_id = ? AND feedback_event_id = ?", (evidence.signal_id, evidence.feedback_event_id)).fetchone()
        return _evidence_from_row(row)

    def list_learning_signal_evidence(self, signal_id: str) -> list[CreatorLearningSignalEvidence]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_learning_signal_evidence WHERE signal_id = ? ORDER BY created_at ASC, id ASC", (signal_id,)).fetchall()
        return [_evidence_from_row(row) for row in rows]

    def delete_learning_signals_for_creator(self, creator_id: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM creator_learning_signals WHERE creator_id = ?", (creator_id,))

    def delete_learning_signal_evidence_for_creator(self, creator_id: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                DELETE FROM creator_learning_signal_evidence
                WHERE signal_id IN (
                    SELECT id FROM creator_learning_signals WHERE creator_id = ?
                )
                """,
                (creator_id,),
            )
