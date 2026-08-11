"""Servicio de aplicacion para Creator Corpus."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from creator_intelligence_studio.domain.creator_corpus.entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
)
from creator_intelligence_studio.domain.creator_corpus.ingestion import (
    CorpusEligibility,
    CorpusIngestionPolicy,
    CorpusIngestionRequest,
    CorpusIngestionResult,
    CorpusTextNormalizationResult,
)
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.creator_corpus.services import build_corpus_identity_fingerprint
from creator_intelligence_studio.domain.creator_corpus.normalization import (
    hash_corpus_text,
    normalize_corpus_language,
    normalize_corpus_text,
    normalize_corpus_title,
    normalize_segment_text,
)
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusAuthorshipClass,
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
    TEXT_NORMALIZATION_VERSION,
)
from creator_intelligence_studio.domain.errors import NotFoundError, ValidationError
from creator_intelligence_studio.domain.transcription.repositories import TranscriptionRepository
from creator_intelligence_studio.domain.projects.repositories import ProjectRepository
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _normalize_text(value: str | None) -> str:
    return normalize_corpus_text(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hash_corpus_text(value)


def _derive_authorship_class(source_kind: CorpusVersionSourceKind) -> CorpusAuthorshipClass:
    if source_kind == CorpusVersionSourceKind.TRANSCRIPTION:
        return CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH
    if source_kind == CorpusVersionSourceKind.USER_EDIT:
        return CorpusAuthorshipClass.CREATOR_EDITED
    if source_kind == CorpusVersionSourceKind.AI_GENERATED:
        return CorpusAuthorshipClass.AI_GENERATED
    if source_kind == CorpusVersionSourceKind.AI_REWRITE:
        return CorpusAuthorshipClass.AI_REWRITTEN
    if source_kind == CorpusVersionSourceKind.ORIGINAL:
        return CorpusAuthorshipClass.CREATOR_ORIGINAL
    return CorpusAuthorshipClass.IMPORTED_UNKNOWN


def _normalization_result(
    *,
    raw_content: str,
    normalized_content: str,
    quality_flags: tuple[str, ...],
) -> CorpusTextNormalizationResult:
    return CorpusTextNormalizationResult(
        raw_content=raw_content,
        normalized_content=normalized_content,
        normalization_version=TEXT_NORMALIZATION_VERSION,
        raw_content_hash=_sha256_text(raw_content),
        normalized_content_hash=_sha256_text(normalized_content),
        quality_flags=quality_flags,
    )


def _eligibility_for_version(
    *,
    authorship_class: CorpusAuthorshipClass,
    quality_flags: tuple[str, ...],
    archived: bool = False,
) -> CorpusEligibility:
    if archived:
        return CorpusEligibility(retrieval_eligible=False, voice_learning_eligible=False)
    retrieval_eligible = True
    voice_learning_eligible = authorship_class in {
        CorpusAuthorshipClass.CREATOR_ORIGINAL,
        CorpusAuthorshipClass.CREATOR_EDITED,
        CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH,
    }
    if "low_confidence_transcript" in quality_flags or "needs_review" in quality_flags:
        voice_learning_eligible = False
    if authorship_class == CorpusAuthorshipClass.IMPORTED_UNKNOWN:
        voice_learning_eligible = False
    return CorpusEligibility(retrieval_eligible=retrieval_eligible, voice_learning_eligible=voice_learning_eligible)


@dataclass(frozen=True, slots=True)
class CreatorCorpusIngestionResult:
    creator_id: str
    source_asset: CorpusSourceAsset | None
    document: CorpusDocument
    version: CorpusDocumentVersion
    segments: tuple[CorpusSegment, ...]
    provenance_edges: tuple[CorpusProvenanceEdge, ...]
    created_document: bool
    created_version: bool
    deduplicated: bool
    normalization: CorpusTextNormalizationResult
    eligibility: CorpusEligibility
    quality_flags: tuple[str, ...]
    corpus_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "source_asset": self.source_asset.to_dict() if self.source_asset else None,
            "document": self.document.to_dict(),
            "version": self.version.to_dict(),
            "segments": [item.to_dict() for item in self.segments],
            "provenance_edges": [item.to_dict() for item in self.provenance_edges],
            "created_document": self.created_document,
            "created_version": self.created_version,
            "deduplicated": self.deduplicated,
            "normalization": self.normalization.to_dict(),
            "eligibility": self.eligibility.to_dict(),
            "quality_flags": list(self.quality_flags),
            "corpus_message": self.corpus_message,
        }


@dataclass(frozen=True, slots=True)
class CreatorCorpusStatus:
    creator_id: str
    source_asset_count: int
    document_count: int
    version_count: int
    segment_count: int
    provenance_count: int
    archived_document_count: int
    missing_source_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "creator_id": self.creator_id,
            "source_asset_count": self.source_asset_count,
            "document_count": self.document_count,
            "version_count": self.version_count,
            "segment_count": self.segment_count,
            "provenance_count": self.provenance_count,
            "archived_document_count": self.archived_document_count,
            "missing_source_count": self.missing_source_count,
        }


class CreatorCorpusService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        repository: CreatorCorpusRepository,
        project_repository: ProjectRepository | None = None,
        video_repository: VideoRepository | None = None,
        transcription_repository: TranscriptionRepository | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.repository = repository
        self.project_repository = project_repository
        self.video_repository = video_repository
        self.transcription_repository = transcription_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio.creator_corpus")

    def _source_asset_for_text(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        original_name: str,
        content: str,
        source_type: CorpusSourceType,
        mime_type: str | None = "text/plain",
        source_metadata: dict[str, object] | None = None,
    ) -> CorpusSourceAsset:
        raw_content = content or ""
        content_hash = _sha256_text(raw_content)
        existing = self.repository.get_source_asset_by_hash(creator_id, content_hash)
        if existing is not None:
            return existing
        now = utc_now()
        asset = CorpusSourceAsset(
            id=str(uuid4()),
            creator_id=creator_id,
            project_id=project_id,
            source_type=source_type,
            original_name=original_name,
            local_path=None,
            content_hash=content_hash,
            size_bytes=len(raw_content.encode("utf-8")),
            mime_type=mime_type,
            status=CorpusSourceAssetStatus.ACTIVE,
            source_metadata_json=_json_dumps(source_metadata or {}),
            created_at=now,
            imported_at=now,
            updated_at=now,
        )
        return self.repository.upsert_source_asset(asset)

    def register_source_asset(
        self,
        *,
        creator_id: str,
        source_type: str | CorpusSourceType,
        original_name: str,
        local_path: str | None = None,
        content_hash: str | None = None,
        size_bytes: int | None = None,
        mime_type: str | None = None,
        project_id: str | None = None,
        source_metadata: dict[str, object] | None = None,
        status: str | CorpusSourceAssetStatus = CorpusSourceAssetStatus.ACTIVE,
    ) -> CorpusSourceAsset:
        resolved_source_type = CorpusSourceType(source_type)
        resolved_original_name = _normalize_text(original_name)
        if not resolved_original_name:
            raise ValidationError("El nombre original de la fuente no puede estar vacio.")
        resolved_local_path = str(Path(local_path).resolve()) if local_path else None
        resolved_hash = content_hash
        if resolved_hash is None:
            if resolved_local_path is None:
                raise ValidationError("Se requiere local_path o content_hash para registrar la fuente.")
            source_path = Path(resolved_local_path)
            if not source_path.exists():
                raise NotFoundError("La fuente local no existe.")
            resolved_hash = _sha256_file(source_path)
            if size_bytes is None:
                size_bytes = source_path.stat().st_size
        if size_bytes is None:
            raise ValidationError("Se requiere size_bytes para registrar la fuente.")
        existing = self.repository.get_source_asset_by_hash(creator_id, resolved_hash)
        if existing is not None:
            return existing
        now = utc_now()
        asset = CorpusSourceAsset(
            id=str(uuid4()),
            creator_id=creator_id,
            project_id=project_id,
            source_type=resolved_source_type,
            original_name=resolved_original_name,
            local_path=resolved_local_path,
            content_hash=resolved_hash,
            size_bytes=int(size_bytes),
            mime_type=mime_type,
            status=CorpusSourceAssetStatus(status),
            source_metadata_json=_json_dumps(source_metadata or {}),
            created_at=now,
            imported_at=now,
            updated_at=now,
        )
        return self.repository.upsert_source_asset(asset)

    def list_source_assets(self, creator_id: str, project_id: str | None = None) -> list[CorpusSourceAsset]:
        return self.repository.list_source_assets(creator_id, project_id)

    def get_source_asset(self, source_asset_id: str) -> CorpusSourceAsset | None:
        return self.repository.get_source_asset(source_asset_id)

    def list_documents(self, creator_id: str, project_id: str | None = None) -> list[CorpusDocument]:
        return self.repository.list_documents(creator_id, project_id)

    def get_document(self, document_id: str) -> CorpusDocument | None:
        return self.repository.get_document(document_id)

    def list_versions(self, document_id: str) -> list[CorpusDocumentVersion]:
        return self.repository.list_document_versions(document_id)

    def list_segments(self, document_version_id: str) -> list[CorpusSegment]:
        return self.repository.list_segments(document_version_id)

    def list_provenance_edges(self, document_version_id: str) -> list[CorpusProvenanceEdge]:
        return self.repository.list_provenance_edges(document_version_id)

    def get_status(self, creator_id: str) -> CreatorCorpusStatus:
        source_assets = self.repository.list_source_assets(creator_id)
        documents = self.repository.list_documents(creator_id)
        versions = [version for document in documents for version in self.repository.list_document_versions(document.id)]
        segments = [segment for version in versions for segment in self.repository.list_segments(version.id)]
        provenance = [edge for version in versions for edge in self.repository.list_provenance_edges(version.id)]
        return CreatorCorpusStatus(
            creator_id=creator_id,
            source_asset_count=len(source_assets),
            document_count=len(documents),
            version_count=len(versions),
            segment_count=len(segments),
            provenance_count=len(provenance),
            archived_document_count=sum(1 for document in documents if document.status == CorpusDocumentStatus.ARCHIVED),
            missing_source_count=sum(1 for asset in source_assets if asset.status == CorpusSourceAssetStatus.MISSING),
        )

    def archive_document(self, document_id: str, *, creator_id: str | None = None) -> CorpusDocument:
        document = self.repository.archive_document(document_id)
        if document is None:
            raise NotFoundError("El documento del corpus no existe.")
        if creator_id is not None and document.creator_id != creator_id:
            raise ValidationError("El documento no pertenece al creador activo.")
        self.repository.refresh_retrieval_index_for_document(document.id)
        return document

    def mark_source_asset_missing(self, source_asset_id: str, *, creator_id: str | None = None) -> CorpusSourceAsset:
        source_asset = self.repository.mark_source_asset_missing(source_asset_id)
        if source_asset is None:
            raise NotFoundError("La fuente del corpus no existe.")
        if creator_id is not None and source_asset.creator_id != creator_id:
            raise ValidationError("La fuente no pertenece al creador activo.")
        return source_asset

    def _normalize_ingestion_content(
        self,
        content: str | None,
        *,
        source_kind: CorpusVersionSourceKind,
        language: str | None = None,
    ) -> CorpusTextNormalizationResult:
        raw_content = content or ""
        normalized_content = _normalize_text(raw_content)
        quality_flags = self._content_quality_flags(
            raw_content=raw_content,
            normalized_content=normalized_content,
            source_kind=source_kind,
            language=language,
        )
        return _normalization_result(
            raw_content=raw_content,
            normalized_content=normalized_content,
            quality_flags=quality_flags,
        )

    def _content_quality_flags(
        self,
        *,
        raw_content: str,
        normalized_content: str,
        source_kind: CorpusVersionSourceKind,
        language: str | None = None,
    ) -> tuple[str, ...]:
        flags: list[str] = []
        if not normalized_content:
            flags.append("empty")
        word_count = len(normalized_content.split())
        if normalized_content and word_count < 3:
            flags.append("too_short")
        alnum_count = sum(1 for char in normalized_content if char.isalnum())
        if normalized_content and alnum_count / max(1, len(normalized_content)) < 0.25:
            flags.append("mostly_non_text")
        if not normalize_corpus_language(language):
            flags.append("missing_language")
        if source_kind == CorpusVersionSourceKind.TRANSCRIPTION and not raw_content.strip():
            flags.append("low_confidence_transcript")
        return tuple(dict.fromkeys(flags))

    def _segment_quality_flags(self, *, confidence: float | None, review_state: str | None, normalized_text: str) -> tuple[str, ...]:
        flags: list[str] = []
        if not normalized_text:
            flags.append("empty")
        if confidence is not None and confidence < 0.8:
            flags.append("low_confidence_transcript")
        if review_state and review_state.strip().lower() in {"needs_review", "low_confidence", "excluded"}:
            flags.append("needs_review")
        if normalized_text and len(normalized_text.split()) < 2:
            flags.append("too_short")
        return tuple(dict.fromkeys(flags))

    def _eligibility_for_segment(
        self,
        *,
        authorship_class: CorpusAuthorshipClass,
        quality_flags: tuple[str, ...],
        archived: bool = False,
    ) -> CorpusEligibility:
        eligibility = _eligibility_for_version(authorship_class=authorship_class, quality_flags=quality_flags, archived=archived)
        if "low_confidence_transcript" in quality_flags:
            return CorpusEligibility(
                retrieval_eligible=eligibility.retrieval_eligible,
                voice_learning_eligible=False,
            )
        return eligibility

    def _prepare_source_reference(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        document_type: CorpusDocumentType,
        title: str,
        language: str | None,
        source_reference: str | None,
        source_asset_type: CorpusSourceType | None,
        source_asset_original_name: str | None,
        content: str,
        metadata: dict[str, object] | None,
    ) -> CorpusSourceAsset | None:
        if source_reference is not None and source_reference.strip():
            return None
        if source_asset_type is None:
            return None
        original_name = source_asset_original_name or title or document_type.value
        return self._source_asset_for_text(
            creator_id=creator_id,
            project_id=project_id,
            original_name=original_name,
            content=content,
            source_type=CorpusSourceType(source_asset_type),
            source_metadata={
                **(metadata or {}),
                "source_reference": source_reference,
                "document_type": document_type.value,
                "title": title,
                "language": language,
            },
        )

    def _document_identity_hash(
        self,
        *,
        creator_id: str,
        project_id: str | None,
        document_type: CorpusDocumentType,
        title: str,
        language: str | None,
        content_hash: str,
    ) -> str:
        return build_corpus_identity_fingerprint(
            {
                "creator_id": creator_id,
                "project_id": project_id,
                "document_type": document_type.value,
                "title": _normalize_text(title),
                "language": language,
                "content_hash": content_hash,
            }
        )

    def _ensure_document(
        self,
        *,
        creator_id: str,
        document_type: CorpusDocumentType,
        title: str,
        language: str | None,
        project_id: str | None,
        source_asset_id: str | None,
        content_hash: str,
    ) -> tuple[CorpusDocument, bool]:
        document_identity_hash = self._document_identity_hash(
            creator_id=creator_id,
            project_id=project_id,
            document_type=document_type,
            title=title,
            language=language,
            content_hash=content_hash,
        )
        existing = self.repository.get_document_by_identity_hash(creator_id, document_identity_hash)
        if existing is not None:
            return existing, False
        now = utc_now()
        document = CorpusDocument(
            id=str(uuid4()),
            creator_id=creator_id,
            source_asset_id=source_asset_id,
            project_id=project_id,
            document_type=document_type,
            title=_normalize_text(title),
            language=language,
            current_version_id=None,
            status=CorpusDocumentStatus.ACTIVE,
            document_identity_hash=document_identity_hash,
            created_at=now,
            updated_at=now,
        )
        return self.repository.upsert_document(document), True

    def _persist_segments(
        self,
        *,
        creator_id: str,
        document_version_id: str,
        segments: list[dict[str, object]],
        authorship_class: CorpusAuthorshipClass,
        source_reference_type: str | None = None,
        source_reference_id: str | None = None,
    ) -> tuple[CorpusSegment, ...]:
        persisted: list[CorpusSegment] = []
        for index, segment_payload in enumerate(segments):
            raw_text = _normalize_text(str(segment_payload.get("raw_text", segment_payload.get("text", ""))))
            normalized_text = _normalize_text(str(segment_payload.get("normalized_text", segment_payload.get("text", raw_text))))
            confidence = segment_payload.get("confidence")
            review_state = segment_payload.get("review_state")
            quality_flags = tuple(segment_payload.get("quality_flags", ()))
            if not quality_flags:
                quality_flags = self._segment_quality_flags(confidence=confidence, review_state=review_state, normalized_text=normalized_text)
            eligibility = self._eligibility_for_segment(
                authorship_class=authorship_class,
                quality_flags=quality_flags,
            )
            segment = CorpusSegment(
                id=str(segment_payload.get("id") or uuid4()),
                document_version_id=document_version_id,
                creator_id=creator_id,
                sequence=int(segment_payload.get("sequence", segment_payload.get("segment_index", index))),
                start_seconds=segment_payload.get("start_seconds"),
                end_seconds=segment_payload.get("end_seconds"),
                text=normalized_text,
                raw_text=raw_text,
                confidence=confidence,
                review_state=review_state,
                normalization_version=str(segment_payload.get("normalization_version") or TEXT_NORMALIZATION_VERSION),
                retrieval_eligible=bool(segment_payload.get("retrieval_eligible", eligibility.retrieval_eligible)),
                voice_learning_eligible=bool(segment_payload.get("voice_learning_eligible", eligibility.voice_learning_eligible)),
                quality_flags=quality_flags,
                source_reference_type=segment_payload.get("source_reference_type", source_reference_type),
                source_reference_id=segment_payload.get("source_reference_id", source_reference_id),
                metadata_json=_json_dumps(
                    {
                        **(segment_payload.get("metadata", {}) if isinstance(segment_payload.get("metadata", {}), dict) else {}),
                        "raw_text": raw_text,
                        "normalized_text": normalized_text,
                        "normalization_version": str(segment_payload.get("normalization_version") or TEXT_NORMALIZATION_VERSION),
                        "retrieval_eligible": bool(segment_payload.get("retrieval_eligible", eligibility.retrieval_eligible)),
                        "voice_learning_eligible": bool(segment_payload.get("voice_learning_eligible", eligibility.voice_learning_eligible)),
                        "quality_flags": list(quality_flags),
                    }
                ),
                created_at=utc_now(),
            )
            persisted.append(self.repository.upsert_segment(segment))
        return tuple(persisted)

    def _append_version(
        self,
        *,
        document: CorpusDocument,
        content: str,
        normalized_content: str,
        normalization: CorpusTextNormalizationResult,
        source_kind: CorpusVersionSourceKind,
        language: str | None,
        created_by: str | None,
        metadata: dict[str, object] | None,
        authorship_class: CorpusAuthorshipClass,
        eligibility: CorpusEligibility,
        quality_flags: tuple[str, ...],
        source_asset_id: str | None = None,
        parent_version_id: str | None = None,
        segments: list[dict[str, object]] | None = None,
        provenance_parent_type: str,
        provenance_parent_id: str,
        relation_type: CorpusProvenanceRelationType,
        promote_current: bool = True,
    ) -> tuple[CorpusDocument, CorpusDocumentVersion, tuple[CorpusSegment, ...], tuple[CorpusProvenanceEdge, ...], bool]:
        raw_content = content or ""
        normalized_content = normalized_content or normalize_corpus_text(raw_content)
        content_hash = normalization.normalized_content_hash
        existing = self.repository.get_document_version_by_hash(document.id, content_hash)
        if existing is not None:
            updated_document = document
            if promote_current and document.current_version_id != existing.id:
                updated_document = self.repository.upsert_document(
                    CorpusDocument(
                        id=document.id,
                        creator_id=document.creator_id,
                        source_asset_id=document.source_asset_id,
                        project_id=document.project_id,
                        document_type=document.document_type,
                        title=document.title,
                        language=language or document.language,
                        current_version_id=existing.id,
                        status=document.status,
                        document_identity_hash=document.document_identity_hash,
                        created_at=document.created_at,
                        updated_at=utc_now(),
                    )
                )
            edges = tuple(self.repository.list_provenance_edges(existing.id))
            stored_segments = tuple(self.repository.list_segments(existing.id))
            self.repository.refresh_retrieval_index_for_document(document.id)
            return updated_document, existing, stored_segments, edges, False
        versions = self.repository.list_document_versions(document.id)
        next_version_number = versions[-1].version_number + 1 if versions else 1
        version = CorpusDocumentVersion(
            id=str(uuid4()),
            document_id=document.id,
            creator_id=document.creator_id,
            version_number=next_version_number,
            content=raw_content,
            content_hash=content_hash,
            raw_content=raw_content,
            normalized_content=normalized_content,
            raw_content_hash=normalization.raw_content_hash,
            normalization_version=normalization.normalization_version,
            authorship_class=authorship_class,
            retrieval_eligible=eligibility.retrieval_eligible,
            voice_learning_eligible=eligibility.voice_learning_eligible,
            quality_flags=quality_flags,
            source_kind=source_kind,
            source_asset_id=source_asset_id or document.source_asset_id,
            parent_version_id=parent_version_id,
            language=language or document.language,
            created_by=created_by,
            metadata_json=_json_dumps(
                {
                    **(metadata or {}),
                    "raw_content": raw_content,
                    "normalized_content": normalized_content,
                    "raw_content_hash": normalization.raw_content_hash,
                    "normalized_content_hash": normalization.normalized_content_hash,
                    "normalization_version": normalization.normalization_version,
                    "authorship_class": authorship_class.value,
                    "retrieval_eligible": eligibility.retrieval_eligible,
                    "voice_learning_eligible": eligibility.voice_learning_eligible,
                    "quality_flags": list(quality_flags),
                }
            ),
            created_at=utc_now(),
        )
        stored_version = self.repository.upsert_document_version(version)
        stored_segments = tuple(
            self._persist_segments(
                creator_id=document.creator_id,
                document_version_id=stored_version.id,
                segments=segments or [],
                authorship_class=authorship_class,
                source_reference_type="transcription_segment" if source_kind == CorpusVersionSourceKind.TRANSCRIPTION else None,
            )
        )
        provenance_edge = CorpusProvenanceEdge(
            id=str(uuid4()),
            creator_id=document.creator_id,
            parent_type=provenance_parent_type,
            parent_id=provenance_parent_id,
            child_version_id=stored_version.id,
            relation_type=relation_type,
            metadata_json=_json_dumps(metadata or {}),
            created_at=utc_now(),
        )
        stored_edge = self.repository.upsert_provenance_edge(provenance_edge)
        updated_document = self.repository.upsert_document(
            CorpusDocument(
                id=document.id,
                creator_id=document.creator_id,
                source_asset_id=document.source_asset_id,
                project_id=document.project_id,
                document_type=document.document_type,
                title=document.title,
                language=language or document.language,
                current_version_id=stored_version.id if promote_current else document.current_version_id,
                status=document.status,
                document_identity_hash=document.document_identity_hash,
                created_at=document.created_at,
                updated_at=utc_now(),
            )
        )
        self.repository.refresh_retrieval_index_for_document(document.id)
        return updated_document, stored_version, stored_segments, (stored_edge,), True

    def ingest_request(self, request: CorpusIngestionRequest) -> CreatorCorpusIngestionResult:
        resolved_document_type = CorpusDocumentType(request.document_type)
        resolved_source_kind = CorpusVersionSourceKind(request.source_kind)
        normalized_title = normalize_corpus_title(request.title) or request.source_reference or resolved_document_type.value
        normalized_language = normalize_corpus_language(request.language)
        normalization = self._normalize_ingestion_content(request.content, source_kind=resolved_source_kind, language=normalized_language)
        authorship_class = request.authorship_class or _derive_authorship_class(resolved_source_kind)
        quality_flags = tuple(
            dict.fromkeys(
                (
                    *normalization.quality_flags,
                    *(("source_missing",) if request.source_asset_id is None and not request.source_reference and resolved_source_kind == CorpusVersionSourceKind.TRANSCRIPTION else ()),
                )
            )
        )
        eligibility = _eligibility_for_version(
            authorship_class=authorship_class,
            quality_flags=quality_flags,
        )
        source_asset: CorpusSourceAsset | None = None
        if request.source_asset_id:
            source_asset = self.repository.get_source_asset(request.source_asset_id)
            if source_asset is None:
                raise NotFoundError("La fuente del corpus no existe.")
            if source_asset.creator_id != request.creator_id:
                raise ValidationError("La fuente no pertenece al creador activo.")
        elif request.source_type:
            source_asset_type = CorpusSourceType(request.source_type)
            if source_asset_type in {CorpusSourceType.IMPORTED_TEXT, CorpusSourceType.MANUAL_TEXT, CorpusSourceType.TRANSCRIPT, CorpusSourceType.SCRIPT, CorpusSourceType.CAPTION, CorpusSourceType.NOTE, CorpusSourceType.FUTURE_DOCUMENT}:
                source_asset = self._source_asset_for_text(
                    creator_id=request.creator_id,
                    project_id=request.project_id,
                    original_name=normalize_corpus_title(request.source_reference or request.title or resolved_document_type.value) or resolved_document_type.value,
                    content=request.content,
                    source_type=source_asset_type,
                    source_metadata={
                        **(request.metadata or {}),
                        "source_reference": request.source_reference,
                        "source_kind": resolved_source_kind.value,
                        "normalization_version": normalization.normalization_version,
                    },
                )
        document_identity_key = normalization.normalized_content_hash
        if source_asset is not None and (
            resolved_source_kind == CorpusVersionSourceKind.TRANSCRIPTION
            or source_asset.source_type in {CorpusSourceType.VIDEO, CorpusSourceType.AUDIO}
        ):
            document_identity_key = source_asset.id
        document, created_document = self._ensure_document(
            creator_id=request.creator_id,
            document_type=resolved_document_type,
            title=normalized_title,
            language=normalized_language,
            project_id=request.project_id,
            source_asset_id=source_asset.id if source_asset else request.source_asset_id,
            content_hash=document_identity_key,
        )
        provenance_parent_type = "source_asset" if source_asset is not None else "external_text"
        provenance_parent_id = source_asset.id if source_asset is not None else build_corpus_identity_fingerprint(
            {
                "creator_id": request.creator_id,
                "project_id": request.project_id,
                "document_type": resolved_document_type.value,
                "title": normalized_title,
                "language": normalized_language,
                "content_hash": normalization.normalized_content_hash,
                "source_reference": request.source_reference,
            }
        )
        metadata = {
            **(request.metadata or {}),
            "source_reference": request.source_reference,
            "source_type": request.source_type,
            "ingestion_policy": request.ingestion_policy.value,
            "normalization_version": normalization.normalization_version,
            "raw_content_hash": normalization.raw_content_hash,
            "normalized_content_hash": normalization.normalized_content_hash,
            "authorship_class": authorship_class.value,
            "retrieval_eligible": eligibility.retrieval_eligible,
            "voice_learning_eligible": eligibility.voice_learning_eligible,
            "quality_flags": list(quality_flags),
        }
        document, version, stored_segments, stored_edges, created_version = self._append_version(
            document=document,
            content=normalization.raw_content,
            normalized_content=normalization.normalized_content,
            normalization=normalization,
            source_kind=resolved_source_kind,
            language=normalized_language,
            created_by=request.created_by,
            metadata=metadata,
            authorship_class=authorship_class,
            eligibility=eligibility,
            quality_flags=quality_flags,
            source_asset_id=source_asset.id if source_asset else request.source_asset_id,
            parent_version_id=None,
            segments=list(request.segments),
            provenance_parent_type=provenance_parent_type,
            provenance_parent_id=provenance_parent_id,
            relation_type=(
                CorpusProvenanceRelationType.TRANSCRIBED_FROM
                if resolved_source_kind == CorpusVersionSourceKind.TRANSCRIPTION
                else CorpusProvenanceRelationType.EDITED_FROM
                if resolved_source_kind == CorpusVersionSourceKind.USER_EDIT
                else CorpusProvenanceRelationType.GENERATED_FROM
                if resolved_source_kind in {CorpusVersionSourceKind.AI_GENERATED, CorpusVersionSourceKind.AI_REWRITE}
                else CorpusProvenanceRelationType.IMPORTED_FROM
            ),
            promote_current=request.promote_current if request.promote_current is not None else resolved_source_kind not in {CorpusVersionSourceKind.AI_GENERATED, CorpusVersionSourceKind.AI_REWRITE},
        )
        corpus_message = "Ya estaba en tu corpus" if not created_version else "Guardado en tu corpus"
        return CreatorCorpusIngestionResult(
            creator_id=request.creator_id,
            source_asset=source_asset,
            document=document,
            version=version,
            segments=stored_segments,
            provenance_edges=stored_edges,
            created_document=created_document,
            created_version=created_version,
            deduplicated=not created_version,
            normalization=normalization,
            eligibility=eligibility,
            quality_flags=quality_flags,
            corpus_message=corpus_message,
        )

    def ingest_text_document(
        self,
        *,
        creator_id: str,
        document_type: str | CorpusDocumentType,
        title: str,
        content: str,
        project_id: str | None = None,
        language: str | None = None,
        source_kind: str | CorpusVersionSourceKind = CorpusVersionSourceKind.IMPORT,
        source_asset_type: str | CorpusSourceType | None = None,
        source_asset_original_name: str | None = None,
        source_asset_id: str | None = None,
        created_by: str | None = "system",
        metadata: dict[str, object] | None = None,
        segments: list[dict[str, object]] | None = None,
    ) -> CreatorCorpusIngestionResult:
        request = CorpusIngestionRequest(
            creator_id=creator_id,
            source_type=source_asset_type.value if isinstance(source_asset_type, CorpusSourceType) else str(source_asset_type or CorpusSourceType.IMPORTED_TEXT.value),
            source_reference=source_asset_original_name or title,
            document_type=CorpusDocumentType(document_type).value,
            title=title,
            language=language,
            content=content,
            segments=tuple(segments or ()),
            source_kind=CorpusVersionSourceKind(source_kind).value,
            project_id=project_id,
            metadata=metadata,
            source_asset_id=source_asset_id,
            created_by=created_by,
        )
        return self.ingest_request(request)

    def append_document_version(
        self,
        *,
        document_id: str,
        creator_id: str,
        content: str,
        source_kind: str | CorpusVersionSourceKind,
        language: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, object] | None = None,
        segments: list[dict[str, object]] | None = None,
        parent_version_id: str | None = None,
    ) -> CreatorCorpusIngestionResult:
        document = self.repository.get_document(document_id)
        if document is None:
            raise NotFoundError("El documento del corpus no existe.")
        if document.creator_id != creator_id:
            raise ValidationError("El documento no pertenece al creador activo.")
        resolved_source_kind = CorpusVersionSourceKind(source_kind)
        last_versions = self.repository.list_document_versions(document_id)
        parent = self.repository.get_document_version(parent_version_id) if parent_version_id else (last_versions[-1] if last_versions else None)
        normalization = self._normalize_ingestion_content(content, source_kind=resolved_source_kind, language=normalize_corpus_language(language or document.language))
        quality_flags = normalization.quality_flags
        authorship_class = _derive_authorship_class(resolved_source_kind)
        eligibility = _eligibility_for_version(authorship_class=authorship_class, quality_flags=quality_flags)
        document, version, stored_segments, stored_edges, created_version = self._append_version(
            document=document,
            content=normalization.raw_content,
            normalized_content=normalization.normalized_content,
            normalization=normalization,
            source_kind=resolved_source_kind,
            language=normalize_corpus_language(language or document.language),
            created_by=created_by,
            metadata=metadata,
            authorship_class=authorship_class,
            eligibility=eligibility,
            quality_flags=quality_flags,
            source_asset_id=document.source_asset_id,
            parent_version_id=parent.id if parent else None,
            segments=segments,
            provenance_parent_type="document_version" if parent else "external_edit",
            provenance_parent_id=parent.id if parent else build_corpus_identity_fingerprint(
                {
                    "document_id": document.id,
                    "content_hash": normalization.normalized_content_hash,
                    "source_kind": resolved_source_kind.value,
                }
            ),
            relation_type=(
                CorpusProvenanceRelationType.EDITED_FROM
                if resolved_source_kind == CorpusVersionSourceKind.USER_EDIT
                else CorpusProvenanceRelationType.GENERATED_FROM
                if resolved_source_kind in {CorpusVersionSourceKind.AI_GENERATED, CorpusVersionSourceKind.AI_REWRITE}
                else CorpusProvenanceRelationType.DERIVED_FROM
            ),
            promote_current=resolved_source_kind not in {CorpusVersionSourceKind.AI_GENERATED, CorpusVersionSourceKind.AI_REWRITE},
        )
        return CreatorCorpusIngestionResult(
            creator_id=creator_id,
            source_asset=self.repository.get_source_asset(document.source_asset_id) if document.source_asset_id else None,
            document=document,
            version=version,
            segments=stored_segments,
            provenance_edges=stored_edges,
            created_document=False,
            created_version=created_version,
            deduplicated=not created_version,
            normalization=normalization,
            eligibility=eligibility,
            quality_flags=quality_flags,
            corpus_message="Ya estaba en tu corpus" if not created_version else "Guardado en tu corpus",
        )

    def ingest_transcription(self, video_asset_id: str) -> CreatorCorpusIngestionResult:
        if self.project_repository is None or self.video_repository is None or self.transcription_repository is None:
            raise ValidationError("El bridge de transcripcion requiere repositorios de video y transcripcion.")
        video = self.video_repository.get_by_id(video_asset_id)
        if video is None:
            raise NotFoundError("El video no existe.")
        project = self.project_repository.get_by_id(video.project_id)
        if project is None:
            raise NotFoundError("El proyecto del video no existe.")
        transcription = self.transcription_repository.get_by_video_asset_id(video_asset_id)
        if transcription is None:
            raise NotFoundError("La transcripcion no existe.")
        if not Path(video.source_path).exists():
            raise NotFoundError("El archivo fuente ya no esta disponible.")
        creator_id = project.creator_id
        source_asset = self.register_source_asset(
            creator_id=creator_id,
            source_type=CorpusSourceType.VIDEO,
            original_name=video.original_filename,
            local_path=video.source_path,
            size_bytes=video.file_size_bytes,
            mime_type=None,
            project_id=video.project_id,
            source_metadata={
                "video_asset_id": video.id,
                "title": video.title,
                "file_available": video.file_available,
            },
        )
        transcription_segments = self.transcription_repository.list_segments(transcription.id)
        segment_payloads: list[dict[str, object]] = []
        for segment in transcription_segments:
            normalized_segment_text = normalize_segment_text(segment.text)
            segment_quality_flags = self._segment_quality_flags(
                confidence=segment.confidence,
                review_state="transcribed",
                normalized_text=normalized_segment_text,
            )
            segment_payloads.append(
                {
                    "sequence": segment.segment_index,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": normalized_segment_text,
                    "raw_text": segment.text,
                    "normalized_text": normalized_segment_text,
                    "confidence": segment.confidence,
                    "review_state": "transcribed",
                    "normalization_version": TEXT_NORMALIZATION_VERSION,
                    "quality_flags": segment_quality_flags,
                    "retrieval_eligible": True,
                    "voice_learning_eligible": "low_confidence_transcript" not in segment_quality_flags,
                    "source_reference_type": "transcription_segment",
                    "source_reference_id": segment.id,
                }
            )
        return self.ingest_request(
            CorpusIngestionRequest(
                creator_id=creator_id,
                source_type=CorpusSourceType.VIDEO.value,
                source_reference=video.source_path,
                document_type=CorpusDocumentType.TRANSCRIPT.value,
                title=video.title,
                language=transcription.detected_language or transcription.requested_language,
                content=transcription.full_text,
                segments=tuple(segment_payloads),
                source_kind=CorpusVersionSourceKind.TRANSCRIPTION.value,
                project_id=video.project_id,
                metadata={
                    "video_asset_id": video.id,
                    "transcription_id": transcription.id,
                    "engine": transcription.engine,
                    "model_name": transcription.model_name,
                    "model_version": transcription.model_version,
                    "engine_version": transcription.engine_version,
                    "segment_count": transcription.segment_count,
                },
                source_asset_id=source_asset.id,
                created_by="system",
                authorship_class=CorpusAuthorshipClass.TRANSCRIBED_CREATOR_SPEECH,
                promote_current=True,
            )
        )


def build_creator_corpus_service(
    *,
    settings: AppSettings,
    paths: ProjectPaths,
    repository: CreatorCorpusRepository,
    video_repository: VideoRepository | None = None,
    transcription_repository: TranscriptionRepository | None = None,
    project_repository: ProjectRepository | None = None,
    logger: logging.Logger | None = None,
) -> CreatorCorpusService:
    return CreatorCorpusService(
        settings=settings,
        paths=paths,
        repository=repository,
        project_repository=project_repository,
        video_repository=video_repository,
        transcription_repository=transcription_repository,
        logger=logger,
    )
