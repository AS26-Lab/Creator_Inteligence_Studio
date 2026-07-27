"""Repositorio SQLite para Audience Model Foundation."""

from __future__ import annotations

import json
import sqlite3

from creator_intelligence_studio.domain.audience_model.audience_types import AudienceConfidenceLevel, AudienceModelRunStatus, AudienceReviewDecision, AudienceSignalType, AudienceStatus
from creator_intelligence_studio.domain.audience_model.entities import (
    AudienceAffinity,
    AudienceJourney,
    AudienceJourneyStep,
    AudienceModelRun,
    AudienceProfile,
    AudienceProfileSnapshot,
    AudienceReview,
    AudienceSegment,
    AudienceSegmentDefinition,
    AudienceSegmentEvidence,
    AudienceSignal,
)
from creator_intelligence_studio.domain.audience_model.repositories import AudienceRepository
from creator_intelligence_studio.domain.audience_model.lifecycle_types import AudienceLifecycleStage
from creator_intelligence_studio.domain.audience_model.segment_types import AudienceSegmentScope, AudienceSegmentType
from creator_intelligence_studio.domain.audience_model.evidence_types import AudienceEvidenceType
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


def _row_to_profile(row: sqlite3.Row) -> AudienceProfile:
    return AudienceProfile(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_version=row["profile_version"],
        status=AudienceStatus(row["status"]),
        summary=row["summary"],
        evidence_quality=row["evidence_quality"],
        confidence_level=AudienceConfidenceLevel(row["confidence_level"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_signal(row: sqlite3.Row) -> AudienceSignal:
    return AudienceSignal(
        id=row["id"],
        creator_id=row["creator_id"],
        platform=row["platform"],
        channel_id=row["channel_id"],
        publication_id=row["publication_id"],
        remote_video_id=row["remote_video_id"],
        signal_type=AudienceSignalType(row["signal_type"]),
        signal_key=row["signal_key"],
        numeric_value=row["numeric_value"],
        text_value=row["text_value"],
        unit=row["unit"],
        period_start=from_iso_z(row["period_start"]),
        period_end=from_iso_z(row["period_end"]),
        observed_at=from_iso_z(row["observed_at"]) or utc_now(),
        source_type=row["source_type"],
        source_id=row["source_id"],
        dimensions_json=row["dimensions_json"],
        quality_status=row["quality_status"],
        warning_codes_json=row["warning_codes_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_segment(row: sqlite3.Row) -> AudienceSegment:
    return AudienceSegment(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        segment_type=AudienceSegmentType(row["segment_type"]),
        description=row["description"],
        scope=AudienceSegmentScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        lifecycle_stage=AudienceLifecycleStage(row["lifecycle_stage"]) if row["lifecycle_stage"] else None,
        status=AudienceStatus(row["status"]),
        confidence_level=AudienceConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        supporting_signal_count=row["supporting_signal_count"],
        contradicting_signal_count=row["contradicting_signal_count"],
        first_observed_at=from_iso_z(row["first_observed_at"]),
        last_observed_at=from_iso_z(row["last_observed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_definition(row: sqlite3.Row) -> AudienceSegmentDefinition:
    return AudienceSegmentDefinition(
        id=row["id"],
        segment_id=row["segment_id"],
        rule_type=row["rule_type"],
        field_key=row["field_key"],
        operator=row["operator"],
        value_json=row["value_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_evidence(row: sqlite3.Row) -> AudienceSegmentEvidence:
    return AudienceSegmentEvidence(
        id=row["id"],
        segment_id=row["segment_id"],
        signal_id=row["signal_id"],
        publication_id=row["publication_id"],
        analytics_finding_id=row["analytics_finding_id"],
        experiment_id=row["experiment_id"],
        evidence_type=AudienceEvidenceType(row["evidence_type"]),
        supports_segment=bool(row["supports_segment"]),
        weight=row["weight"],
        notes=row["notes"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_affinity(row: sqlite3.Row) -> AudienceAffinity:
    return AudienceAffinity(
        id=row["id"],
        creator_id=row["creator_id"],
        segment_id=row["segment_id"],
        affinity_type=row["affinity_type"],
        target_key=row["target_key"],
        target_value=row["target_value"],
        platform=row["platform"],
        content_type=row["content_type"],
        score=row["score"],
        supporting_example_count=row["supporting_example_count"],
        contradicting_example_count=row["contradicting_example_count"],
        confidence_level=AudienceConfidenceLevel(row["confidence_level"]),
        status=AudienceStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_journey(row: sqlite3.Row) -> AudienceJourney:
    return AudienceJourney(
        id=row["id"],
        creator_id=row["creator_id"],
        name=row["name"],
        entry_platform=row["entry_platform"],
        entry_source=row["entry_source"],
        entry_content_type=row["entry_content_type"],
        next_step_type=row["next_step_type"],
        conversion_type=row["conversion_type"],
        status=AudienceStatus(row["status"]),
        confidence_level=AudienceConfidenceLevel(row["confidence_level"]),
        evidence_json=row["evidence_json"],
        limitations_json=row["limitations_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_journey_step(row: sqlite3.Row) -> AudienceJourneyStep:
    return AudienceJourneyStep(
        id=row["id"],
        journey_id=row["journey_id"],
        step_order=row["step_order"],
        platform=row["platform"],
        content_type=row["content_type"],
        action_type=row["action_type"],
        metric_key=row["metric_key"],
        observed_value=row["observed_value"],
        evidence_json=row["evidence_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_snapshot(row: sqlite3.Row) -> AudienceProfileSnapshot:
    return AudienceProfileSnapshot(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_version=row["profile_version"],
        snapshot_json=row["snapshot_json"],
        source_fingerprint=row["source_fingerprint"],
        status=AudienceStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_review(row: sqlite3.Row) -> AudienceReview:
    return AudienceReview(
        id=row["id"],
        creator_id=row["creator_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        decision=AudienceReviewDecision(row["decision"]),
        previous_value_json=row["previous_value_json"],
        new_value_json=row["new_value_json"],
        reason=row["reason"],
        reviewed_at=from_iso_z(row["reviewed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_run(row: sqlite3.Row) -> AudienceModelRun:
    return AudienceModelRun(
        id=row["id"],
        creator_id=row["creator_id"],
        status=AudienceModelRunStatus(row["status"]),
        configuration_json=row["configuration_json"],
        source_fingerprint=row["source_fingerprint"],
        signal_count=row["signal_count"],
        segment_count=row["segment_count"],
        warning_count=row["warning_count"],
        started_at=from_iso_z(row["started_at"]) or utc_now(),
        completed_at=from_iso_z(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteAudienceRepository(AudienceRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def _fetch_one(self, query: str, params: tuple[object, ...]) -> sqlite3.Row | None:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchone()

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        with self._database.connect() as connection:
            return connection.execute(query, params).fetchall()

    def upsert_profile(self, profile: AudienceProfile) -> AudienceProfile:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_profiles (id, creator_id, profile_version, status, summary, evidence_quality, confidence_level, created_at, updated_at)
                VALUES (:id, :creator_id, :profile_version, :status, :summary, :evidence_quality, :confidence_level, :created_at, :updated_at)
                ON CONFLICT(creator_id, profile_version) DO UPDATE SET
                    status = excluded.status,
                    summary = excluded.summary,
                    evidence_quality = excluded.evidence_quality,
                    confidence_level = excluded.confidence_level,
                    updated_at = excluded.updated_at
                """,
                profile.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM audience_profiles WHERE creator_id = ? AND profile_version = ?", (profile.creator_id, profile.profile_version))
        return _row_to_profile(row)

    def get_profile(self, creator_id: str, profile_version: int | None = None) -> AudienceProfile | None:
        query = "SELECT * FROM audience_profiles WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if profile_version is not None:
            query += " AND profile_version = ?"
            params.append(profile_version)
        query += " ORDER BY profile_version DESC LIMIT 1"
        row = self._fetch_one(query, tuple(params))
        return _row_to_profile(row) if row else None

    def list_profiles(self, creator_id: str) -> list[AudienceProfile]:
        rows = self._fetch_all("SELECT * FROM audience_profiles WHERE creator_id = ? ORDER BY profile_version DESC", (creator_id,))
        return [_row_to_profile(row) for row in rows]

    def upsert_signal(self, signal: AudienceSignal) -> AudienceSignal:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_signals (
                    id, creator_id, platform, channel_id, publication_id, remote_video_id,
                    signal_type, signal_key, numeric_value, text_value, unit,
                    period_start, period_end, observed_at, source_type, source_id,
                    dimensions_json, quality_status, warning_codes_json, created_at
                ) VALUES (
                    :id, :creator_id, :platform, :channel_id, :publication_id, :remote_video_id,
                    :signal_type, :signal_key, :numeric_value, :text_value, :unit,
                    :period_start, :period_end, :observed_at, :source_type, :source_id,
                    :dimensions_json, :quality_status, :warning_codes_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    numeric_value = excluded.numeric_value,
                    text_value = excluded.text_value,
                    unit = excluded.unit,
                    period_start = excluded.period_start,
                    period_end = excluded.period_end,
                    source_type = excluded.source_type,
                    dimensions_json = excluded.dimensions_json,
                    quality_status = excluded.quality_status,
                    warning_codes_json = excluded.warning_codes_json
                """,
                signal.to_dict() | {"signal_type": signal.signal_type.value},
            )
        row = self._fetch_one("SELECT * FROM audience_signals WHERE id = ?", (signal.id,))
        return _row_to_signal(row)

    def list_signals(self, creator_id: str, *, platform: str | None = None) -> list[AudienceSignal]:
        query = "SELECT * FROM audience_signals WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if platform is not None:
            query += " AND platform = ?"
            params.append(platform)
        query += " ORDER BY observed_at ASC, created_at ASC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_signal(row) for row in rows]

    def get_signal(self, signal_id: str) -> AudienceSignal | None:
        row = self._fetch_one("SELECT * FROM audience_signals WHERE id = ?", (signal_id,))
        return _row_to_signal(row) if row else None

    def upsert_segment(self, segment: AudienceSegment) -> AudienceSegment:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_segments (
                    id, creator_id, name, segment_type, description, scope, platform,
                    content_type, topic, lifecycle_stage, status, confidence_level,
                    confidence_score, supporting_signal_count, contradicting_signal_count,
                    first_observed_at, last_observed_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :name, :segment_type, :description, :scope, :platform,
                    :content_type, :topic, :lifecycle_stage, :status, :confidence_level,
                    :confidence_score, :supporting_signal_count, :contradicting_signal_count,
                    :first_observed_at, :last_observed_at, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    segment_type = excluded.segment_type,
                    description = excluded.description,
                    status = excluded.status,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    supporting_signal_count = excluded.supporting_signal_count,
                    contradicting_signal_count = excluded.contradicting_signal_count,
                    first_observed_at = excluded.first_observed_at,
                    last_observed_at = excluded.last_observed_at,
                    updated_at = excluded.updated_at
                """,
                segment.to_dict() | {"segment_type": segment.segment_type.value, "scope": segment.scope.value, "lifecycle_stage": None if segment.lifecycle_stage is None else segment.lifecycle_stage.value, "status": segment.status.value, "confidence_level": segment.confidence_level.value},
            )
        row = self._fetch_one("SELECT * FROM audience_segments WHERE id = ?", (segment.id,))
        return _row_to_segment(row)

    def list_segments(self, creator_id: str) -> list[AudienceSegment]:
        rows = self._fetch_all("SELECT * FROM audience_segments WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,))
        return [_row_to_segment(row) for row in rows]

    def get_segment(self, segment_id: str) -> AudienceSegment | None:
        row = self._fetch_one("SELECT * FROM audience_segments WHERE id = ?", (segment_id,))
        return _row_to_segment(row) if row else None

    def upsert_segment_definition(self, definition: AudienceSegmentDefinition) -> AudienceSegmentDefinition:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_segment_definitions (id, segment_id, rule_type, field_key, operator, value_json, created_at)
                VALUES (:id, :segment_id, :rule_type, :field_key, :operator, :value_json, :created_at)
                ON CONFLICT(id) DO UPDATE SET created_at = excluded.created_at
                """,
                definition.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM audience_segment_definitions WHERE id = ?", (definition.id,))
        return _row_to_definition(row)

    def list_segment_definitions(self, segment_id: str) -> list[AudienceSegmentDefinition]:
        rows = self._fetch_all("SELECT * FROM audience_segment_definitions WHERE segment_id = ? ORDER BY created_at ASC", (segment_id,))
        return [_row_to_definition(row) for row in rows]

    def upsert_segment_evidence(self, evidence: AudienceSegmentEvidence) -> AudienceSegmentEvidence:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_segment_evidence (
                    id, segment_id, signal_id, publication_id, analytics_finding_id,
                    experiment_id, evidence_type, supports_segment, weight, notes, created_at
                ) VALUES (
                    :id, :segment_id, :signal_id, :publication_id, :analytics_finding_id,
                    :experiment_id, :evidence_type, :supports_segment, :weight, :notes, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    signal_id = excluded.signal_id,
                    publication_id = excluded.publication_id,
                    analytics_finding_id = excluded.analytics_finding_id,
                    experiment_id = excluded.experiment_id,
                    evidence_type = excluded.evidence_type,
                    supports_segment = excluded.supports_segment,
                    weight = excluded.weight,
                    notes = excluded.notes
                """,
                evidence.to_dict() | {"evidence_type": evidence.evidence_type.value, "supports_segment": 1 if evidence.supports_segment else 0},
            )
        row = self._fetch_one("SELECT * FROM audience_segment_evidence WHERE id = ?", (evidence.id,))
        return _row_to_evidence(row)

    def list_segment_evidence(self, segment_id: str) -> list[AudienceSegmentEvidence]:
        rows = self._fetch_all("SELECT * FROM audience_segment_evidence WHERE segment_id = ? ORDER BY created_at ASC", (segment_id,))
        return [_row_to_evidence(row) for row in rows]

    def upsert_affinity(self, affinity: AudienceAffinity) -> AudienceAffinity:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_affinities (
                    id, creator_id, segment_id, affinity_type, target_key, target_value,
                    platform, content_type, score, supporting_example_count,
                    contradicting_example_count, confidence_level, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :segment_id, :affinity_type, :target_key, :target_value,
                    :platform, :content_type, :score, :supporting_example_count,
                    :contradicting_example_count, :confidence_level, :status,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    score = excluded.score,
                    supporting_example_count = excluded.supporting_example_count,
                    contradicting_example_count = excluded.contradicting_example_count,
                    confidence_level = excluded.confidence_level,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                affinity.to_dict() | {"confidence_level": affinity.confidence_level.value, "status": affinity.status.value},
            )
        row = self._fetch_one("SELECT * FROM audience_affinities WHERE id = ?", (affinity.id,))
        return _row_to_affinity(row)

    def list_affinities(self, creator_id: str) -> list[AudienceAffinity]:
        rows = self._fetch_all("SELECT * FROM audience_affinities WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,))
        return [_row_to_affinity(row) for row in rows]

    def get_affinity(self, affinity_id: str) -> AudienceAffinity | None:
        row = self._fetch_one("SELECT * FROM audience_affinities WHERE id = ?", (affinity_id,))
        return _row_to_affinity(row) if row else None

    def upsert_journey(self, journey: AudienceJourney) -> AudienceJourney:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_journeys (
                    id, creator_id, name, entry_platform, entry_source, entry_content_type,
                    next_step_type, conversion_type, status, confidence_level, evidence_json,
                    limitations_json, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :name, :entry_platform, :entry_source, :entry_content_type,
                    :next_step_type, :conversion_type, :status, :confidence_level, :evidence_json,
                    :limitations_json, :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    confidence_level = excluded.confidence_level,
                    evidence_json = excluded.evidence_json,
                    limitations_json = excluded.limitations_json,
                    updated_at = excluded.updated_at
                """,
                journey.to_dict() | {"status": journey.status.value, "confidence_level": journey.confidence_level.value},
            )
        row = self._fetch_one("SELECT * FROM audience_journeys WHERE id = ?", (journey.id,))
        return _row_to_journey(row)

    def list_journeys(self, creator_id: str) -> list[AudienceJourney]:
        rows = self._fetch_all("SELECT * FROM audience_journeys WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,))
        return [_row_to_journey(row) for row in rows]

    def get_journey(self, journey_id: str) -> AudienceJourney | None:
        row = self._fetch_one("SELECT * FROM audience_journeys WHERE id = ?", (journey_id,))
        return _row_to_journey(row) if row else None

    def upsert_journey_step(self, step: AudienceJourneyStep) -> AudienceJourneyStep:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_journey_steps (id, journey_id, step_order, platform, content_type, action_type, metric_key, observed_value, evidence_json, created_at)
                VALUES (:id, :journey_id, :step_order, :platform, :content_type, :action_type, :metric_key, :observed_value, :evidence_json, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    content_type = excluded.content_type,
                    observed_value = excluded.observed_value,
                    evidence_json = excluded.evidence_json
                """,
                step.to_dict(),
            )
        row = self._fetch_one("SELECT * FROM audience_journey_steps WHERE id = ?", (step.id,))
        return _row_to_journey_step(row)

    def list_journey_steps(self, journey_id: str) -> list[AudienceJourneyStep]:
        rows = self._fetch_all("SELECT * FROM audience_journey_steps WHERE journey_id = ? ORDER BY step_order ASC", (journey_id,))
        return [_row_to_journey_step(row) for row in rows]

    def upsert_profile_snapshot(self, snapshot: AudienceProfileSnapshot) -> AudienceProfileSnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_profile_snapshots (id, creator_id, profile_version, snapshot_json, source_fingerprint, status, created_at)
                VALUES (:id, :creator_id, :profile_version, :snapshot_json, :source_fingerprint, :status, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    snapshot_json = excluded.snapshot_json,
                    status = excluded.status
                """,
                snapshot.to_dict() | {"status": snapshot.status.value},
            )
        row = self._fetch_one("SELECT * FROM audience_profile_snapshots WHERE id = ?", (snapshot.id,))
        return _row_to_snapshot(row)

    def list_profile_snapshots(self, creator_id: str) -> list[AudienceProfileSnapshot]:
        rows = self._fetch_all("SELECT * FROM audience_profile_snapshots WHERE creator_id = ? ORDER BY profile_version DESC, created_at DESC", (creator_id,))
        return [_row_to_snapshot(row) for row in rows]

    def upsert_review(self, review: AudienceReview) -> AudienceReview:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_reviews (id, creator_id, target_type, target_id, decision, previous_value_json, new_value_json, reason, reviewed_at, created_at)
                VALUES (:id, :creator_id, :target_type, :target_id, :decision, :previous_value_json, :new_value_json, :reason, :reviewed_at, :created_at)
                ON CONFLICT(id) DO UPDATE SET
                    decision = excluded.decision,
                    previous_value_json = excluded.previous_value_json,
                    new_value_json = excluded.new_value_json,
                    reason = excluded.reason,
                    reviewed_at = excluded.reviewed_at
                """,
                review.to_dict() | {"decision": review.decision.value},
            )
        row = self._fetch_one("SELECT * FROM audience_reviews WHERE id = ?", (review.id,))
        return _row_to_review(row)

    def list_reviews(self, creator_id: str, *, target_type: str | None = None) -> list[AudienceReview]:
        query = "SELECT * FROM audience_reviews WHERE creator_id = ?"
        params: list[object] = [creator_id]
        if target_type is not None:
            query += " AND target_type = ?"
            params.append(target_type)
        query += " ORDER BY reviewed_at DESC"
        rows = self._fetch_all(query, tuple(params))
        return [_row_to_review(row) for row in rows]

    def upsert_run(self, run: AudienceModelRun) -> AudienceModelRun:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audience_model_runs (
                    id, creator_id, status, configuration_json, source_fingerprint,
                    signal_count, segment_count, warning_count, started_at, completed_at,
                    error_code, error_message, created_at
                ) VALUES (
                    :id, :creator_id, :status, :configuration_json, :source_fingerprint,
                    :signal_count, :segment_count, :warning_count, :started_at, :completed_at,
                    :error_code, :error_message, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    configuration_json = excluded.configuration_json,
                    source_fingerprint = excluded.source_fingerprint,
                    signal_count = excluded.signal_count,
                    segment_count = excluded.segment_count,
                    warning_count = excluded.warning_count,
                    completed_at = excluded.completed_at,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                run.to_dict() | {"status": run.status.value},
            )
        row = self._fetch_one("SELECT * FROM audience_model_runs WHERE id = ?", (run.id,))
        return _row_to_run(row)

    def get_run_by_fingerprint(self, creator_id: str, source_fingerprint: str, configuration_json: str) -> AudienceModelRun | None:
        row = self._fetch_one(
            """
            SELECT * FROM audience_model_runs
            WHERE creator_id = ? AND source_fingerprint = ? AND configuration_json = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (creator_id, source_fingerprint, configuration_json),
        )
        return _row_to_run(row) if row else None

    def get_run(self, run_id: str) -> AudienceModelRun | None:
        row = self._fetch_one("SELECT * FROM audience_model_runs WHERE id = ?", (run_id,))
        return _row_to_run(row) if row else None

    def list_runs(self, creator_id: str) -> list[AudienceModelRun]:
        rows = self._fetch_all("SELECT * FROM audience_model_runs WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,))
        return [_row_to_run(row) for row in rows]
