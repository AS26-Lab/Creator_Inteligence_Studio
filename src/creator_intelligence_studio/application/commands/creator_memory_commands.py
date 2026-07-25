"""Comandos de Creator Memory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreatorMemoryProfileCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class UpdateCreatorMemoryProfileCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListCreatorTraitsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorTraitCommand:
    creator_id: str
    trait_type: str
    trait_key: str
    display_name: str


@dataclass(frozen=True, slots=True)
class ShowCreatorTraitCommand:
    trait_id: str


@dataclass(frozen=True, slots=True)
class UpdateCreatorTraitCommand:
    trait_id: str


@dataclass(frozen=True, slots=True)
class AddCreatorTraitEvidenceCommand:
    trait_id: str
    source_type: str


@dataclass(frozen=True, slots=True)
class ListCreatorExamplesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorExampleCommand:
    creator_id: str
    example_type: str
    category: str
    title: str
    source_type: str


@dataclass(frozen=True, slots=True)
class ReviewCreatorExampleCommand:
    example_id: str
    approval_status: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ListCreatorVocabularyCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorVocabularyCommand:
    creator_id: str
    term: str
    vocabulary_type: str


@dataclass(frozen=True, slots=True)
class ListCreatorRulesCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorRuleCommand:
    creator_id: str
    rule_type: str
    statement: str


@dataclass(frozen=True, slots=True)
class ReviewCreatorRuleCommand:
    rule_id: str
    decision: str
    reason: str


@dataclass(frozen=True, slots=True)
class ListCreatorLimitsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorLimitCommand:
    creator_id: str
    limit_type: str
    category: str
    statement: str


@dataclass(frozen=True, slots=True)
class UpdateCreatorLimitCommand:
    limit_id: str
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListCreatorSnapshotsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CreateCreatorSnapshotCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CompareCreatorSnapshotsCommand:
    creator_id: str
    base_snapshot_id: str
    compare_snapshot_id: str


@dataclass(frozen=True, slots=True)
class RetrieveCreatorMemoryCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class RecordCreatorMemoryFeedbackCommand:
    creator_id: str
    target_type: str
    target_id: str
    feedback_type: str
    reason: str

