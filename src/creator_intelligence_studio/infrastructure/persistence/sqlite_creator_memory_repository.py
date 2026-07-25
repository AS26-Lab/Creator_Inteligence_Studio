"""Repositorio SQLite para Creator Memory."""

from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from creator_intelligence_studio.domain.creator_memory.entities import (
    CreatorExample,
    CreatorLimit,
    CreatorMemoryFeedback,
    CreatorProfile,
    CreatorProfileSnapshot,
    CreatorStyleRule,
    CreatorStyleRuleReview,
    CreatorTrait,
    CreatorTraitEvidence,
    CreatorVocabulary,
)
from creator_intelligence_studio.domain.creator_memory.memory_types import (
    CreatorMemoryQueryFilters,
    CreatorMemoryRetrievalResult,
    CreatorProfileSnapshotComparison,
)
from creator_intelligence_studio.domain.creator_memory.repositories import CreatorMemoryRepository
from creator_intelligence_studio.domain.creator_memory.value_objects import (
    CreatorExampleApprovalStatus,
    CreatorExampleType,
    CreatorFeedbackType,
    CreatorLimitSeverity,
    CreatorLimitStatus,
    CreatorLimitType,
    CreatorMemoryConfidenceLevel,
    CreatorMemoryScope,
    CreatorProfileStatus,
    CreatorRuleReviewDecision,
    CreatorRuleStatus,
    CreatorSnapshotStatus,
    CreatorStyleRuleType,
    CreatorTraitStatus,
    CreatorTraitType,
    CreatorVocabularyStatus,
    CreatorVocabularyType,
    CreatorEvidenceType,
)
from creator_intelligence_studio.infrastructure.creator_memory.memory_retriever import rank_memory_items
from creator_intelligence_studio.infrastructure.persistence.database import SQLiteDatabase
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, fallback):
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _bool_to_db(value: bool) -> int:
    return 1 if value else 0


