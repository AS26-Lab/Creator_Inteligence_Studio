"""Comandos de aplicacion para ranking de clips."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RankClipCandidatesCommand:
    video_id: str
    profile: str = "balanced"
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowClipRankingCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ListClipCandidatesCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class CandidateClipCommand:
    candidate_id: str


@dataclass(frozen=True, slots=True)
class RateClipCandidateCommand:
    candidate_id: str
    rating: int


@dataclass(frozen=True, slots=True)
class NoteClipCandidateCommand:
    candidate_id: str
    text: str


@dataclass(frozen=True, slots=True)
class TagsClipCandidateCommand:
    candidate_id: str
    tags: list[str]


@dataclass(frozen=True, slots=True)
class AdjustClipCandidateCommand:
    candidate_id: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class ExportClipPlanCommand:
    video_id: str
    format: str


@dataclass(frozen=True, slots=True)
class DeleteClipRankingCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class CreateClipCollectionCommand:
    video_id: str
    name: str


@dataclass(frozen=True, slots=True)
class AddClipToCollectionCommand:
    collection_id: str
    candidate_id: str


@dataclass(frozen=True, slots=True)
class RemoveClipFromCollectionCommand:
    collection_id: str
    candidate_id: str
