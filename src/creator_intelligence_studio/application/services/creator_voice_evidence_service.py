"""Canonical Creator Voice evidence selection and snapshot building."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from creator_intelligence_studio.domain.creator_corpus import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentVersion,
    CorpusSegment,
    CreatorCorpusRepository,
)
from creator_intelligence_studio.domain.creator_corpus.normalization import normalize_corpus_language, normalize_corpus_text
from creator_intelligence_studio.domain.creator_preferences import CreatorConfirmedPreference, CreatorPreferenceRepository
from creator_intelligence_studio.domain.projects.repositories import ProjectRepository
from creator_intelligence_studio.domain.creator_voice import (
    CreatorVoiceEvidenceExclusion,
    CreatorVoiceEvidenceItem,
    CreatorVoiceEvidenceQuality,
    CreatorVoiceEvidenceSnapshot,
    CreatorVoiceEvidenceSourceKind,
    CreatorVoiceEvidenceType,
    CreatorVoiceExclusionReason,
    CreatorVoiceScopeMode,
    CreatorVoiceSelectionPolicyVersion,
)
from creator_intelligence_studio.shared.dates import utc_now

from .creator_revision_diff_service import CreatorRevisionDiffService


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _normalize_text(value: str | None) -> str:
    return normalize_corpus_text(value)


def _normalize_workflow(value: str | None) -> str | None:
    cleaned = _normalize_text(value)
    return cleaned or None


def _word_count(value: str | None) -> int:
    clean = _normalize_text(value)
    if not clean:
        return 0
    return len(clean.split())


def _char_count(value: str | None) -> int:
    return len(_normalize_text(value))


def _language_key(value: str | None) -> str | None:
    normalized = normalize_corpus_language(value)
    return normalized or None


def _quality_rank(value: CreatorVoiceEvidenceQuality) -> int:
    return {
        CreatorVoiceEvidenceQuality.HIGH: 0,
        CreatorVoiceEvidenceQuality.MEDIUM: 1,
        CreatorVoiceEvidenceQuality.LOW: 2,
    }[value]


def _source_scope_for_item(
    *,
    item_project_id: str | None,
    item_workflow_type: str | None,
    request_project_id: str | None,
    request_workflow_type: str | None,
) -> CreatorVoiceScopeMode:
    if request_project_id is not None and item_project_id == request_project_id:
        return CreatorVoiceScopeMode.PROJECT_SPECIFIC
    if request_workflow_type is not None and item_workflow_type == request_workflow_type:
        return CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
    return CreatorVoiceScopeMode.CREATOR_GLOBAL


@dataclass(frozen=True, slots=True)
class CreatorVoiceEvidenceRequest:
    creator_id: str
    project_id: str | None = None
    workflow_type: str | None = None
    language: str | None = None
    include_historical_versions: bool = False
    include_creator_global_when_project_scope: bool = False
    include_creator_global_when_workflow_scope: bool = True
    max_items: int = 24
    max_items_per_source: int = 3
    max_items_per_type: int = 8

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "project_id": self.project_id,
            "workflow_type": self.workflow_type,
            "language": self.language,
            "include_historical_versions": self.include_historical_versions,
            "include_creator_global_when_project_scope": self.include_creator_global_when_project_scope,
            "include_creator_global_when_workflow_scope": self.include_creator_global_when_workflow_scope,
            "max_items": self.max_items,
            "max_items_per_source": self.max_items_per_source,
            "max_items_per_type": self.max_items_per_type,
        }


@dataclass(frozen=True, slots=True)
class _Candidate:
    identity: str
    evidence_type: CreatorVoiceEvidenceType
    source_key: str
    source_kind: CreatorVoiceEvidenceSourceKind
    source_scope: CreatorVoiceScopeMode
    creator_id: str
    project_id: str | None
    workflow_type: str | None
    document_id: str | None
    version_id: str | None
    segment_id: str | None
    authorship_class: CorpusAuthorshipClass | None
    text_reference: str | None
    language: str | None
    confidence_state: str | None
    voice_learning_eligible: bool
    quality_flags: tuple[str, ...]
    provenance: str
    content_hash: str
    created_at: datetime
    evidence_quality: CreatorVoiceEvidenceQuality
    evidence_weight: float
    qualification_reason: str
    allow_when_project_scope: bool
    allow_when_workflow_scope: bool


class CreatorVoiceEvidenceService:
    POLICY_VERSION = CreatorVoiceSelectionPolicyVersion.V1

    def __init__(
        self,
        *,
        corpus_repository: CreatorCorpusRepository,
        preference_repository: CreatorPreferenceRepository,
        project_repository: ProjectRepository | None = None,
        diff_service: CreatorRevisionDiffService | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.corpus_repository = corpus_repository
        self.preference_repository = preference_repository
        self.project_repository = project_repository
        self.diff_service = diff_service or CreatorRevisionDiffService()
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_voice")

    def _project_for(self, creator_id: str, project_id: str | None) -> None:
        if project_id is None:
            return
        if self.project_repository is None:
            return
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ValueError("El proyecto no existe.")
        if project.creator_id != creator_id:
            raise ValueError("El proyecto no pertenece al creador indicado.")

    def _current_document_map(self, creator_id: str) -> dict[str, Any]:
        documents = self.corpus_repository.list_documents(creator_id)
        return {document.id: document for document in documents}

    def _ancestor_has_ai_origin(
        self,
        *,
        version: CorpusDocumentVersion,
        versions_by_id: dict[str, CorpusDocumentVersion],
    ) -> bool:
        seen: set[str] = set()
        current = version
        while current.parent_version_id and current.parent_version_id not in seen:
            seen.add(current.parent_version_id)
            parent = versions_by_id.get(current.parent_version_id)
            if parent is None:
                break
            if parent.authorship_class in {CorpusAuthorshipClass.AI_GENERATED, CorpusAuthorshipClass.AI_REWRITTEN}:
                return True
            current = parent
        return False

    def _version_evidence(
        self,
        *,
        version: CorpusDocumentVersion,
        document,
        segments_for_version: list[CorpusSegment] | None,
        versions_by_id: dict[str, CorpusDocumentVersion],
        request: CreatorVoiceEvidenceRequest,
    ) -> tuple[CreatorVoiceEvidenceItem | None, CreatorVoiceEvidenceExclusion | None]:
        if document.creator_id != request.creator_id:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        if document.status != CorpusDocumentStatus.ACTIVE:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.ARCHIVED.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        language = _language_key(version.language or document.language)
        request_language = _language_key(request.language)
        if request_language is not None and language != request_language:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=language,
                reason=CreatorVoiceExclusionReason.WRONG_LANGUAGE.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        if version.authorship_class == CorpusAuthorshipClass.AI_GENERATED:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=language,
                reason=CreatorVoiceExclusionReason.AI_GENERATED.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        if version.authorship_class == CorpusAuthorshipClass.AI_REWRITTEN:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=language,
                reason=CreatorVoiceExclusionReason.AI_REWRITTEN.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        if version.authorship_class == CorpusAuthorshipClass.IMPORTED_UNKNOWN:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=language,
                reason=CreatorVoiceExclusionReason.UNSUPPORTED_AUTHORSHIP.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        if (
            version.authorship_class == CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH
            and segments_for_version is not None
            and segments_for_version
        ):
            unsafe_review_states = {"needs_review", "excluded"}
            if any(
                segment.voice_learning_eligible is False
                and str(segment.review_state or "").strip().lower() in unsafe_review_states
                for segment in segments_for_version
            ):
                exclusion = CreatorVoiceEvidenceExclusion(
                    id=str(uuid4()),
                    creator_id=request.creator_id,
                    project_id=document.project_id,
                    workflow_type=None,
                    document_id=document.id,
                    version_id=version.id,
                    segment_id=None,
                    evidence_type=CreatorVoiceEvidenceType.CREATOR_SPOKEN,
                    source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                    language=language,
                    reason=CreatorVoiceExclusionReason.NEEDS_REVIEW.value,
                    quality_flags=version.quality_flags,
                    source_identity=f"{document.id}:{version.id}",
                    created_at=version.created_at,
                )
                return None, exclusion
            if any(segment.confidence is not None and segment.confidence < 0.8 for segment in segments_for_version):
                exclusion = CreatorVoiceEvidenceExclusion(
                    id=str(uuid4()),
                    creator_id=request.creator_id,
                    project_id=document.project_id,
                    workflow_type=None,
                    document_id=document.id,
                    version_id=version.id,
                    segment_id=None,
                    evidence_type=CreatorVoiceEvidenceType.CREATOR_SPOKEN,
                    source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                    language=language,
                    reason=CreatorVoiceExclusionReason.LOW_CONFIDENCE.value,
                    quality_flags=version.quality_flags,
                    source_identity=f"{document.id}:{version.id}",
                    created_at=version.created_at,
                )
                return None, exclusion
        if not request.include_historical_versions and document.current_version_id != version.id:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=None,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.HISTORICAL_VERSION.value,
                quality_flags=version.quality_flags,
                source_identity=f"{document.id}:{version.id}",
                created_at=version.created_at,
            )
            return None, exclusion
        evidence_type = (
            CreatorVoiceEvidenceType.CREATOR_SPOKEN
            if version.authorship_class == CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH
            else CreatorVoiceEvidenceType.CREATOR_EDITED
            if version.authorship_class == CorpusAuthorshipClass.CREATOR_EDITED
            else CreatorVoiceEvidenceType.CREATOR_WRITTEN
        )
        quality_flags = list(version.quality_flags)
        if version.authorship_class == CorpusAuthorshipClass.CREATOR_EDITED:
            quality_flags.append("creator_edited")
        if version.authorship_class == CorpusAuthorshipClass.CREATOR_ORIGINAL:
            quality_flags.append("creator_original")
        if version.authorship_class == CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH:
            quality_flags.append("creator_spoken")
        ai_origin = self._ancestor_has_ai_origin(version=version, versions_by_id=versions_by_id)
        if ai_origin:
            quality_flags.append("ai_origin_contaminated")
        word_count = _word_count(version.normalized_content)
        if word_count < 2:
            quality_flags.append("too_little_signal")
        diff_summary = None
        if version.parent_version_id and version.parent_version_id in versions_by_id:
            parent = versions_by_id[version.parent_version_id]
            diff_summary = self.diff_service.summarize(parent.raw_content, version.raw_content)
        quality, weight = self._quality_for_version(
            version=version,
            ai_origin=ai_origin,
            diff_summary=diff_summary,
            word_count=word_count,
        )
        qualification_reason = self._qualification_reason_for_version(
            version=version,
            ai_origin=ai_origin,
            diff_summary=diff_summary,
            word_count=word_count,
        )
        item = CreatorVoiceEvidenceItem(
            id=version.id,
            creator_id=request.creator_id,
            project_id=document.project_id,
            workflow_type=None,
            document_id=document.id,
            version_id=version.id,
            segment_id=None,
            authorship_class=version.authorship_class,
            evidence_type=evidence_type,
            text_reference=version.normalized_content,
            language=language,
            source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
            confidence_state="active" if version.voice_learning_eligible else "not_voice_learning_eligible",
            voice_learning_eligible=version.voice_learning_eligible,
            quality_flags=tuple(dict.fromkeys(quality_flags)),
            provenance=self._version_provenance(document=document, version=version, ai_origin=ai_origin),
            content_hash=version.content_hash,
            created_at=version.created_at,
            evidence_quality=quality,
            evidence_weight=weight,
            qualification_reason=qualification_reason,
            source_identity=f"{document.id}:{version.id}",
            source_scope=_source_scope_for_item(
                item_project_id=document.project_id,
                item_workflow_type=None,
                request_project_id=request.project_id,
                request_workflow_type=request.workflow_type,
            ),
        )
        if version.voice_learning_eligible:
            return item, None
        exclusion = CreatorVoiceEvidenceExclusion(
            id=str(uuid4()),
            creator_id=request.creator_id,
            project_id=document.project_id,
            workflow_type=None,
            document_id=document.id,
            version_id=version.id,
            segment_id=None,
            evidence_type=evidence_type,
            source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_VERSION,
            language=language,
            reason=CreatorVoiceExclusionReason.NOT_VOICE_LEARNING_ELIGIBLE.value,
            quality_flags=tuple(dict.fromkeys(quality_flags)),
            source_identity=f"{document.id}:{version.id}",
            created_at=version.created_at,
        )
        return None, exclusion

    def _segment_evidence(
        self,
        *,
        segment: CorpusSegment,
        version: CorpusDocumentVersion,
        document,
        request: CreatorVoiceEvidenceRequest,
    ) -> tuple[CreatorVoiceEvidenceItem | None, CreatorVoiceEvidenceExclusion | None]:
        if document.creator_id != request.creator_id:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        if document.status != CorpusDocumentStatus.ACTIVE:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.ARCHIVED.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        if not request.include_historical_versions and document.current_version_id != version.id:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=version.language or document.language,
                reason=CreatorVoiceExclusionReason.HISTORICAL_VERSION.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        language = _language_key(version.language or document.language)
        request_language = _language_key(request.language)
        if request_language is not None and language != request_language:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=language,
                reason=CreatorVoiceExclusionReason.WRONG_LANGUAGE.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        if version.authorship_class != CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=None,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=language,
                reason=CreatorVoiceExclusionReason.UNSUPPORTED_AUTHORSHIP.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        if not segment.voice_learning_eligible:
            reason = (
                CreatorVoiceExclusionReason.NEEDS_REVIEW.value
                if segment.review_state and str(segment.review_state).strip().lower() in {"needs_review", "excluded"}
                else CreatorVoiceExclusionReason.LOW_CONFIDENCE.value
            )
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=CreatorVoiceEvidenceType.CREATOR_SPOKEN,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=language,
                reason=reason,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        if segment.confidence is not None and segment.confidence < 0.8:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=document.project_id,
                workflow_type=None,
                document_id=document.id,
                version_id=version.id,
                segment_id=segment.id,
                evidence_type=CreatorVoiceEvidenceType.CREATOR_SPOKEN,
                source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
                language=language,
                reason=CreatorVoiceExclusionReason.LOW_CONFIDENCE.value,
                quality_flags=segment.quality_flags,
                source_identity=f"{document.id}:{version.id}:{segment.id}",
                created_at=segment.created_at,
            )
            return None, exclusion
        item = CreatorVoiceEvidenceItem(
            id=segment.id,
            creator_id=request.creator_id,
            project_id=document.project_id,
            workflow_type=None,
            document_id=document.id,
            version_id=version.id,
            segment_id=segment.id,
            authorship_class=version.authorship_class,
            evidence_type=CreatorVoiceEvidenceType.CREATOR_SPOKEN,
            text_reference=segment.text,
            language=language,
            source_kind=CreatorVoiceEvidenceSourceKind.CORPUS_SEGMENT,
            confidence_state=segment.review_state or "reviewed",
            voice_learning_eligible=True,
            quality_flags=tuple(dict.fromkeys((*segment.quality_flags, "creator_spoken"))),
            provenance=self._segment_provenance(document=document, version=version, segment=segment),
            content_hash=_hash_text(segment.text or ""),
            created_at=segment.created_at,
            evidence_quality=CreatorVoiceEvidenceQuality.HIGH,
            evidence_weight=self._spoken_weight(segment=segment),
            qualification_reason="transcribed creator speech active segment with acceptable confidence and review state",
            source_identity=f"{document.id}:{version.id}:{segment.id}",
            source_scope=_source_scope_for_item(
                item_project_id=document.project_id,
                item_workflow_type=None,
                request_project_id=request.project_id,
                request_workflow_type=request.workflow_type,
            ),
        )
        return item, None

    def _preference_evidence(
        self,
        *,
        preference: CreatorConfirmedPreference,
        request: CreatorVoiceEvidenceRequest,
    ) -> tuple[CreatorVoiceEvidenceItem | None, CreatorVoiceEvidenceExclusion | None]:
        if preference.creator_id != request.creator_id:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=preference.project_id,
                workflow_type=preference.workflow_type,
                document_id=None,
                version_id=None,
                segment_id=None,
                evidence_type=CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
                source_kind=CreatorVoiceEvidenceSourceKind.CONFIRMED_PREFERENCE,
                language=None,
                reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                quality_flags=("confirmed_preference",),
                source_identity=preference.preference_key,
                created_at=preference.created_at,
            )
            return None, exclusion
        if not preference.active:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=preference.project_id,
                workflow_type=preference.workflow_type,
                document_id=None,
                version_id=None,
                segment_id=None,
                evidence_type=CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
                source_kind=CreatorVoiceEvidenceSourceKind.CONFIRMED_PREFERENCE,
                language=None,
                reason=CreatorVoiceExclusionReason.NOT_VOICE_LEARNING_ELIGIBLE.value,
                quality_flags=("confirmed_preference",),
                source_identity=preference.preference_key,
                created_at=preference.created_at,
            )
            return None, exclusion
        if request.project_id is not None and preference.project_id is None and not request.include_creator_global_when_project_scope:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=preference.project_id,
                workflow_type=preference.workflow_type,
                document_id=None,
                version_id=None,
                segment_id=None,
                evidence_type=CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
                source_kind=CreatorVoiceEvidenceSourceKind.CONFIRMED_PREFERENCE,
                language=None,
                reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                quality_flags=("confirmed_preference",),
                source_identity=preference.preference_key,
                created_at=preference.created_at,
            )
            return None, exclusion
        if request.workflow_type is not None and preference.workflow_type is None and not request.include_creator_global_when_workflow_scope:
            exclusion = CreatorVoiceEvidenceExclusion(
                id=str(uuid4()),
                creator_id=request.creator_id,
                project_id=preference.project_id,
                workflow_type=preference.workflow_type,
                document_id=None,
                version_id=None,
                segment_id=None,
                evidence_type=CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
                source_kind=CreatorVoiceEvidenceSourceKind.CONFIRMED_PREFERENCE,
                language=None,
                reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                quality_flags=("confirmed_preference",),
                source_identity=preference.preference_key,
                created_at=preference.created_at,
            )
            return None, exclusion
        text_reference = self._render_preference_reference(preference)
        item = CreatorVoiceEvidenceItem(
            id=preference.id,
            creator_id=preference.creator_id,
            project_id=preference.project_id,
            workflow_type=preference.workflow_type,
            document_id=None,
            version_id=None,
            segment_id=None,
            authorship_class=None,
            evidence_type=CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
            text_reference=text_reference,
            language=None,
            source_kind=CreatorVoiceEvidenceSourceKind.CONFIRMED_PREFERENCE,
            confidence_state="confirmed_active",
            voice_learning_eligible=False,
            quality_flags=("confirmed_preference", "structured_guidance"),
            provenance=f"confirmed_preference:{preference.preference_key}",
            content_hash=_hash_text(f"{preference.preference_key}|{preference.value_json}|{preference.scope.value}"),
            created_at=preference.confirmed_at,
            evidence_quality=CreatorVoiceEvidenceQuality.MEDIUM,
            evidence_weight=0.35,
            qualification_reason="confirmed preference kept as separate structured guidance, not textual style sample",
            source_identity=preference.preference_key,
            source_scope=_source_scope_for_item(
                item_project_id=preference.project_id,
                item_workflow_type=preference.workflow_type,
                request_project_id=request.project_id,
                request_workflow_type=request.workflow_type,
            ),
        )
        return item, None

    def _quality_for_version(
        self,
        *,
        version: CorpusDocumentVersion,
        ai_origin: bool,
        diff_summary,
        word_count: int,
    ) -> tuple[CreatorVoiceEvidenceQuality, float]:
        if version.authorship_class in {CorpusAuthorshipClass.CREATOR_ORIGINAL, CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH} and word_count >= 3:
            return CreatorVoiceEvidenceQuality.HIGH, 1.0 if version.authorship_class == CorpusAuthorshipClass.CREATOR_ORIGINAL else 0.95
        if version.authorship_class == CorpusAuthorshipClass.CREATOR_EDITED:
            if ai_origin:
                changed_ratio = getattr(diff_summary, "changed_ratio", 0.0) if diff_summary is not None else 0.0
                if changed_ratio < 0.25:
                    return CreatorVoiceEvidenceQuality.LOW, 0.25
                if changed_ratio < 0.75:
                    return CreatorVoiceEvidenceQuality.MEDIUM, 0.45
                return CreatorVoiceEvidenceQuality.MEDIUM, 0.6
            if word_count < 3:
                return CreatorVoiceEvidenceQuality.LOW, 0.3
            return CreatorVoiceEvidenceQuality.MEDIUM, 0.7
        if word_count < 3:
            return CreatorVoiceEvidenceQuality.LOW, 0.2
        return CreatorVoiceEvidenceQuality.LOW, 0.45

    def _spoken_weight(self, *, segment: CorpusSegment) -> float:
        weight = 0.95
        if segment.confidence is not None:
            weight = min(weight, round(0.7 + (segment.confidence * 0.25), 3))
        if _word_count(segment.text) < 3:
            weight = min(weight, 0.5)
        return max(0.1, min(weight, 1.0))

    def _qualification_reason_for_version(
        self,
        *,
        version: CorpusDocumentVersion,
        ai_origin: bool,
        diff_summary,
        word_count: int,
    ) -> str:
        if version.authorship_class == CorpusAuthorshipClass.CREATOR_ORIGINAL:
            return "creator original active current version"
        if version.authorship_class == CorpusAuthorshipClass.CREATOR_EDITED:
            if ai_origin:
                changed_ratio = getattr(diff_summary, "changed_ratio", 0.0) if diff_summary is not None else 0.0
                if changed_ratio < 0.25:
                    return "creator edited from AI base with minimal change"
                if changed_ratio < 0.75:
                    return "creator edited from AI base with partial rewrite"
                return "creator edited from AI base with heavy rewrite"
            return "creator edited active current version"
        if version.authorship_class == CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH:
            return "transcribed creator speech active and reviewable"
        if word_count < 3:
            return "minimal signal evidence"
        return "eligible creator-authentic version"

    def _version_provenance(self, *, document, version: CorpusDocumentVersion, ai_origin: bool) -> str:
        payload = {
            "document_id": document.id,
            "version_id": version.id,
            "project_id": document.project_id,
            "source_kind": version.source_kind.value,
            "parent_version_id": version.parent_version_id,
            "source_asset_id": version.source_asset_id,
            "ai_origin_contaminated": ai_origin,
        }
        return _stable_json(payload)

    def _segment_provenance(self, *, document, version: CorpusDocumentVersion, segment: CorpusSegment) -> str:
        payload = {
            "document_id": document.id,
            "version_id": version.id,
            "segment_id": segment.id,
            "project_id": document.project_id,
            "source_reference_type": segment.source_reference_type,
            "source_reference_id": segment.source_reference_id,
        }
        return _stable_json(payload)

    def _render_preference_reference(self, preference: CreatorConfirmedPreference) -> str:
        value = preference.value_json
        try:
            parsed = json.loads(value) if value else {}
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {"value": parsed}
        preference_type = parsed.get("preference_type") or preference.preference_type.value
        direction = parsed.get("direction") or parsed.get("value") or parsed.get("proposed_value")
        scope = preference.scope.value
        return _normalize_text(f"{preference_type} {direction or ''} {scope}".strip())

    def _candidate_key(self, candidate: _Candidate) -> str:
        payload = {
            "identity": candidate.identity,
            "evidence_type": candidate.evidence_type.value,
            "source_key": candidate.source_key,
            "content_hash": candidate.content_hash,
        }
        return sha256(_stable_json(payload).encode("utf-8")).hexdigest()

    def _load_candidates(self, request: CreatorVoiceEvidenceRequest) -> tuple[list[_Candidate], list[CreatorVoiceEvidenceExclusion]]:
        documents = self._current_document_map(request.creator_id)
        versions = self.corpus_repository.list_document_versions_for_creator(request.creator_id)
        segments = self.corpus_repository.list_segments_for_creator(request.creator_id)
        versions_by_id = {version.id: version for version in versions}
        segments_by_version: dict[str, list[CorpusSegment]] = defaultdict(list)
        for segment in segments:
            segments_by_version[segment.document_version_id].append(segment)
        exclusions: list[CreatorVoiceEvidenceExclusion] = []
        candidates: list[_Candidate] = []
        request_language = _language_key(request.language)
        for version in versions:
            document = documents.get(version.document_id)
            if document is None:
                continue
            item, exclusion = self._version_evidence(
                version=version,
                document=document,
                segments_for_version=segments_by_version.get(version.id, []),
                versions_by_id=versions_by_id,
                request=request,
            )
            if item is not None:
                source_key = f"{item.document_id}:{item.version_id}" if item.document_id and item.version_id else item.source_identity
                if not self._scope_allows_item(request=request, item_project_id=item.project_id, item_workflow_type=item.workflow_type):
                    exclusions.append(
                        CreatorVoiceEvidenceExclusion(
                            id=str(uuid4()),
                            creator_id=request.creator_id,
                            project_id=item.project_id,
                            workflow_type=item.workflow_type,
                            document_id=item.document_id,
                            version_id=item.version_id,
                            segment_id=item.segment_id,
                            evidence_type=item.evidence_type,
                            source_kind=item.source_kind,
                            language=item.language,
                            reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                            quality_flags=item.quality_flags,
                            source_identity=item.source_identity,
                            created_at=item.created_at,
                        )
                    )
                else:
                    candidates.append(
                        _Candidate(
                            identity=item.id,
                            evidence_type=item.evidence_type,
                            source_key=source_key,
                            source_kind=item.source_kind,
                            source_scope=item.source_scope,
                            creator_id=item.creator_id,
                            project_id=item.project_id,
                            workflow_type=item.workflow_type,
                            document_id=item.document_id,
                            version_id=item.version_id,
                            segment_id=item.segment_id,
                            authorship_class=item.authorship_class,
                            text_reference=item.text_reference,
                            language=item.language,
                            confidence_state=item.confidence_state,
                            voice_learning_eligible=item.voice_learning_eligible,
                            quality_flags=item.quality_flags,
                            provenance=item.provenance,
                            content_hash=item.content_hash,
                            created_at=item.created_at,
                            evidence_quality=item.evidence_quality,
                            evidence_weight=item.evidence_weight,
                            qualification_reason=item.qualification_reason,
                            allow_when_project_scope=request.include_creator_global_when_project_scope,
                            allow_when_workflow_scope=request.include_creator_global_when_workflow_scope,
                        )
                    )
            elif exclusion is not None:
                exclusions.append(exclusion)

            if version.authorship_class == CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH:
                segment_candidates = sorted(
                    segments_by_version.get(version.id, []),
                    key=lambda segment: (
                        -float(segment.confidence or 0.0),
                        float(segment.start_seconds or 0.0),
                        segment.sequence,
                        segment.id,
                    ),
                )
                for segment in segment_candidates:
                    item, exclusion = self._segment_evidence(
                        segment=segment,
                        version=version,
                        document=document,
                        request=request,
                    )
                    if item is not None:
                        source_key = f"{item.document_id}:{item.version_id}" if item.document_id and item.version_id else item.source_identity
                        if not self._scope_allows_item(request=request, item_project_id=item.project_id, item_workflow_type=item.workflow_type):
                            exclusions.append(
                                CreatorVoiceEvidenceExclusion(
                                    id=str(uuid4()),
                                    creator_id=request.creator_id,
                                    project_id=item.project_id,
                                    workflow_type=item.workflow_type,
                                    document_id=item.document_id,
                                    version_id=item.version_id,
                                    segment_id=item.segment_id,
                                    evidence_type=item.evidence_type,
                                    source_kind=item.source_kind,
                                    language=item.language,
                                    reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                                    quality_flags=item.quality_flags,
                                    source_identity=item.source_identity,
                                    created_at=item.created_at,
                                )
                            )
                        else:
                            candidates.append(
                                _Candidate(
                                    identity=item.id,
                                    evidence_type=item.evidence_type,
                                    source_key=source_key,
                                    source_kind=item.source_kind,
                                    source_scope=item.source_scope,
                                    creator_id=item.creator_id,
                                    project_id=item.project_id,
                                    workflow_type=item.workflow_type,
                                    document_id=item.document_id,
                                    version_id=item.version_id,
                                    segment_id=item.segment_id,
                                    authorship_class=item.authorship_class,
                                    text_reference=item.text_reference,
                                    language=item.language,
                                    confidence_state=item.confidence_state,
                                    voice_learning_eligible=item.voice_learning_eligible,
                                    quality_flags=item.quality_flags,
                                    provenance=item.provenance,
                                    content_hash=item.content_hash,
                                    created_at=item.created_at,
                                    evidence_quality=item.evidence_quality,
                                    evidence_weight=item.evidence_weight,
                                    qualification_reason=item.qualification_reason,
                                    allow_when_project_scope=request.include_creator_global_when_project_scope,
                                    allow_when_workflow_scope=request.include_creator_global_when_workflow_scope,
                                )
                            )
                    elif exclusion is not None:
                        exclusions.append(exclusion)

        preferences = self.preference_repository.list_confirmed_preferences(request.creator_id, active=True, limit=1000)
        for preference in preferences:
            item, exclusion = self._preference_evidence(preference=preference, request=request)
            if item is not None:
                source_key = item.source_identity
                if not self._scope_allows_item(request=request, item_project_id=item.project_id, item_workflow_type=item.workflow_type):
                    exclusions.append(
                        CreatorVoiceEvidenceExclusion(
                            id=str(uuid4()),
                            creator_id=request.creator_id,
                            project_id=item.project_id,
                            workflow_type=item.workflow_type,
                            document_id=None,
                            version_id=None,
                            segment_id=None,
                            evidence_type=item.evidence_type,
                            source_kind=item.source_kind,
                            language=item.language,
                            reason=CreatorVoiceExclusionReason.WRONG_SCOPE.value,
                            quality_flags=item.quality_flags,
                            source_identity=item.source_identity,
                            created_at=item.created_at,
                        )
                    )
                else:
                    candidates.append(
                        _Candidate(
                            identity=item.id,
                            evidence_type=item.evidence_type,
                            source_key=source_key,
                            source_kind=item.source_kind,
                            source_scope=item.source_scope,
                            creator_id=item.creator_id,
                            project_id=item.project_id,
                            workflow_type=item.workflow_type,
                            document_id=item.document_id,
                            version_id=item.version_id,
                            segment_id=item.segment_id,
                            authorship_class=item.authorship_class,
                            text_reference=item.text_reference,
                            language=item.language,
                            confidence_state=item.confidence_state,
                            voice_learning_eligible=item.voice_learning_eligible,
                            quality_flags=item.quality_flags,
                            provenance=item.provenance,
                            content_hash=item.content_hash,
                            created_at=item.created_at,
                            evidence_quality=item.evidence_quality,
                            evidence_weight=item.evidence_weight,
                            qualification_reason=item.qualification_reason,
                            allow_when_project_scope=request.include_creator_global_when_project_scope,
                            allow_when_workflow_scope=request.include_creator_global_when_workflow_scope,
                        )
                    )
            elif exclusion is not None:
                exclusions.append(exclusion)
        return candidates, exclusions

    def _scope_allows_item(self, *, request: CreatorVoiceEvidenceRequest, item_project_id: str | None, item_workflow_type: str | None) -> bool:
        if request.project_id is not None:
            if item_project_id == request.project_id:
                return True
            if item_project_id is None:
                return request.include_creator_global_when_project_scope
            return False
        if request.workflow_type is not None:
            if item_workflow_type == request.workflow_type:
                return True
            if item_workflow_type is None:
                return request.include_creator_global_when_workflow_scope
            return False
        return True

    def _select_candidates(
        self,
        candidates: list[_Candidate],
        *,
        request: CreatorVoiceEvidenceRequest,
    ) -> tuple[list[CreatorVoiceEvidenceItem], list[CreatorVoiceEvidenceExclusion]]:
        by_type: dict[CreatorVoiceEvidenceType, list[_Candidate]] = defaultdict(list)
        for candidate in candidates:
            by_type[candidate.evidence_type].append(candidate)
        for bucket in by_type.values():
            bucket.sort(
                key=lambda candidate: (
                    _quality_rank(candidate.evidence_quality),
                    -candidate.evidence_weight,
                    0 if candidate.source_scope != CreatorVoiceScopeMode.CREATOR_GLOBAL else 1,
                    -int(candidate.created_at.timestamp()),
                    candidate.source_key,
                    candidate.identity,
                )
            )
        type_order = (
            CreatorVoiceEvidenceType.CREATOR_WRITTEN,
            CreatorVoiceEvidenceType.CREATOR_SPOKEN,
            CreatorVoiceEvidenceType.CREATOR_EDITED,
            CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE,
        )
        selected: list[CreatorVoiceEvidenceItem] = []
        exclusions: list[CreatorVoiceEvidenceExclusion] = []
        seen_content_hashes: set[str] = set()
        source_counts: dict[str, int] = defaultdict(int)
        type_counts: dict[CreatorVoiceEvidenceType, int] = defaultdict(int)
        max_rounds = max(len(bucket) for bucket in by_type.values()) if by_type else 0
        for round_index in range(max_rounds):
            for evidence_type in type_order:
                bucket = by_type.get(evidence_type, [])
                if round_index >= len(bucket):
                    continue
                candidate = bucket[round_index]
                if len(selected) >= request.max_items:
                    exclusions.append(self._candidate_to_exclusion(candidate, CreatorVoiceExclusionReason.EVIDENCE_CAP.value))
                    continue
                if type_counts[candidate.evidence_type] >= request.max_items_per_type:
                    exclusions.append(self._candidate_to_exclusion(candidate, CreatorVoiceExclusionReason.EVIDENCE_CAP.value))
                    continue
                if source_counts[candidate.source_key] >= request.max_items_per_source:
                    exclusions.append(self._candidate_to_exclusion(candidate, CreatorVoiceExclusionReason.SOURCE_CAP.value))
                    continue
                if candidate.content_hash in seen_content_hashes:
                    exclusions.append(self._candidate_to_exclusion(candidate, CreatorVoiceExclusionReason.DUPLICATE.value))
                    continue
                seen_content_hashes.add(candidate.content_hash)
                source_counts[candidate.source_key] += 1
                type_counts[candidate.evidence_type] += 1
                selected.append(
                    CreatorVoiceEvidenceItem(
                        id=candidate.identity,
                        creator_id=candidate.creator_id,
                        project_id=candidate.project_id,
                        workflow_type=candidate.workflow_type,
                        document_id=candidate.document_id,
                        version_id=candidate.version_id,
                        segment_id=candidate.segment_id,
                        authorship_class=candidate.authorship_class,
                        evidence_type=candidate.evidence_type,
                        text_reference=candidate.text_reference,
                        language=candidate.language,
                        source_kind=candidate.source_kind,
                        confidence_state=candidate.confidence_state,
                        voice_learning_eligible=candidate.voice_learning_eligible,
                        quality_flags=candidate.quality_flags,
                        provenance=candidate.provenance,
                        content_hash=candidate.content_hash,
                        created_at=candidate.created_at,
                        evidence_quality=candidate.evidence_quality,
                        evidence_weight=candidate.evidence_weight,
                        qualification_reason=candidate.qualification_reason,
                        source_identity=candidate.source_key,
                        source_scope=candidate.source_scope,
                    )
                )
        return selected, exclusions

    def _candidate_to_exclusion(self, candidate: _Candidate, reason: str) -> CreatorVoiceEvidenceExclusion:
        return CreatorVoiceEvidenceExclusion(
            id=str(uuid4()),
            creator_id=candidate.creator_id,
            project_id=candidate.project_id,
            workflow_type=candidate.workflow_type,
            document_id=candidate.document_id,
            version_id=candidate.version_id,
            segment_id=candidate.segment_id,
            evidence_type=candidate.evidence_type,
            source_kind=candidate.source_kind,
            language=candidate.language,
            reason=reason,
            quality_flags=candidate.quality_flags,
            source_identity=candidate.source_key,
            created_at=candidate.created_at,
        )

    def build_snapshot(self, request: CreatorVoiceEvidenceRequest | dict[str, object]) -> CreatorVoiceEvidenceSnapshot:
        normalized = self._normalize_request(request)
        self._project_for(normalized.creator_id, normalized.project_id)
        candidates, pre_exclusions = self._load_candidates(normalized)
        selected, post_exclusions = self._select_candidates(candidates, request=normalized)
        exclusions = pre_exclusions + post_exclusions
        excluded_counts = Counter(item.reason for item in exclusions)
        category_counts = Counter(item.evidence_type.value for item in selected)
        quality_counts = Counter(item.evidence_quality.value for item in selected)
        language_distribution = Counter(item.language for item in selected if item.language)
        project_distribution = Counter(item.project_id or "creator_global" for item in selected)
        workflow_distribution = Counter(item.workflow_type or "creator_global" for item in selected)
        total_words = sum(_word_count(item.text_reference) for item in selected if item.evidence_type != CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE)
        total_characters = sum(_char_count(item.text_reference) for item in selected if item.evidence_type != CreatorVoiceEvidenceType.CONFIRMED_PREFERENCE)
        fingerprint_payload = {
            "request": normalized.to_dict(),
            "selected": [
                {
                    "id": item.id,
                    "evidence_type": item.evidence_type.value,
                    "source_identity": item.source_identity,
                    "content_hash": item.content_hash,
                    "quality": item.evidence_quality.value,
                    "weight": item.evidence_weight,
                    "scope": item.source_scope.value,
                }
                for item in selected
            ],
            "excluded": [
                {
                    "source_identity": item.source_identity,
                    "reason": item.reason,
                    "evidence_type": item.evidence_type.value if item.evidence_type else None,
                }
                for item in exclusions
            ],
        }
        fingerprint = sha256(_stable_json(fingerprint_payload).encode("utf-8")).hexdigest()
        snapshot = CreatorVoiceEvidenceSnapshot(
            creator_id=normalized.creator_id,
            project_id=normalized.project_id,
            workflow_type=normalized.workflow_type,
            language=_language_key(normalized.language),
            policy_version=self.POLICY_VERSION,
            source_scope=(
                CreatorVoiceScopeMode.PROJECT_SPECIFIC
                if normalized.project_id is not None
                else CreatorVoiceScopeMode.WORKFLOW_SPECIFIC
                if normalized.workflow_type is not None
                else CreatorVoiceScopeMode.CREATOR_GLOBAL
            ),
            generated_at=utc_now(),
            evidence_items=tuple(selected),
            excluded_candidates=tuple(exclusions[:200]),
            evidence_count=len(selected),
            category_counts=dict(category_counts),
            quality_counts=dict(quality_counts),
            excluded_counts=dict(excluded_counts),
            language_distribution=dict(language_distribution),
            project_distribution=dict(project_distribution),
            workflow_distribution=dict(workflow_distribution),
            total_estimated_words=total_words,
            total_estimated_characters=total_characters,
            content_fingerprint=fingerprint,
        )
        return snapshot

    def diagnostics(self, request: CreatorVoiceEvidenceRequest | dict[str, object], *, debug: bool = False) -> dict[str, object]:
        snapshot = self.build_snapshot(request)
        payload = snapshot.to_debug_dict() if debug else snapshot.to_dict()
        return {
            "snapshot": payload,
            "summary": {
                "creator_id": snapshot.creator_id,
                "project_id": snapshot.project_id,
                "workflow_type": snapshot.workflow_type,
                "language": snapshot.language,
                "policy_version": snapshot.policy_version.value,
                "source_scope": snapshot.source_scope.value,
                "evidence_count": snapshot.evidence_count,
                "content_fingerprint": snapshot.content_fingerprint,
            },
        }

    def _normalize_request(self, request: CreatorVoiceEvidenceRequest | dict[str, object]) -> CreatorVoiceEvidenceRequest:
        if isinstance(request, CreatorVoiceEvidenceRequest):
            normalized = request
        else:
            normalized = CreatorVoiceEvidenceRequest(**request)
        creator_id = str(normalized.creator_id or "").strip()
        if not creator_id:
            raise ValueError("El creator_id es obligatorio para construir evidencia de voz.")
        max_items = max(1, min(int(normalized.max_items), 100))
        max_items_per_source = max(1, min(int(normalized.max_items_per_source), 20))
        max_items_per_type = max(1, min(int(normalized.max_items_per_type), 20))
        return CreatorVoiceEvidenceRequest(
            creator_id=creator_id,
            project_id=str(normalized.project_id).strip() if normalized.project_id and str(normalized.project_id).strip() else None,
            workflow_type=_normalize_workflow(normalized.workflow_type),
            language=_language_key(normalized.language),
            include_historical_versions=bool(normalized.include_historical_versions),
            include_creator_global_when_project_scope=bool(normalized.include_creator_global_when_project_scope),
            include_creator_global_when_workflow_scope=bool(normalized.include_creator_global_when_workflow_scope),
            max_items=max_items,
            max_items_per_source=max_items_per_source,
            max_items_per_type=max_items_per_type,
        )


def build_creator_voice_evidence_service(
    *,
    corpus_repository: CreatorCorpusRepository,
    preference_repository: CreatorPreferenceRepository,
    project_repository: ProjectRepository | None = None,
    diff_service: CreatorRevisionDiffService | None = None,
    logger: logging.Logger | None = None,
) -> CreatorVoiceEvidenceService:
    return CreatorVoiceEvidenceService(
        corpus_repository=corpus_repository,
        preference_repository=preference_repository,
        project_repository=project_repository,
        diff_service=diff_service,
        logger=logger,
    )
