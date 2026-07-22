"""Modelo de coordinacion para la interfaz de escritorio."""

from __future__ import annotations

from pathlib import Path

from creator_intelligence_studio.application.services.audio_preparation_service import (
    AudioCacheDeletionResult,
    AudioPreparationService,
    PreparedAudioReport,
)
from creator_intelligence_studio.application.services.catalog_service import (
    CatalogService,
    VideoVerificationReport,
)
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
)
from creator_intelligence_studio.application.services.transcription_service import (
    TranscriptionExportResult,
    TranscriptionReport,
    TranscriptionService,
)
from creator_intelligence_studio.application.services.acoustic_analysis_service import (
    AcousticAnalysisExportResult,
    AcousticAnalysisReport,
    AcousticAnalysisService,
)
from creator_intelligence_studio.application.services.visual_analysis_service import (
    VisualAnalysisExportResult,
    VisualAnalysisReport,
    VisualAnalysisService,
)
from creator_intelligence_studio.application.services.multimodal_analysis_service import (
    MultimodalAnalysisExportResult,
    MultimodalAnalysisReport,
    MultimodalAnalysisService,
)
from creator_intelligence_studio.application.services.clip_ranking_service import (
    ClipRankingExportResult,
    ClipRankingReport,
    ClipRankingService,
)
from creator_intelligence_studio.domain.creators.entities import CreatorStatus
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow
from creator_intelligence_studio.domain.transcription.value_objects import (
    TranscriptionExportFormat,
    TranscriptionModelInfo,
    TranscriptionOptions,
)
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import MultimodalAnalysisOptions
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


def _audio_status_label(report: PreparedAudioReport | None) -> str:
    if report is None:
        return "No preparado"
    labels = {
        "not_prepared": "No preparado",
        "queued": "Pendiente",
        "extracting": "Preparando",
        "completed": "Preparado",
        "failed": "Error",
        "file_missing": "Archivo faltante",
        "no_audio_stream": "Sin audio",
        "tool_unavailable": "Herramienta no disponible",
        "stale": "Desactualizado",
    }
    return labels.get(report.status.value, report.status.value)


def _audio_stream_label(report: PreparedAudioReport | None) -> str:
    if report is None or report.selected_stream is None:
        return "No seleccionado"
    stream = report.selected_stream
    parts = [f"Stream {stream.index}"]
    if stream.channels is not None:
        parts.append(f"{stream.channels} canales")
    if stream.language:
        parts.append(stream.language)
    if stream.is_default:
        parts.append("default")
    return " · ".join(parts)


def _audio_text(value: int | None, unit: str) -> str:
    if value is None:
        return "No verificado"
    if not unit:
        return str(value)
    return f"{value} {unit}"


