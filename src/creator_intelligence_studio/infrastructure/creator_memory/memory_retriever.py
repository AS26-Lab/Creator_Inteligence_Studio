"""Recuperacion local y determinista para Creator Memory."""

from __future__ import annotations

from datetime import datetime, timezone

from creator_intelligence_studio.domain.creator_memory.memory_types import (
    CreatorMemoryQueryFilters,
    CreatorMemoryRetrievalResult,
)
from creator_intelligence_studio.domain.creator_memory.entities import (
    CreatorExample,
    CreatorLimit,
    CreatorProfile,
    CreatorStyleRule,
    CreatorTrait,
    CreatorVocabulary,
)
from creator_intelligence_studio.infrastructure.creator_memory.example_indexer import example_rank_score, normalize_text


def _days_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    return max(0, (datetime.now(timezone.utc).date() - value.astimezone(timezone.utc).date()).days)


def _scope_match(score_scope: str, filters: CreatorMemoryQueryFilters, *, platform: str | None, content_type: str | None, topic: str | None) -> tuple[bool, bool, bool]:
    platform_match = not filters.platform or platform == filters.platform
    content_type_match = not filters.content_type or content_type == filters.content_type
    topic_match = not filters.topic or topic == filters.topic
    return platform_match, content_type_match, topic_match


def _free_text_match(query: str | None, *values: str | None) -> bool:
    if not query:
        return True
    needle = normalize_text(query)
    if not needle:
        return True
    haystack = " ".join(normalize_text(value) for value in values if value)
    return needle in haystack


