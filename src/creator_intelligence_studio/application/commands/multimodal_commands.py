"""Comandos de aplicacion para analisis multimodal."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyzeMultimodalCommand:
    video_id: str
    force: bool = False


@dataclass(frozen=True, slots=True)
class ShowMultimodalCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class TimelineMultimodalCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class CandidatesMultimodalCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class CandidateMultimodalCommand:
    candidate_id: str


@dataclass(frozen=True, slots=True)
class ExportMultimodalCommand:
    video_id: str
    format: str


@dataclass(frozen=True, slots=True)
class DeleteMultimodalCommand:
    video_id: str

