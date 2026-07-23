"""Comandos de aplicacion para renderizado local de clips."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RenderCapabilitiesCommand:
    pass


@dataclass(frozen=True, slots=True)
class RenderProfilesCommand:
    pass


@dataclass(frozen=True, slots=True)
class RenderCandidateCommand:
    candidate_id: str
    profile: str = "balanced"
    output: str | None = None
    explicit: bool = False
    allow_stale: bool = False
    allow_overwrite: bool = False
    custom_name: str | None = None


@dataclass(frozen=True, slots=True)
class ShowRenderJobCommand:
    job_id: str


@dataclass(frozen=True, slots=True)
class ListCandidateRendersCommand:
    candidate_id: str


@dataclass(frozen=True, slots=True)
class VerifyRenderCommand:
    job_id: str


@dataclass(frozen=True, slots=True)
class CancelRenderCommand:
    job_id: str


@dataclass(frozen=True, slots=True)
class RetryRenderCommand:
    job_id: str


@dataclass(frozen=True, slots=True)
class DeleteRenderArtifactCommand:
    job_id: str


@dataclass(frozen=True, slots=True)
class RenderCollectionCommand:
    collection_id: str
    profile: str = "balanced"
    output_root: str | None = None
    explicit: bool = False
    allow_stale: bool = False
    continue_on_failure: bool = False


@dataclass(frozen=True, slots=True)
class ShowRenderBatchCommand:
    batch_id: str


@dataclass(frozen=True, slots=True)
class CancelRenderBatchCommand:
    batch_id: str


@dataclass(frozen=True, slots=True)
class RetryRenderBatchCommand:
    batch_id: str


@dataclass(frozen=True, slots=True)
class ExportRenderPlanCommand:
    job_id: str
    format: str = "json"
    output: str | None = None
