"""Comandos de aplicacion para datasets de personalizacion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuildCreatorDatasetCommand:
    creator_id: str
    project_id: str | None = None
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowCreatorDatasetCommand:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class LatestCreatorDatasetCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class ListCreatorDatasetsCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class DatasetExamplesCommand:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class DatasetQualityCommand:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class CreatorReadinessCommand:
    creator_id: str


@dataclass(frozen=True, slots=True)
class CompareDatasetSnapshotsCommand:
    snapshot_a_id: str
    snapshot_b_id: str


@dataclass(frozen=True, slots=True)
class ArchiveDatasetSnapshotCommand:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class ExportDatasetCommand:
    snapshot_id: str
    format: str

