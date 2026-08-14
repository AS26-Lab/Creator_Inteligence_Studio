"""Deterministic application of confirmed creator preferences."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from creator_intelligence_studio.domain.creator_preferences import (
    CreatorConfirmedPreference,
    CreatorPreferenceRepository,
    CreatorPreferenceScope,
    CreatorPreferenceType,
)
from creator_intelligence_studio.shared.dates import utc_now


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback):
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return fallback if value is None else value
    except json.JSONDecodeError:
        return fallback


def _serialize(value: Any) -> object:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _stable_id(*parts: str) -> str:
    return sha256(_json_dumps(parts).encode("utf-8")).hexdigest()


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _scope_rank(preference: CreatorConfirmedPreference) -> int:
    if preference.project_id and preference.workflow_type:
        return 3
    if preference.project_id:
        return 2
    if preference.workflow_type:
        return 1
    return 0


def _infer_length_direction(text: str | None) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    shorter_tokens = (
        "short",
        "shorter",
        "brief",
        "concise",
        "compact",
        "tight",
        "summar",
        "reduce",
        "less",
        "under 15",
        "15 seconds",
    )
    longer_tokens = (
        "long",
        "longer",
        "detailed",
        "expanded",
        "comprehensive",
        "cinematic",
        "thorough",
        "more detail",
    )
    shorter = any(token in normalized for token in shorter_tokens)
    longer = any(token in normalized for token in longer_tokens)
    if shorter and longer:
        return None
    if shorter:
        return "shorter"
    if longer:
        return "longer"
    return None


def _preference_value(preference: CreatorConfirmedPreference) -> dict[str, object]:
    value = _json_loads(preference.value_json, {})
    if not isinstance(value, dict):
        value = {}
    direction = str(value.get("direction") or value.get("value") or value.get("proposed_value") or "").strip().lower()
    return {
        "direction": direction or None,
        "preference_type": str(value.get("preference_type") or preference.preference_type.value),
        "source": value.get("source"),
    }


def _render_preference_text(
    *,
    preference: CreatorConfirmedPreference,
    value: dict[str, object],
) -> str:
    scope_label = {
        CreatorPreferenceScope.CREATOR_GLOBAL: "para todos tus proyectos",
        CreatorPreferenceScope.PROJECT_SPECIFIC: "solo para este proyecto",
        CreatorPreferenceScope.WORKFLOW_SPECIFIC: "solo para este flujo de trabajo",
    }[preference.scope]
    direction = str(value.get("direction") or "").strip().lower()
    if preference.preference_type == CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE:
        if direction == "shorter":
            return f"{scope_label}: preferir introducciones mas breves."
        if direction == "longer":
            return f"{scope_label}: preferir introducciones mas detalladas."
    return f"{scope_label}: preferencia confirmada."


def _supported_preference_types() -> tuple[CreatorPreferenceType, ...]:
    return (CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE,)


@dataclass(frozen=True, slots=True)
class CreatorPreferenceApplicationItem:
    preference_id: str
    preference_key: str
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    scope: str
    preference_type: str
    value: dict[str, object]
    rendered_text: str
    specificity_rank: int
    source_candidate_id: str | None
    confirmed_by: str
    confirmed_at: datetime
    active: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "preference_id": self.preference_id,
            "preference_key": self.preference_key,
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "scope": self.scope,
            "preference_type": self.preference_type,
            "value": _serialize(self.value),
            "rendered_text": self.rendered_text,
            "specificity_rank": self.specificity_rank,
            "source_candidate_id": self.source_candidate_id,
            "confirmed_by": self.confirmed_by,
            "confirmed_at": self.confirmed_at.isoformat().replace("+00:00", "Z"),
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class CreatorPreferenceApplicationBundle:
    creator_id: str
    project_id: str | None
    workflow_type: str
    current_user_instruction: str | None
    project_instruction: str | None
    primary_artifact_metadata: dict[str, object]
    corpus_context_present: bool
    corpus_context_item_count: int
    confirmed_preferences_present: bool
    applied_preferences: tuple[CreatorPreferenceApplicationItem, ...]
    omitted_preferences: tuple[dict[str, object], ...]
    conflicts: tuple[dict[str, object], ...]
    rendered_context: str
    preferences_used_count: int
    preferences_omitted_count: int
    conflict_count: int
    application_state: str
    request_trace: dict[str, object]
    bundle_fingerprint: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "current_user_instruction": self.current_user_instruction,
            "project_instruction": self.project_instruction,
            "primary_artifact_metadata": _serialize(self.primary_artifact_metadata),
            "corpus_context_present": self.corpus_context_present,
            "corpus_context_item_count": self.corpus_context_item_count,
            "confirmed_preferences_present": self.confirmed_preferences_present,
            "applied_preferences": [item.to_dict() for item in self.applied_preferences],
            "omitted_preferences": [_serialize(item) for item in self.omitted_preferences],
            "conflicts": [_serialize(item) for item in self.conflicts],
            "rendered_context": self.rendered_context,
            "preferences_used_count": self.preferences_used_count,
            "preferences_omitted_count": self.preferences_omitted_count,
            "conflict_count": self.conflict_count,
            "application_state": self.application_state,
            "request_trace": _serialize(self.request_trace),
            "bundle_fingerprint": self.bundle_fingerprint,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
        }


class CreatorPreferenceApplicationService:
    MAX_RENDERED_ITEMS = 6
    MAX_RENDERED_CHARS = 800

    def __init__(
        self,
        *,
        repository: CreatorPreferenceRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_preference_application")

    @staticmethod
    def audit_supported_preference_matrix() -> tuple[dict[str, object], ...]:
        return (
            {
                "preference_type": CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE.value,
                "can_apply": True,
                "required_evidence": "confirmed + active preference",
                "scope": "creator_global/project_specific/workflow_specific",
                "safe_human_wording": "Preferir textos mas breves o mas detallados cuando no contradiga la solicitud actual.",
                "why": "Es una preferencia estructural y conservadora.",
            },
        )

    def _select_preferences(
        self,
        preferences: list[CreatorConfirmedPreference],
        *,
        current_user_instruction: str | None,
        project_instruction: str | None,
    ) -> tuple[list[CreatorPreferenceApplicationItem], list[dict[str, object]], list[dict[str, object]]]:
        supported: list[CreatorConfirmedPreference] = [
            preference
            for preference in preferences
            if preference.preference_type in _supported_preference_types()
        ]
        grouped: dict[str, list[CreatorConfirmedPreference]] = {}
        for preference in supported:
            grouped.setdefault(preference.preference_type.value, []).append(preference)

        applied: list[CreatorPreferenceApplicationItem] = []
        omitted: list[dict[str, object]] = []
        conflicts: list[dict[str, object]] = []
        user_direction = _infer_length_direction(current_user_instruction)
        project_direction = _infer_length_direction(project_instruction)

        for preference_type, items in grouped.items():
            ranked = sorted(
                items,
                key=lambda item: (
                    -_scope_rank(item),
                    -int(item.confirmed_at.timestamp()),
                    item.id,
                ),
            )
            chosen: CreatorConfirmedPreference | None = None
            conflict_group: list[CreatorConfirmedPreference] = []
            if ranked:
                top_rank = _scope_rank(ranked[0])
                same_rank = [item for item in ranked if _scope_rank(item) == top_rank]
                chosen = same_rank[0]
                if len(same_rank) > 1:
                    conflict_group = same_rank
            if chosen is None:
                continue
            value = _preference_value(chosen)
            direction = str(value.get("direction") or "").strip().lower()
            if not direction:
                omitted.append(
                    {
                        "preference_id": chosen.id,
                        "preference_key": chosen.preference_key,
                        "preference_type": preference_type,
                        "scope": chosen.scope.value,
                        "reason": "unsupported_value",
                    }
                )
                continue
            if user_direction and user_direction != direction:
                omitted.append(
                    {
                        "preference_id": chosen.id,
                        "preference_key": chosen.preference_key,
                        "preference_type": preference_type,
                        "scope": chosen.scope.value,
                        "reason": "overridden_by_current_user_instruction",
                        "current_user_direction": user_direction,
                    }
                )
                continue
            if project_direction and project_direction != direction:
                omitted.append(
                    {
                        "preference_id": chosen.id,
                        "preference_key": chosen.preference_key,
                        "preference_type": preference_type,
                        "scope": chosen.scope.value,
                        "reason": "overridden_by_project_instruction",
                        "project_direction": project_direction,
                    }
                )
                continue
            if conflict_group:
                conflicts.append(
                    {
                        "preference_type": preference_type,
                        "scope": chosen.scope.value,
                        "preference_ids": [item.id for item in conflict_group],
                        "reason": "equal_specificity_conflict",
                    }
                )
                omitted.extend(
                    {
                        "preference_id": item.id,
                        "preference_key": item.preference_key,
                        "preference_type": preference_type,
                        "scope": item.scope.value,
                        "reason": "equal_specificity_conflict",
                    }
                    for item in conflict_group[1:]
                )
            applied.append(
                CreatorPreferenceApplicationItem(
                    preference_id=chosen.id,
                    preference_key=chosen.preference_key,
                    creator_id=chosen.creator_id,
                    project_id=chosen.project_id,
                    workflow_type=chosen.workflow_type,
                    scope=chosen.scope.value,
                    preference_type=preference_type,
                    value=value,
                    rendered_text=_render_preference_text(preference=chosen, value=value),
                    specificity_rank=_scope_rank(chosen),
                    source_candidate_id=chosen.source_candidate_id,
                    confirmed_by=chosen.confirmed_by,
                    confirmed_at=chosen.confirmed_at,
                    active=chosen.active,
                )
            )
            for broader in ranked[1:]:
                omitted.append(
                    {
                        "preference_id": broader.id,
                        "preference_key": broader.preference_key,
                        "preference_type": preference_type,
                        "scope": broader.scope.value,
                        "reason": "overridden_by_more_specific_preference",
                        "overridden_by": chosen.id,
                    }
                )
        return applied, omitted, conflicts

    def build_application_bundle(
        self,
        *,
        creator_id: str,
        workflow_type: str,
        project_id: str | None = None,
        current_user_instruction: str | None = None,
        project_instruction: str | None = None,
        primary_artifact_metadata: dict[str, object] | None = None,
        corpus_context_present: bool = False,
        corpus_context_item_count: int = 0,
    ) -> CreatorPreferenceApplicationBundle:
        confirmed_preferences = self.repository.list_confirmed_preferences(
            creator_id,
            project_id=None,
            workflow_type=None,
            active=True,
            limit=1000,
        )
        scoped_preferences = [
            preference
            for preference in confirmed_preferences
            if preference.creator_id == creator_id
            and (preference.project_id is None or (project_id is not None and preference.project_id == project_id))
            and (preference.workflow_type is None or preference.workflow_type == workflow_type)
        ]
        applied, omitted, conflicts = self._select_preferences(
            scoped_preferences,
            current_user_instruction=current_user_instruction,
            project_instruction=project_instruction,
        )
        rendered_lines = [
            "CONFIRMED CREATOR PREFERENCES",
            "Treat these as secondary guidance. Current user request and project instructions win.",
        ]
        for item in applied[: self.MAX_RENDERED_ITEMS]:
            rendered_lines.append(f"- {item.rendered_text}")
        rendered_context = "\n".join(rendered_lines).strip() if applied else ""
        if rendered_context and len(rendered_context) > self.MAX_RENDERED_CHARS:
            rendered_context = rendered_context[: self.MAX_RENDERED_CHARS].rstrip() + "..."
        preferences_used_ids = [item.preference_id for item in applied]
        preferences_used_types = [item.preference_type for item in applied]
        application_state = (
            ("corpus" if corpus_context_present else "no_corpus")
            + "_"
            + ("preferences" if applied else "no_preferences")
        )
        request_trace = {
            "preferences_used": bool(applied),
            "preference_ids": preferences_used_ids,
            "preference_types": preferences_used_types,
            "preference_scope": [item.scope for item in applied],
            "preferences_omitted": omitted,
            "conflicts": conflicts,
            "current_user_override": bool(current_user_instruction and _infer_length_direction(current_user_instruction) is not None),
            "project_override": bool(project_instruction and _infer_length_direction(project_instruction) is not None),
            "application_state": application_state,
            "corpus_context_present": corpus_context_present,
            "confirmed_preferences_present": bool(confirmed_preferences),
        }
        bundle_fingerprint = _stable_id(
            creator_id,
            workflow_type,
            project_id or "",
            current_user_instruction or "",
            project_instruction or "",
            _json_dumps(primary_artifact_metadata or {}),
            _json_dumps(request_trace),
        )
        return CreatorPreferenceApplicationBundle(
            creator_id=creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            current_user_instruction=current_user_instruction,
            project_instruction=project_instruction,
            primary_artifact_metadata=dict(primary_artifact_metadata or {}),
            corpus_context_present=corpus_context_present,
            corpus_context_item_count=int(corpus_context_item_count),
            confirmed_preferences_present=bool(confirmed_preferences),
            applied_preferences=tuple(applied),
            omitted_preferences=tuple(omitted),
            conflicts=tuple(conflicts),
            rendered_context=rendered_context,
            preferences_used_count=len(applied),
            preferences_omitted_count=len(omitted),
            conflict_count=len(conflicts),
            application_state=application_state,
            request_trace=request_trace,
            bundle_fingerprint=bundle_fingerprint,
            created_at=utc_now(),
        )

    def render_prompt(self, bundle: CreatorPreferenceApplicationBundle) -> str:
        if not bundle.rendered_context:
            return ""
        return bundle.rendered_context.strip()

    def diagnostics(
        self,
        *,
        creator_id: str,
        workflow_type: str,
        project_id: str | None = None,
        current_user_instruction: str | None = None,
        project_instruction: str | None = None,
        primary_artifact_metadata: dict[str, object] | None = None,
        corpus_context_present: bool = False,
        corpus_context_item_count: int = 0,
    ) -> dict[str, object]:
        bundle = self.build_application_bundle(
            creator_id=creator_id,
            workflow_type=workflow_type,
            project_id=project_id,
            current_user_instruction=current_user_instruction,
            project_instruction=project_instruction,
            primary_artifact_metadata=primary_artifact_metadata,
            corpus_context_present=corpus_context_present,
            corpus_context_item_count=corpus_context_item_count,
        )
        return {
            "bundle": bundle.to_dict(),
            "matrix": (
                {
                    "state": "no_corpus_no_preferences",
                    "corpus_context_present": False,
                    "confirmed_preferences_present": False,
                },
                {
                    "state": "corpus_no_preferences",
                    "corpus_context_present": True,
                    "confirmed_preferences_present": False,
                },
                {
                    "state": "no_corpus_preferences",
                    "corpus_context_present": False,
                    "confirmed_preferences_present": True,
                },
                {
                    "state": "corpus_preferences",
                    "corpus_context_present": True,
                    "confirmed_preferences_present": True,
                },
            ),
        }


def build_creator_preference_application_service(
    *,
    repository: CreatorPreferenceRepository,
    logger: logging.Logger | None = None,
) -> CreatorPreferenceApplicationService:
    return CreatorPreferenceApplicationService(repository=repository, logger=logger)
