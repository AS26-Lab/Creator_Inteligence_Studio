"""Creator-scoped feedback capture and conservative learning signals."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from hashlib import sha256
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.content_briefs.entities import BriefRecord
from creator_intelligence_studio.domain.creator_feedback import (
    CreatorFeedbackEvent,
    CreatorFeedbackEventSource,
    CreatorFeedbackEventType,
    CreatorFeedbackExplicitness,
    CreatorFeedbackRepository,
    CreatorFeedbackScope,
    CreatorLearningSignal,
    CreatorLearningSignalConfidence,
    CreatorLearningSignalEvidence,
    CreatorLearningSignalPolarity,
    CreatorLearningSignalStatus,
    CreatorLearningSignalType,
    CreatorLearningSnapshot,
)
from creator_intelligence_studio.domain.projects.entities import Project
from creator_intelligence_studio.domain.projects.repositories import ProjectRepository
from creator_intelligence_studio.shared.dates import from_iso_z, utc_now

from .creator_revision_diff_service import CreatorRevisionDiffService, CreatorRevisionDiffSummary


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _json_loads(payload: str | None, fallback: dict[str, object] | list[object]) -> dict[str, object] | list[object]:
    if not payload:
        return fallback
    try:
        value = json.loads(payload)
        return fallback if value is None else value
    except json.JSONDecodeError:
        return fallback


def _normalize_enum(value: Any, enum_cls, default):
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    try:
        return enum_cls(str(value))
    except Exception:
        return default


def _creator_scoped_scope(project_id: str | None, workflow_type: str | None) -> CreatorFeedbackScope:
    if project_id is not None:
        return CreatorFeedbackScope.PROJECT_SPECIFIC
    if workflow_type is not None:
        return CreatorFeedbackScope.WORKFLOW_SPECIFIC
    return CreatorFeedbackScope.CREATOR_GLOBAL


def _signal_defaults(signal_type: CreatorLearningSignalType, signal_value: str) -> tuple[CreatorLearningSignalPolarity, float]:
    mapping: dict[CreatorLearningSignalType, tuple[CreatorLearningSignalPolarity, float]] = {
        CreatorLearningSignalType.ACCEPTANCE: (CreatorLearningSignalPolarity.POSITIVE, 0.8),
        CreatorLearningSignalType.REJECTION: (CreatorLearningSignalPolarity.NEGATIVE, 1.0),
        CreatorLearningSignalType.REGENERATION: (CreatorLearningSignalPolarity.NEGATIVE, 0.7),
        CreatorLearningSignalType.EDIT_FREQUENCY: (CreatorLearningSignalPolarity.NEUTRAL, 0.5),
        CreatorLearningSignalType.LENGTH_CHANGE: (CreatorLearningSignalPolarity.NEUTRAL, 0.4),
        CreatorLearningSignalType.CONTENT_REMOVED: (CreatorLearningSignalPolarity.NEUTRAL, 0.6),
        CreatorLearningSignalType.CONTENT_ADDED: (CreatorLearningSignalPolarity.NEUTRAL, 0.6),
        CreatorLearningSignalType.VERSION_ADOPTION: (CreatorLearningSignalPolarity.POSITIVE if signal_value == "adopted" else CreatorLearningSignalPolarity.NEUTRAL, 0.75),
    }
    return mapping.get(signal_type, (CreatorLearningSignalPolarity.NEUTRAL, 0.4))


def _confidence_from_counts(evidence_count: int, contradicting_count: int) -> CreatorLearningSignalConfidence:
    if evidence_count >= 5 and contradicting_count == 0:
        return CreatorLearningSignalConfidence.HIGH
    if evidence_count >= 3 and contradicting_count <= 1:
        return CreatorLearningSignalConfidence.MEDIUM
    return CreatorLearningSignalConfidence.LOW


def _status_from_counts(evidence_count: int, dismissed: bool) -> CreatorLearningSignalStatus:
    if dismissed:
        return CreatorLearningSignalStatus.DISMISSED
    if evidence_count >= 3:
        return CreatorLearningSignalStatus.CANDIDATE
    return CreatorLearningSignalStatus.OBSERVED


def _artifact_type_from_workflow(workflow_type: str) -> str:
    mapping = {
        "content_brief": "content_brief",
        "production_preparation": "script_outline",
        "strategic_planning": "strategic_plan",
    }
    return mapping.get(workflow_type, workflow_type)


class CreatorFeedbackService:
    def __init__(
        self,
        *,
        repository: CreatorFeedbackRepository,
        project_repository: ProjectRepository | None = None,
        brief_service: Any | None = None,
        production_service: Any | None = None,
        planning_service: Any | None = None,
        ai_runtime_service: Any | None = None,
        diff_service: CreatorRevisionDiffService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.brief_service = brief_service
        self.production_service = production_service
        self.planning_service = planning_service
        self.ai_runtime_service = ai_runtime_service
        self.diff_service = diff_service or CreatorRevisionDiffService()
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_feedback")

    def _project_for(self, creator_id: str, project_id: str | None) -> Project | None:
        if project_id is None:
            return None
        if self.project_repository is None:
            raise ValueError("Se requiere repositorio de proyectos para validar project_id.")
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ValueError("El proyecto no existe.")
        if project.creator_id != creator_id:
            raise ValueError("El proyecto no pertenece al creador indicado.")
        return project

    def _brief_for(self, brief_id: str) -> BriefRecord:
        if self.brief_service is None:
            raise ValueError("Se requiere content_brief_service para validar el brief.")
        brief = self.brief_service.get_brief(brief_id)
        if brief is None:
            raise ValueError("El brief no existe.")
        return brief

    def _outline_for(self, outline_id: str):
        if self.production_service is None:
            raise ValueError("Se requiere production_service para validar el outline.")
        outline = self.production_service.get_outline(outline_id)
        if outline is None:
            raise ValueError("El outline no existe.")
        return outline

    def _plan_for(self, plan_id: str):
        if self.planning_service is None:
            raise ValueError("Se requiere strategic_planning_service para validar el plan.")
        plan = self.planning_service.get_plan(plan_id)
        if plan is None:
            raise ValueError("El plan no existe.")
        return plan

    def _execution_for(self, execution_id: str):
        if self.ai_runtime_service is None:
            raise ValueError("Se requiere ai_runtime_service para validar la ejecucion.")
        execution = self.ai_runtime_service.get_execution(execution_id)
        if execution is None:
            raise ValueError("La ejecucion AI no existe.")
        return execution

    def _validate_artifact_ownership(
        self,
        *,
        creator_id: str,
        artifact_type: str,
        artifact_id: str,
        source_version_id: str | None,
        result_version_id: str | None,
        ai_execution_id: str | None,
    ) -> None:
        if artifact_type == "content_brief":
            brief = self._brief_for(artifact_id)
            if brief.creator_id != creator_id:
                raise ValueError("El brief no pertenece al creador indicado.")
            if source_version_id is not None:
                source = self._brief_for(source_version_id)
                if source.creator_id != creator_id:
                    raise ValueError("La version origen no pertenece al creador indicado.")
            if result_version_id is not None:
                result = self._brief_for(result_version_id)
                if result.creator_id != creator_id:
                    raise ValueError("La version resultado no pertenece al creador indicado.")
        elif artifact_type == "script_outline":
            outline = self._outline_for(artifact_id)
            if outline.creator_id != creator_id:
                raise ValueError("El outline no pertenece al creador indicado.")
            if source_version_id is not None:
                source = self._outline_for(source_version_id)
                if source.creator_id != creator_id:
                    raise ValueError("La version origen no pertenece al creador indicado.")
            if result_version_id is not None:
                result = self._outline_for(result_version_id)
                if result.creator_id != creator_id:
                    raise ValueError("La version resultado no pertenece al creador indicado.")
        elif artifact_type == "strategic_plan":
            plan = self._plan_for(artifact_id)
            if plan.creator_id != creator_id:
                raise ValueError("El plan no pertenece al creador indicado.")
            if source_version_id is not None:
                source = self._plan_for(source_version_id)
                if source.creator_id != creator_id:
                    raise ValueError("La version origen no pertenece al creador indicado.")
            if result_version_id is not None:
                result = self._plan_for(result_version_id)
                if result.creator_id != creator_id:
                    raise ValueError("La version resultado no pertenece al creador indicado.")
        elif artifact_type == "ai_execution":
            execution = self._execution_for(artifact_id)
            if execution.creator_id != creator_id:
                raise ValueError("La ejecucion AI no pertenece al creador indicado.")
            if ai_execution_id is not None and ai_execution_id != artifact_id:
                linked = self._execution_for(ai_execution_id)
                if linked.creator_id != creator_id:
                    raise ValueError("La ejecucion vinculada no pertenece al creador indicado.")

    def _dedupe_key(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        workflow_type: str,
        artifact_type: str,
        artifact_id: str,
        source_version_id: str | None,
        result_version_id: str | None,
        ai_execution_id: str | None,
        event_type: CreatorFeedbackEventType,
        event_source: CreatorFeedbackEventSource,
        signal_explicitness: CreatorFeedbackExplicitness,
    ) -> str:
        payload = _json_dumps(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "ai_execution_id": ai_execution_id,
                "creator_id": creator_id,
                "event_source": event_source.value,
                "event_type": event_type.value,
                "project_id": project_id,
                "result_version_id": result_version_id,
                "signal_explicitness": signal_explicitness.value,
                "source_version_id": source_version_id,
                "workflow_type": workflow_type,
            }
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _event_from_payload(self, row: dict[str, object]) -> CreatorFeedbackEvent:
        return CreatorFeedbackEvent(
            id=str(row["id"]),
            dedupe_key=str(row["dedupe_key"]),
            creator_id=str(row["creator_id"]),
            project_id=row.get("project_id") if row.get("project_id") is not None else None,
            workflow_type=str(row["workflow_type"]),
            artifact_type=str(row["artifact_type"]),
            artifact_id=str(row["artifact_id"]),
            source_version_id=row.get("source_version_id") if row.get("source_version_id") is not None else None,
            result_version_id=row.get("result_version_id") if row.get("result_version_id") is not None else None,
            ai_execution_id=row.get("ai_execution_id") if row.get("ai_execution_id") is not None else None,
            event_type=_normalize_enum(row.get("event_type"), CreatorFeedbackEventType, CreatorFeedbackEventType.EDITED),
            event_source=_normalize_enum(row.get("event_source"), CreatorFeedbackEventSource, CreatorFeedbackEventSource.WORKFLOW_ACTION),
            signal_explicitness=_normalize_enum(row.get("signal_explicitness"), CreatorFeedbackExplicitness, CreatorFeedbackExplicitness.BEHAVIORAL),
            created_at=from_iso_z(str(row["created_at"])) or utc_now(),
            metadata_json=str(row.get("metadata_json") or "{}"),
        )

    def _signal_from_payload(self, row: dict[str, object]) -> CreatorLearningSignal:
        return CreatorLearningSignal(
            id=str(row["id"]),
            creator_id=str(row["creator_id"]),
            project_id=row.get("project_id") if row.get("project_id") is not None else None,
            workflow_type=row.get("workflow_type") if row.get("workflow_type") is not None else None,
            scope=_normalize_enum(row.get("scope"), CreatorFeedbackScope, CreatorFeedbackScope.CREATOR_GLOBAL),
            signal_type=_normalize_enum(row.get("signal_type"), CreatorLearningSignalType, CreatorLearningSignalType.EDIT_FREQUENCY),
            signal_value=str(row.get("signal_value") or ""),
            polarity=_normalize_enum(row.get("polarity"), CreatorLearningSignalPolarity, CreatorLearningSignalPolarity.NEUTRAL),
            strength=float(row.get("strength") or 0.0),
            confidence=_normalize_enum(row.get("confidence"), CreatorLearningSignalConfidence, CreatorLearningSignalConfidence.LOW),
            evidence_count=int(row.get("evidence_count") or 0),
            supporting_event_count=int(row.get("supporting_event_count") or 0),
            contradicting_event_count=int(row.get("contradicting_event_count") or 0),
            status=_normalize_enum(row.get("status"), CreatorLearningSignalStatus, CreatorLearningSignalStatus.OBSERVED),
            first_observed_at=from_iso_z(str(row["first_observed_at"])) or utc_now(),
            last_observed_at=from_iso_z(str(row["last_observed_at"])) or utc_now(),
            algorithm_version=str(row.get("algorithm_version") or CreatorRevisionDiffService.ALGORITHM_VERSION),
            metadata_json=str(row.get("metadata_json") or "{}"),
            created_at=from_iso_z(str(row["created_at"])) or utc_now(),
            updated_at=from_iso_z(str(row["updated_at"])) or utc_now(),
        )

    def _resolve_event(self, event_id: str | None = None, *, dedupe_key: str | None = None) -> CreatorFeedbackEvent | None:
        if event_id is not None:
            row = self.repository.get_feedback_event_by_id(event_id)
            return row
        if dedupe_key is not None:
            return self.repository.get_feedback_event_by_dedupe_key(dedupe_key)
        return None

    def _event_metadata(self, metadata: dict[str, object] | None) -> str:
        return _json_dumps(metadata or {})

    def _signal_metadata(self, metadata: dict[str, object] | None) -> str:
        return _json_dumps(metadata or {})

    def _observations_for_event(
        self,
        event: CreatorFeedbackEvent,
        *,
        metadata: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        observations: list[dict[str, object]] = []
        scope = _creator_scoped_scope(event.project_id, event.workflow_type)
        if event.event_type == CreatorFeedbackEventType.ACCEPTED:
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.ACCEPTANCE,
                    "signal_value": "accepted",
                    "polarity": CreatorLearningSignalPolarity.POSITIVE,
                    "strength": 0.8,
                    "scope": scope,
                }
            )
        elif event.event_type == CreatorFeedbackEventType.REJECTED:
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.REJECTION,
                    "signal_value": "rejected",
                    "polarity": CreatorLearningSignalPolarity.NEGATIVE,
                    "strength": 1.0,
                    "scope": scope,
                }
            )
        elif event.event_type == CreatorFeedbackEventType.REGENERATED:
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.REGENERATION,
                    "signal_value": "regenerated",
                    "polarity": CreatorLearningSignalPolarity.NEGATIVE,
                    "strength": 0.7,
                    "scope": scope,
                }
            )
        elif event.event_type == CreatorFeedbackEventType.ADOPTED:
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.VERSION_ADOPTION,
                    "signal_value": "adopted",
                    "polarity": CreatorLearningSignalPolarity.POSITIVE,
                    "strength": 0.75,
                    "scope": scope,
                }
            )
        elif event.event_type == CreatorFeedbackEventType.SUPERSEDED:
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.VERSION_ADOPTION,
                    "signal_value": "superseded",
                    "polarity": CreatorLearningSignalPolarity.NEUTRAL,
                    "strength": 0.6,
                    "scope": scope,
                }
            )
        elif event.event_type == CreatorFeedbackEventType.EDITED:
            diff_metadata = metadata or _json_loads(event.metadata_json, {})
            diff_summary = diff_metadata.get("diff_summary") if isinstance(diff_metadata, dict) else None
            if not isinstance(diff_summary, dict):
                raise ValueError("Los eventos editados requieren un diff estructurado.")
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.EDIT_FREQUENCY,
                    "signal_value": "edited",
                    "polarity": CreatorLearningSignalPolarity.NEUTRAL,
                    "strength": 0.5,
                    "scope": scope,
                    "metadata": {"diff_summary": diff_summary},
                }
            )
            length_direction = str(diff_summary.get("length_direction") or "stable")
            observations.append(
                {
                    "signal_type": CreatorLearningSignalType.LENGTH_CHANGE,
                    "signal_value": length_direction,
                    "polarity": CreatorLearningSignalPolarity.NEUTRAL,
                    "strength": 0.4,
                    "scope": scope,
                    "metadata": {"diff_summary": diff_summary},
                }
            )
            if int(diff_summary.get("deletions") or 0) > 0:
                observations.append(
                    {
                        "signal_type": CreatorLearningSignalType.CONTENT_REMOVED,
                        "signal_value": "removed",
                        "polarity": CreatorLearningSignalPolarity.NEUTRAL,
                        "strength": 0.6,
                        "scope": scope,
                        "metadata": {"diff_summary": diff_summary},
                    }
                )
            if int(diff_summary.get("insertions") or 0) > 0:
                observations.append(
                    {
                        "signal_type": CreatorLearningSignalType.CONTENT_ADDED,
                        "signal_value": "added",
                        "polarity": CreatorLearningSignalPolarity.NEUTRAL,
                        "strength": 0.6,
                        "scope": scope,
                        "metadata": {"diff_summary": diff_summary},
                    }
                )
        return observations

    def _upsert_signal_for_observation(self, event: CreatorFeedbackEvent, observation: dict[str, object]) -> CreatorLearningSignal:
        signal_type = observation["signal_type"]
        signal_value = str(observation["signal_value"])
        polarity = observation["polarity"]
        scope = observation["scope"]
        strength = float(observation["strength"])
        metadata = observation.get("metadata")
        existing = self.repository.get_learning_signal_by_key(
            creator_id=event.creator_id,
            project_id=event.project_id,
            workflow_type=event.workflow_type,
            scope=scope.value,
            signal_type=signal_type.value,
            signal_value=signal_value,
            polarity=polarity.value,
        )
        now = utc_now()
        if existing is None:
            signal = CreatorLearningSignal(
                id=str(uuid4()),
                creator_id=event.creator_id,
                project_id=event.project_id,
                workflow_type=event.workflow_type,
                scope=scope,
                signal_type=signal_type,
                signal_value=signal_value,
                polarity=polarity,
                strength=strength,
                confidence=CreatorLearningSignalConfidence.LOW,
                evidence_count=1,
                supporting_event_count=1,
                contradicting_event_count=0,
                status=CreatorLearningSignalStatus.OBSERVED,
                first_observed_at=event.created_at,
                last_observed_at=event.created_at,
                algorithm_version=CreatorRevisionDiffService.ALGORITHM_VERSION,
                metadata_json=self._signal_metadata(metadata if isinstance(metadata, dict) else {}),
                created_at=now,
                updated_at=now,
            )
        else:
            evidence_rows = self.repository.list_learning_signal_evidence(existing.id)
            evidence_count = len({row.feedback_event_id for row in evidence_rows} | {event.id})
            contradicting_count = self._contradicting_event_count(existing, event)
            signal = replace(
                existing,
                strength=max(existing.strength, strength),
                confidence=_confidence_from_counts(evidence_count, contradicting_count),
                evidence_count=evidence_count,
                supporting_event_count=evidence_count,
                contradicting_event_count=contradicting_count,
                status=_status_from_counts(evidence_count, existing.status == CreatorLearningSignalStatus.DISMISSED),
                first_observed_at=min(existing.first_observed_at, event.created_at),
                last_observed_at=max(existing.last_observed_at, event.created_at),
                metadata_json=self._signal_metadata(metadata if isinstance(metadata, dict) else _json_loads(existing.metadata_json, {})),
                updated_at=now,
            )
        persisted = self.repository.upsert_learning_signal(signal)
        self.repository.upsert_learning_signal_evidence(
            CreatorLearningSignalEvidence(
                id=str(uuid4()),
                signal_id=persisted.id,
                feedback_event_id=event.id,
                created_at=now,
            )
        )
        evidence_rows = self.repository.list_learning_signal_evidence(persisted.id)
        evidence_count = len({row.feedback_event_id for row in evidence_rows})
        contradicting_count = self._contradicting_event_count(persisted, event)
        refreshed = replace(
            persisted,
            evidence_count=evidence_count,
            supporting_event_count=evidence_count,
            contradicting_event_count=contradicting_count,
            confidence=_confidence_from_counts(evidence_count, contradicting_count),
            status=_status_from_counts(evidence_count, persisted.status == CreatorLearningSignalStatus.DISMISSED),
            updated_at=now,
        )
        return self.repository.upsert_learning_signal(refreshed)

    def _contradicting_event_count(self, signal: CreatorLearningSignal, event: CreatorFeedbackEvent) -> int:
        rows = self.repository.list_learning_signals(
            signal.creator_id,
            project_id=signal.project_id,
            workflow_type=signal.workflow_type,
            status=None,
            signal_type=signal.signal_type.value,
            limit=1000,
            offset=0,
        )
        conflicting = [
            row
            for row in rows
            if row.signal_value != signal.signal_value and row.id != signal.id
        ]
        return len(conflicting)

    def _sync_event_signals(self, event: CreatorFeedbackEvent) -> list[CreatorLearningSignal]:
        observations = self._observations_for_event(event)
        synced: list[CreatorLearningSignal] = []
        for observation in observations:
            synced.append(self._upsert_signal_for_observation(event, observation))
        return synced

    def record_feedback_event(
        self,
        *,
        creator_id: str,
        workflow_type: str,
        artifact_type: str,
        artifact_id: str,
        event_type: CreatorFeedbackEventType | str,
        event_source: CreatorFeedbackEventSource | str | None = None,
        signal_explicitness: CreatorFeedbackExplicitness | str | None = None,
        project_id: str | None = None,
        source_version_id: str | None = None,
        result_version_id: str | None = None,
        ai_execution_id: str | None = None,
        metadata: dict[str, object] | None = None,
        dedupe_key: str | None = None,
    ) -> CreatorFeedbackEvent:
        event_type_enum = _normalize_enum(event_type, CreatorFeedbackEventType, CreatorFeedbackEventType.EDITED)
        event_source_enum = _normalize_enum(
            event_source,
            CreatorFeedbackEventSource,
            CreatorFeedbackEventSource.USER_ACTION if event_type_enum in {CreatorFeedbackEventType.ACCEPTED, CreatorFeedbackEventType.REJECTED, CreatorFeedbackEventType.REGENERATED} else CreatorFeedbackEventSource.VERSION_TRANSITION,
        )
        explicitness_enum = _normalize_enum(
            signal_explicitness,
            CreatorFeedbackExplicitness,
            CreatorFeedbackExplicitness.EXPLICIT if event_source_enum == CreatorFeedbackEventSource.USER_ACTION else CreatorFeedbackExplicitness.BEHAVIORAL,
        )
        project = self._project_for(creator_id, project_id)
        if project is not None and project.creator_id != creator_id:
            raise ValueError("El proyecto no pertenece al creador indicado.")
        self._validate_artifact_ownership(
            creator_id=creator_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            source_version_id=source_version_id,
            result_version_id=result_version_id,
            ai_execution_id=ai_execution_id,
        )
        resolved_metadata = dict(metadata or {})
        if event_type_enum == CreatorFeedbackEventType.EDITED:
            if source_version_id is None or result_version_id is None:
                raise ValueError("Los eventos editados requieren source_version_id y result_version_id.")
            before_text = resolved_metadata.get("source_text")
            after_text = resolved_metadata.get("result_text")
            diff_summary = self.diff_service.summarize(
                before_text if isinstance(before_text, str) else None,
                after_text if isinstance(after_text, str) else None,
            )
            resolved_metadata["diff_summary"] = diff_summary.to_dict()
        resolved_artifact_type = artifact_type or _artifact_type_from_workflow(workflow_type)
        computed_dedupe_key = dedupe_key or self._dedupe_key(
            creator_id=creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            artifact_type=resolved_artifact_type,
            artifact_id=artifact_id,
            source_version_id=source_version_id,
            result_version_id=result_version_id,
            ai_execution_id=ai_execution_id,
            event_type=event_type_enum,
            event_source=event_source_enum,
            signal_explicitness=explicitness_enum,
        )
        existing = self.repository.get_feedback_event_by_dedupe_key(computed_dedupe_key)
        if existing is not None:
            self._sync_event_signals(existing)
            return existing
        event = CreatorFeedbackEvent(
            id=str(uuid4()),
            dedupe_key=computed_dedupe_key,
            creator_id=creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            artifact_type=resolved_artifact_type,
            artifact_id=artifact_id,
            source_version_id=source_version_id,
            result_version_id=result_version_id,
            ai_execution_id=ai_execution_id,
            event_type=event_type_enum,
            event_source=event_source_enum,
            signal_explicitness=explicitness_enum,
            created_at=utc_now(),
            metadata_json=self._event_metadata(resolved_metadata),
        )
        persisted = self.repository.upsert_feedback_event(event)
        self._sync_event_signals(persisted)
        self.logger.info(
            "creator_feedback.event creator_id=%s workflow=%s artifact_type=%s artifact_id=%s event_type=%s project_id=%s",
            creator_id,
            workflow_type,
            resolved_artifact_type,
            artifact_id,
            event_type_enum.value,
            project_id,
        )
        return persisted

    def record_acceptance(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.ACCEPTED, event_source=CreatorFeedbackEventSource.USER_ACTION, signal_explicitness=CreatorFeedbackExplicitness.EXPLICIT, **kwargs)

    def record_rejection(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.REJECTED, event_source=CreatorFeedbackEventSource.USER_ACTION, signal_explicitness=CreatorFeedbackExplicitness.EXPLICIT, **kwargs)

    def record_regeneration(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.REGENERATED, event_source=CreatorFeedbackEventSource.USER_ACTION, signal_explicitness=CreatorFeedbackExplicitness.EXPLICIT, **kwargs)

    def record_adoption(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.ADOPTED, event_source=CreatorFeedbackEventSource.VERSION_TRANSITION, signal_explicitness=CreatorFeedbackExplicitness.BEHAVIORAL, **kwargs)

    def record_supersession(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.SUPERSEDED, event_source=CreatorFeedbackEventSource.VERSION_TRANSITION, signal_explicitness=CreatorFeedbackExplicitness.BEHAVIORAL, **kwargs)

    def record_edit(self, **kwargs) -> CreatorFeedbackEvent:
        return self.record_feedback_event(event_type=CreatorFeedbackEventType.EDITED, event_source=CreatorFeedbackEventSource.VERSION_TRANSITION, signal_explicitness=CreatorFeedbackExplicitness.BEHAVIORAL, **kwargs)

    def get_feedback_event(self, event_id: str) -> CreatorFeedbackEvent | None:
        return self.repository.get_feedback_event_by_id(event_id)

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
        return self.repository.list_feedback_events(
            creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )

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
        return self.repository.list_learning_signals(
            creator_id,
            project_id=project_id,
            workflow_type=workflow_type,
            status=status,
            signal_type=signal_type,
            limit=limit,
            offset=offset,
        )

    def get_learning_signal(self, signal_id: str) -> CreatorLearningSignal | None:
        return self.repository.get_learning_signal_by_id(signal_id)

    def dismiss_signal(self, signal_id: str, *, reason: str) -> CreatorLearningSignal:
        signal = self.repository.get_learning_signal_by_id(signal_id)
        if signal is None:
            raise ValueError("La señal no existe.")
        dismissed = replace(
            signal,
            status=CreatorLearningSignalStatus.DISMISSED,
            metadata_json=self._signal_metadata({**(_json_loads(signal.metadata_json, {}) if isinstance(_json_loads(signal.metadata_json, {}), dict) else {}), "dismiss_reason": reason}),
            updated_at=utc_now(),
        )
        return self.repository.upsert_learning_signal(dismissed)

    def rebuild_learning_signals(self, creator_id: str) -> list[CreatorLearningSignal]:
        events = self.list_feedback_events(creator_id, limit=10000)
        self.repository.delete_learning_signal_evidence_for_creator(creator_id)
        self.repository.delete_learning_signals_for_creator(creator_id)
        rebuilt: list[CreatorLearningSignal] = []
        for event in events:
            rebuilt.extend(self._sync_event_signals(event))
        return rebuilt

    def learning_snapshot(self, creator_id: str) -> CreatorLearningSnapshot:
        signals = self.list_learning_signals(creator_id, limit=1000)
        events = self.list_feedback_events(creator_id, limit=1000)
        evidence_count = 0
        dismissed = sum(1 for signal in signals if signal.status == CreatorLearningSignalStatus.DISMISSED)
        candidates = sum(1 for signal in signals if signal.status == CreatorLearningSignalStatus.CANDIDATE)
        active = sum(1 for signal in signals if signal.status in {CreatorLearningSignalStatus.OBSERVED, CreatorLearningSignalStatus.CANDIDATE})
        orphan_count = 0
        signal_summaries = tuple(signal.to_dict() for signal in signals)
        for signal in signals:
            evidence_count += len(self.repository.list_learning_signal_evidence(signal.id))
        return CreatorLearningSnapshot(
            creator_id=creator_id,
            generated_at=utc_now(),
            feedback_event_count=len(events),
            active_signal_count=active,
            candidate_signal_count=candidates,
            dismissed_signal_count=dismissed,
            orphan_evidence_count=orphan_count,
            signals=signal_summaries,
        )

    def health(self, creator_id: str) -> dict[str, object]:
        signals = self.list_learning_signals(creator_id, limit=1000)
        events = self.list_feedback_events(creator_id, limit=1000)
        return {
            "creator_id": creator_id,
            "feedback_event_count": len(events),
            "active_signal_count": sum(1 for signal in signals if signal.status in {CreatorLearningSignalStatus.OBSERVED, CreatorLearningSignalStatus.CANDIDATE}),
            "candidate_signal_count": sum(1 for signal in signals if signal.status == CreatorLearningSignalStatus.CANDIDATE),
            "dismissed_signal_count": sum(1 for signal in signals if signal.status == CreatorLearningSignalStatus.DISMISSED),
            "orphan_evidence_count": 0,
            "last_rebuild": None,
        }
