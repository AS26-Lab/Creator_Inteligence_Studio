"""Contratos de persistencia para Creator Corpus."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import (
    CorpusDocument,
    CorpusDocumentVersion,
    CorpusProvenanceEdge,
    CorpusSegment,
    CorpusSourceAsset,
)
from .retrieval import CorpusRetrievalIndexHealth, CorpusRetrievalQuery


class CreatorCorpusRepository(ABC):
    @abstractmethod
    def upsert_source_asset(self, asset: CorpusSourceAsset) -> CorpusSourceAsset:
        raise NotImplementedError

    @abstractmethod
    def get_source_asset(self, source_asset_id: str) -> CorpusSourceAsset | None:
        raise NotImplementedError

    @abstractmethod
    def get_source_asset_by_hash(self, creator_id: str, content_hash: str) -> CorpusSourceAsset | None:
        raise NotImplementedError

    @abstractmethod
    def list_source_assets(self, creator_id: str, project_id: str | None = None) -> list[CorpusSourceAsset]:
        raise NotImplementedError

    @abstractmethod
    def upsert_document(self, document: CorpusDocument) -> CorpusDocument:
        raise NotImplementedError

    @abstractmethod
    def get_document(self, document_id: str) -> CorpusDocument | None:
        raise NotImplementedError

    @abstractmethod
    def list_documents(self, creator_id: str, project_id: str | None = None) -> list[CorpusDocument]:
        raise NotImplementedError

    @abstractmethod
    def get_document_by_identity_hash(self, creator_id: str, document_identity_hash: str) -> CorpusDocument | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_document_version(self, version: CorpusDocumentVersion) -> CorpusDocumentVersion:
        raise NotImplementedError

    @abstractmethod
    def get_document_version(self, version_id: str) -> CorpusDocumentVersion | None:
        raise NotImplementedError

    @abstractmethod
    def list_document_versions(self, document_id: str) -> list[CorpusDocumentVersion]:
        raise NotImplementedError

    @abstractmethod
    def list_document_versions_for_creator(self, creator_id: str, project_id: str | None = None) -> list[CorpusDocumentVersion]:
        raise NotImplementedError

    @abstractmethod
    def get_document_version_by_hash(self, document_id: str, content_hash: str) -> CorpusDocumentVersion | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_segment(self, segment: CorpusSegment) -> CorpusSegment:
        raise NotImplementedError

    @abstractmethod
    def list_segments(self, document_version_id: str) -> list[CorpusSegment]:
        raise NotImplementedError

    @abstractmethod
    def list_segments_for_creator(self, creator_id: str, project_id: str | None = None) -> list[CorpusSegment]:
        raise NotImplementedError

    @abstractmethod
    def upsert_provenance_edge(self, edge: CorpusProvenanceEdge) -> CorpusProvenanceEdge:
        raise NotImplementedError

    @abstractmethod
    def list_provenance_edges(self, document_version_id: str) -> list[CorpusProvenanceEdge]:
        raise NotImplementedError

    @abstractmethod
    def archive_document(self, document_id: str) -> CorpusDocument | None:
        raise NotImplementedError

    @abstractmethod
    def mark_source_asset_missing(self, source_asset_id: str) -> CorpusSourceAsset | None:
        raise NotImplementedError

    @abstractmethod
    def supports_fts5(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def refresh_retrieval_index_for_document(self, document_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def rebuild_retrieval_index(self, creator_id: str | None = None) -> int:
        raise NotImplementedError

    @abstractmethod
    def search_retrieval_rows(self, query: CorpusRetrievalQuery) -> tuple[list[dict[str, object]], int]:
        raise NotImplementedError

    @abstractmethod
    def get_retrieval_index_health(self, creator_id: str | None = None) -> CorpusRetrievalIndexHealth:
        raise NotImplementedError
