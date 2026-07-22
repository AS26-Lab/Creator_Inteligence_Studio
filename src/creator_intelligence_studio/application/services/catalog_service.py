"""Servicio de catalogo para creadores, proyectos y videos."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path

from creator_intelligence_studio.domain.creators.entities import Creator, CreatorStatus
from creator_intelligence_studio.domain.creators.repositories import CreatorRepository
from creator_intelligence_studio.domain.creators.services import (
    build_creator,
    ensure_active_creator,
    next_available_slug,
    normalize_slug,
    validate_display_name,
)
from creator_intelligence_studio.domain.errors import ConflictError, DomainError, NotFoundError
from creator_intelligence_studio.domain.projects.entities import Project, ProjectStatus
from creator_intelligence_studio.domain.projects.repositories import ProjectRepository
from creator_intelligence_studio.domain.projects.services import (
    build_project,
    ensure_active_project,
    validate_project_name,
    validate_project_type,
)
from creator_intelligence_studio.domain.videos.entities import VideoAsset
from creator_intelligence_studio.domain.videos.repositories import VideoRepository
from creator_intelligence_studio.domain.videos.services import (
    build_current_availability,
    build_video_asset,
    ensure_project_allows_videos,
    has_metadata_changed,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_repository import (
    SQLiteCreatorRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import (
    SQLiteProjectRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import (
    SQLiteVideoRepository,
)
from creator_intelligence_studio.shared.dates import utc_now
from creator_intelligence_studio.shared.paths import ProjectPaths


@dataclass(frozen=True, slots=True)
class VideoVerificationReport:
    """Resultado de verificación de disponibilidad de un video."""

    video: VideoAsset
    status: str
    metadata_changed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "video": self.video.to_dict(),
            "status": self.status,
            "metadata_changed": self.metadata_changed,
        }


class CatalogService:
    """Orquesta el catálogo de creadores, proyectos y videos."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        paths: ProjectPaths,
        creator_repository: CreatorRepository,
        project_repository: ProjectRepository,
        video_repository: VideoRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.paths = paths
        self.creator_repository = creator_repository
        self.project_repository = project_repository
        self.video_repository = video_repository
        self.logger = logger or logging.getLogger("creator_intelligence_studio")

    def _resolve_creator(self, creator_reference: str) -> Creator:
        creator = self.creator_repository.get_by_id(creator_reference)
        if creator is None:
            creator = self.creator_repository.get_by_slug(creator_reference)
        if creator is None:
            raise NotFoundError("El creador solicitado no existe.")
        return creator

    def _resolve_active_creator(self, creator_reference: str) -> Creator:
        return ensure_active_creator(self._resolve_creator(creator_reference))

    def _resolve_project(self, project_id: str) -> Project:
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise NotFoundError("El proyecto solicitado no existe.")
        return project

    def _current_video(self, video: VideoAsset) -> VideoAsset:
        available, _, _ = build_current_availability(video)
        return replace(video, file_available=available)

    def create_creator(
        self,
        *,
        display_name: str,
        slug: str | None = None,
        description: str | None = None,
    ) -> Creator:
        validate_display_name(display_name)
        base_slug = slug or display_name
        existing_slugs = {creator.slug for creator in self.creator_repository.list()}
        final_slug = normalize_slug(base_slug) if slug else next_available_slug(base_slug, existing_slugs)
        if slug and final_slug in existing_slugs:
            raise ConflictError("Ya existe un creador con ese slug.")
        creator = build_creator(
            display_name=display_name,
            slug=final_slug,
            description=description,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.creator_repository.create(creator)

    def list_creators(self) -> list[Creator]:
        return self.creator_repository.list()

    def get_creator(self, creator_reference: str) -> Creator:
        return self._resolve_creator(creator_reference)

    def archive_creator(self, creator_reference: str) -> Creator:
        creator = self._resolve_creator(creator_reference)
        if creator.status == CreatorStatus.ARCHIVED:
            return creator
        archived = self.creator_repository.archive(creator.id)
        if archived is None:
            raise NotFoundError("El creador solicitado no existe.")
        return archived

    def create_project(
        self,
        *,
        creator_reference: str,
        name: str,
        project_type: str,
        description: str | None = None,
    ) -> Project:
        creator = self._resolve_active_creator(creator_reference)
        validate_project_name(name)
        validate_project_type(project_type)
        project = build_project(
            creator_id=creator.id,
            name=name,
            description=description,
            project_type=project_type,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.project_repository.create(project)

    def list_projects(self, creator_reference: str | None = None) -> list[Project]:
        if creator_reference is None:
            return self.project_repository.list()
        creator = self._resolve_creator(creator_reference)
        return self.project_repository.list_by_creator(creator.id)

    def get_project(self, project_id: str) -> Project:
        project = self._resolve_project(project_id)
        return project

    def archive_project(self, project_id: str) -> Project:
        project = self._resolve_project(project_id)
        if project.status == ProjectStatus.ARCHIVED:
            return project
        archived = self.project_repository.archive(project.id)
        if archived is None:
            raise NotFoundError("El proyecto solicitado no existe.")
        return archived

    def register_video(
        self,
        *,
        project_id: str,
        file_path: str,
        title: str,
        notes: str | None = None,
    ) -> VideoAsset:
        project = ensure_active_project(self._resolve_project(project_id))
        video = build_video_asset(
            project_id=project.id,
            title=title,
            source_path=Path(file_path),
            notes=notes,
            registered_at=utc_now(),
            updated_at=utc_now(),
        )
        return self.video_repository.create(video)

    def list_videos(self, project_id: str) -> list[VideoAsset]:
        self._resolve_project(project_id)
        videos = self.video_repository.list_by_project(project_id)
        return [self._current_video(video) for video in videos]

    def get_video(self, video_id: str) -> VideoAsset:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        return self._current_video(video)

    def verify_video_availability(self, video_id: str) -> VideoVerificationReport:
        video = self.video_repository.get_by_id(video_id)
        if video is None:
            raise NotFoundError("El video solicitado no existe.")
        current_video = self._current_video(video)
        available, _, _ = build_current_availability(video)
        metadata_changed = available and has_metadata_changed(video)
        status = "available" if available else "missing"
        return VideoVerificationReport(
            video=current_video,
            status=status,
            metadata_changed=metadata_changed,
        )


def build_catalog_service(settings: AppSettings, paths: ProjectPaths, logger: logging.Logger | None = None) -> CatalogService:
    """Construye el servicio de catálogo con SQLite local."""

    database = build_database(settings, paths)
    with database.connect() as connection:
        run_migrations(connection)
    return CatalogService(
        settings=settings,
        paths=paths,
        creator_repository=SQLiteCreatorRepository(database),
        project_repository=SQLiteProjectRepository(database),
        video_repository=SQLiteVideoRepository(database),
        logger=logger,
    )
