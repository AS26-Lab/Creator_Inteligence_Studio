"""Servicio principal de Creator Memory."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
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
from creator_intelligence_studio.domain.creator_memory.errors import (
    CreatorMemoryNotFoundError,
    CreatorMemoryStateError,
    CreatorMemoryValidationError,
)
from creator_intelligence_studio.domain.creator_memory.memory_types import (
    CreatorMemoryQueryFilters,
    CreatorMemoryRetrievalResult,
    CreatorProfileSnapshotComparison,
)
from creator_intelligence_studio.domain.creator_memory.services import build_creator_memory_fingerprint
from creator_intelligence_studio.domain.creator_memory.value_objects import (
    CreatorExampleApprovalStatus,
    CreatorExampleType,
    CreatorFeedbackType,
    CreatorLimitSeverity,
    CreatorLimitStatus,
    CreatorLimitType,
    CreatorMemoryConfidenceLevel,
    CreatorMemoryScope,
    CreatorObjectiveStatus,
    CreatorObjectiveType,
    CreatorProfileStatus,
    CreatorRuleReviewDecision,
    CreatorRuleStatus,
    CreatorStyleRuleType,
    CreatorSnapshotStatus,
    CreatorTraitStatus,
    CreatorTraitType,
    CreatorVocabularyStatus,
    CreatorVocabularyType,
    CreatorEvidenceType,
)
from creator_intelligence_studio.domain.creator_memory.repositories import CreatorMemoryRepository
from creator_intelligence_studio.infrastructure.creator_memory.evidence_linker import build_evidence_link
from creator_intelligence_studio.infrastructure.creator_memory.profile_builder import build_profile_summary
from creator_intelligence_studio.infrastructure.creator_memory.profile_snapshot_builder import build_profile_snapshot
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import (
    SQLiteCreatorMemoryRepository,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | list | dict | None, fallback):
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_slug(value: str | None) -> str:
    return _normalize_text(value).replace(" ", "_").lower()


@dataclass(frozen=True, slots=True)
class CreatorMemoryProfileDetail:
    profile: CreatorProfile
    summary: object
    traits: tuple[CreatorTrait, ...]
    vocabulary: tuple[CreatorVocabulary, ...]
    examples: tuple[CreatorExample, ...]
    rules: tuple[CreatorStyleRule, ...]
    limits: tuple[CreatorLimit, ...]
    evidence: tuple[CreatorTraitEvidence, ...]
    snapshots: tuple[CreatorProfileSnapshot, ...]
    feedback: tuple[CreatorMemoryFeedback, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile.to_dict(),
            "summary": self.summary.to_dict() if hasattr(self.summary, "to_dict") else self.summary,
            "traits": [item.to_dict() for item in self.traits],
            "vocabulary": [item.to_dict() for item in self.vocabulary],
            "examples": [item.to_dict() for item in self.examples],
            "rules": [item.to_dict() for item in self.rules],
            "limits": [item.to_dict() for item in self.limits],
            "evidence": [item.to_dict() for item in self.evidence],
            "snapshots": [item.to_dict() for item in self.snapshots],
            "feedback": [item.to_dict() for item in self.feedback],
        }


class CreatorMemoryService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: CreatorMemoryRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_memory")
        self._exports_root = self.paths.data_directory / "creator_memory" / "exports"

    def _get_profile_or_error(self, creator_id: str) -> CreatorProfile:
        profile = self.repository.get_profile(creator_id)
        if profile is None:
            raise CreatorMemoryNotFoundError("El perfil del creador no existe.")
        return profile

    def _load_profile_sections(self, creator_id: str) -> tuple[CreatorProfile, object, list[CreatorTrait], list[CreatorVocabulary], list[CreatorExample], list[CreatorStyleRule], list[CreatorLimit], list[CreatorTraitEvidence], list[CreatorProfileSnapshot], list[CreatorMemoryFeedback]]:
        profile = self._get_profile_or_error(creator_id)
        traits = self.repository.list_traits(creator_id)
        vocabulary = self.repository.list_vocabulary(creator_id)
        examples = self.repository.list_examples(creator_id)
        rules = self.repository.list_style_rules(creator_id)
        limits = self.repository.list_limits(creator_id)
        evidence = [item for trait in traits for item in self.repository.list_trait_evidence(trait.id)]
        snapshots = self.repository.list_profile_snapshots(creator_id)
        feedback = self.repository.list_feedback(creator_id)
        summary = build_profile_summary(
            profile,
            trait_count=len(traits),
            example_count=len(examples),
            vocabulary_count=len(vocabulary),
            rule_count=len(rules),
            limit_count=len(limits),
        )
        return profile, summary, traits, vocabulary, examples, rules, limits, evidence, snapshots, feedback

    def get_creator_profile(self, creator_id: str) -> CreatorProfile | None:
        return self.repository.get_profile(creator_id)

    def update_creator_profile(
        self,
        *,
        creator_id: str,
        display_name: str | None = None,
        summary: str | None = None,
        primary_language: str | None = None,
        secondary_languages: list[str] | str | None = None,
        default_tone: str | None = None,
        default_formality: str | None = None,
        objectives: list[dict[str, object]] | str | None = None,
        status: str | CreatorProfileStatus | None = None,
    ) -> CreatorProfile:
        current = self.repository.get_profile(creator_id)
        profile_version = (current.profile_version + 1) if current else 1
        resolved_display_name = _normalize_text(display_name) if display_name else (current.display_name if current else creator_id)
        payload = CreatorProfile(
            id=current.id if current else str(uuid4()),
            creator_id=creator_id,
            display_name=resolved_display_name,
            profile_version=profile_version,
            status=CreatorProfileStatus(status) if status else (current.status if current else CreatorProfileStatus.ACTIVE),
            summary=summary if summary is not None else (current.summary if current else None),
            primary_language=primary_language if primary_language is not None else (current.primary_language if current else None),
            secondary_languages_json=_json_dumps(_json_loads(secondary_languages, [])),
            default_tone=default_tone if default_tone is not None else (current.default_tone if current else None),
            default_formality=default_formality if default_formality is not None else (current.default_formality if current else None),
            objectives_json=_json_dumps(_json_loads(objectives, _json_loads(current.objectives_json if current else None, []))),
            created_at=current.created_at if current else utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_profile(payload)

    def list_traits(self, creator_id: str, filters: dict[str, object] | None = None) -> list[CreatorTrait]:
        traits = self.repository.list_traits(creator_id)
        filters = filters or {}
        if not filters:
            return traits
        result: list[CreatorTrait] = []
        for trait in traits:
            if filters.get("platform") and trait.platform != filters.get("platform"):
                continue
            if filters.get("content_type") and trait.content_type != filters.get("content_type"):
                continue
            if filters.get("topic") and trait.topic != filters.get("topic"):
                continue
            if filters.get("trait_type") and trait.trait_type.value != filters.get("trait_type"):
                continue
            if filters.get("status") and trait.status.value != filters.get("status"):
                continue
            if filters.get("confidence_level") and trait.confidence_level.value != filters.get("confidence_level"):
                continue
            result.append(trait)
        return result

    def get_trait(self, trait_id: str) -> CreatorTrait | None:
        return self.repository.get_trait(trait_id)

    def create_trait(
        self,
        *,
        creator_id: str,
        trait_type: str,
        trait_key: str,
        display_name: str,
        description: str | None = None,
        value_json: str | dict | list = "{}",
        scope: str = CreatorMemoryScope.CREATOR_GENERAL.value,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        confidence_level: str = CreatorMemoryConfidenceLevel.LOW.value,
        confidence_score: float | None = None,
        status: str = CreatorTraitStatus.OBSERVED.value,
        first_observed_at=None,
        last_observed_at=None,
    ) -> CreatorTrait:
        trait = CreatorTrait(
            id=str(uuid4()),
            creator_id=creator_id,
            trait_type=CreatorTraitType(trait_type),
            trait_key=_normalize_slug(trait_key),
            display_name=display_name.strip(),
            description=description,
            value_json=_json_dumps(_json_loads(value_json, {})),
            scope=CreatorMemoryScope(scope),
            platform=platform,
            content_type=content_type,
            topic=topic,
            confidence_level=CreatorMemoryConfidenceLevel(confidence_level),
            confidence_score=confidence_score,
            status=CreatorTraitStatus(status),
            first_observed_at=first_observed_at,
            last_observed_at=last_observed_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_trait(trait)

    def update_trait(self, trait_id: str, **changes) -> CreatorTrait:
        current = self.repository.get_trait(trait_id)
        if current is None:
            raise CreatorMemoryNotFoundError("El trait solicitado no existe.")
        payload = current
        if "trait_type" in changes and changes["trait_type"] is not None:
            changes["trait_type"] = CreatorTraitType(changes["trait_type"])
        if "scope" in changes and changes["scope"] is not None:
            changes["scope"] = CreatorMemoryScope(changes["scope"])
        if "confidence_level" in changes and changes["confidence_level"] is not None:
            changes["confidence_level"] = CreatorMemoryConfidenceLevel(changes["confidence_level"])
        if "status" in changes and changes["status"] is not None:
            changes["status"] = CreatorTraitStatus(changes["status"])
        if "value_json" in changes and changes["value_json"] is not None:
            changes["value_json"] = _json_dumps(_json_loads(changes["value_json"], {}))
        if "trait_key" in changes and changes["trait_key"] is not None:
            changes["trait_key"] = _normalize_slug(changes["trait_key"])
        payload = replace(payload, **changes, updated_at=utc_now())
        return self.repository.upsert_trait(payload)

    def archive_trait(self, trait_id: str) -> CreatorTrait:
        trait = self.repository.archive_trait(trait_id)
        if trait is None:
            raise CreatorMemoryNotFoundError("El trait solicitado no existe.")
        return trait

    def add_trait_evidence(
        self,
        *,
        trait_id: str,
        source_type: str,
        source_id: str | None = None,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        transcript_segment_id: str | None = None,
        start_seconds: float | None = None,
        end_seconds: float | None = None,
        quoted_text: str | None = None,
        evidence_type: str | CreatorEvidenceType = CreatorEvidenceType.MANUAL_OBSERVATION,
        supports_trait: bool = True,
        weight: float = 1.0,
        notes: str | None = None,
    ) -> CreatorTraitEvidence:
        current = self.repository.get_trait(trait_id)
        if current is None:
            raise CreatorMemoryNotFoundError("El trait solicitado no existe.")
        existing = self.repository.list_trait_evidence(trait_id)
        fingerprint = build_creator_memory_fingerprint(
            {
                "trait_id": trait_id,
                "source_type": source_type,
                "source_id": source_id,
                "publication_id": publication_id,
                "video_asset_id": video_asset_id,
                "transcript_segment_id": transcript_segment_id,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "quoted_text": quoted_text,
                "evidence_type": str(evidence_type),
                "supports_trait": supports_trait,
                "weight": weight,
                "notes": notes,
            }
        )
        for item in existing:
            candidate = build_creator_memory_fingerprint(item.to_dict())
            if candidate == fingerprint:
                return item
        evidence = build_evidence_link(
            source_type=source_type,
            source_id=source_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            transcript_segment_id=transcript_segment_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            quoted_text=quoted_text,
            evidence_type=evidence_type,
            supports_trait=supports_trait,
            weight=weight,
            notes=notes,
        )
        record = CreatorTraitEvidence(
            id=str(uuid4()),
            trait_id=trait_id,
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            publication_id=evidence.publication_id,
            video_asset_id=evidence.video_asset_id,
            transcript_segment_id=evidence.transcript_segment_id,
            start_seconds=evidence.start_seconds,
            end_seconds=evidence.end_seconds,
            quoted_text=evidence.quoted_text,
            evidence_type=evidence.evidence_type,
            supports_trait=evidence.supports_trait,
            weight=evidence.weight,
            notes=evidence.notes,
            created_at=evidence.created_at,
        )
        return self.repository.upsert_trait_evidence(record)

    def list_trait_evidence(self, trait_id: str) -> list[CreatorTraitEvidence]:
        return self.repository.list_trait_evidence(trait_id)

    def list_examples(self, creator_id: str, filters: dict[str, object] | None = None) -> list[CreatorExample]:
        examples = self.repository.list_examples(creator_id)
        filters = filters or {}
        if not filters:
            return examples
        result: list[CreatorExample] = []
        for example in examples:
            if filters.get("platform") and example.platform != filters.get("platform"):
                continue
            if filters.get("content_type") and example.content_type != filters.get("content_type"):
                continue
            if filters.get("topic") and example.topic != filters.get("topic"):
                continue
            if filters.get("example_type") and example.example_type.value != filters.get("example_type"):
                continue
            if filters.get("approval_status") and example.approval_status.value != filters.get("approval_status"):
                continue
            result.append(example)
        return result

    def create_example(
        self,
        *,
        creator_id: str,
        example_type: str,
        category: str,
        title: str,
        source_type: str,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        text_content: str | None = None,
        source_id: str | None = None,
        publication_id: str | None = None,
        video_asset_id: str | None = None,
        start_seconds: float | None = None,
        end_seconds: float | None = None,
        representativeness: float | None = None,
        approval_status: str = CreatorExampleApprovalStatus.PENDING.value,
        approval_reason: str | None = None,
    ) -> CreatorExample:
        example = CreatorExample(
            id=str(uuid4()),
            creator_id=creator_id,
            example_type=CreatorExampleType(example_type),
            category=category,
            platform=platform,
            content_type=content_type,
            topic=topic,
            title=title.strip(),
            text_content=text_content,
            source_type=source_type,
            source_id=source_id,
            publication_id=publication_id,
            video_asset_id=video_asset_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            representativeness=representativeness,
            approval_status=CreatorExampleApprovalStatus(approval_status),
            approval_reason=approval_reason,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_example(example)

    def review_example(self, example_id: str, *, approval_status: str, reason: str | None = None) -> CreatorExample:
        reviewed = self.repository.review_example(example_id, approval_status, reason)
        if reviewed is None:
            raise CreatorMemoryNotFoundError("El ejemplo solicitado no existe.")
        return reviewed

    def get_example(self, example_id: str) -> CreatorExample | None:
        return self.repository.get_example(example_id)

    def list_vocabulary(self, creator_id: str, filters: dict[str, object] | None = None) -> list[CreatorVocabulary]:
        vocabulary = self.repository.list_vocabulary(creator_id)
        filters = filters or {}
        if not filters:
            return vocabulary
        result: list[CreatorVocabulary] = []
        for item in vocabulary:
            if filters.get("platform") and item.platform != filters.get("platform"):
                continue
            if filters.get("content_type") and item.content_type != filters.get("content_type"):
                continue
            if filters.get("vocabulary_type") and item.vocabulary_type.value != filters.get("vocabulary_type"):
                continue
            result.append(item)
        return result

    def create_vocabulary_entry(
        self,
        *,
        creator_id: str,
        term: str,
        vocabulary_type: str,
        meaning: str | None = None,
        usage_notes: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        confidence_level: str = CreatorMemoryConfidenceLevel.LOW.value,
        frequency_count: int = 1,
        status: str = CreatorVocabularyStatus.ACTIVE.value,
    ) -> CreatorVocabulary:
        vocab = CreatorVocabulary(
            id=str(uuid4()),
            creator_id=creator_id,
            term=term.strip(),
            normalized_term=_normalize_slug(term),
            vocabulary_type=CreatorVocabularyType(vocabulary_type),
            meaning=meaning,
            usage_notes=usage_notes,
            platform=platform,
            content_type=content_type,
            frequency_count=frequency_count,
            confidence_level=CreatorMemoryConfidenceLevel(confidence_level),
            status=CreatorVocabularyStatus(status),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_vocabulary(vocab)

    def list_style_rules(self, creator_id: str, filters: dict[str, object] | None = None) -> list[CreatorStyleRule]:
        rules = self.repository.list_style_rules(creator_id)
        filters = filters or {}
        if not filters:
            return rules
        result: list[CreatorStyleRule] = []
        for rule in rules:
            if filters.get("platform") and rule.platform != filters.get("platform"):
                continue
            if filters.get("content_type") and rule.content_type != filters.get("content_type"):
                continue
            if filters.get("topic") and rule.topic != filters.get("topic"):
                continue
            if filters.get("status") and rule.status.value != filters.get("status"):
                continue
            result.append(rule)
        return result

    def get_style_rule(self, rule_id: str) -> CreatorStyleRule | None:
        return self.repository.get_style_rule(rule_id)

    def create_style_rule(
        self,
        *,
        creator_id: str,
        rule_type: str,
        scope: str = CreatorMemoryScope.CREATOR_GENERAL.value,
        statement: str,
        rationale: str | None = None,
        platform: str | None = None,
        content_type: str | None = None,
        topic: str | None = None,
        confidence_level: str = CreatorMemoryConfidenceLevel.LOW.value,
        status: str = CreatorRuleStatus.OBSERVED.value,
        supporting_example_count: int = 0,
        contradicting_example_count: int = 0,
        first_observed_at=None,
        last_reviewed_at=None,
    ) -> CreatorStyleRule:
        rule = CreatorStyleRule(
            id=str(uuid4()),
            creator_id=creator_id,
            rule_type=CreatorStyleRuleType(rule_type),
            scope=CreatorMemoryScope(scope),
            platform=platform,
            content_type=content_type,
            topic=topic,
            statement=statement.strip(),
            rationale=rationale,
            status=CreatorRuleStatus(status),
            confidence_level=CreatorMemoryConfidenceLevel(confidence_level),
            supporting_example_count=supporting_example_count,
            contradicting_example_count=contradicting_example_count,
            first_observed_at=first_observed_at,
            last_reviewed_at=last_reviewed_at,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_style_rule(rule)

    def review_style_rule(
        self,
        rule_id: str,
        *,
        decision: str,
        reason: str,
        previous_statement: str | None = None,
        new_statement: str | None = None,
    ) -> CreatorStyleRuleReview:
        current = self.repository.get_style_rule(rule_id)
        if current is None:
            raise CreatorMemoryNotFoundError("La regla solicitada no existe.")
        review = CreatorStyleRuleReview(
            id=str(uuid4()),
            rule_id=rule_id,
            decision=CreatorRuleReviewDecision(decision),
            previous_statement=previous_statement or current.statement,
            new_statement=new_statement,
            reason=reason,
            reviewed_at=utc_now(),
            created_at=utc_now(),
        )
        return self.repository.review_style_rule(review)

    def list_limits(self, creator_id: str) -> list[CreatorLimit]:
        return self.repository.list_limits(creator_id)

    def get_limit(self, creator_id: str, limit_id: str) -> CreatorLimit | None:
        return next((item for item in self.repository.list_limits(creator_id) if item.id == limit_id), None)

    def create_limit(
        self,
        *,
        creator_id: str,
        limit_type: str,
        category: str,
        statement: str,
        severity: str = CreatorLimitSeverity.CAUTION.value,
        scope: str = CreatorMemoryScope.CREATOR_GENERAL.value,
        platform: str | None = None,
        status: str = CreatorLimitStatus.ACTIVE.value,
    ) -> CreatorLimit:
        limit = CreatorLimit(
            id=str(uuid4()),
            creator_id=creator_id,
            limit_type=CreatorLimitType(limit_type),
            category=category,
            statement=statement.strip(),
            severity=CreatorLimitSeverity(severity),
            scope=CreatorMemoryScope(scope),
            platform=platform,
            status=CreatorLimitStatus(status),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.repository.upsert_limit(limit)

    def update_limit(self, limit_id: str, *, creator_id: str, **changes) -> CreatorLimit:
        limit = next((item for item in self.repository.list_limits(creator_id) if item.id == limit_id), None)
        if limit is None:
            raise CreatorMemoryNotFoundError("El limite solicitado no existe.")
        if "limit_type" in changes and changes["limit_type"] is not None:
            changes["limit_type"] = CreatorLimitType(changes["limit_type"])
        if "severity" in changes and changes["severity"] is not None:
            changes["severity"] = CreatorLimitSeverity(changes["severity"])
        if "scope" in changes and changes["scope"] is not None:
            changes["scope"] = CreatorMemoryScope(changes["scope"])
        if "status" in changes and changes["status"] is not None:
            changes["status"] = CreatorLimitStatus(changes["status"])
        return self.repository.upsert_limit(replace(limit, **changes, updated_at=utc_now()))

    def create_profile_snapshot(self, creator_id: str) -> CreatorProfileSnapshot:
        profile, summary, traits, vocabulary, examples, rules, limits, evidence, snapshots, feedback = self._load_profile_sections(creator_id)
        snapshot, payload = build_profile_snapshot(profile, traits=traits, examples=examples, vocabulary=vocabulary, rules=rules, limits=limits, evidence=evidence, feedback=[item.to_dict() for item in feedback])
        existing = next((item for item in snapshots if item.source_fingerprint == snapshot.source_fingerprint), None)
        if existing is not None:
            return existing
        return self.repository.upsert_profile_snapshot(snapshot)

    def list_profile_snapshots(self, creator_id: str) -> list[CreatorProfileSnapshot]:
        return self.repository.list_profile_snapshots(creator_id)

    def get_profile_snapshot(self, snapshot_id: str) -> CreatorProfileSnapshot | None:
        return self.repository.get_profile_snapshot(snapshot_id)

    def compare_profile_snapshots(self, creator_id: str, base_snapshot_id: str, compare_snapshot_id: str) -> CreatorProfileSnapshotComparison:
        return self.repository.compare_snapshots(creator_id, base_snapshot_id, compare_snapshot_id)

    def retrieve_creator_context(self, creator_id: str, query_filters: CreatorMemoryQueryFilters | dict[str, object]) -> list[CreatorMemoryRetrievalResult]:
        filters = query_filters if isinstance(query_filters, dict) else query_filters.__dict__
        filters = dict(filters)
        filters["creator_id"] = creator_id
        return self.repository.retrieve(creator_id, filters)

    def record_memory_feedback(
        self,
        *,
        creator_id: str,
        target_type: str,
        target_id: str,
        feedback_type: str,
        reason: str,
        corrected_value_json: str | dict | list | None = None,
    ) -> CreatorMemoryFeedback:
        feedback = CreatorMemoryFeedback(
            id=str(uuid4()),
            creator_id=creator_id,
            target_type=target_type,
            target_id=target_id,
            feedback_type=CreatorFeedbackType(feedback_type),
            reason=reason,
            corrected_value_json=_json_dumps(_json_loads(corrected_value_json, None)) if corrected_value_json is not None else None,
            created_at=utc_now(),
        )
        return self.repository.upsert_feedback(feedback)

    def list_feedback(self, creator_id: str) -> list[CreatorMemoryFeedback]:
        return self.repository.list_feedback(creator_id)

    def get_profile_detail(self, creator_id: str) -> CreatorMemoryProfileDetail:
        profile, summary, traits, vocabulary, examples, rules, limits, evidence, snapshots, feedback = self._load_profile_sections(creator_id)
        return CreatorMemoryProfileDetail(
            profile=profile,
            summary=summary,
            traits=tuple(traits),
            vocabulary=tuple(vocabulary),
            examples=tuple(examples),
            rules=tuple(rules),
            limits=tuple(limits),
            evidence=tuple(evidence),
            snapshots=tuple(snapshots),
            feedback=tuple(feedback),
        )

    def export_json(self, creator_id: str, *, summary_only: bool = False) -> str:
        detail = self.get_profile_detail(creator_id)
        payload = detail.to_dict()
        if summary_only:
            payload = {
                "profile": payload["profile"],
                "summary": payload["summary"],
                "traits": payload["traits"][:10],
                "vocabulary": payload["vocabulary"][:10],
                "examples": payload["examples"][:10],
                "rules": payload["rules"][:10],
                "limits": payload["limits"][:10],
                "snapshots": payload["snapshots"][:10],
            }
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    def export_txt(self, creator_id: str) -> str:
        detail = self.get_profile_detail(creator_id)
        payload = detail.to_dict()
        lines = [
            f"Perfil: {payload['profile']['display_name']}",
            f"Version: {payload['profile']['profile_version']}",
            f"Idioma primario: {payload['profile']['primary_language']}",
            f"Traits: {len(payload['traits'])}",
            f"Vocabulary: {len(payload['vocabulary'])}",
            f"Examples: {len(payload['examples'])}",
            f"Rules: {len(payload['rules'])}",
            f"Limits: {len(payload['limits'])}",
        ]
        return "\n".join(lines)

    def export_csv(self, creator_id: str, kind: str) -> str:
        rows: list[dict[str, object]]
        if kind == "traits":
            rows = [item.to_dict() for item in self.list_traits(creator_id)]
        elif kind == "vocabulary":
            rows = [item.to_dict() for item in self.list_vocabulary(creator_id)]
        elif kind == "examples":
            rows = [item.to_dict() for item in self.list_examples(creator_id)]
        else:
            raise CreatorMemoryValidationError("Tipo de exportacion no soportado.")
        if not rows:
            return ""
        from io import StringIO

        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _sanitize_csv_value(value) for key, value in row.items()})
        return buffer.getvalue()


def _sanitize_csv_value(value: object) -> object:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


def build_creator_memory_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: CreatorMemoryRepository | None = None,
    logger: logging.Logger | None = None,
) -> CreatorMemoryService:
    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    repository = repository or SQLiteCreatorMemoryRepository(database)
    return CreatorMemoryService(settings=settings, paths=paths, repository=repository, logger=logger)
