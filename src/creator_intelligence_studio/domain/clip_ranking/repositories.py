"""Contratos de persistencia para ranking de clips."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import ClipCollection, ClipCollectionItem, ClipRankingRun, ClipReviewEvent, RankedClipCandidate


class ClipRankingRepository(ABC):
    """Persistencia de rankings de clips."""

    @abstractmethod
    def upsert(self, run: ClipRankingRun, candidates: list[RankedClipCandidate]) -> ClipRankingRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_video_asset_id(self, video_asset_id: str) -> ClipRankingRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, ranking_run_id: str) -> ClipRankingRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_candidates(self, ranking_run_id: str) -> list[RankedClipCandidate]:
        raise NotImplementedError

    @abstractmethod
    def get_candidate_by_id(self, candidate_id: str) -> RankedClipCandidate | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_candidate(self, candidate: RankedClipCandidate) -> RankedClipCandidate:
        raise NotImplementedError

    @abstractmethod
    def append_review_event(self, event: ClipReviewEvent) -> ClipReviewEvent:
        raise NotImplementedError

    @abstractmethod
    def list_review_events(self, ranked_clip_candidate_id: str) -> list[ClipReviewEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_collection_by_id(self, collection_id: str) -> ClipCollection | None:
        raise NotImplementedError

    @abstractmethod
    def list_collections(self, video_asset_id: str) -> list[ClipCollection]:
        raise NotImplementedError

    @abstractmethod
    def list_collection_items(self, collection_id: str) -> list[ClipCollectionItem]:
        raise NotImplementedError

    @abstractmethod
    def upsert_collection(self, collection: ClipCollection) -> ClipCollection:
        raise NotImplementedError

    @abstractmethod
    def add_collection_item(self, item: ClipCollectionItem) -> ClipCollectionItem:
        raise NotImplementedError

    @abstractmethod
    def remove_collection_item(self, collection_id: str, ranked_clip_candidate_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_by_video_asset_id(self, video_asset_id: str) -> bool:
        raise NotImplementedError
