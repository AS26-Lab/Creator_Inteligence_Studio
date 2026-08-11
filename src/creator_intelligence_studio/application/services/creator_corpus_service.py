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
from creator_intelligence_studio.domain.creator_corpus.repositories import CreatorCorpusRepository
from creator_intelligence_studio.domain.creator_corpus.services import build_corpus_identity_fingerprint
from creator_intelligence_studio.domain.creator_corpus.value_objects import (
    CorpusDocumentStatus,
    CorpusDocumentType,
    CorpusProvenanceRelationType,
    CorpusSourceAssetStatus,
    CorpusSourceType,
    CorpusVersionSourceKind,
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
    return (value or "").strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        content_hash = _sha256_text(_normalize_text(content))
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
            size_bytes=len(content.encode("utf-8")),
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

    def archive_document(self, document_id: str) -> CorpusDocument:
        document = self.repository.archive_document(document_id)
        if document is None:
            raise NotFoundError("El documento del corpus no existe.")
        return document

    def mark_source_asset_missing(self, source_asset_id: str) -> CorpusSourceAsset:
        source_asset = self.repository.mark_source_asset_missing(source_asset_id)
        if source_asset is None:
            raise NotFoundError("La fuente del corpus no existe.")
        return source_asset

    def _document_identity_hash(
        self,
        *,
        creator_id: str,
        source_asset_id: str | None,
        project_id: str | None,
        document_type: CorpusDocumentType,
        title: str,
        language: str | None,
    ) -> str:
        return build_corpus_identity_fingerprint(
            {
                "creator_id": creator_id,
                "source_asset_id": source_asset_id,
                "project_id": project_id,
                "document_type": document_type.value,
                "title": _normalize_text(title),
                "language": language,
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
    ) -> tuple[CorpusDocument, bool]:
        document_identity_hash = self._document_identity_hash(
            creator_id=creator_id,
            source_asset_id=source_asset_id,
            project_id=project_id,
            document_type=document_type,
            title=title,
            language=language,
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
        source_reference_type: str | None = None,
        source_reference_id: str | None = None,
    ) -> tuple[CorpusSegment, ...]:
        persisted: list[CorpusSegment] = []
        for index, segment_payload in enumerate(segments):
            segment = CorpusSegment(
                id=str(segment_payload.get("id") or uuid4()),
                document_version_id=document_version_id,
                creator_id=creator_id,
                sequence=int(segment_payload.get("sequence", segment_payload.get("segment_index", index))),
                start_seconds=segment_payload.get("start_seconds"),
                end_seconds=segment_payload.get("end_seconds"),
                text=_normalize_text(str(segment_payload.get("text", ""))),
                confidence=segment_payload.get("confidence"),
                review_state=segment_payload.get("review_state"),
                source_reference_type=segment_payload.get("source_reference_type", source_reference_type),
                source_reference_id=segment_payload.get("source_reference_id", source_reference_id),
                metadata_json=_json_dumps(segment_payload.get("metadata", {})),
                created_at=utc_now(),
            )
            persisted.append(self.repository.upsert_segment(segment))
        return tuple(persisted)

    def _append_version(
        self,
        *,
        document: CorpusDocument,
        content: str,
        source_kind: CorpusVersionSourceKind,
        language: str | None,
        created_by: str | None,
        metadata: dict[str, object] | None,
        source_asset_id: str | None = None,
        parent_version_id: str | None = None,
        segments: list[dict[str, object]] | None = None,
        provenance_parent_type: str,
        provenance_parent_id: str,
        relation_type: CorpusProvenanceRelationType,
    ) -> tuple[CorpusDocument, CorpusDocumentVersion, tuple[CorpusSegment, ...], tuple[CorpusProvenanceEdge, ...], bool]:
        content = content or ""
        content_hash = _sha256_text(content)
        existing = self.repository.get_document_version_by_hash(document.id, content_hash)
        if existing is not None:
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
            return updated_document, existing, stored_segments, edges, False
        next_version_number = (self.repository.list_document_versions(document.id)[-1].version_number + 1) if self.repository.list_document_versions(document.id) else 1
        version = CorpusDocumentVersion(
            id=str(uuid4()),
            document_id=document.id,
            creator_id=document.creator_id,
            version_number=next_version_number,
            content=content,
            content_hash=content_hash,
            source_kind=source_kind,
            source_asset_id=source_asset_id or document.source_asset_id,
            parent_version_id=parent_version_id,
            language=language or document.language,
            created_by=created_by,
            metadata_json=_json_dumps(metadata or {}),
            created_at=utc_now(),
        )
        stored_version = self.repository.upsert_document_version(version)
        stored_segments = tuple(
            self._persist_segments(
                creator_id=document.creator_id,
                document_version_id=stored_version.id,
                segments=segments or [],
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
                current_version_id=stored_version.id,
                status=document.status,
                document_identity_hash=document.document_identity_hash,
                created_at=document.created_at,
                updated_at=utc_now(),
            )
        )
        return updated_document, stored_version, stored_segments, (stored_edge,), True

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
        resolved_document_type = CorpusDocumentType(document_type)
        resolved_source_kind = CorpusVersionSourceKind(source_kind)
        source_asset: CorpusSourceAsset | None = None
        if source_asset_id:
            source_asset = self.repository.get_source_asset(source_asset_id)
            if source_asset is None:
                raise NotFoundError("La fuente del corpus no existe.")
        elif source_asset_type is not None:
            source_asset = self._source_asset_for_text(
                creator_id=creator_id,
                project_id=project_id,
                original_name=source_asset_original_name or title,
                content=content,
                source_type=CorpusSourceType(source_asset_type),
                source_metadata=metadata,
            )
        document, created_document = self._ensure_document(
            creator_id=creator_id,
            document_type=resolved_document_type,
            title=title,
            language=language,
            project_id=project_id,
            source_asset_id=source_asset.id if source_asset else source_asset_id,
        )
        provenance_parent_type = "source_asset" if source_asset is not None else "external_text"
        provenance_parent_id = source_asset.id if source_asset is not None else build_corpus_identity_fingerprint(
            {
                "creator_id": creator_id,
                "project_id": project_id,
                "document_type": resolved_document_type.value,
                "title": _normalize_text(title),
                "language": language,
                "content": content,
            }
        )
        document, version, stored_segments, stored_edges, created_version = self._append_version(
            document=document,
            content=content,
            source_kind=resolved_source_kind,
            language=language,
            created_by=created_by,
            metadata=metadata,
            source_asset_id=source_asset.id if source_asset else source_asset_id,
            parent_version_id=None,
            segments=segments,
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
        )
        return CreatorCorpusIngestionResult(
            creator_id=creator_id,
            source_asset=source_asset,
            document=document,
            version=version,
            segments=stored_segments,
            provenance_edges=stored_edges,
            created_document=created_document,
            created_version=created_version,
        )

    def append_document_version(
        self,
        *,
        document_id: str,
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
        resolved_source_kind = CorpusVersionSourceKind(source_kind)
        last_versions = self.repository.list_document_versions(document_id)
        parent = self.repository.get_document_version(parent_version_id) if parent_version_id else (last_versions[-1] if last_versions else None)
        document, version, stored_segments, stored_edges, created_version = self._append_version(
            document=document,
            content=content,
            source_kind=resolved_source_kind,
            language=language or document.language,
            created_by=created_by,
            metadata=metadata,
            source_asset_id=document.source_asset_id,
            parent_version_id=parent.id if parent else None,
            segments=segments,
            provenance_parent_type="document_version" if parent else "external_edit",
            provenance_parent_id=parent.id if parent else build_corpus_identity_fingerprint(
                {
                    "document_id": document.id,
                    "content": content,
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
        )
        return CreatorCorpusIngestionResult(
            creator_id=document.creator_id,
            source_asset=self.repository.get_source_asset(document.source_asset_id) if document.source_asset_id else None,
            document=document,
            version=version,
            segments=stored_segments,
            provenance_edges=stored_edges,
            created_document=False,
            created_version=created_version,
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
            segment_payloads.append(
                {
                    "sequence": segment.segment_index,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": segment.text,
                    "confidence": segment.confidence,
                    "review_state": "transcribed",
                    "source_reference_type": "transcription_segment",
                    "source_reference_id": segment.id,
                }
            )
        return self.ingest_text_document(
            creator_id=creator_id,
            document_type=CorpusDocumentType.TRANSCRIPT,
            title=video.title,
            content=transcription.full_text,
            project_id=video.project_id,
            language=transcription.detected_language or transcription.requested_language,
            source_kind=CorpusVersionSourceKind.TRANSCRIPTION,
            source_asset_id=source_asset.id,
            created_by="system",
            metadata={
                "video_asset_id": video.id,
                "transcription_id": transcription.id,
                "engine": transcription.engine,
                "model_name": transcription.model_name,
                "model_version": transcription.model_version,
                "engine_version": transcription.engine_version,
                "segment_count": transcription.segment_count,
            },
            segments=segment_payloads,
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