def rank_memory_items(
    profile: CreatorProfile,
    traits: list[CreatorTrait],
    examples: list[CreatorExample],
    vocabulary: list[CreatorVocabulary],
    rules: list[CreatorStyleRule],
    limits: list[CreatorLimit],
    filters: CreatorMemoryQueryFilters,
) -> list[CreatorMemoryRetrievalResult]:
    results: list[CreatorMemoryRetrievalResult] = []

    if _free_text_match(filters.query, profile.display_name, profile.summary):
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="profile",
                item_id=profile.id,
                title=profile.display_name,
                summary=profile.summary,
                platform=None,
                content_type=None,
                topic=None,
                scope="creator_general",
                status=profile.status.value,
                confidence_level=None,
                approval_status=None,
                evidence_weight=1.0,
                recency_score=1.0,
                match_score=2.0,
                created_at=profile.updated_at,
            )
        )

    for trait in traits:
        platform_match, content_type_match, topic_match = _scope_match(
            trait.scope.value,
            filters,
            platform=trait.platform,
            content_type=trait.content_type,
            topic=trait.topic,
        )
        if not (platform_match and content_type_match and topic_match):
            continue
        if filters.trait_type and trait.trait_type.value != filters.trait_type:
            continue
        if filters.status and trait.status.value != filters.status:
            continue
        if filters.confidence_level and trait.confidence_level.value != filters.confidence_level:
            continue
        if not _free_text_match(filters.query, trait.display_name, trait.description, trait.value_json):
            continue
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="trait",
                item_id=trait.id,
                title=trait.display_name,
                summary=trait.description,
                platform=trait.platform,
                content_type=trait.content_type,
                topic=trait.topic,
                scope=trait.scope.value,
                status=trait.status.value,
                confidence_level=trait.confidence_level.value,
                approval_status=None,
                evidence_weight=1.0,
                recency_score=1.0 if trait.last_observed_at is None else max(0.0, 1.0 - min(_days_since(trait.last_observed_at) or 0, 365) / 365.0),
                match_score=(3.0 if platform_match else 0.0) + (2.0 if content_type_match else 0.0) + (2.0 if topic_match else 0.0),
                created_at=trait.updated_at,
            )
        )

    for example in examples:
        platform_match, content_type_match, topic_match = _scope_match(
            "creator_general",
            filters,
            platform=example.platform,
            content_type=example.content_type,
            topic=example.topic,
        )
        if not (platform_match and content_type_match and topic_match):
            continue
        if filters.example_type and example.example_type.value != filters.example_type:
            continue
        if filters.approval_status and example.approval_status.value != filters.approval_status:
            continue
        if filters.status and example.approval_status.value != filters.status and filters.status != "any":
            continue
        if not _free_text_match(filters.query, example.title, example.text_content, example.category):
            continue
        recency_days = _days_since(example.updated_at)
        score = example_rank_score(
            platform_match=platform_match,
            content_type_match=content_type_match,
            topic_match=topic_match,
            approval_status=example.approval_status.value,
            confidence_score=None,
            representativeness=example.representativeness,
            recency_days=recency_days,
        )
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="example",
                item_id=example.id,
                title=example.title,
                summary=example.text_content or example.approval_reason,
                platform=example.platform,
                content_type=example.content_type,
                topic=example.topic,
                scope="creator_general",
                status=example.approval_status.value,
                confidence_level=None,
                approval_status=example.approval_status.value,
                evidence_weight=example.representativeness or 0.0,
                recency_score=max(0.0, 1.0 - min(recency_days or 0, 365) / 365.0),
                match_score=score,
                created_at=example.updated_at,
            )
        )

    for vocab in vocabulary:
        if filters.platform and vocab.platform != filters.platform:
            continue
        if filters.content_type and vocab.content_type != filters.content_type:
            continue
        if filters.status and vocab.status.value != filters.status:
            continue
        if filters.confidence_level and vocab.confidence_level.value != filters.confidence_level:
            continue
        if not _free_text_match(filters.query, vocab.term, vocab.meaning, vocab.usage_notes):
            continue
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="vocabulary",
                item_id=vocab.id,
                title=vocab.term,
                summary=vocab.meaning or vocab.usage_notes,
                platform=vocab.platform,
                content_type=vocab.content_type,
                topic=None,
                scope="creator_general",
                status=vocab.status.value,
                confidence_level=vocab.confidence_level.value,
                approval_status=None,
                evidence_weight=float(vocab.frequency_count),
                recency_score=1.0 if vocab.updated_at else 0.5,
                match_score=float(vocab.frequency_count) / 10.0,
                created_at=vocab.updated_at,
            )
        )

    for rule in rules:
        if filters.platform and rule.platform != filters.platform:
            continue
        if filters.content_type and rule.content_type != filters.content_type:
            continue
        if filters.topic and rule.topic != filters.topic:
            continue
        if filters.status and rule.status.value != filters.status:
            continue
        if filters.confidence_level and rule.confidence_level.value != filters.confidence_level:
            continue
        if not _free_text_match(filters.query, rule.statement, rule.rationale):
            continue
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="rule",
                item_id=rule.id,
                title=rule.statement,
                summary=rule.rationale,
                platform=rule.platform,
                content_type=rule.content_type,
                topic=rule.topic,
                scope=rule.scope.value,
                status=rule.status.value,
                confidence_level=rule.confidence_level.value,
                approval_status=None,
                evidence_weight=float(rule.supporting_example_count),
                recency_score=1.0 if rule.last_reviewed_at is None else max(0.0, 1.0 - min(_days_since(rule.last_reviewed_at) or 0, 365) / 365.0),
                match_score=float(rule.supporting_example_count) - float(rule.contradicting_example_count),
                created_at=rule.updated_at,
            )
        )

    for limit in limits:
        if filters.platform and limit.platform != filters.platform:
            continue
        if filters.status and limit.status.value != filters.status:
            continue
        if not _free_text_match(filters.query, limit.statement, limit.category):
            continue
        results.append(
            CreatorMemoryRetrievalResult(
                item_type="limit",
                item_id=limit.id,
                title=limit.statement,
                summary=limit.category,
                platform=limit.platform,
                content_type=None,
                topic=None,
                scope=limit.scope.value,
                status=limit.status.value,
                confidence_level=None,
                approval_status=None,
                evidence_weight=1.0,
                recency_score=1.0,
                match_score={"note": 0.25, "caution": 0.5, "strong": 0.75, "absolute": 1.0}.get(limit.severity.value, 0.0),
                created_at=limit.updated_at,
            )
        )

    results.sort(
        key=lambda item: (
            item.match_score,
            item.evidence_weight,
            item.recency_score,
            item.created_at,
        ),
        reverse=True,
    )
    return results

