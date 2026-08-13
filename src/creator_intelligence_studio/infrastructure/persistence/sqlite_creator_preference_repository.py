"""SQLite repository for creator preference candidates and confirmed preferences."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.creator_preferences import (
    CreatorConfirmedPreference,
    CreatorPreferenceCandidate,
    CreatorPreferenceCandidateEvidence,
)
from creator_intelligence_studio.domain.creator_preferences.value_objects import (
    CreatorPreferenceCandidateStatus,
    CreatorPreferenceConfidence,
    CreatorPreferenceScope,
    CreatorPreferenceType,
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


def _candidate_from_row(row: sqlite3.Row) -> CreatorPreferenceCandidate:
    return CreatorPreferenceCandidate(
        id=row["id"],
        candidate_key=row["candidate_key"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        workflow_type=row["workflow_type"],
        scope=CreatorPreferenceScope(row["scope"]),
        preference_type=CreatorPreferenceType(row["preference_type"]),
        proposed_value=row["proposed_value"],
        evidence_count=row["evidence_count"],
        supporting_signal_count=row["supporting_signal_count"],
        conflicting_signal_count=row["conflicting_signal_count"],
        confidence=CreatorPreferenceConfidence(row["confidence"]),
        status=CreatorPreferenceCandidateStatus(row["status"]),
        dismissed_evidence_count=row["dismissed_evidence_count"],
        source_signal_ids_json=row["source_signal_ids_json"] or "[]",
        explanation_json=row["explanation_json"] or "{}",
        algorithm_version=row["algorithm_version"],
        first_observed_at=from_iso_z(row["first_observed_at"]) or utc_now(),
        last_observed_at=from_iso_z(row["last_observed_at"]) or utc_now(),
        confirmed_preference_id=row["confirmed_preference_id"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _preference_from_row(row: sqlite3.Row) -> CreatorConfirmedPreference:
    return CreatorConfirmedPreference(
        id=row["id"],
        preference_key=row["preference_key"],
        creator_id=row["creator_id"],
        project_id=row["project_id"],
        workflow_type=row["workflow_type"],
        scope=CreatorPreferenceScope(row["scope"]),
        preference_type=CreatorPreferenceType(row["preference_type"]),
        value_json=row["value_json"] or "{}",
        source_candidate_id=row["source_candidate_id"],
        confirmed_by=row["confirmed_by"],
        confirmed_at=from_iso_z(row["confirmed_at"]) or utc_now(),
        active=bool(row["active"]),
        provenance_json=row["provenance_json"] or "{}",
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _evidence_from_row(row: sqlite3.Row) -> CreatorPreferenceCandidateEvidence:
    return CreatorPreferenceCandidateEvidence(
        id=row["id"],
        candidate_id=row["candidate_id"],
        learning_signal_id=row["learning_signal_id"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteCreatorPreferenceRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def upsert_candidate(self, candidate: CreatorPreferenceCandidate) -> CreatorPreferenceCandidate:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_preference_candidates (
                    id, candidate_key, creator_id, project_id, workflow_type, scope,
                    preference_type, proposed_value, evidence_count,
                    supporting_signal_count, conflicting_signal_count, confidence,
                    status, dismissed_evidence_count, source_signal_ids_json,
                    explanation_json, algorithm_version, first_observed_at,
                    last_observed_at, confirmed_preference_id, created_at, updated_at
                ) VALUES (
                    :id, :candidate_key, :creator_id, :project_id, :workflow_type, :scope,
                    :preference_type, :proposed_value, :evidence_count,
                    :supporting_signal_count, :conflicting_signal_count, :confidence,
                    :status, :dismissed_evidence_count, :source_signal_ids_json,
                    :explanation_json, :algorithm_version, :first_observed_at,
                    :last_observed_at, :confirmed_preference_id, :created_at, :updated_at
                )
                ON CONFLICT(candidate_key) DO UPDATE SET
                    evidence_count = excluded.evidence_count,
                    supporting_signal_count = excluded.supporting_signal_count,
                    conflicting_signal_count = excluded.conflicting_signal_count,
                    confidence = excluded.confidence,
                    status = excluded.status,
                    dismissed_evidence_count = excluded.dismissed_evidence_count,
                    source_signal_ids_json = excluded.source_signal_ids_json,
                    explanation_json = excluded.explanation_json,
                    algorithm_version = excluded.algorithm_version,
                    first_observed_at = excluded.first_observed_at,
                    last_observed_at = excluded.last_observed_at,
                    confirmed_preference_id = excluded.confirmed_preference_id,
                    updated_at = excluded.updated_at
                """,
                candidate.to_dict(),
            )
            row = connection.execute("SELECT * FROM creator_preference_candidates WHERE candidate_key = ?", (candidate.candidate_key,)).fetchone()
        return _candidate_from_row(row)

    def get_candidate_by_id(self, candidate_id: str) -> CreatorPreferenceCandidate | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_preference_candidates WHERE id = ?", (candidate_id,)).fetchone()
        return _candidate_from_row(row) if row else None

    def get_candidate_by_key(self, candidate_key: str) -> CreatorPreferenceCandidate | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_preference_candidates WHERE candidate_key = ?", (candidate_key,)).fetchone()
        return _candidate_from_row(row) if row else None

    def list_candidates(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
        preference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorPreferenceCandidate]:
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
        if preference_type is not None:
            clauses.append("preference_type = ?")
            params.append(preference_type)
        sql = f"SELECT * FROM creator_preference_candidates WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        with self._database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [_candidate_from_row(row) for row in rows]

    def upsert_candidate_evidence(self, evidence: CreatorPreferenceCandidateEvidence) -> CreatorPreferenceCandidateEvidence:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_preference_candidate_evidence (
                    id, candidate_id, learning_signal_id, created_at
                ) VALUES (
                    :id, :candidate_id, :learning_signal_id, :created_at
                )
                ON CONFLICT(candidate_id, learning_signal_id) DO NOTHING
                """,
                evidence.to_dict(),
            )
            row = connection.execute(
                "SELECT * FROM creator_preference_candidate_evidence WHERE candidate_id = ? AND learning_signal_id = ?",
                (evidence.candidate_id, evidence.learning_signal_id),
            ).fetchone()
        return _evidence_from_row(row)

    def list_candidate_evidence(self, candidate_id: str) -> list[CreatorPreferenceCandidateEvidence]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM creator_preference_candidate_evidence WHERE candidate_id = ? ORDER BY created_at ASC, id ASC",
                (candidate_id,),
            ).fetchall()
        return [_evidence_from_row(row) for row in rows]

    def upsert_confirmed_preference(self, preference: CreatorConfirmedPreference) -> CreatorConfirmedPreference:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_preferences (
                    id, preference_key, creator_id, project_id, workflow_type, scope,
                    preference_type, value_json, source_candidate_id, confirmed_by,
                    confirmed_at, active, provenance_json, created_at, updated_at
                ) VALUES (
                    :id, :preference_key, :creator_id, :project_id, :workflow_type, :scope,
                    :preference_type, :value_json, :source_candidate_id, :confirmed_by,
                    :confirmed_at, :active, :provenance_json, :created_at, :updated_at
                )
                ON CONFLICT(preference_key) DO UPDATE SET
                    project_id = excluded.project_id,
                    workflow_type = excluded.workflow_type,
                    scope = excluded.scope,
                    preference_type = excluded.preference_type,
                    value_json = excluded.value_json,
                    source_candidate_id = excluded.source_candidate_id,
                    confirmed_by = excluded.confirmed_by,
                    confirmed_at = excluded.confirmed_at,
                    active = excluded.active,
                    provenance_json = excluded.provenance_json,
                    updated_at = excluded.updated_at
                """,
                preference.to_dict(),
            )
            row = connection.execute("SELECT * FROM creator_preferences WHERE preference_key = ?", (preference.preference_key,)).fetchone()
        return _preference_from_row(row)

    def get_confirmed_preference_by_id(self, preference_id: str) -> CreatorConfirmedPreference | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_preferences WHERE id = ?", (preference_id,)).fetchone()
        return _preference_from_row(row) if row else None

    def get_confirmed_preference_by_key(self, preference_key: str) -> CreatorConfirmedPreference | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_preferences WHERE preference_key = ?", (preference_key,)).fetchone()
        return _preference_from_row(row) if row else None

    def list_confirmed_preferences(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
        active: bool | None = None,
        preference_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreatorConfirmedPreference]:
        clauses = ["creator_id = ?"]
        params: list[object] = [creator_id]
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if workflow_type is not None:
            clauses.append("workflow_type = ?")
            params.append(workflow_type)
        if active is not None:
            clauses.append("active = ?")
            params.append(1 if active else 0)
        if preference_type is not None:
            clauses.append("preference_type = ?")
            params.append(preference_type)
        sql = f"SELECT * FROM creator_preferences WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([int(limit), int(offset)])
        with self._database.connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [_preference_from_row(row) for row in rows]

    def deactivate_confirmed_preference(self, preference_id: str) -> CreatorConfirmedPreference | None:
        current = self.get_confirmed_preference_by_id(preference_id)
        if current is None:
            return None
        updated = CreatorConfirmedPreference(
            id=current.id,
            preference_key=current.preference_key,
            creator_id=current.creator_id,
            project_id=current.project_id,
            workflow_type=current.workflow_type,
            scope=current.scope,
            preference_type=current.preference_type,
            value_json=current.value_json,
            source_candidate_id=current.source_candidate_id,
            confirmed_by=current.confirmed_by,
            confirmed_at=current.confirmed_at,
            active=False,
            provenance_json=current.provenance_json,
            created_at=current.created_at,
            updated_at=utc_now(),
        )
        return self.upsert_confirmed_preference(updated)

    def reactivate_confirmed_preference(self, preference_id: str) -> CreatorConfirmedPreference | None:
        current = self.get_confirmed_preference_by_id(preference_id)
        if current is None:
            return None
        updated = CreatorConfirmedPreference(
            id=current.id,
            preference_key=current.preference_key,
            creator_id=current.creator_id,
            project_id=current.project_id,
            workflow_type=current.workflow_type,
            scope=current.scope,
            preference_type=current.preference_type,
            value_json=current.value_json,
            source_candidate_id=current.source_candidate_id,
            confirmed_by=current.confirmed_by,
            confirmed_at=current.confirmed_at,
            active=True,
            provenance_json=current.provenance_json,
            created_at=current.created_at,
            updated_at=utc_now(),
        )
        return self.upsert_confirmed_preference(updated)
