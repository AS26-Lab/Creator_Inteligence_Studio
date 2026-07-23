"""Construccion determinista de labels para personalizacion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_intelligence_studio.domain.clip_ranking.entities import ClipCollectionItem, ClipRankingRun, ClipReviewEvent, RankedClipCandidate
from creator_intelligence_studio.domain.personalization_data.value_objects import PersonalizationDatasetOptions, PersonalizationLabel


@dataclass(frozen=True, slots=True)
class LabelDecision:
    label: PersonalizationLabel
    label_source: tuple[str, ...]
    confidence: float
    quality_flags: dict[str, Any]
    conflict_entries: tuple[dict[str, Any], ...]


def _has_collection_membership(collection_items: list[ClipCollectionItem], candidate_id: str) -> bool:
    return any(item.ranked_clip_candidate_id == candidate_id for item in collection_items)


def _event_statuses(review_events: list[ClipReviewEvent]) -> set[str]:
    return {event.new_status.value for event in review_events if event.new_status is not None}


def _history_is_conflicted(review_events: list[ClipReviewEvent]) -> bool:
    statuses = _event_statuses(review_events)
    if "approved" in statuses and "rejected" in statuses:
        return True
    if "duplicate" in statuses and ("approved" in statuses or "rejected" in statuses):
        return True
    if "invalid" in statuses and ("approved" in statuses or "rejected" in statuses):
        return True
    return False


def build_dataset_label(
    *,
    ranked_candidate: RankedClipCandidate,
    review_events: list[ClipReviewEvent],
    collection_items: list[ClipCollectionItem],
    options: PersonalizationDatasetOptions,
) -> LabelDecision:
    review_status = ranked_candidate.review_status.value
    rating = ranked_candidate.user_rating
    tags = tuple(sorted(ranked_candidate.tags))
    label_source: list[str] = []
    conflict_entries: list[dict[str, Any]] = []
    label = PersonalizationLabel.NEUTRAL_OR_UNCERTAIN
    confidence = 0.35

    if review_status == "approved":
        label_source.append("review_status")
        label = PersonalizationLabel.POSITIVE
        confidence = 0.92
    elif review_status == "rejected":
        label_source.append("review_status")
        label = PersonalizationLabel.NEGATIVE
        confidence = 0.92
    elif review_status == "shortlisted":
        label_source.append("review_status")
        confidence = 0.60
    elif review_status in {"needs_review", "unreviewed"}:
        label_source.append("review_status")
        confidence = 0.30
    elif review_status == "duplicate":
        label_source.append("review_status")
        label = PersonalizationLabel.EXCLUDED
        confidence = 0.10
    elif review_status == "invalid":
        label_source.append("review_status")
        label = PersonalizationLabel.EXCLUDED
        confidence = 0.10

    if rating is not None:
        label_source.append("rating")
        if review_status in {"duplicate", "invalid"}:
            confidence = min(confidence, 0.15)
        elif rating >= 4:
            label = PersonalizationLabel.POSITIVE
            confidence = max(confidence, 0.85 if rating == 4 else 0.95)
        elif rating <= 2:
            label = PersonalizationLabel.NEGATIVE
            confidence = max(confidence, 0.85 if rating == 2 else 0.95)
        else:
            if label == PersonalizationLabel.POSITIVE and review_status != "approved":
                confidence = max(confidence, 0.70)
            elif label == PersonalizationLabel.NEGATIVE and review_status != "rejected":
                confidence = max(confidence, 0.70)
            else:
                label = PersonalizationLabel.NEUTRAL_OR_UNCERTAIN
                confidence = max(confidence, 0.45)

    if _has_collection_membership(collection_items, ranked_candidate.id):
        label_source.append("collection")
        confidence = min(1.0, confidence + 0.05)

    if ranked_candidate.adjusted_start_seconds != ranked_candidate.original_start_seconds or ranked_candidate.adjusted_end_seconds != ranked_candidate.original_end_seconds:
        label_source.append("manual_bounds")
        confidence = min(1.0, confidence + 0.05)

    if len(review_events) > 1:
        label_source.append("combined_human_rule")
        confidence = min(1.0, confidence + 0.05)

    if _history_is_conflicted(review_events):
        conflict_entries.append(
            {
                "type": "history_conflict",
                "description": "El historial contiene estados humanos incompatibles.",
                "evidence": [event.to_dict() for event in review_events],
            }
        )
        if options.conflict_policy == "excluded":
            label = PersonalizationLabel.EXCLUDED
            confidence = 0.15
        else:
            label = PersonalizationLabel.NEUTRAL_OR_UNCERTAIN
            confidence = min(confidence, 0.4)

    if rating is not None and review_status == "approved" and rating <= 2:
        conflict_entries.append(
            {
                "type": "rating_status_conflict",
                "description": "Rating bajo con estado aprobado.",
                "evidence": {"review_status": review_status, "rating": rating},
            }
        )
        label = PersonalizationLabel.EXCLUDED if options.conflict_policy == "excluded" else PersonalizationLabel.NEUTRAL_OR_UNCERTAIN
        confidence = 0.20

    if rating is not None and review_status == "rejected" and rating >= 4:
        conflict_entries.append(
            {
                "type": "rating_status_conflict",
                "description": "Rating alto con estado rechazado.",
                "evidence": {"review_status": review_status, "rating": rating},
            }
        )
        label = PersonalizationLabel.EXCLUDED if options.conflict_policy == "excluded" else PersonalizationLabel.NEUTRAL_OR_UNCERTAIN
        confidence = 0.20

    if review_status == "invalid":
        conflict_entries.append(
            {
                "type": "invalid_review_status",
                "description": "El candidato quedo marcado como duplicado o invalido.",
                "evidence": {"review_status": review_status, "tags": list(tags)},
            }
        )
        label = PersonalizationLabel.EXCLUDED
        confidence = 0.10

    quality_flags = {
        "review_status": review_status,
        "rating": rating,
        "tags": list(tags),
        "has_collection_membership": _has_collection_membership(collection_items, ranked_candidate.id),
        "manual_bounds_changed": ranked_candidate.adjusted_start_seconds != ranked_candidate.original_start_seconds
        or ranked_candidate.adjusted_end_seconds != ranked_candidate.original_end_seconds,
        "review_event_count": len(review_events),
        "is_conflicted": bool(conflict_entries),
        "is_excluded": label == PersonalizationLabel.EXCLUDED,
    }
    return LabelDecision(
        label=label,
        label_source=tuple(sorted(dict.fromkeys(label_source))),
        confidence=min(1.0, max(0.0, confidence)),
        quality_flags=quality_flags,
        conflict_entries=tuple(conflict_entries),
    )
