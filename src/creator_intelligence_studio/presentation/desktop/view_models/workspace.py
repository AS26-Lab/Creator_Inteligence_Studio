"""Modelo de coordinacion para la interfaz de escritorio."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_studio.application.services.catalog_service import (
    CatalogService,
    VideoVerificationReport,
)
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
)
from creator_intelligence_studio.domain.creators.entities import CreatorStatus
from creator_intelligence_studio.domain.projects.entities import ProjectStatus
from creator_intelligence_studio.domain.videos.entities import (
    VideoAsset,
    VideoProcessingStatus,
    VideoSourceType,
)
from creator_intelligence_studio.infrastructure.configuration.settings import AppSettings
from creator_intelligence_studio.infrastructure.diagnostics.models import EnvironmentDiagnostic
from creator_intelligence_studio.shared.dates import to_iso_z
from creator_intelligence_studio.shared.paths import ProjectPaths

from .models import (
    ActivityEntryViewModel,
    CardViewModel,
    CreatorRowViewModel,
    InspectorItemViewModel,
    ProjectRowViewModel,
    SystemItemViewModel,
    VideoFiltersViewModel,
    VideoRowViewModel,
)


def _humanize_bytes(value: int | None) -> str:
    if value is None:
        return "No verificado"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(value)
    unit_index = 0
    while amount >= 1024 and unit_index < len(units) - 1:
        amount /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(amount)} {units[unit_index]}"
    return f"{amount:.1f} {units[unit_index]}"


def _humanize_seconds(value: float | None) -> str:
    if value is None:
        return "No verificada"
    if value < 60:
        return f"{value:.1f} s"
    minutes = int(value // 60)
    seconds = value % 60
    return f"{minutes} min {seconds:.1f} s"


def _humanize_hz(value: int | None) -> str:
    if value is None:
        return "No verificada"
    return f"{value} Hz"


def _format_datetime(value) -> str:
    return to_iso_z(value) if value is not None else "No verificado"


def _creator_status_label(status: CreatorStatus) -> str:
    return "Activo" if status == CreatorStatus.ACTIVE else "Archivado"


def _project_status_label(status: ProjectStatus) -> str:
    labels = {
        ProjectStatus.ACTIVE: "Activo",
        ProjectStatus.COMPLETED: "Completado",
        ProjectStatus.ARCHIVED: "Archivado",
    }
    return labels[status]


def _project_type_label(value: str) -> str:
    return {
        "long_form": "Largo",
        "short_form": "Corto",
        "mixed": "Mixto",
        "research": "Investigacion",
    }.get(value, value)


def _video_status_label(video: VideoAsset) -> str:
    status = video.processing_status
    availability = "Disponible" if video.file_available else "Archivo faltante"
    labels = {
        VideoProcessingStatus.REGISTERED: "Registrado",
        VideoProcessingStatus.QUEUED: "Pendiente",
        VideoProcessingStatus.PROCESSING: "Procesando",
        VideoProcessingStatus.COMPLETED: "Completado",
        VideoProcessingStatus.FAILED: "Error",
        VideoProcessingStatus.CANCELLED: "Error",
    }
    return f"{labels[status]} / {availability}"


def _source_type_label(value: VideoSourceType) -> str:
    return {
        VideoSourceType.LOCAL_FILE: "Archivo local",
        VideoSourceType.PLATFORM_IMPORT: "Importacion de plataforma",
        VideoSourceType.MANUAL_REFERENCE: "Referencia manual",
    }[value]


def _fps_text(report: VideoInspectionReport | None) -> str:
    if report is None or report.summary is None:
        return "No verificado"
    summary = report.summary
    value = summary.average_frame_rate.to_float() or summary.frame_rate.to_float()
    if value is None:
        return "No verificado"
    return f"{value:.3f} fps"


class WorkspaceViewModel:
    """Coordina datos, selecciones y transformaciones de presentacion."""

    def __init__(
        self,
        *,
        service: CatalogService,
        media_service: MediaInspectionService,
        diagnostic: EnvironmentDiagnostic,
        settings: AppSettings,
        paths: ProjectPaths,
    ) -> None:
        self.service = service
        self.media_service = media_service
        self.diagnostic = diagnostic
        self.settings = settings
        self.paths = paths
        self.selected_creator_id: str | None = None
        self.selected_project_id: str | None = None
        self.selected_video_id: str | None = None
        self.activity_log: list[str] = []
        self._sync_default_selection()

    def _sync_default_selection(self) -> None:
        creators = self.service.list_creators()
        if not creators:
            self.selected_creator_id = None
            self.selected_project_id = None
            self.selected_video_id = None
            return
        if self.selected_creator_id not in {creator.id for creator in creators}:
            active_creator = next((creator for creator in creators if creator.status == CreatorStatus.ACTIVE), creators[0])
            self.selected_creator_id = active_creator.id
        projects = self.projects_for_selected_creator()
        if projects:
            if self.selected_project_id not in {project.id for project in projects}:
                self.selected_project_id = projects[0].id
        else:
            self.selected_project_id = None
        if self.selected_project_id is None:
            self.selected_video_id = None

    def refresh(self) -> None:
        self._sync_default_selection()

    def creators(self):
        return self.service.list_creators()

    def projects_for_selected_creator(self):
        if self.selected_creator_id is None:
            return []
        return self.service.list_projects(self.selected_creator_id)

    def videos_for_selected_project(self):
        if self.selected_project_id is None:
            return []
        return self.service.list_videos(self.selected_project_id)

    def select_creator(self, creator_reference: str) -> None:
        creator = self.service.get_creator(creator_reference)
        self.selected_creator_id = creator.id
        projects = self.projects_for_selected_creator()
        self.selected_project_id = projects[0].id if projects else None
        self.selected_video_id = None

    def select_project(self, project_id: str) -> None:
        project = self.service.get_project(project_id)
        self.selected_project_id = project.id
        self.selected_creator_id = project.creator_id
        self.selected_video_id = None

    def select_video(self, video_id: str | None) -> None:
        self.selected_video_id = video_id

    def create_creator(self, display_name: str, slug: str | None = None, description: str | None = None):
        creator = self.service.create_creator(
            display_name=display_name,
            slug=slug,
            description=description,
        )
        self.activity_log.insert(0, f"Creador creado: {creator.display_name}")
        self.selected_creator_id = creator.id
        self.selected_project_id = None
        self.selected_video_id = None
        self._sync_default_selection()
        return creator

    def archive_creator(self, creator_reference: str):
        creator = self.service.archive_creator(creator_reference)
        self.activity_log.insert(0, f"Creador archivado: {creator.display_name}")
        self._sync_default_selection()
        return creator

    def create_project(self, creator_reference: str, name: str, project_type: str, description: str | None = None):
        project = self.service.create_project(
            creator_reference=creator_reference,
            name=name,
            project_type=project_type,
            description=description,
        )
        self.activity_log.insert(0, f"Proyecto creado: {project.name}")
        self.selected_creator_id = project.creator_id
        self.selected_project_id = project.id
        self.selected_video_id = None
        return project

    def archive_project(self, project_id: str):
        project = self.service.archive_project(project_id)
        self.activity_log.insert(0, f"Proyecto archivado: {project.name}")
        self._sync_default_selection()
        return project

    def register_video(self, project_id: str, file_path: str, title: str, notes: str | None = None):
        video = self.service.register_video(
            project_id=project_id,
            file_path=file_path,
            title=title,
            notes=notes,
        )
        self.activity_log.insert(0, f"Video registrado: {video.title}")
        self.selected_project_id = project_id
        self.selected_video_id = video.id
        return video

    def verify_video(self, video_id: str) -> VideoVerificationReport:
        report = self.service.verify_video_availability(video_id)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Verificacion de video: {report.status}")
        return report

    def inspect_video(self, video_id: str, force: bool = False) -> VideoInspectionReport:
        report = self.media_service.inspect_video(video_id, force=force)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Inspeccion tecnica: {report.status.value}")
        return report

    def get_video_inspection(self, video_id: str) -> VideoInspectionReport | None:
        return self.media_service.get_video_inspection(video_id)

    def is_inspection_stale(self, video_id: str) -> bool:
        return self.media_service.is_inspection_stale(video_id)

    def media_tools(self) -> MediaToolsReport:
        return self.media_service.verify_media_tools()

    def creator_rows(self) -> list[CreatorRowViewModel]:
        creators = self.service.list_creators()
        projects = self.service.list_projects()
        project_counts = {creator.id: 0 for creator in creators}
        video_counts = {creator.id: 0 for creator in creators}
        for project in projects:
            project_counts[project.creator_id] = project_counts.get(project.creator_id, 0) + 1
            for video in self.service.list_videos(project.id):
                video_counts[project.creator_id] = video_counts.get(project.creator_id, 0) + 1
        rows = []
        for creator in creators:
            rows.append(
                CreatorRowViewModel(
                    id=creator.id,
                    display_name=creator.display_name,
                    slug=creator.slug,
                    description=creator.description or "",
                    status=_creator_status_label(creator.status),
                    projects_count=project_counts.get(creator.id, 0),
                    videos_count=video_counts.get(creator.id, 0),
                )
            )
        return rows

    def project_rows(self) -> list[ProjectRowViewModel]:
        if self.selected_creator_id is None:
            return []
        projects = self.service.list_projects(self.selected_creator_id)
        rows: list[ProjectRowViewModel] = []
        for project in projects:
            rows.append(
                ProjectRowViewModel(
                    id=project.id,
                    creator_id=project.creator_id,
                    name=project.name,
                    description=project.description or "",
                    project_type=_project_type_label(project.project_type.value),
                    status=_project_status_label(project.status),
                    videos_count=len(self.service.list_videos(project.id)),
                )
            )
        return rows

    def video_rows(self, filters: VideoFiltersViewModel | None = None) -> list[VideoRowViewModel]:
        if self.selected_project_id is None:
            return []
        videos = self.service.list_videos(self.selected_project_id)
        rows: list[VideoRowViewModel] = []
        for video in videos:
            if filters and filters.search_text:
                search_text = filters.search_text.lower()
                haystack = " ".join(
                    [
                        video.title,
                        video.original_filename,
                        video.extension,
                        video.source_path,
                        video.notes or "",
                    ]
                ).lower()
                if search_text not in haystack:
                    continue
            if filters and filters.processing_status:
                if _video_status_label(video).split(" / ")[0] != filters.processing_status:
                    continue
            if filters and filters.availability:
                label = "Disponible" if video.file_available else "Archivo faltante"
                if label != filters.availability:
                    continue
            if filters and filters.source_type:
                if _source_type_label(video.source_type) != filters.source_type:
                    continue
            rows.append(
                VideoRowViewModel(
                    id=video.id,
                    project_id=video.project_id,
                    title=video.title,
                    original_filename=video.original_filename,
                    extension=video.extension,
                    file_size_bytes=video.file_size_bytes,
                    source_type=_source_type_label(video.source_type),
                    processing_status=_video_status_label(video),
                    file_available=video.file_available,
                    registered_at=_format_datetime(video.registered_at),
                    notes=video.notes or "",
                    source_path=video.source_path,
                    file_modified_at=_format_datetime(video.file_modified_at),
                )
            )
        return rows

    def selected_creator(self):
        if self.selected_creator_id is None:
            return None
        return self.service.get_creator(self.selected_creator_id)

    def selected_project(self):
        if self.selected_project_id is None:
            return None
        return self.service.get_project(self.selected_project_id)

    def selected_video(self):
        if self.selected_video_id is None:
            return None
        return self.service.get_video(self.selected_video_id)

    def dashboard_cards(self) -> list[CardViewModel]:
        creators = self.service.list_creators()
        projects = self.service.list_projects()
        videos = [video for project in projects for video in self.service.list_videos(project.id)]
        active_projects = [project for project in projects if project.status == ProjectStatus.ACTIVE]
        pending_videos = [
            video
            for video in videos
            if video.processing_status in {
                VideoProcessingStatus.REGISTERED,
                VideoProcessingStatus.QUEUED,
                VideoProcessingStatus.PROCESSING,
            }
        ]
        active_creator = self.selected_creator()
        active_project = self.selected_project()
        return [
            CardViewModel(
                title="Creador activo",
                value=active_creator.display_name if active_creator else "Ninguno",
                detail=active_creator.slug if active_creator else "Seleccione uno",
                icon="◉",
            ),
            CardViewModel(
                title="Proyectos activos",
                value=str(len(active_projects)),
                detail=f"Total de proyectos: {len(projects)}",
                accent="accent_ml",
                icon="▣",
            ),
            CardViewModel(
                title="Videos registrados",
                value=str(len(videos)),
                detail="Metadatos locales registrados",
                icon="▶",
            ),
            CardViewModel(
                title="Videos pendientes",
                value=str(len(pending_videos)),
                detail="Registrados, en cola o procesando",
                accent="warning",
                icon="⏳",
            ),
            CardViewModel(
                title="Almacenamiento disponible",
                value=_humanize_bytes(self.paths.free_space_bytes()),
                detail="Espacio libre en la unidad del proyecto",
                icon="¤",
            ),
            CardViewModel(
                title="GPU detectada",
                value=self.diagnostic.gpu_devices[0].name if self.diagnostic.gpu_devices else "No verificada",
                detail=(
                    f"VRAM: {self.diagnostic.gpu_devices[0].memory_total_mib / 1024:.1f} GiB"
                    if self.diagnostic.gpu_devices and self.diagnostic.gpu_devices[0].memory_total_mib is not None
                    else "VRAM no verificada"
                ),
                accent="success" if self.diagnostic.gpu_devices else "warning",
                icon="⬢",
            ),
            CardViewModel(
                title="Estado CUDA",
                value=(
                    f"Detectada por el controlador: {self.diagnostic.cuda_version_reported}"
                    if self.diagnostic.cuda_version_reported
                    else "Detectada por el controlador: no verificado"
                ),
                detail="Runtime: no verificado",
                accent="accent_ml",
                icon="λ",
            ),
            CardViewModel(
                title="Actividad reciente",
                value=self.activity_log[0] if self.activity_log else "Sin actividad reciente",
                detail=active_project.name if active_project else "Sin proyecto activo",
                accent="accent",
                icon="↻",
            ),
        ]

    def system_items(self) -> list[SystemItemViewModel]:
        gpu = self.diagnostic.gpu_devices[0] if self.diagnostic.gpu_devices else None
        tools = self.media_tools()
        return [
            SystemItemViewModel("Aplicacion", f"{self.diagnostic.application_name} {self.diagnostic.application_version}"),
            SystemItemViewModel("Sistema operativo", f"{self.diagnostic.os_name} {self.diagnostic.os_version or 'no verificado'}"),
            SystemItemViewModel("Arquitectura", self.diagnostic.os_architecture or "No verificado"),
            SystemItemViewModel("CPU", self.diagnostic.cpu_reported or "No verificado"),
            SystemItemViewModel("Procesadores logicos", str(self.diagnostic.logical_processors or "No verificado")),
            SystemItemViewModel("Python", self.diagnostic.python_version),
            SystemItemViewModel("Interprete", self.diagnostic.python_executable),
            SystemItemViewModel("Git", self.diagnostic.git_version or "No verificado"),
            SystemItemViewModel("nvidia-smi", "Disponible" if self.diagnostic.nvidia_smi_available else "No disponible"),
            SystemItemViewModel("GPU NVIDIA", gpu.name if gpu else "No verificada"),
            SystemItemViewModel("VRAM", f"{gpu.memory_total_mib} MiB" if gpu and gpu.memory_total_mib is not None else "No verificada"),
            SystemItemViewModel(
                "Version del controlador NVIDIA",
                gpu.driver_version if gpu and gpu.driver_version else (self.diagnostic.nvidia_driver_version or "No verificado"),
            ),
            SystemItemViewModel("Detectada por el controlador", self.diagnostic.cuda_version_reported or "No verificado"),
            SystemItemViewModel("Runtime CUDA", "No verificado" if self.diagnostic.state.cuda_runtime_not_verified else "Verificado"),
            SystemItemViewModel("Base local", str(self.paths.database_path)),
            SystemItemViewModel("Espacio libre", f"{_humanize_bytes(self.paths.free_space_bytes())} disponibles"),
            SystemItemViewModel("Modo basico", "Disponible" if self.diagnostic.state.ready_for_basic_mode else "No disponible"),
            SystemItemViewModel("Backend activo", self.diagnostic.preferred_compute_backend),
            SystemItemViewModel("ffmpeg", f"{tools.ffmpeg.version or 'No verificada'}"),
            SystemItemViewModel("ffprobe", f"{tools.ffprobe.version or 'No verificada'}"),
        ]

    def creator_inspector_items(self, creator) -> list[InspectorItemViewModel]:
        if creator is None:
            return []
        return [
            InspectorItemViewModel("ID", creator.id),
            InspectorItemViewModel("Nombre", creator.display_name),
            InspectorItemViewModel("Slug", creator.slug),
            InspectorItemViewModel("Estado", _creator_status_label(creator.status)),
            InspectorItemViewModel("Descripcion", creator.description or "Sin descripcion"),
        ]

    def project_inspector_items(self, project) -> list[InspectorItemViewModel]:
        if project is None:
            return []
        return [
            InspectorItemViewModel("ID", project.id),
            InspectorItemViewModel("Creador", project.creator_id),
            InspectorItemViewModel("Nombre", project.name),
            InspectorItemViewModel("Tipo", _project_type_label(project.project_type.value)),
            InspectorItemViewModel("Estado", _project_status_label(project.status)),
            InspectorItemViewModel("Descripcion", project.description or "Sin descripcion"),
        ]

    def video_inspector_items(self, video, inspection_report: VideoInspectionReport | None = None) -> list[InspectorItemViewModel]:
        if video is None:
            return []
        items = [
            InspectorItemViewModel("ID", video.id),
            InspectorItemViewModel("Titulo", video.title),
            InspectorItemViewModel("Ruta local", video.source_path),
            InspectorItemViewModel("Proyecto", video.project_id),
            InspectorItemViewModel("Nombre original", video.original_filename),
            InspectorItemViewModel("Extension", video.extension),
            InspectorItemViewModel("Tamano", _humanize_bytes(video.file_size_bytes)),
            InspectorItemViewModel("Fuente", _source_type_label(video.source_type)),
            InspectorItemViewModel("Estado", _video_status_label(video)),
            InspectorItemViewModel("Disponible", "Si" if video.file_available else "No"),
            InspectorItemViewModel("Registro", _format_datetime(video.registered_at)),
            InspectorItemViewModel("Modificado", _format_datetime(video.file_modified_at)),
            InspectorItemViewModel("Notas", video.notes or "Sin notas"),
        ]
        if inspection_report is not None:
            summary = inspection_report.summary
            items.extend(
                [
                    InspectorItemViewModel("Estado de inspeccion", inspection_report.status.value),
                    InspectorItemViewModel("Vigencia", "Stale" if inspection_report.is_stale else "Vigente"),
                    InspectorItemViewModel("Duracion", _humanize_seconds(summary.duration_seconds if summary else None)),
                    InspectorItemViewModel(
                        "Resolucion",
                        f"{summary.width}x{summary.height}" if summary and summary.width and summary.height else "No verificada",
                    ),
                    InspectorItemViewModel("FPS", _fps_text(inspection_report)),
                    InspectorItemViewModel("Codec de video", summary.video_codec if summary and summary.video_codec else "No verificado"),
                    InspectorItemViewModel("Codec de audio", summary.audio_codec if summary and summary.audio_codec else "No verificado"),
                    InspectorItemViewModel(
                        "Canales",
                        str(summary.audio_channels) if summary and summary.audio_channels is not None else "No verificados",
                    ),
                    InspectorItemViewModel(
                        "Frecuencia de muestreo",
                        _humanize_hz(summary.audio_sample_rate if summary else None),
                    ),
                    InspectorItemViewModel(
                        "Bitrate",
                        f"{summary.overall_bitrate} bps" if summary and summary.overall_bitrate is not None else "No verificado",
                    ),
                    InspectorItemViewModel(
                        "Streams",
                        str(summary.stream_count) if summary else "No verificado",
                    ),
                    InspectorItemViewModel(
                        "Ultima inspeccion",
                        _format_datetime(inspection_report.inspection.inspected_at) if inspection_report.inspection else "No verificada",
                    ),
                    InspectorItemViewModel(
                        "Miniatura inicial",
                        inspection_report.thumbnail_path or "No disponible",
                    ),
                ]
            )
        return items
