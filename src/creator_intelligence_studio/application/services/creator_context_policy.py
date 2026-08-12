"""Reusable creator context policies for grounded workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from creator_intelligence_studio.application.services.creator_context_assembly_service import (
    CreatorContextRequest,
    CreatorContextTaskType,
)
from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentType,
)
from creator_intelligence_studio.domain.errors import ValidationError
from creator_intelligence_studio.domain.creator_corpus.normalization import normalize_corpus_text


class CreatorContextGroundingMode(str, Enum):
    CONTEXT_REQUIRED = "context_required"
    CONTEXT_PREFERRED = "context_preferred"
    CONTEXT_OPTIONAL = "context_optional"
    CONTEXT_NOT_ALLOWED = "context_not_allowed"


_BASE_DOCUMENT_TYPES = (
    CorpusDocumentType.SCRIPT,
    CorpusDocumentType.TRANSCRIPT,
    CorpusDocumentType.NOTE,
    CorpusDocumentType.IMPORTED_TEXT,
    CorpusDocumentType.CAPTION,
)

_DEFAULT_AUTHORSHIP_PRIORITY = (
    CorpusAuthorshipClass.CREATOR_ORIGINAL,
    CorpusAuthorshipClass.CREATOR_EDITED,
    CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH,
    CorpusAuthorshipClass.IMPORTED_UNKNOWN,
    CorpusAuthorshipClass.AI_REWRITTEN,
    CorpusAuthorshipClass.AI_GENERATED,
)


def _normalize_document_types(
    values: tuple[CorpusDocumentType | str, ...] | None,
    *,
    include_scripts: bool,
    include_transcripts: bool,
) -> tuple[CorpusDocumentType, ...]:
    document_types: list[CorpusDocumentType] = []
    for value in values or ():
        try:
            document_type = value if isinstance(value, CorpusDocumentType) else CorpusDocumentType(str(value))
        except Exception:
            continue
        document_types.append(document_type)
    if not document_types:
        document_types = list(_BASE_DOCUMENT_TYPES)
    if not include_scripts:
        document_types = [item for item in document_types if item not in {CorpusDocumentType.SCRIPT}]
    if not include_transcripts:
        document_types = [item for item in document_types if item not in {CorpusDocumentType.TRANSCRIPT, CorpusDocumentType.CAPTION}]
    return tuple(dict.fromkeys(document_types))


def _normalize_authorship_priority(
    values: tuple[CorpusAuthorshipClass | str, ...] | None,
    *,
    include_ai_generated: bool,
    include_imported_unknown: bool,
) -> tuple[CorpusAuthorshipClass, ...]:
    priority: list[CorpusAuthorshipClass] = []
    for value in values or _DEFAULT_AUTHORSHIP_PRIORITY:
        try:
            authorship_class = value if isinstance(value, CorpusAuthorshipClass) else CorpusAuthorshipClass(str(value))
        except Exception:
            continue
        priority.append(authorship_class)
    if not include_ai_generated:
        priority = [item for item in priority if item not in {CorpusAuthorshipClass.AI_GENERATED, CorpusAuthorshipClass.AI_REWRITTEN}]
    if not include_imported_unknown:
        priority = [item for item in priority if item is not CorpusAuthorshipClass.IMPORTED_UNKNOWN]
    return tuple(dict.fromkeys(priority))


@dataclass(frozen=True, slots=True)
class CreatorContextPolicy:
    policy_id: str
    workflow_key: str
    task_type: CreatorContextTaskType | str
    grounding_mode: CreatorContextGroundingMode
    enabled: bool = True
    required: bool = False
    project_priority: bool = True
    allowed_document_types: tuple[CorpusDocumentType, ...] = ()
    allowed_authorship_classes: tuple[CorpusAuthorshipClass, ...] = ()
    max_items: int = 8
    context_budget: int = 1200
    include_transcripts: bool = True
    include_scripts: bool = True
    include_ai_generated: bool = True
    include_imported_unknown: bool = True
    fallback_when_empty: str = "continue_without_context"
    include_provenance: bool = True
    include_historical_versions: bool = False
    language: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "workflow_key": self.workflow_key,
            "task_type": self.task_type.value if hasattr(self.task_type, "value") else str(self.task_type),
            "grounding_mode": self.grounding_mode.value,
            "enabled": self.enabled,
            "required": self.required,
            "project_priority": self.project_priority,
            "allowed_document_types": [item.value for item in self.allowed_document_types],
            "allowed_authorship_classes": [item.value for item in self.allowed_authorship_classes],
            "max_items": self.max_items,
            "context_budget": self.context_budget,
            "include_transcripts": self.include_transcripts,
            "include_scripts": self.include_scripts,
            "include_ai_generated": self.include_ai_generated,
            "include_imported_unknown": self.include_imported_unknown,
            "fallback_when_empty": self.fallback_when_empty,
            "include_provenance": self.include_provenance,
            "include_historical_versions": self.include_historical_versions,
            "language": self.language,
            "notes": self.notes,
        }

    def is_context_allowed(self) -> bool:
        return self.enabled and self.grounding_mode != CreatorContextGroundingMode.CONTEXT_NOT_ALLOWED

    def describe(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "workflow_key": self.workflow_key,
            "task_type": self.task_type.value if hasattr(self.task_type, "value") else str(self.task_type),
            "grounding_mode": self.grounding_mode.value,
            "enabled": self.enabled,
            "required": self.required,
            "project_priority": self.project_priority,
            "should_ground_now": self.grounding_mode in {
                CreatorContextGroundingMode.CONTEXT_REQUIRED,
                CreatorContextGroundingMode.CONTEXT_PREFERRED,
            } and self.enabled,
            "why": self.notes or self.fallback_when_empty,
        }

    def build_request(
        self,
        *,
        creator_id: str,
        user_request: str | None = None,
        project_id: str | None = None,
        query_text: str | None = None,
        language: str | None = None,
        document_types: tuple[CorpusDocumentType | str, ...] | None = None,
        authorship_priority: tuple[CorpusAuthorshipClass | str, ...] | None = None,
        max_context_items: int | None = None,
        context_budget: int | None = None,
        include_provenance: bool | None = None,
        include_historical_versions: bool | None = None,
    ) -> CreatorContextRequest:
        if not self.is_context_allowed():
            raise ValidationError(f"La politica de contexto {self.policy_id} no permite grounding.")
        normalized_document_types = _normalize_document_types(
            document_types or self.allowed_document_types,
            include_scripts=self.include_scripts,
            include_transcripts=self.include_transcripts,
        )
        normalized_authorship_priority = _normalize_authorship_priority(
            authorship_priority or self.allowed_authorship_classes or None,
            include_ai_generated=self.include_ai_generated,
            include_imported_unknown=self.include_imported_unknown,
        )
        effective_project_id = project_id if self.project_priority else None
        effective_language = normalize_corpus_text(language or self.language) or None
        return CreatorContextRequest(
            creator_id=creator_id,
            user_request=user_request,
            task_type=self.task_type,
            context_policy_id=self.policy_id,
            project_id=effective_project_id,
            document_types=normalized_document_types,
            allowed_authorship_classes=normalized_authorship_priority,
            authorship_priority=normalized_authorship_priority,
            max_context_items=max_context_items if max_context_items is not None else self.max_items,
            context_budget=context_budget if context_budget is not None else self.context_budget,
            include_provenance=self.include_provenance if include_provenance is None else bool(include_provenance),
            include_historical_versions=self.include_historical_versions if include_historical_versions is None else bool(include_historical_versions),
            include_transcripts=self.include_transcripts,
            include_scripts=self.include_scripts,
            include_ai_generated=self.include_ai_generated,
            include_imported_unknown=self.include_imported_unknown,
            language=effective_language,
            query_text=query_text or user_request,
        )


@dataclass(frozen=True, slots=True)
class CreatorContextPolicyRegistry:
    policies: tuple[CreatorContextPolicy, ...]
    _by_id: dict[str, CreatorContextPolicy] = field(init=False, repr=False, compare=False)
    _by_workflow: dict[str, CreatorContextPolicy] = field(init=False, repr=False, compare=False)
    _by_task: dict[str, CreatorContextPolicy] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_id", {policy.policy_id: policy for policy in self.policies})
        object.__setattr__(self, "_by_workflow", {policy.workflow_key: policy for policy in self.policies})
        by_task: dict[str, CreatorContextPolicy] = {}
        for policy in self.policies:
            task_type = policy.task_type.value if hasattr(policy.task_type, "value") else str(policy.task_type)
            by_task.setdefault(task_type, policy)
        object.__setattr__(self, "_by_task", by_task)

    def get(self, policy_id: str) -> CreatorContextPolicy | None:
        return self._by_id.get(policy_id)

    def get_by_workflow(self, workflow_key: str) -> CreatorContextPolicy | None:
        return self._by_workflow.get(workflow_key)

    def get_by_task_type(self, task_type: CreatorContextTaskType | str) -> CreatorContextPolicy | None:
        key = task_type.value if hasattr(task_type, "value") else str(task_type)
        return self._by_task.get(key)

    def list_policies(self) -> tuple[CreatorContextPolicy, ...]:
        return self.policies

    def workflow_matrix(self) -> tuple[dict[str, Any], ...]:
        matrix: list[dict[str, Any]] = []
        for policy in self.policies:
            matrix.append(
                {
                    "workflow": policy.workflow_key,
                    "policy_id": policy.policy_id,
                    "task_type": policy.task_type.value if hasattr(policy.task_type, "value") else str(policy.task_type),
                    "grounding_mode": policy.grounding_mode.value,
                    "enabled": policy.enabled,
                    "required": policy.required,
                    "project_priority": policy.project_priority,
                    "creator_context_useful": policy.grounding_mode != CreatorContextGroundingMode.CONTEXT_NOT_ALLOWED,
                    "project_context_useful": policy.project_priority,
                    "creator_voice_relevant": any(
                        item in {CorpusAuthorshipClass.CREATOR_ORIGINAL, CorpusAuthorshipClass.CREATOR_EDITED, CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH}
                        for item in policy.allowed_authorship_classes
                    )
                    or policy.include_ai_generated
                    or policy.include_imported_unknown,
                    "should_ground_now": policy.grounding_mode in {
                        CreatorContextGroundingMode.CONTEXT_REQUIRED,
                        CreatorContextGroundingMode.CONTEXT_PREFERRED,
                    }
                    and policy.enabled,
                    "why": policy.notes or policy.fallback_when_empty,
                }
            )
        return tuple(matrix)


def build_default_creator_context_policy_registry() -> CreatorContextPolicyRegistry:
    return CreatorContextPolicyRegistry(
        policies=(
            CreatorContextPolicy(
                policy_id="content_brief",
                workflow_key="content_brief",
                task_type=CreatorContextTaskType.CONTENT_IDEATION,
                grounding_mode=CreatorContextGroundingMode.CONTEXT_PREFERRED,
                project_priority=True,
                allowed_document_types=(
                    CorpusDocumentType.SCRIPT,
                    CorpusDocumentType.TRANSCRIPT,
                    CorpusDocumentType.NOTE,
                    CorpusDocumentType.IMPORTED_TEXT,
                    CorpusDocumentType.CAPTION,
                ),
                allowed_authorship_classes=_DEFAULT_AUTHORSHIP_PRIORITY,
                max_items=6,
                context_budget=900,
                include_provenance=True,
                include_historical_versions=False,
                notes="Content Brief ya usa corpus como base de ideacion para briefs y preguntas de origen.",
            ),
            CreatorContextPolicy(
                policy_id="production_preparation",
                workflow_key="production_preparation",
                task_type=CreatorContextTaskType.SCRIPT_WRITING,
                grounding_mode=CreatorContextGroundingMode.CONTEXT_PREFERRED,
                project_priority=True,
                allowed_document_types=(
                    CorpusDocumentType.SCRIPT,
                    CorpusDocumentType.TRANSCRIPT,
                    CorpusDocumentType.NOTE,
                    CorpusDocumentType.IMPORTED_TEXT,
                    CorpusDocumentType.CAPTION,
                ),
                allowed_authorship_classes=_DEFAULT_AUTHORSHIP_PRIORITY,
                max_items=8,
                context_budget=1200,
                include_provenance=True,
                include_historical_versions=False,
                notes="Production Preparation se beneficia de evidencia del proyecto y de material creador para outlines.",
            ),
            CreatorContextPolicy(
                policy_id="strategic_planning",
                workflow_key="strategic_planning",
                task_type=CreatorContextTaskType.PROJECT_CONTEXT,
                grounding_mode=CreatorContextGroundingMode.CONTEXT_PREFERRED,
                project_priority=True,
                allowed_document_types=(
                    CorpusDocumentType.SCRIPT,
                    CorpusDocumentType.TRANSCRIPT,
                    CorpusDocumentType.NOTE,
                    CorpusDocumentType.IMPORTED_TEXT,
                    CorpusDocumentType.CAPTION,
                ),
                allowed_authorship_classes=_DEFAULT_AUTHORSHIP_PRIORITY,
                max_items=5,
                context_budget=700,
                include_provenance=True,
                include_historical_versions=False,
                notes="Strategic Planning puede usar corpus de apoyo pero debe seguir funcionando sin el.",
            ),
            CreatorContextPolicy(
                policy_id="script_revision",
                workflow_key="script_revision",
                task_type=CreatorContextTaskType.SCRIPT_REVISION,
                grounding_mode=CreatorContextGroundingMode.CONTEXT_PREFERRED,
                project_priority=True,
                allowed_document_types=(
                    CorpusDocumentType.SCRIPT,
                    CorpusDocumentType.TRANSCRIPT,
                    CorpusDocumentType.NOTE,
                    CorpusDocumentType.IMPORTED_TEXT,
                    CorpusDocumentType.CAPTION,
                ),
                allowed_authorship_classes=_DEFAULT_AUTHORSHIP_PRIORITY,
                max_items=8,
                context_budget=1000,
                include_provenance=True,
                include_historical_versions=False,
                notes="Revision de guion debe preservar el artefacto primario y usar corpus como evidencia secundaria.",
            ),
            CreatorContextPolicy(
                policy_id="provider_diagnostic",
                workflow_key="provider_diagnostic",
                task_type="provider_diagnostic",
                grounding_mode=CreatorContextGroundingMode.CONTEXT_NOT_ALLOWED,
                enabled=False,
                project_priority=False,
                allowed_document_types=(),
                allowed_authorship_classes=(),
                max_items=0,
                context_budget=0,
                include_transcripts=False,
                include_scripts=False,
                include_ai_generated=False,
                include_imported_unknown=False,
                include_provenance=False,
                include_historical_versions=False,
                fallback_when_empty="diagnostico_tecnico_sin_corpus",
                notes="El diagnostico de proveedor no debe recibir corpus del creador.",
            ),
        )
    )
