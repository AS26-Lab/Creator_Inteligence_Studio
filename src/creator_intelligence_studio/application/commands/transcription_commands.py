"""Comandos de aplicacion para transcripcion."""

from __future__ import annotations

from dataclasses import dataclass

from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionExportFormat, TranscriptionOptions


@dataclass(frozen=True, slots=True)
class TranscribeVideoCommand:
    video_id: str
    options: TranscriptionOptions


@dataclass(frozen=True, slots=True)
class ShowTranscriptionCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ListSegmentsCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ExportTranscriptionCommand:
    video_id: str
    format: TranscriptionExportFormat


@dataclass(frozen=True, slots=True)
class DeleteTranscriptionCommand:
    video_id: str


@dataclass(frozen=True, slots=True)
class ModelStatusCommand:
    model_name: str


@dataclass(frozen=True, slots=True)
class DownloadModelCommand:
    model_name: str


@dataclass(frozen=True, slots=True)
class VerifyModelCommand:
    model_name: str
