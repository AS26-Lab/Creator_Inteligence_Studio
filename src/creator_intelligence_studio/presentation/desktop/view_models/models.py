"""Modelos simples de presentacion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CardViewModel:
    title: str
    value: str
    detail: str = ""
    accent: str = "accent"
    icon: str = "◼"


@dataclass(frozen=True, slots=True)
class InspectorItemViewModel:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class ActivityEntryViewModel:
    message: str


@dataclass(frozen=True, slots=True)
class CreatorRowViewModel:
    id: str
    display_name: str
    slug: str
    description: str
    status: str
    projects_count: int
    videos_count: int


@dataclass(frozen=True, slots=True)
class ProjectRowViewModel:
    id: str
    creator_id: str
    name: str
    description: str
    project_type: str
    status: str
    videos_count: int


@dataclass(frozen=True, slots=True)
class VideoRowViewModel:
    id: str
    project_id: str
    title: str
    original_filename: str
    extension: str
    file_size_bytes: int
    source_type: str
    processing_status: str
    file_available: bool
    registered_at: str
    notes: str
    source_path: str
    file_modified_at: str


@dataclass(frozen=True, slots=True)
class SystemItemViewModel:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class VideoFiltersViewModel:
    project_id: str | None = None
    processing_status: str | None = None
    availability: str | None = None
    source_type: str | None = None
    search_text: str = ""