def _row_to_profile(row: sqlite3.Row) -> CreatorProfile:
    return CreatorProfile(
        id=row["id"],
        creator_id=row["creator_id"],
        display_name=row["display_name"],
        profile_version=row["profile_version"],
        status=CreatorProfileStatus(row["status"]),
        summary=row["summary"],
        primary_language=row["primary_language"],
        secondary_languages_json=row["secondary_languages_json"],
        default_tone=row["default_tone"],
        default_formality=row["default_formality"],
        objectives_json=row["objectives_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_trait(row: sqlite3.Row) -> CreatorTrait:
    return CreatorTrait(
        id=row["id"],
        creator_id=row["creator_id"],
        trait_type=CreatorTraitType(row["trait_type"]),
        trait_key=row["trait_key"],
        display_name=row["display_name"],
        description=row["description"],
        value_json=row["value_json"],
        scope=CreatorMemoryScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        confidence_level=CreatorMemoryConfidenceLevel(row["confidence_level"]),
        confidence_score=row["confidence_score"],
        status=CreatorTraitStatus(row["status"]),
        first_observed_at=from_iso_z(row["first_observed_at"]),
        last_observed_at=from_iso_z(row["last_observed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_trait_evidence(row: sqlite3.Row) -> CreatorTraitEvidence:
    return CreatorTraitEvidence(
        id=row["id"],
        trait_id=row["trait_id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        transcript_segment_id=row["transcript_segment_id"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        quoted_text=row["quoted_text"],
        evidence_type=CreatorEvidenceType(row["evidence_type"]),
        supports_trait=bool(row["supports_trait"]),
        weight=row["weight"],
        notes=row["notes"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_example(row: sqlite3.Row) -> CreatorExample:
    return CreatorExample(
        id=row["id"],
        creator_id=row["creator_id"],
        example_type=CreatorExampleType(row["example_type"]),
        category=row["category"],
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        title=row["title"],
        text_content=row["text_content"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        publication_id=row["publication_id"],
        video_asset_id=row["video_asset_id"],
        start_seconds=row["start_seconds"],
        end_seconds=row["end_seconds"],
        representativeness=row["representativeness"],
        approval_status=CreatorExampleApprovalStatus(row["approval_status"]),
        approval_reason=row["approval_reason"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_vocab(row: sqlite3.Row) -> CreatorVocabulary:
    return CreatorVocabulary(
        id=row["id"],
        creator_id=row["creator_id"],
        term=row["term"],
        normalized_term=row["normalized_term"],
        vocabulary_type=CreatorVocabularyType(row["vocabulary_type"]),
        meaning=row["meaning"],
        usage_notes=row["usage_notes"],
        platform=row["platform"],
        content_type=row["content_type"],
        frequency_count=row["frequency_count"],
        confidence_level=CreatorMemoryConfidenceLevel(row["confidence_level"]),
        status=CreatorVocabularyStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_rule(row: sqlite3.Row) -> CreatorStyleRule:
    return CreatorStyleRule(
        id=row["id"],
        creator_id=row["creator_id"],
        rule_type=CreatorStyleRuleType(row["rule_type"]),
        scope=CreatorMemoryScope(row["scope"]),
        platform=row["platform"],
        content_type=row["content_type"],
        topic=row["topic"],
        statement=row["statement"],
        rationale=row["rationale"],
        status=CreatorRuleStatus(row["status"]),
        confidence_level=CreatorMemoryConfidenceLevel(row["confidence_level"]),
        supporting_example_count=row["supporting_example_count"],
        contradicting_example_count=row["contradicting_example_count"],
        first_observed_at=from_iso_z(row["first_observed_at"]),
        last_reviewed_at=from_iso_z(row["last_reviewed_at"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_rule_review(row: sqlite3.Row) -> CreatorStyleRuleReview:
    return CreatorStyleRuleReview(
        id=row["id"],
        rule_id=row["rule_id"],
        decision=CreatorRuleReviewDecision(row["decision"]),
        previous_statement=row["previous_statement"],
        new_statement=row["new_statement"],
        reason=row["reason"],
        reviewed_at=from_iso_z(row["reviewed_at"]) or utc_now(),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_limit(row: sqlite3.Row) -> CreatorLimit:
    return CreatorLimit(
        id=row["id"],
        creator_id=row["creator_id"],
        limit_type=CreatorLimitType(row["limit_type"]),
        category=row["category"],
        statement=row["statement"],
        severity=CreatorLimitSeverity(row["severity"]),
        scope=CreatorMemoryScope(row["scope"]),
        platform=row["platform"],
        status=CreatorLimitStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
        updated_at=from_iso_z(row["updated_at"]) or utc_now(),
    )


def _row_to_snapshot(row: sqlite3.Row) -> CreatorProfileSnapshot:
    return CreatorProfileSnapshot(
        id=row["id"],
        creator_id=row["creator_id"],
        profile_version=row["profile_version"],
        snapshot_json=row["snapshot_json"],
        source_fingerprint=row["source_fingerprint"],
        status=CreatorSnapshotStatus(row["status"]),
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


def _row_to_feedback(row: sqlite3.Row) -> CreatorMemoryFeedback:
    return CreatorMemoryFeedback(
        id=row["id"],
        creator_id=row["creator_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        feedback_type=CreatorFeedbackType(row["feedback_type"]),
        reason=row["reason"],
        corrected_value_json=row["corrected_value_json"],
        created_at=from_iso_z(row["created_at"]) or utc_now(),
    )


class SQLiteCreatorMemoryRepository(CreatorMemoryRepository):
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    def get_profile(self, creator_id: str) -> CreatorProfile | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_profiles WHERE creator_id = ?", (creator_id,)).fetchone()
        return _row_to_profile(row) if row else None

    def upsert_profile(self, profile: CreatorProfile) -> CreatorProfile:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_profiles (
                    id, creator_id, display_name, profile_version, status, summary,
                    primary_language, secondary_languages_json, default_tone, default_formality,
                    objectives_json, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :display_name, :profile_version, :status, :summary,
                    :primary_language, :secondary_languages_json, :default_tone, :default_formality,
                    :objectives_json, :created_at, :updated_at
                )
                ON CONFLICT(creator_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    profile_version = excluded.profile_version,
                    status = excluded.status,
                    summary = excluded.summary,
                    primary_language = excluded.primary_language,
                    secondary_languages_json = excluded.secondary_languages_json,
                    default_tone = excluded.default_tone,
                    default_formality = excluded.default_formality,
                    objectives_json = excluded.objectives_json,
                    updated_at = excluded.updated_at
                """,
                profile.to_dict() | {"status": profile.status.value},
            )
            row = connection.execute("SELECT * FROM creator_profiles WHERE creator_id = ?", (profile.creator_id,)).fetchone()
        return _row_to_profile(row)

    def list_traits(self, creator_id: str) -> list[CreatorTrait]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_traits WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,)).fetchall()
        return [_row_to_trait(row) for row in rows]

    def get_trait(self, trait_id: str) -> CreatorTrait | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_traits WHERE id = ?", (trait_id,)).fetchone()
        return _row_to_trait(row) if row else None

    def upsert_trait(self, trait: CreatorTrait) -> CreatorTrait:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_traits (
                    id, creator_id, trait_type, trait_key, display_name, description,
                    value_json, scope, platform, content_type, topic, confidence_level,
                    confidence_score, status, first_observed_at, last_observed_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :trait_type, :trait_key, :display_name, :description,
                    :value_json, :scope, :platform, :content_type, :topic, :confidence_level,
                    :confidence_score, :status, :first_observed_at, :last_observed_at,
                    :created_at, :updated_at
                )
                ON CONFLICT(creator_id, trait_key, scope, platform, content_type, topic) DO UPDATE SET
                    trait_type = excluded.trait_type,
                    display_name = excluded.display_name,
                    description = excluded.description,
                    value_json = excluded.value_json,
                    confidence_level = excluded.confidence_level,
                    confidence_score = excluded.confidence_score,
                    status = excluded.status,
                    first_observed_at = excluded.first_observed_at,
                    last_observed_at = excluded.last_observed_at,
                    updated_at = excluded.updated_at
                """,
                trait.to_dict() | {
                    "trait_type": trait.trait_type.value,
                    "scope": trait.scope.value,
                    "confidence_level": trait.confidence_level.value,
                    "status": trait.status.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_traits WHERE id = ?", (trait.id,)).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM creator_traits WHERE creator_id = ? AND trait_key = ? AND scope = ? AND platform IS ? AND content_type IS ? AND topic IS ?",
                    (trait.creator_id, trait.trait_key, trait.scope.value, trait.platform, trait.content_type, trait.topic),
                ).fetchone()
        return _row_to_trait(row)

    def archive_trait(self, trait_id: str) -> CreatorTrait | None:
        trait = self.get_trait(trait_id)
        if trait is None:
            return None
        archived = CreatorTrait(
            id=trait.id,
            creator_id=trait.creator_id,
            trait_type=trait.trait_type,
            trait_key=trait.trait_key,
            display_name=trait.display_name,
            description=trait.description,
            value_json=trait.value_json,
            scope=trait.scope,
            platform=trait.platform,
            content_type=trait.content_type,
            topic=trait.topic,
            confidence_level=trait.confidence_level,
            confidence_score=trait.confidence_score,
            status=CreatorTraitStatus.DEPRECATED,
            first_observed_at=trait.first_observed_at,
            last_observed_at=trait.last_observed_at,
            created_at=trait.created_at,
            updated_at=utc_now(),
        )
        return self.upsert_trait(archived)

    def list_trait_evidence(self, trait_id: str) -> list[CreatorTraitEvidence]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_trait_evidence WHERE trait_id = ? ORDER BY created_at DESC", (trait_id,)).fetchall()
        return [_row_to_trait_evidence(row) for row in rows]

    def upsert_trait_evidence(self, evidence: CreatorTraitEvidence) -> CreatorTraitEvidence:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_trait_evidence (
                    id, trait_id, source_type, source_id, publication_id, video_asset_id,
                    transcript_segment_id, start_seconds, end_seconds, quoted_text,
                    evidence_type, supports_trait, weight, notes, created_at
                ) VALUES (
                    :id, :trait_id, :source_type, :source_id, :publication_id, :video_asset_id,
                    :transcript_segment_id, :start_seconds, :end_seconds, :quoted_text,
                    :evidence_type, :supports_trait, :weight, :notes, :created_at
                )
                """,
                evidence.to_dict() | {
                    "evidence_type": evidence.evidence_type.value,
                    "supports_trait": _bool_to_db(evidence.supports_trait),
                },
            )
            row = connection.execute("SELECT * FROM creator_trait_evidence WHERE id = ?", (evidence.id,)).fetchone()
        return _row_to_trait_evidence(row)

    def list_examples(self, creator_id: str) -> list[CreatorExample]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_examples WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,)).fetchall()
        return [_row_to_example(row) for row in rows]

    def get_example(self, example_id: str) -> CreatorExample | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_examples WHERE id = ?", (example_id,)).fetchone()
        return _row_to_example(row) if row else None

    def upsert_example(self, example: CreatorExample) -> CreatorExample:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_examples (
                    id, creator_id, example_type, category, platform, content_type, topic,
                    title, text_content, source_type, source_id, publication_id, video_asset_id,
                    start_seconds, end_seconds, representativeness, approval_status, approval_reason,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :example_type, :category, :platform, :content_type, :topic,
                    :title, :text_content, :source_type, :source_id, :publication_id, :video_asset_id,
                    :start_seconds, :end_seconds, :representativeness, :approval_status, :approval_reason,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    example_type = excluded.example_type,
                    category = excluded.category,
                    platform = excluded.platform,
                    content_type = excluded.content_type,
                    topic = excluded.topic,
                    title = excluded.title,
                    text_content = excluded.text_content,
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    publication_id = excluded.publication_id,
                    video_asset_id = excluded.video_asset_id,
                    start_seconds = excluded.start_seconds,
                    end_seconds = excluded.end_seconds,
                    representativeness = excluded.representativeness,
                    approval_status = excluded.approval_status,
                    approval_reason = excluded.approval_reason,
                    updated_at = excluded.updated_at
                """,
                example.to_dict() | {
                    "example_type": example.example_type.value,
                    "approval_status": example.approval_status.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_examples WHERE id = ?", (example.id,)).fetchone()
        return _row_to_example(row)

    def review_example(self, example_id: str, approval_status: str, approval_reason: str | None) -> CreatorExample | None:
        example = self.get_example(example_id)
        if example is None:
            return None
        updated = CreatorExample(
            id=example.id,
            creator_id=example.creator_id,
            example_type=example.example_type,
            category=example.category,
            platform=example.platform,
            content_type=example.content_type,
            topic=example.topic,
            title=example.title,
            text_content=example.text_content,
            source_type=example.source_type,
            source_id=example.source_id,
            publication_id=example.publication_id,
            video_asset_id=example.video_asset_id,
            start_seconds=example.start_seconds,
            end_seconds=example.end_seconds,
            representativeness=example.representativeness,
            approval_status=CreatorExampleApprovalStatus(approval_status),
            approval_reason=approval_reason,
            created_at=example.created_at,
            updated_at=utc_now(),
        )
        return self.upsert_example(updated)

    def list_vocabulary(self, creator_id: str) -> list[CreatorVocabulary]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_vocabulary WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,)).fetchall()
        return [_row_to_vocab(row) for row in rows]

    def upsert_vocabulary(self, vocabulary: CreatorVocabulary) -> CreatorVocabulary:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_vocabulary (
                    id, creator_id, term, normalized_term, vocabulary_type, meaning,
                    usage_notes, platform, content_type, frequency_count, confidence_level,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :term, :normalized_term, :vocabulary_type, :meaning,
                    :usage_notes, :platform, :content_type, :frequency_count, :confidence_level,
                    :status, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, normalized_term, vocabulary_type, platform, content_type) DO UPDATE SET
                    term = excluded.term,
                    meaning = excluded.meaning,
                    usage_notes = excluded.usage_notes,
                    frequency_count = excluded.frequency_count,
                    confidence_level = excluded.confidence_level,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                vocabulary.to_dict() | {
                    "vocabulary_type": vocabulary.vocabulary_type.value,
                    "confidence_level": vocabulary.confidence_level.value,
                    "status": vocabulary.status.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_vocabulary WHERE id = ?", (vocabulary.id,)).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM creator_vocabulary WHERE creator_id = ? AND normalized_term = ? AND vocabulary_type = ? AND platform IS ? AND content_type IS ?",
                    (vocabulary.creator_id, vocabulary.normalized_term, vocabulary.vocabulary_type.value, vocabulary.platform, vocabulary.content_type),
                ).fetchone()
        return _row_to_vocab(row)

    def list_style_rules(self, creator_id: str) -> list[CreatorStyleRule]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_style_rules WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,)).fetchall()
        return [_row_to_rule(row) for row in rows]

    def get_style_rule(self, rule_id: str) -> CreatorStyleRule | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_style_rules WHERE id = ?", (rule_id,)).fetchone()
        return _row_to_rule(row) if row else None

    def upsert_style_rule(self, rule: CreatorStyleRule) -> CreatorStyleRule:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_style_rules (
                    id, creator_id, rule_type, scope, platform, content_type, topic,
                    statement, rationale, status, confidence_level,
                    supporting_example_count, contradicting_example_count,
                    first_observed_at, last_reviewed_at, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :rule_type, :scope, :platform, :content_type, :topic,
                    :statement, :rationale, :status, :confidence_level,
                    :supporting_example_count, :contradicting_example_count,
                    :first_observed_at, :last_reviewed_at, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, rule_type, scope, platform, content_type, topic, statement) DO UPDATE SET
                    rationale = excluded.rationale,
                    status = excluded.status,
                    confidence_level = excluded.confidence_level,
                    supporting_example_count = excluded.supporting_example_count,
                    contradicting_example_count = excluded.contradicting_example_count,
                    first_observed_at = excluded.first_observed_at,
                    last_reviewed_at = excluded.last_reviewed_at,
                    updated_at = excluded.updated_at
                """,
                rule.to_dict() | {
                    "rule_type": rule.rule_type.value,
                    "scope": rule.scope.value,
                    "status": rule.status.value,
                    "confidence_level": rule.confidence_level.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_style_rules WHERE id = ?", (rule.id,)).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM creator_style_rules WHERE creator_id = ? AND rule_type = ? AND scope = ? AND platform IS ? AND content_type IS ? AND topic IS ? AND statement = ?",
                    (rule.creator_id, rule.rule_type.value, rule.scope.value, rule.platform, rule.content_type, rule.topic, rule.statement),
                ).fetchone()
        return _row_to_rule(row)

    def review_style_rule(self, review: CreatorStyleRuleReview) -> CreatorStyleRuleReview:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_style_rule_reviews (
                    id, rule_id, decision, previous_statement, new_statement,
                    reason, reviewed_at, created_at
                ) VALUES (
                    :id, :rule_id, :decision, :previous_statement, :new_statement,
                    :reason, :reviewed_at, :created_at
                )
                """,
                review.to_dict() | {"decision": review.decision.value},
            )
            if review.decision == CreatorRuleReviewDecision.EDIT and review.new_statement is not None:
                connection.execute(
                    "UPDATE creator_style_rules SET statement = ?, updated_at = ? WHERE id = ?",
                    (review.new_statement, review.reviewed_at.isoformat(), review.rule_id),
                )
            elif review.decision == CreatorRuleReviewDecision.CONFIRM:
                connection.execute(
                    "UPDATE creator_style_rules SET status = ?, updated_at = ?, last_reviewed_at = ? WHERE id = ?",
                    (CreatorRuleStatus.CONFIRMED.value, review.reviewed_at.isoformat(), review.reviewed_at.isoformat(), review.rule_id),
                )
            elif review.decision == CreatorRuleReviewDecision.REJECT:
                connection.execute(
                    "UPDATE creator_style_rules SET status = ?, updated_at = ?, last_reviewed_at = ? WHERE id = ?",
                    (CreatorRuleStatus.REJECTED.value, review.reviewed_at.isoformat(), review.reviewed_at.isoformat(), review.rule_id),
                )
            elif review.decision == CreatorRuleReviewDecision.DEPRECATE:
                connection.execute(
                    "UPDATE creator_style_rules SET status = ?, updated_at = ?, last_reviewed_at = ? WHERE id = ?",
                    (CreatorRuleStatus.DEPRECATED.value, review.reviewed_at.isoformat(), review.reviewed_at.isoformat(), review.rule_id),
                )
            elif review.decision == CreatorRuleReviewDecision.NEED_MORE_DATA:
                connection.execute(
                    "UPDATE creator_style_rules SET status = ?, updated_at = ?, last_reviewed_at = ? WHERE id = ?",
                    (CreatorRuleStatus.NEEDS_MORE_DATA.value, review.reviewed_at.isoformat(), review.reviewed_at.isoformat(), review.rule_id),
                )
            row = connection.execute("SELECT * FROM creator_style_rule_reviews WHERE id = ?", (review.id,)).fetchone()
        return _row_to_rule_review(row)

    def list_style_rule_reviews(self, rule_id: str) -> list[CreatorStyleRuleReview]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_style_rule_reviews WHERE rule_id = ? ORDER BY reviewed_at DESC", (rule_id,)).fetchall()
        return [_row_to_rule_review(row) for row in rows]

    def list_limits(self, creator_id: str) -> list[CreatorLimit]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_limits WHERE creator_id = ? ORDER BY updated_at DESC", (creator_id,)).fetchall()
        return [_row_to_limit(row) for row in rows]

    def upsert_limit(self, limit: CreatorLimit) -> CreatorLimit:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_limits (
                    id, creator_id, limit_type, category, statement, severity,
                    scope, platform, status, created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :limit_type, :category, :statement, :severity,
                    :scope, :platform, :status, :created_at, :updated_at
                )
                ON CONFLICT(creator_id, limit_type, category, scope, platform, statement) DO UPDATE SET
                    severity = excluded.severity,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                limit.to_dict() | {
                    "limit_type": limit.limit_type.value,
                    "severity": limit.severity.value,
                    "scope": limit.scope.value,
                    "status": limit.status.value,
                },
            )
            row = connection.execute("SELECT * FROM creator_limits WHERE id = ?", (limit.id,)).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM creator_limits WHERE creator_id = ? AND limit_type = ? AND category = ? AND scope = ? AND platform IS ? AND statement = ?",
                    (limit.creator_id, limit.limit_type.value, limit.category, limit.scope.value, limit.platform, limit.statement),
                ).fetchone()
        return _row_to_limit(row)

    def list_profile_snapshots(self, creator_id: str) -> list[CreatorProfileSnapshot]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_profile_snapshots WHERE creator_id = ? ORDER BY profile_version DESC, created_at DESC", (creator_id,)).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def upsert_profile_snapshot(self, snapshot: CreatorProfileSnapshot) -> CreatorProfileSnapshot:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_profile_snapshots (
                    id, creator_id, profile_version, snapshot_json, source_fingerprint, status, created_at
                ) VALUES (
                    :id, :creator_id, :profile_version, :snapshot_json, :source_fingerprint, :status, :created_at
                )
                ON CONFLICT(creator_id, profile_version) DO UPDATE SET
                    snapshot_json = excluded.snapshot_json,
                    source_fingerprint = excluded.source_fingerprint,
                    status = excluded.status
                """,
                snapshot.to_dict() | {"status": snapshot.status.value},
            )
            row = connection.execute("SELECT * FROM creator_profile_snapshots WHERE creator_id = ? AND profile_version = ?", (snapshot.creator_id, snapshot.profile_version)).fetchone()
        return _row_to_snapshot(row)

    def get_profile_snapshot(self, snapshot_id: str) -> CreatorProfileSnapshot | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM creator_profile_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return _row_to_snapshot(row) if row else None

    def list_feedback(self, creator_id: str) -> list[CreatorMemoryFeedback]:
        with self._database.connect() as connection:
            rows = connection.execute("SELECT * FROM creator_memory_feedback WHERE creator_id = ? ORDER BY created_at DESC", (creator_id,)).fetchall()
        return [_row_to_feedback(row) for row in rows]

    def upsert_feedback(self, feedback: CreatorMemoryFeedback) -> CreatorMemoryFeedback:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_memory_feedback (
                    id, creator_id, target_type, target_id, feedback_type, reason,
                    corrected_value_json, created_at
                ) VALUES (
                    :id, :creator_id, :target_type, :target_id, :feedback_type, :reason,
                    :corrected_value_json, :created_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    target_type = excluded.target_type,
                    target_id = excluded.target_id,
                    feedback_type = excluded.feedback_type,
                    reason = excluded.reason,
                    corrected_value_json = excluded.corrected_value_json
                """,
                feedback.to_dict() | {"feedback_type": feedback.feedback_type.value},
            )
            row = connection.execute("SELECT * FROM creator_memory_feedback WHERE id = ?", (feedback.id,)).fetchone()
        return _row_to_feedback(row)

    def retrieve(self, creator_id: str, filters: dict[str, object]) -> list[CreatorMemoryRetrievalResult]:
        profile = self.get_profile(creator_id)
        if profile is None:
            return []
        query_filters = CreatorMemoryQueryFilters(
            creator_id=creator_id,
            query=str(filters.get("query")) if filters.get("query") is not None else None,
            platform=filters.get("platform"),
            content_type=filters.get("content_type"),
            topic=filters.get("topic"),
            trait_type=filters.get("trait_type"),
            example_type=filters.get("example_type"),
            approval_status=filters.get("approval_status"),
            confidence_level=filters.get("confidence_level"),
            status=filters.get("status"),
        )
        return rank_memory_items(
            profile,
            self.list_traits(creator_id),
            self.list_examples(creator_id),
            self.list_vocabulary(creator_id),
            self.list_style_rules(creator_id),
            self.list_limits(creator_id),
            query_filters,
        )

    def compare_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str) -> CreatorProfileSnapshotComparison:
        base = self.get_profile_snapshot(base_snapshot_id)
        compare = self.get_profile_snapshot(compare_snapshot_id)
        if base is None or compare is None:
            raise sqlite3.DatabaseError("No se encontraron snapshots para comparar.")
        base_payload = _json_loads(base.snapshot_json, {})
        compare_payload = _json_loads(compare.snapshot_json, {})
        changed = tuple(
            sorted(
                key
                for key in set(base_payload) | set(compare_payload)
                if base_payload.get(key) != compare_payload.get(key)
            )
        )
        summary = f"{len(changed)} campos cambiaron entre v{base.profile_version} y v{compare.profile_version}."
        return CreatorProfileSnapshotComparison(
            creator_id=creator_id,
            base_snapshot_id=base_snapshot_id,
            compare_snapshot_id=compare_snapshot_id,
            base_version=base.profile_version,
            compare_version=compare.profile_version,
            changed_fields=changed,
            summary=summary,
        )
