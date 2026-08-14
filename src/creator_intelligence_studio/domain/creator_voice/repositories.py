"""Repository contracts used by Creator Voice evidence selection."""

from __future__ import annotations

from abc import ABC, abstractmethod

from creator_intelligence_studio.domain.creator_corpus.entities import CorpusDocumentVersion, CorpusSegment


class CreatorVoiceCorpusQueryRepository(ABC):
    @abstractmethod
    def list_document_versions_for_creator(self, creator_id: str, project_id: str | None = None) -> list[CorpusDocumentVersion]:
        raise NotImplementedError

    @abstractmethod
    def list_segments_for_creator(self, creator_id: str, project_id: str | None = None) -> list[CorpusSegment]:
        raise NotImplementedError