class WorkspaceViewModel:
    """Coordina datos, selecciones y transformaciones de presentacion."""

    def __init__(
        self,
        *,
        service: CatalogService,
        media_service: MediaInspectionService,
        audio_service: AudioPreparationService,
        transcription_service: TranscriptionService,
        acoustic_service: AcousticAnalysisService,
        visual_service: VisualAnalysisService,
        multimodal_service: MultimodalAnalysisService | None = None,
        clip_service: ClipRankingService | None = None,
        diagnostic: EnvironmentDiagnostic,
        settings: AppSettings,
        paths: ProjectPaths,
    ) -> None:
        self.service = service
        self.media_service = media_service
        self.audio_service = audio_service
        self.transcription_service = transcription_service
        self.acoustic_service = acoustic_service
        self.visual_service = visual_service
        if multimodal_service is None:
            from types import SimpleNamespace

            multimodal_service = SimpleNamespace(
                analyze_multimodal=lambda *args, **kwargs: SimpleNamespace(
                    status=SimpleNamespace(value="not_analyzed"),
                    is_stale=False,
                    analysis=None,
                    windows=(),
                    candidates=(),
                    available_sources=(),
                    missing_sources=(),
                    warnings=(),
                    errors=(),
                    progress_message=None,
                ),
                get_multimodal_analysis=lambda *args, **kwargs: SimpleNamespace(
                    status=SimpleNamespace(value="not_analyzed"),
                    is_stale=False,
                    analysis=None,
                    windows=(),
                    candidates=(),
                    available_sources=(),
                    missing_sources=(),
                    warnings=(),
                    errors=(),
                    progress_message=None,
                ),
                get_multimodal_timeline=lambda *args, **kwargs: (),
                list_moment_candidates=lambda *args, **kwargs: (),
                get_moment_candidate=lambda *args, **kwargs: None,
                is_multimodal_analysis_stale=lambda *args, **kwargs: False,
                delete_multimodal_analysis=lambda *args, **kwargs: False,
                export_multimodal_analysis=lambda *args, **kwargs: SimpleNamespace(path="cache/multimodal/video/multimodal_analysis.json", to_dict=lambda: {}),
            )
        self.multimodal_service = multimodal_service
        if clip_service is None:
            from types import SimpleNamespace

            clip_service = SimpleNamespace(
                rank_clip_candidates=lambda *args, **kwargs: SimpleNamespace(
                    video=SimpleNamespace(to_dict=lambda: {}),
                    multimodal_report=None,
                    run=None,
                    candidates=(),
                    status=SimpleNamespace(value="not_ranked"),
                    is_stale=False,
                    available_sources=(),
                    missing_sources=(),
                    warnings=(),
                    errors=(),
                    progress_message=None,
                ),
                get_ranking_run=lambda *args, **kwargs: SimpleNamespace(
                    video=SimpleNamespace(to_dict=lambda: {}),
                    multimodal_report=None,
                    run=None,
                    candidates=(),
                    status=SimpleNamespace(value="not_ranked"),
                    is_stale=False,
                    available_sources=(),
                    missing_sources=(),
                    warnings=(),
                    errors=(),
                    progress_message=None,
                ),
                list_ranked_candidates=lambda *args, **kwargs: (),
                get_ranked_candidate=lambda *args, **kwargs: None,
                approve_candidate=lambda *args, **kwargs: None,
                reject_candidate=lambda *args, **kwargs: None,
                shortlist_candidate=lambda *args, **kwargs: None,
                mark_candidate_needs_review=lambda *args, **kwargs: None,
                rate_candidate=lambda *args, **kwargs: None,
                add_candidate_note=lambda *args, **kwargs: None,
                set_candidate_tags=lambda *args, **kwargs: None,
                adjust_candidate_bounds=lambda *args, **kwargs: None,
                reset_candidate_review=lambda *args, **kwargs: None,
                get_candidate_review_history=lambda *args, **kwargs: (),
                is_clip_ranking_stale=lambda *args, **kwargs: False,
                delete_clip_ranking=lambda *args, **kwargs: False,
                create_clip_collection=lambda *args, **kwargs: SimpleNamespace(id="", name="", to_dict=lambda: {}),
                add_candidate_to_collection=lambda *args, **kwargs: None,
                remove_candidate_from_collection=lambda *args, **kwargs: False,
                export_clip_plan=lambda *args, **kwargs: SimpleNamespace(path="", to_dict=lambda: {}),
            )
        self.clip_service = clip_service
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

    def prepare_audio(self, video_id: str, force: bool = False) -> PreparedAudioReport:
        report = self.audio_service.prepare_audio(video_id, force=force)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Audio preparado: {report.status.value}")
        return report

    def get_prepared_audio(self, video_id: str) -> PreparedAudioReport:
        return self.audio_service.get_prepared_audio(video_id)

    def is_prepared_audio_stale(self, video_id: str) -> bool:
        return self.audio_service.is_prepared_audio_stale(video_id)

    def verify_prepared_audio(self, video_id: str) -> PreparedAudioReport:
        report = self.audio_service.verify_prepared_audio(video_id)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Audio verificado: {report.status.value}")
        return report

    def clear_prepared_audio_cache(self, video_id: str) -> AudioCacheDeletionResult:
        result = self.audio_service.delete_prepared_audio_cache(video_id)
        self.activity_log.insert(0, "Cache de audio limpiada")
        return result

    def verify_transcription_backend(self):
        return self.transcription_service.verify_transcription_backend()

    def transcription_models(self):
        return self.transcription_service.list_models()

    def transcription_model_status(self, model_name: str) -> TranscriptionModelInfo:
        return self.transcription_service.get_model_status(model_name)

    def verify_transcription_model(self, model_name: str) -> TranscriptionModelInfo:
        return self.transcription_service.verify_model(model_name)

    def download_transcription_model(self, model_name: str, *, progress_callback=None):
        return self.transcription_service.download_model(model_name, progress_callback=progress_callback)

    def remove_transcription_model(self, model_name: str) -> bool:
        return self.transcription_service.remove_model(model_name)

    def transcribe_video(self, video_id: str, options: TranscriptionOptions, *, progress_callback=None):
        report = self.transcription_service.transcribe_video(
            video_id,
            options,
            progress_callback=progress_callback,
        )
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Transcripcion: {report.status.value}")
        return report

    def get_transcription(self, video_id: str) -> TranscriptionReport:
        return self.transcription_service.get_transcription(video_id)

    def is_transcription_stale(self, video_id: str) -> bool:
        return self.transcription_service.is_transcription_stale(video_id)

    def cancel_transcription(self, video_id: str) -> bool:
        return self.transcription_service.cancel_transcription(video_id)

    def delete_transcription(self, video_id: str) -> bool:
        deleted = self.transcription_service.delete_transcription(video_id)
        if deleted:
            self.activity_log.insert(0, "Transcripcion eliminada")
        return deleted

    def analyze_acoustics(self, video_id: str, force: bool = False, *, progress_callback=None) -> AcousticAnalysisReport:
        report = self.acoustic_service.analyze_acoustics(video_id, force=force, progress_callback=progress_callback)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Analisis acustico: {report.status.value}")
        return report

    def get_acoustic_analysis(self, video_id: str) -> AcousticAnalysisReport:
        return self.acoustic_service.get_acoustic_analysis(video_id)

    def get_acoustic_timeline(self, video_id: str) -> list[AcousticTimelineWindow]:
        return self.acoustic_service.get_acoustic_timeline(video_id)

    def list_acoustic_events(self, video_id: str) -> list[AcousticEvent]:
        return self.acoustic_service.list_acoustic_events(video_id)

    def is_acoustic_analysis_stale(self, video_id: str) -> bool:
        return self.acoustic_service.is_acoustic_analysis_stale(video_id)

    def delete_acoustic_analysis(self, video_id: str) -> bool:
        deleted = self.acoustic_service.delete_acoustic_analysis(video_id)
        if deleted:
            self.activity_log.insert(0, "Analisis acustico eliminado")
        return deleted

    def export_acoustic_analysis(self, video_id: str, format: str) -> AcousticAnalysisExportResult:
        result = self.acoustic_service.export_acoustic_analysis(video_id, format)
        self.activity_log.insert(0, f"Analisis acustico exportado: {format}")
        return result

    def analyze_visuals(self, video_id: str, force: bool = False, *, progress_callback=None) -> VisualAnalysisReport:
        report = self.visual_service.analyze_visuals(video_id, force=force, progress_callback=progress_callback)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Analisis visual: {report.status.value}")
        return report

    def get_visual_analysis(self, video_id: str) -> VisualAnalysisReport:
        return self.visual_service.get_visual_analysis(video_id)

    def get_visual_timeline(self, video_id: str) -> list[VisualTimelineWindow]:
        return self.visual_service.get_visual_timeline(video_id)

    def list_visual_scenes(self, video_id: str) -> list[VisualScene]:
        return self.visual_service.list_visual_scenes(video_id)

    def list_visual_events(self, video_id: str) -> list[VisualEvent]:
        return self.visual_service.list_visual_events(video_id)

    def is_visual_analysis_stale(self, video_id: str) -> bool:
        return self.visual_service.is_visual_analysis_stale(video_id)

    def delete_visual_analysis(self, video_id: str) -> bool:
        deleted = self.visual_service.delete_visual_analysis(video_id)
        if deleted:
            self.activity_log.insert(0, "Analisis visual eliminado")
        return deleted

    def export_visual_analysis(self, video_id: str, format: str) -> VisualAnalysisExportResult:
        result = self.visual_service.export_visual_analysis(video_id, format)
        self.activity_log.insert(0, f"Analisis visual exportado: {format}")
        return result

    def export_transcription(self, video_id: str, format: TranscriptionExportFormat) -> TranscriptionExportResult:
        result = self.transcription_service.export_transcription(video_id, format)
        self.activity_log.insert(0, f"Transcripcion exportada: {format.value}")
        return result

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

    def video_inspector_items(
        self,
        video,
        inspection_report: VideoInspectionReport | None = None,
        audio_report: PreparedAudioReport | None = None,
    ) -> list[InspectorItemViewModel]:
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
        items.append(InspectorItemViewModel("Audio preparado", _audio_status_label(audio_report)))
        if audio_report is not None:
            selected = audio_report.selected_stream
            items.extend(
                [
                    InspectorItemViewModel("Stream seleccionado", _audio_stream_label(audio_report)),
                    InspectorItemViewModel("Formato de audio", audio_report.prepared_audio.format_name if audio_report.prepared_audio else "No verificado"),
                    InspectorItemViewModel("Codec de audio", audio_report.prepared_audio.codec_name if audio_report.prepared_audio else "No verificado"),
                    InspectorItemViewModel(
                        "Sample rate",
                        _audio_text(audio_report.prepared_audio.sample_rate_hz if audio_report.prepared_audio else None, "Hz"),
                    ),
                    InspectorItemViewModel(
                        "Canales",
                        _audio_text(audio_report.prepared_audio.channels if audio_report.prepared_audio else None, ""),
                    ),
                    InspectorItemViewModel(
                        "Bit depth",
                        _audio_text(audio_report.prepared_audio.bit_depth if audio_report.prepared_audio else None, "bit"),
                    ),
                    InspectorItemViewModel(
                        "Duracion",
                        _humanize_seconds(audio_report.prepared_audio.duration_seconds if audio_report.prepared_audio else None),
                    ),
                    InspectorItemViewModel(
                        "Tamano",
                        _humanize_bytes(audio_report.prepared_audio.file_size_bytes if audio_report.prepared_audio else None),
                    ),
                    InspectorItemViewModel(
                        "Generado",
                        _format_datetime(audio_report.prepared_audio.extraction_completed_at if audio_report.prepared_audio else None),
                    ),
                    InspectorItemViewModel(
                        "Vigencia",
                        "Stale" if audio_report.is_stale else "Vigente",
                    ),
                    InspectorItemViewModel(
                        "Ruta de caché",
                        audio_report.cache_path or "No disponible",
                    ),
                ]
            )
            if selected is not None:
                items.extend(
                    [
                        InspectorItemViewModel("Stream idioma", selected.language or "No verificado"),
                        InspectorItemViewModel("Stream default", "Si" if selected.is_default else "No"),
                    ]
                )
        transcription_report = self.get_transcription(video.id)
        transcription = transcription_report.transcription
        items.extend(
            [
                InspectorItemViewModel("Transcripcion", transcription_report.status.value),
                InspectorItemViewModel("Transcripcion stale", "Si" if transcription_report.is_stale else "No"),
            ]
        )
        if transcription is not None:
            items.extend(
                [
                    InspectorItemViewModel("Modelo de transcripcion", transcription.model_name),
                    InspectorItemViewModel(
                        "Estado del modelo",
                        self.transcription_model_status(transcription.model_name).status.value,
                    ),
                    InspectorItemViewModel("Dispositivo de transcripcion", transcription.device),
                    InspectorItemViewModel("Compute type", transcription.compute_type),
                    InspectorItemViewModel("Idioma detectado", transcription.detected_language or "No verificado"),
                    InspectorItemViewModel(
                        "Tiempo de procesamiento",
                        f"{transcription.processing_time_seconds:.3f} s",
                    ),
                    InspectorItemViewModel(
                        "Real-time factor",
                        f"{transcription.real_time_factor:.3f}",
                    ),
                ]
            )
        acoustic_report = self.get_acoustic_analysis(video.id)
        acoustic = acoustic_report.analysis
        items.extend(
            [
                InspectorItemViewModel("Analisis acustico", acoustic_report.status.value),
                InspectorItemViewModel("Analisis acustico stale", "Si" if acoustic_report.is_stale else "No"),
            ]
        )
        if acoustic is not None:
            items.extend(
                [
                    InspectorItemViewModel("Duracion de voz", f"{acoustic.speech_duration_seconds:.3f} s"),
                    InspectorItemViewModel("Duracion de silencio", f"{acoustic.silence_duration_seconds:.3f} s"),
                    InspectorItemViewModel("Speech ratio", f"{acoustic.speech_ratio:.3f}"),
                    InspectorItemViewModel(
                        "Palabras por minuto",
                        f"{acoustic.words_per_minute:.3f}" if acoustic.words_per_minute is not None else "No verificado",
                    ),
                    InspectorItemViewModel("Pausas", str(acoustic.pause_count)),
                    InspectorItemViewModel(
                        "Pausa mas larga",
                        f"{acoustic.longest_pause_seconds:.3f} s" if acoustic.longest_pause_seconds is not None else "No verificada",
                    ),
                    InspectorItemViewModel("Energia media", f"{acoustic.average_energy:.6f}"),
                    InspectorItemViewModel("Rango dinamico", f"{acoustic.dynamic_range:.6f}"),
                    InspectorItemViewModel("Cambios bruscos", str(acoustic.abrupt_change_count)),
                    InspectorItemViewModel("Eventos candidatos", str(acoustic.event_candidate_count)),
                ]
            )
        visual_report = self.get_visual_analysis(video.id)
        visual = visual_report.analysis
        items.extend(
            [
                InspectorItemViewModel("Analisis visual", visual_report.status.value),
                InspectorItemViewModel("Analisis visual stale", "Si" if visual_report.is_stale else "No"),
            ]
        )
        if visual is not None:
            items.extend(
                [
                    InspectorItemViewModel("Cortes visuales", str(visual.detected_cut_count)),
                    InspectorItemViewModel("Escenas visuales", str(visual.detected_scene_count)),
                    InspectorItemViewModel("Keyframes", str(visual.keyframe_count)),
                    InspectorItemViewModel("Movimiento medio", f"{visual.average_motion:.4f}"),
                    InspectorItemViewModel("Movimiento pico", f"{visual.peak_motion:.4f}"),
                    InspectorItemViewModel("Brillo medio", f"{visual.average_brightness:.4f}"),
                    InspectorItemViewModel("Contraste medio", f"{visual.average_contrast:.4f}"),
                    InspectorItemViewModel("Segmentos estaticos", str(visual.static_segment_count)),
                    InspectorItemViewModel("Frames negros", str(visual.black_frame_event_count)),
                    InspectorItemViewModel("Congelamientos", str(visual.freeze_event_count)),
                ]
            )
        multimodal_report = self.get_multimodal_analysis(video.id)
        multimodal = multimodal_report.analysis
        items.extend(
            [
                InspectorItemViewModel("Analisis multimodal", multimodal_report.status.value),
                InspectorItemViewModel("Analisis multimodal stale", "Si" if multimodal_report.is_stale else "No"),
            ]
        )
        if multimodal is not None:
            items.extend(
                [
                    InspectorItemViewModel("Ventanas multimodales", str(multimodal.window_count)),
                    InspectorItemViewModel("Candidatos multimodales", str(multimodal.candidate_count)),
                    InspectorItemViewModel("Candidatos alta actividad", str(multimodal.high_activity_candidate_count)),
                    InspectorItemViewModel("Candidatos transicion", str(multimodal.transition_candidate_count)),
                    InspectorItemViewModel("Candidatos baja actividad", str(multimodal.silence_candidate_count)),
                    InspectorItemViewModel("Duracion multimodal", f"{multimodal.duration_seconds:.3f} s"),
                ]
            )
            if multimodal_report.missing_sources:
                items.extend(
                    [
                        InspectorItemViewModel("Fuentes faltantes", ", ".join(multimodal_report.missing_sources)),
                    ]
                )
        clip_report = self.get_ranking_run(video.id)
        items.extend(
            [
                InspectorItemViewModel("Ranking de clips", clip_report.status.value),
                InspectorItemViewModel("Ranking de clips stale", "Si" if clip_report.is_stale else "No"),
            ]
        )
        if clip_report.run is not None:
            items.extend(
                [
                    InspectorItemViewModel("Candidatos rankeados", str(clip_report.run.ranked_candidate_count)),
                    InspectorItemViewModel("Seleccionados", str(clip_report.run.selected_count)),
                    InspectorItemViewModel("Rechazados", str(clip_report.run.rejected_count)),
                    InspectorItemViewModel("Revision humana", str(clip_report.run.review_count)),
                ]
            )
            if clip_report.missing_sources:
                items.append(InspectorItemViewModel("Fuentes faltantes ranking", ", ".join(clip_report.missing_sources)))
        return items

    def analyze_multimodal(self, video_id: str, force: bool = False, *, progress_callback=None) -> MultimodalAnalysisReport:
        report = self.multimodal_service.analyze_multimodal(video_id, force=force, progress_callback=progress_callback)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Analisis multimodal: {report.status.value}")
        return report

    def get_multimodal_analysis(self, video_id: str) -> MultimodalAnalysisReport:
        return self.multimodal_service.get_multimodal_analysis(video_id)

    def get_multimodal_timeline(self, video_id: str):
        return self.multimodal_service.get_multimodal_timeline(video_id)

    def list_moment_candidates(self, video_id: str):
        return self.multimodal_service.list_moment_candidates(video_id)

    def get_moment_candidate(self, candidate_id: str):
        return self.multimodal_service.get_moment_candidate(candidate_id)

    def is_multimodal_analysis_stale(self, video_id: str) -> bool:
        return self.multimodal_service.is_multimodal_analysis_stale(video_id)

    def delete_multimodal_analysis(self, video_id: str) -> bool:
        deleted = self.multimodal_service.delete_multimodal_analysis(video_id)
        if deleted:
            self.activity_log.insert(0, f"Analisis multimodal eliminado: {video_id}")
        return deleted

    def export_multimodal_analysis(self, video_id: str, format_name: str) -> MultimodalAnalysisExportResult:
        result = self.multimodal_service.export_multimodal_analysis(video_id, format_name)
        self.activity_log.insert(0, f"Exportacion multimodal: {format_name}")
        return result

    def rank_clip_candidates(self, video_id: str, profile: str = "balanced", force: bool = False, *, progress_callback=None) -> ClipRankingReport:
        report = self.clip_service.rank_clip_candidates(video_id, profile=profile, force=force, progress_callback=progress_callback)
        self.selected_video_id = video_id
        self.activity_log.insert(0, f"Ranking de clips: {report.status.value}")
        return report

    def get_ranking_run(self, video_id: str) -> ClipRankingReport:
        return self.clip_service.get_ranking_run(video_id)

    def list_ranked_candidates(self, video_id: str, filters=None, sort=None):
        return self.clip_service.list_ranked_candidates(video_id, filters=filters, sort=sort)

    def get_ranked_candidate(self, candidate_id: str):
        return self.clip_service.get_ranked_candidate(candidate_id)

    def approve_candidate(self, candidate_id: str):
        candidate = self.clip_service.approve_candidate(candidate_id)
        self.activity_log.insert(0, f"Clip aprobado: {candidate.id}")
        return candidate

    def reject_candidate(self, candidate_id: str):
        candidate = self.clip_service.reject_candidate(candidate_id)
        self.activity_log.insert(0, f"Clip rechazado: {candidate.id}")
        return candidate

    def shortlist_candidate(self, candidate_id: str):
        candidate = self.clip_service.shortlist_candidate(candidate_id)
        self.activity_log.insert(0, f"Clip preseleccionado: {candidate.id}")
        return candidate

    def mark_candidate_needs_review(self, candidate_id: str):
        candidate = self.clip_service.mark_candidate_needs_review(candidate_id)
        self.activity_log.insert(0, f"Clip marcado para revision: {candidate.id}")
        return candidate

    def rate_candidate(self, candidate_id: str, rating: int):
        candidate = self.clip_service.rate_candidate(candidate_id, rating)
        self.activity_log.insert(0, f"Rating de clip: {candidate.id} -> {rating}")
        return candidate

    def add_candidate_note(self, candidate_id: str, note: str):
        candidate = self.clip_service.add_candidate_note(candidate_id, note)
        self.activity_log.insert(0, f"Nota de clip: {candidate.id}")
        return candidate

    def set_candidate_tags(self, candidate_id: str, tags: list[str]):
        candidate = self.clip_service.set_candidate_tags(candidate_id, tags)
        self.activity_log.insert(0, f"Tags de clip: {candidate.id}")
        return candidate

    def adjust_candidate_bounds(self, candidate_id: str, start_seconds: float, end_seconds: float):
        candidate = self.clip_service.adjust_candidate_bounds(candidate_id, start_seconds, end_seconds)
        self.activity_log.insert(0, f"Bordes de clip ajustados: {candidate.id}")
        return candidate

    def reset_candidate_review(self, candidate_id: str):
        candidate = self.clip_service.reset_candidate_review(candidate_id)
        self.activity_log.insert(0, f"Revision de clip restablecida: {candidate.id}")
        return candidate

    def get_candidate_review_history(self, candidate_id: str):
        return self.clip_service.get_candidate_review_history(candidate_id)

    def is_clip_ranking_stale(self, video_id: str) -> bool:
        return self.clip_service.is_clip_ranking_stale(video_id)

    def delete_clip_ranking(self, video_id: str) -> bool:
        deleted = self.clip_service.delete_clip_ranking(video_id)
        if deleted:
            self.activity_log.insert(0, f"Ranking de clips eliminado: {video_id}")
        return deleted

    def create_clip_collection(self, video_id: str, name: str, description: str | None = None):
        collection = self.clip_service.create_clip_collection(video_id, name, description=description)
        self.activity_log.insert(0, f"Coleccion de clips creada: {collection.name}")
        return collection

    def add_candidate_to_collection(self, collection_id: str, candidate_id: str):
        item = self.clip_service.add_candidate_to_collection(collection_id, candidate_id)
        self.activity_log.insert(0, f"Clip agregado a coleccion: {candidate_id}")
        return item

    def remove_candidate_from_collection(self, collection_id: str, candidate_id: str) -> bool:
        removed = self.clip_service.remove_candidate_from_collection(collection_id, candidate_id)
        if removed:
            self.activity_log.insert(0, f"Clip removido de coleccion: {candidate_id}")
        return removed

    def export_clip_plan(self, video_id: str, format_name: str) -> ClipRankingExportResult:
        result = self.clip_service.export_clip_plan(video_id, format_name)
        self.activity_log.insert(0, f"Exportacion de clip plan: {format_name}")
        return result
