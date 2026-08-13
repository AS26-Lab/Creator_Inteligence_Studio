"""Deterministic synthesis and confirmation for creator preferences."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.application.services.creator_feedback_service import CreatorFeedbackService
from creator_intelligence_studio.domain.creator_feedback import (
    CreatorLearningSignal,
    CreatorLearningSignalStatus,
    CreatorLearningSignalType,
)
from creator_intelligence_studio.domain.creator_preferences import (
    CreatorConfirmedPreference,
    CreatorPreferenceCandidate,
    CreatorPreferenceCandidateEvidence,
    CreatorPreferenceCandidateStatus,
    CreatorPreferenceConfidence,
    CreatorPreferenceRepository,
    CreatorPreferenceScope,
    CreatorPreferenceSnapshot,
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


def _confidence_from_counts(evidence_count: int, conflict_count: int) -> CreatorPreferenceConfidence:
    if evidence_count >= 5 and conflict_count == 0:
        return CreatorPreferenceConfidence.HIGH
    if evidence_count >= 3 and conflict_count == 0:
        return CreatorPreferenceConfidence.MEDIUM
    return CreatorPreferenceConfidence.LOW


def _status_from_counts(evidence_count: int, conflict_count: int, dismissed_evidence_count: int) -> CreatorPreferenceCandidateStatus:
    if dismissed_evidence_count and evidence_count < dismissed_evidence_count + 2:
        return CreatorPreferenceCandidateStatus.DISMISSED
    if evidence_count >= 3 and conflict_count == 0:
        return CreatorPreferenceCandidateStatus.CANDIDATE
    return CreatorPreferenceCandidateStatus.OBSERVED


def _scope_from_signal(signal: CreatorLearningSignal) -> CreatorPreferenceScope:
    return CreatorPreferenceScope(signal.scope.value)


class CreatorPreferenceSynthesisService:
    ALGORITHM_VERSION = "creator-preference-synthesis-v1"
    MIN_EVIDENCE_COUNT = 3
    RECONSIDERATION_EVIDENCE_DELTA = 2

    def __init__(
        self,
        *,
        repository: CreatorPreferenceRepository,
        feedback_service: CreatorFeedbackService,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.feedback_service = feedback_service
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_preferences")

    @staticmethod
    def audit_supported_signal_matrix() -> tuple[dict[str, object], ...]:
        return (
            {
                "signal_type": "length_change",
                "can_synthesize": True,
                "required_evidence": "3 independent consistent events",
                "scope": "creator_global/project_specific/workflow_specific",
                "safe_human_wording": "He notado que sueles acortar o ampliar los textos.",
                "why": "La evidencia es estructural y no infiere rasgos subjetivos.",
            },
            {
                "signal_type": "acceptance",
                "can_synthesize": False,
                "required_evidence": "N/A",
                "scope": "N/A",
                "safe_human_wording": "No sintetiza por si sola.",
                "why": "Aceptar un resultado no prueba una preferencia estructural.",
            },
            {
                "signal_type": "rejection",
                "can_synthesize": False,
                "required_evidence": "N/A",
                "scope": "N/A",
                "safe_human_wording": "No sintetiza por si sola.",
                "why": "Rechazar no revela la causa de la decisión.",
            },
        )

    def _preference_key(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str | None,
        preference_type: CreatorPreferenceType,
    ) -> str:
        payload = _json_dumps(
            {
                "creator_id": creator_id,
                "project_id": project_id,
                "workflow_type": workflow_type,
                "preference_type": preference_type.value,
            }
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _candidate_key(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str | None,
        preference_type: CreatorPreferenceType,
        proposed_value: str,
    ) -> str:
        payload = _json_dumps(
            {
                "creator_id": creator_id,
                "project_id": project_id,
                "workflow_type": workflow_type,
                "preference_type": preference_type.value,
                "proposed_value": proposed_value,
            }
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _candidate_explanation(
        self,
        *,
        scope: CreatorPreferenceScope,
        preference_type: CreatorPreferenceType,
        proposed_value: str,
        evidence_count: int,
        supporting_signal_count: int,
        conflicting_signal_count: int,
        project_id: str | None,
        workflow_type: str | None,
    ) -> dict[str, object]:
        scope_label = {
            CreatorPreferenceScope.CREATOR_GLOBAL: "para todos tus proyectos",
            CreatorPreferenceScope.PROJECT_SPECIFIC: "solo para este proyecto",
            CreatorPreferenceScope.WORKFLOW_SPECIFIC: "solo para este flujo de trabajo",
        }[scope]
        if preference_type == CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE:
            if proposed_value == "shorter":
                summary = "He notado que sueles acortar los textos."
            else:
                summary = "He notado que sueles ampliar los textos."
        else:
            summary = "He notado un patron estructural repetido."
        evidence_summary = f"Basado en {evidence_count} eventos consistentes y {supporting_signal_count} señales."
        if conflicting_signal_count:
            evidence_summary += f" Hay {conflicting_signal_count} señales en conflicto."
        return {
            "summary": summary,
            "evidence_summary": evidence_summary,
            "scope_label": scope_label,
            "project_id": project_id,
            "workflow_type": workflow_type,
            "preference_type": preference_type.value,
            "proposed_value": proposed_value,
            "safe_human_wording": summary,
        }

    def _supported_candidates_from_signals(
        self,
        creator_id: str,
        signals: list[CreatorLearningSignal],
    ) -> list[dict[str, object]]:
        grouped: dict[tuple[str | None, str | None, CreatorPreferenceType, str], list[CreatorLearningSignal]] = defaultdict(list)
        for signal in signals:
            if signal.status == CreatorLearningSignalStatus.DISMISSED:
                continue
            if signal.signal_type != CreatorLearningSignalType.LENGTH_CHANGE:
                continue
            if signal.signal_value not in {"shorter", "longer"}:
                continue
            preference_type = CreatorPreferenceType.CONTENT_LENGTH_PREFERENCE
            key = (signal.project_id, signal.workflow_type, preference_type, signal.signal_value)
            grouped[key].append(signal)

        value_support: dict[tuple[str | None, str | None, CreatorPreferenceType], dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for (project_id, workflow_type, preference_type, value), signal_list in grouped.items():
            key = (project_id, workflow_type, preference_type)
            evidence_ids: set[str] = set()
            signal_ids: set[str] = set()
            first_observed_at = None
            last_observed_at = None
            for signal in signal_list:
                signal_ids.add(signal.id)
                for evidence in self.feedback_service.repository.list_learning_signal_evidence(signal.id):
                    evidence_ids.add(evidence.feedback_event_id)
                if first_observed_at is None or signal.first_observed_at < first_observed_at:
                    first_observed_at = signal.first_observed_at
                if last_observed_at is None or signal.last_observed_at > last_observed_at:
                    last_observed_at = signal.last_observed_at
            value_support[key][value] = len(evidence_ids)
        results: list[dict[str, object]] = []
        for (project_id, workflow_type, preference_type, value), signal_list in grouped.items():
            key = (project_id, workflow_type, preference_type)
            supporting_events: set[str] = set()
            supporting_signal_ids: list[str] = []
            first_observed_at = None
            last_observed_at = None
            for signal in signal_list:
                supporting_signal_ids.append(signal.id)
                if first_observed_at is None or signal.first_observed_at < first_observed_at:
                    first_observed_at = signal.first_observed_at
                if last_observed_at is None or signal.last_observed_at > last_observed_at:
                    last_observed_at = signal.last_observed_at
                for evidence in self.feedback_service.repository.list_learning_signal_evidence(signal.id):
                    supporting_events.add(evidence.feedback_event_id)
            conflicting_signal_count = sum(
                count
                for other_value, count in value_support[key].items()
                if other_value != value
            )
            evidence_count = len(supporting_events)
            dismissed_evidence_count = 0
            candidate_key = self._candidate_key(
                creator_id=creator_id,
                project_id=project_id,
                workflow_type=workflow_type,
                preference_type=preference_type,
                proposed_value=value,
            )
            existing = self.repository.get_candidate_by_key(candidate_key)
            if existing is not None and existing.status == CreatorPreferenceCandidateStatus.DISMISSED:
                dismissed_evidence_count = existing.dismissed_evidence_count or existing.evidence_count
            status = _status_from_counts(evidence_count, conflicting_signal_count, dismissed_evidence_count)
            if existing is not None and (existing.status == CreatorPreferenceCandidateStatus.CONFIRMED or existing.confirmed_preference_id):
                status = CreatorPreferenceCandidateStatus.CONFIRMED
            confidence = _confidence_from_counts(evidence_count, conflicting_signal_count)
            explanation = self._candidate_explanation(
                scope=_scope_from_signal(signal_list[0]),
                preference_type=preference_type,
                proposed_value=value,
                evidence_count=evidence_count,
                supporting_signal_count=len(signal_list),
                conflicting_signal_count=conflicting_signal_count,
                project_id=project_id,
                workflow_type=workflow_type,
            )
            results.append(
                {
                    "candidate_key": candidate_key,
                    "creator_id": creator_id,
                    "project_id": project_id,
                    "workflow_type": workflow_type,
                    "scope": _scope_from_signal(signal_list[0]),
                    "preference_type": preference_type,
                    "proposed_value": value,
                    "evidence_count": evidence_count,
                    "supporting_signal_count": len(signal_list),
                    "conflicting_signal_count": conflicting_signal_count,
                    "confidence": confidence,
                    "status": status,
                    "dismissed_evidence_count": dismissed_evidence_count,
                    "source_signal_ids_json": _json_dumps(supporting_signal_ids),
                    "explanation_json": _json_dumps(explanation),
                    "algorithm_version": self.ALGORITHM_VERSION,
                    "first_observed_at": first_observed_at or utc_now(),
                    "last_observed_at": last_observed_at or utc_now(),
                }
            )
        return results

    def _synthesize_for_creator(self, creator_id: str) -> list[CreatorPreferenceCandidate]:
        signals = self.feedback_service.list_learning_signals(creator_id, limit=10000)
        candidates_payload = self._supported_candidates_from_signals(creator_id, signals)
        persisted: list[CreatorPreferenceCandidate] = []
        now = utc_now()
        for payload in candidates_payload:
            existing = self.repository.get_candidate_by_key(payload["candidate_key"])
            candidate = CreatorPreferenceCandidate(
                id=existing.id if existing else str(uuid4()),
                candidate_key=payload["candidate_key"],
                creator_id=creator_id,
                project_id=payload["project_id"],
                workflow_type=payload["workflow_type"],
                scope=payload["scope"],
                preference_type=payload["preference_type"],
                proposed_value=payload["proposed_value"],
                evidence_count=payload["evidence_count"],
                supporting_signal_count=payload["supporting_signal_count"],
                conflicting_signal_count=payload["conflicting_signal_count"],
                confidence=payload["confidence"],
                status=payload["status"],
                dismissed_evidence_count=payload["dismissed_evidence_count"],
                source_signal_ids_json=payload["source_signal_ids_json"],
                explanation_json=payload["explanation_json"],
                algorithm_version=payload["algorithm_version"],
                first_observed_at=payload["first_observed_at"],
                last_observed_at=payload["last_observed_at"],
                confirmed_preference_id=existing.confirmed_preference_id if existing else None,
                created_at=existing.created_at if existing else now,
                updated_at=now,
            )
            persisted_candidate = self.repository.upsert_candidate(candidate)
            persisted.append(persisted_candidate)
            for signal_id in json.loads(candidate.source_signal_ids_json or "[]"):
                self.repository.upsert_candidate_evidence(
                    CreatorPreferenceCandidateEvidence(
                        id=str(uuid4()),
                        candidate_id=persisted_candidate.id,
                        learning_signal_id=signal_id,
                        created_at=now,
                    )
                )
        return persisted

    def rebuild_candidates(self, creator_id: str) -> list[CreatorPreferenceCandidate]:
        return self._synthesize_for_creator(creator_id)

    def synthesize_candidates(
        self,
        creator_id: str,
        *,
        project_id: str | None = None,
        workflow_type: str | None = None,
    ) -> list[CreatorPreferenceCandidate]:
        candidates = self._synthesize_for_creator(creator_id)
        filtered = []
        for candidate in candidates:
            if project_id is not None and candidate.project_id != project_id:
                continue
            if workflow_type is not None and candidate.workflow_type != workflow_type:
                continue
            filtered.append(candidate)
        return filtered

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
        return self.repository.list_candidates(
            creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            status=status,
            preference_type=preference_type,
            limit=limit,
            offset=offset,
        )

    def get_candidate(self, candidate_id: str) -> CreatorPreferenceCandidate | None:
        return self.repository.get_candidate_by_id(candidate_id)

    def confirm_candidate(
        self,
        candidate_id: str,
        *,
        confirmed_by: str,
        edited_value: str | dict[str, object] | None = None,
    ) -> CreatorConfirmedPreference:
        candidate = self.repository.get_candidate_by_id(candidate_id)
        if candidate is None:
            raise ValueError("La sugerencia no existe.")
        now = utc_now()
        preference_key = self._preference_key(
            creator_id=candidate.creator_id,
            project_id=candidate.project_id,
            workflow_type=candidate.workflow_type,
            preference_type=candidate.preference_type,
        )
        existing = self.repository.get_confirmed_preference_by_key(preference_key)
        if edited_value is None:
            value_payload: object = {
                "preference_type": candidate.preference_type.value,
                "direction": candidate.proposed_value,
                "source": "candidate",
            }
            provenance = {
                "origin": "candidate",
                "candidate_id": candidate.id,
                "candidate_key": candidate.candidate_key,
                "edited": False,
            }
        else:
            value_payload = {
                "preference_type": candidate.preference_type.value,
                "direction": candidate.proposed_value,
                "raw_text": edited_value,
                "source": "user_edit",
            }
            provenance = {
                "origin": "user_edit",
                "candidate_id": candidate.id,
                "candidate_key": candidate.candidate_key,
                "edited": True,
            }
        confirmed = CreatorConfirmedPreference(
            id=(existing.id if existing else str(uuid4())),
            preference_key=preference_key,
            creator_id=candidate.creator_id,
            project_id=candidate.project_id,
            workflow_type=candidate.workflow_type,
            scope=candidate.scope,
            preference_type=candidate.preference_type,
            value_json=_json_dumps(value_payload),
            source_candidate_id=candidate.id,
            confirmed_by=confirmed_by,
            confirmed_at=now,
            active=True,
            provenance_json=_json_dumps(provenance),
            created_at=(existing.created_at if existing else now),
            updated_at=now,
        )
        persisted = self.repository.upsert_confirmed_preference(confirmed)
        self.repository.upsert_candidate(
            replace(
                candidate,
                status=CreatorPreferenceCandidateStatus.CONFIRMED,
                confirmed_preference_id=persisted.id,
                updated_at=now,
                explanation_json=_json_dumps(
                    {
                        **_json_loads(candidate.explanation_json, {}),
                        "confirmed_preference_id": persisted.id,
                        "confirmed_by": confirmed_by,
                    }
                ),
            )
        )
        return persisted

    def edit_and_confirm_candidate(
        self,
        candidate_id: str,
        *,
        confirmed_by: str,
        edited_value: str,
    ) -> CreatorConfirmedPreference:
        return self.confirm_candidate(candidate_id, confirmed_by=confirmed_by, edited_value=edited_value)

    def dismiss_candidate(self, candidate_id: str, *, dismissed_by: str, reason: str) -> CreatorPreferenceCandidate:
        candidate = self.repository.get_candidate_by_id(candidate_id)
        if candidate is None:
            raise ValueError("La sugerencia no existe.")
        now = utc_now()
        dismissed = replace(
            candidate,
            status=CreatorPreferenceCandidateStatus.DISMISSED,
            dismissed_evidence_count=candidate.evidence_count,
            explanation_json=_json_dumps({**_json_loads(candidate.explanation_json, {}), "dismissed_by": dismissed_by, "dismiss_reason": reason}),
            updated_at=now,
        )
        return self.repository.upsert_candidate(dismissed)

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
        return self.repository.list_confirmed_preferences(
            creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            active=active,
            preference_type=preference_type,
            limit=limit,
            offset=offset,
        )

    def deactivate_preference(self, preference_id: str) -> CreatorConfirmedPreference | None:
        return self.repository.deactivate_confirmed_preference(preference_id)

    def reactivate_preference(self, preference_id: str) -> CreatorConfirmedPreference | None:
        return self.repository.reactivate_confirmed_preference(preference_id)

    def preference_snapshot(self, creator_id: str) -> CreatorPreferenceSnapshot:
        candidates = self.list_candidates(creator_id, limit=1000)
        confirmed = self.list_confirmed_preferences(creator_id, limit=1000)
        return CreatorPreferenceSnapshot(
            creator_id=creator_id,
            generated_at=utc_now(),
            candidate_count=len(candidates),
            active_candidate_count=sum(1 for item in candidates if item.status in {CreatorPreferenceCandidateStatus.OBSERVED, CreatorPreferenceCandidateStatus.CANDIDATE, CreatorPreferenceCandidateStatus.CONFIRMED}),
            confirmed_count=len(confirmed),
            active_confirmed_count=sum(1 for item in confirmed if item.active),
            dismissed_candidate_count=sum(1 for item in candidates if item.status == CreatorPreferenceCandidateStatus.DISMISSED),
            conflict_count=sum(1 for item in candidates if item.conflicting_signal_count > 0),
            candidates=tuple(item.to_dict() for item in candidates),
            confirmed_preferences=tuple(item.to_dict() for item in confirmed),
        )

    def health(self, creator_id: str) -> dict[str, object]:
        snapshot = self.preference_snapshot(creator_id)
        return {
            "creator_id": creator_id,
            "candidate_count": snapshot.candidate_count,
            "active_candidate_count": snapshot.active_candidate_count,
            "confirmed_count": snapshot.confirmed_count,
            "active_confirmed_count": snapshot.active_confirmed_count,
            "dismissed_candidate_count": snapshot.dismissed_candidate_count,
            "conflict_count": snapshot.conflict_count,
        }


def build_creator_preference_synthesis_service(
    *,
    repository: CreatorPreferenceRepository,
    feedback_service: CreatorFeedbackService,
    logger: logging.Logger | None = None,
) -> CreatorPreferenceSynthesisService:
    return CreatorPreferenceSynthesisService(repository=repository, feedback_service=feedback_service, logger=logger)
