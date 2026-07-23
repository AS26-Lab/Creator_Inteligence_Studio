"""Contratos de persistencia para renderizado de clips."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import ClipRenderArtifact, ClipRenderBatch, ClipRenderBatchItem, ClipRenderEvent, ClipRenderJob


class ClipRenderRepository(ABC):
    @abstractmethod
    def upsert_job(self, job: ClipRenderJob) -> ClipRenderJob:
        raise NotImplementedError

    @abstractmethod
    def get_job_by_id(self, job_id: str) -> ClipRenderJob | None:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self) -> list[ClipRenderJob]:
        raise NotImplementedError

    @abstractmethod
    def get_job_by_candidate_id(self, candidate_id: str) -> ClipRenderJob | None:
        raise NotImplementedError

    @abstractmethod
    def list_jobs_for_candidate(self, candidate_id: str) -> list[ClipRenderJob]:
        raise NotImplementedError

    @abstractmethod
    def list_jobs_for_collection(self, collection_id: str) -> list[ClipRenderJob]:
        raise NotImplementedError

    @abstractmethod
    def list_jobs_for_video(self, video_asset_id: str) -> list[ClipRenderJob]:
        raise NotImplementedError

    @abstractmethod
    def upsert_artifact(self, artifact: ClipRenderArtifact) -> ClipRenderArtifact:
        raise NotImplementedError

    @abstractmethod
    def list_artifacts_for_job(self, render_job_id: str) -> list[ClipRenderArtifact]:
        raise NotImplementedError

    @abstractmethod
    def get_artifact_for_job(self, render_job_id: str) -> ClipRenderArtifact | None:
        raise NotImplementedError

    @abstractmethod
    def delete_artifact_for_job(self, render_job_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def append_event(self, event: ClipRenderEvent) -> ClipRenderEvent:
        raise NotImplementedError

    @abstractmethod
    def list_events_for_job(self, render_job_id: str) -> list[ClipRenderEvent]:
        raise NotImplementedError

    @abstractmethod
    def upsert_batch(self, batch: ClipRenderBatch) -> ClipRenderBatch:
        raise NotImplementedError

    @abstractmethod
    def get_batch_by_id(self, batch_id: str) -> ClipRenderBatch | None:
        raise NotImplementedError

    @abstractmethod
    def list_batches_for_collection(self, collection_id: str) -> list[ClipRenderBatch]:
        raise NotImplementedError

    @abstractmethod
    def list_batches_for_video(self, video_asset_id: str) -> list[ClipRenderBatch]:
        raise NotImplementedError

    @abstractmethod
    def add_batch_item(self, item: ClipRenderBatchItem) -> ClipRenderBatchItem:
        raise NotImplementedError

    @abstractmethod
    def list_batch_items(self, batch_id: str) -> list[ClipRenderBatchItem]:
        raise NotImplementedError

    @abstractmethod
    def delete_job(self, job_id: str) -> bool:
        raise NotImplementedError
