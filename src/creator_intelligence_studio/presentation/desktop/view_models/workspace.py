"""Modelo de coordinacion para la interfaz de escritorio."""

from __future__ import annotations

from dataclasses import replace
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
from creator_intelligence_studio.application.services.clip_rendering_service import (
    ClipRenderBatchReport,
    ClipRenderOperationReport,
    ClipRenderService,
)
from creator_intelligence_studio.application.services.analytics_import_service import (
    AnalyticsImportService,
)
from creator_intelligence_studio.application.services.subtitle_service import (
    SubtitleExportResult,
    SubtitleService,
    SubtitleTrackReport,
)
from creator_intelligence_studio.application.services.personalization_dataset_service import (
    CreatorReadinessReport,
    DatasetSnapshotComparison,
    PersonalizationDatasetExportResult,
    PersonalizationDatasetReport,
    PersonalizationDatasetService,
)
from creator_intelligence_studio.application.services.personalization_training_service import (
    PersonalizationActiveModelReport,
    PersonalizedScoreReport,
    PersonalizationTrainingReport,
    PersonalizationTrainingService,
    TrainingValidationReport,
)
from creator_intelligence_studio.application.services.operational_evaluation_service import (
    OperationalEvaluationComparisonReport,
    OperationalEvaluationService,
)
from creator_intelligence_studio.application.services.video_pipeline_service import (
    VideoPipelineService,
    VideoPipelineStatus,
    VideoWorkflowStepResult,
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
from creator_intelligence_studio.presentation.desktop.ui_state import (
    BackgroundTaskRecord,
    WorkspaceUiStateStore,
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


class _RenderCancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


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
        render_service: ClipRenderService | None = None,
        subtitle_service: SubtitleService | None = None,
        diagnostic: EnvironmentDiagnostic,
        settings: AppSettings,
        paths: ProjectPaths,
        personalization_service: PersonalizationDatasetService | None = None,
        model_service: PersonalizationTrainingService | None = None,
        evaluation_service: OperationalEvaluationService | None = None,
        analytics_service: AnalyticsImportService | None = None,
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
        if render_service is None:
            from types import SimpleNamespace

            render_service = SimpleNamespace(
                render_capabilities=lambda: SimpleNamespace(available=False, to_dict=lambda: {"available": False}),
                render_profiles=lambda: (),
                render_candidate=lambda *args, **kwargs: SimpleNamespace(job=SimpleNamespace(to_dict=lambda: {}), plan=SimpleNamespace(to_dict=lambda: {}), verification=None, artifact=None, reused_output=False, warnings=(), errors=(), to_dict=lambda: {}),
                get_render_job=lambda *args, **kwargs: None,
                list_render_jobs=lambda *args, **kwargs: (),
                list_candidate_renders=lambda *args, **kwargs: (),
                list_collection_renders=lambda *args, **kwargs: (),
                list_video_renders=lambda *args, **kwargs: (),
                list_render_batches_for_collection=lambda *args, **kwargs: (),
                list_render_batches_for_video=lambda *args, **kwargs: (),
                get_render_batch=lambda *args, **kwargs: None,
                list_batch_items=lambda *args, **kwargs: (),
                verify_render=lambda *args, **kwargs: SimpleNamespace(to_dict=lambda: {}),
                delete_render_artifact=lambda *args, **kwargs: False,
                reveal_render_output=lambda *args, **kwargs: None,
                cancel_render=lambda *args, **kwargs: None,
                cancel_render_batch=lambda *args, **kwargs: None,
                retry_render=lambda *args, **kwargs: SimpleNamespace(to_dict=lambda: {}),
                retry_render_batch=lambda *args, **kwargs: SimpleNamespace(batch=SimpleNamespace(to_dict=lambda: {}), jobs=(), warnings=(), errors=(), to_dict=lambda: {}),
                render_collection=lambda *args, **kwargs: SimpleNamespace(batch=SimpleNamespace(to_dict=lambda: {}), jobs=(), warnings=(), errors=(), to_dict=lambda: {}),
                create_render_job=lambda *args, **kwargs: SimpleNamespace(to_dict=lambda: {}),
                export_render_plan=lambda *args, **kwargs: Path(""),
            )
        self.render_service = render_service
        self.subtitle_service = subtitle_service
        self.analytics_service = analytics_service
        self.personalization_service = personalization_service
        self.model_service = model_service
        self.evaluation_service = evaluation_service
        self.diagnostic = diagnostic
        self.settings = settings
        self.paths = paths
        self.ui_state_store = WorkspaceUiStateStore(paths.data_directory / "workspace_ui_state.json")
        self.ui_state = self.ui_state_store.load()
        self._active_render_tokens: dict[str, _RenderCancellationToken] = {}
        self.selected_creator_id: str | None = self.ui_state.active_creator_id
        self.selected_project_id: str | None = self.ui_state.active_project_id
        self.selected_video_id: str | None = None
        self.activity_log: list[str] = []
        self.pipeline_service = VideoPipelineService(
            catalog_service=self.service,
            media_service=self.media_service,
            audio_service=self.audio_service,
            transcription_service=self.transcription_service,
            acoustic_service=self.acoustic_service,
            visual_service=self.visual_service,
            multimodal_service=self.multimodal_service,
            clip_service=self.clip_service,
            subtitle_service=self.subtitle_service,
            personalization_service=self.personalization_service,
        )
        self._sync_default_selection()

    def _sync_default_selection(self) -> None:
        creators = self.service.list_creators()
        if not creators:
            self.selected_creator_id = None
            self.selected_project_id = None
            self.selected_video_id = None
            return
        creator_ids = {creator.id for creator in creators}
        if self.selected_creator_id not in creator_ids:
            if self.ui_state.active_creator_id in creator_ids:
                self.selected_creator_id = self.ui_state.active_creator_id
            else:
                active_creator = next((creator for creator in creators if creator.status == CreatorStatus.ACTIVE), creators[0])
                self.selected_creator_id = active_creator.id
        projects = self.projects_for_selected_creator()
        if projects:
            project_ids = {project.id for project in projects}
            if self.selected_project_id not in project_ids:
                if self.ui_state.active_project_id in project_ids and self.selected_creator_id == self.ui_state.active_creator_id:
                    self.selected_project_id = self.ui_state.active_project_id
                else:
                    self.selected_project_id = projects[0].id
        else:
            self.selected_project_id = None
        if self.selected_project_id is None:
            self.selected_video_id = None

    def refresh(self) -> None:
        self._sync_default_selection()

    def set_last_page(self, page_key: str) -> None:
        self.ui_state = self.ui_state_store.update(self.ui_state, last_page=page_key)

    def set_onboarding_seen(self, seen: bool) -> None:
        self.ui_state = self.ui_state_store.update(self.ui_state, onboarding_seen=seen)

    def set_technical_details_visible(self, visible: bool) -> None:
        self.ui_state = self.ui_state_store.update(self.ui_state, show_technical_details=visible)

    def set_transcription_preferences(self, *, device: str | None = None, profile: str | None = None) -> None:
        changes: dict[str, object] = {}
        if device is not None:
            changes["preferred_transcription_device"] = device
        if profile is not None:
            changes["transcription_profile"] = profile
        if changes:
            self.ui_state = self.ui_state_store.update(self.ui_state, **changes)

    def set_ranking_profile(self, profile: str) -> None:
        self.ui_state = self.ui_state_store.update(self.ui_state, ranking_profile=profile)

    def _persist_selection(self) -> None:
        self.ui_state = self.ui_state_store.update(
            self.ui_state,
            active_creator_id=self.selected_creator_id,
            active_project_id=self.selected_project_id,
        )

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
        self._persist_selection()

    def select_project(self, project_id: str) -> None:
        project = self.service.get_project(project_id)
        self.selected_project_id = project.id
        self.selected_creator_id = project.creator_id
        self.selected_video_id = None
        self._persist_selection()

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
        self._persist_selection()
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
        self._persist_selection()
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
        self._persist_selection()
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

    def default_transcription_options(self) -> TranscriptionOptions:
        return TranscriptionOptions(
            profile=self.ui_state.transcription_profile,
            device=self.ui_state.preferred_transcription_device,
            model_name="small",
        )

    def video_pipeline_status(self, video_id: str) -> VideoPipelineStatus:
        return self.pipeline_service.get_video_pipeline_status(video_id)

    def run_pipeline_next_step(self, video_id: str, *, progress_callback=None) -> VideoWorkflowStepResult:
        return self.pipeline_service.run_next_step(
            video_id,
            transcription_device=self.ui_state.preferred_transcription_device,
            transcription_profile=self.ui_state.transcription_profile,
            progress_callback=progress_callback,
        )

    def run_pipeline_until_ranking(self, video_id: str, *, progress_callback=None) -> list[VideoWorkflowStepResult]:
        return self.pipeline_service.run_until_ranking(
            video_id,
            transcription_device=self.ui_state.preferred_transcription_device,
            transcription_profile=self.ui_state.transcription_profile,
            progress_callback=progress_callback,
        )

    def run_pipeline_group(self, video_id: str, group_name: str, *, progress_callback=None) -> list[VideoWorkflowStepResult]:
        return self.pipeline_service.run_stage_group(
            video_id,
            group_name,
            transcription_device=self.ui_state.preferred_transcription_device,
            transcription_profile=self.ui_state.transcription_profile,
            progress_callback=progress_callback,
        )

    def retry_pipeline_stage(self, video_id: str, stage_name: str, *, progress_callback=None) -> VideoWorkflowStepResult:
        return self.pipeline_service.retry_stage(
            video_id,
            stage_name,
            transcription_device=self.ui_state.preferred_transcription_device,
            transcription_profile=self.ui_state.transcription_profile,
            progress_callback=progress_callback,
        )

    def background_tasks(self) -> list[BackgroundTaskRecord]:
        tasks = list(self.ui_state.tasks)
        if self.render_service is not None:
            try:
                render_jobs = self.render_service.list_render_jobs()
            except Exception:
                render_jobs = []
            for job in render_jobs:
                try:
                    video = self.service.get_video(job.video_asset_id)
                    video_title = video.title if video else job.video_asset_id
                except Exception:
                    video_title = job.video_asset_id
                tasks.append(
                    BackgroundTaskRecord(
                        task_id=job.id,
                        title="Render de clip",
                        status=job.status.value,
                        stage_name=job.status.value,
                        video_id=job.video_asset_id,
                        video_title=video_title,
                        action_id=job.ranked_clip_candidate_id,
                        progress_percent=job.progress_percent,
                        message=job.warning_message or job.error_message or job.status.value,
                        error=job.error_message,
                        cancellable=job.status.value in {"queued", "validating", "preparing", "rendering", "verifying"},
                        created_at=to_iso_z(job.created_at),
                        updated_at=to_iso_z(job.updated_at),
                        interrupted_at=to_iso_z(job.cancelled_at) if job.status.value == "interrupted" else None,
                        completed_at=to_iso_z(job.completed_at),
                        payload=job.to_dict(),
                    )
                )
                try:
                    deliveries = self.render_service.list_render_deliveries(job.id)
                except Exception:
                    deliveries = []
                for delivery in deliveries:
                    tasks.append(
                        BackgroundTaskRecord(
                            task_id=delivery.id,
                            title="Entrega de subtitulos" if delivery.subtitle_mode.value != "burn_in" else "Render con subtitulos",
                            status=delivery.status.value,
                            stage_name=delivery.status.value,
                            video_id=job.video_asset_id,
                            video_title=video_title,
                            action_id=delivery.subtitle_track_id,
                            progress_percent=delivery.progress_percent,
                            message=delivery.warning_message or delivery.error_message or delivery.status.value,
                            error=delivery.error_message,
                            cancellable=delivery.status.value in {"queued", "validating", "preparing", "rendering", "verifying"},
                            created_at=to_iso_z(delivery.created_at),
                            updated_at=to_iso_z(delivery.updated_at),
                            interrupted_at=to_iso_z(delivery.cancelled_at) if delivery.status.value == "interrupted" else None,
                            completed_at=to_iso_z(delivery.completed_at),
                            payload={"delivery": delivery.to_dict(), "kind": "subtitle_delivery"},
                    )
                )
        if self.analytics_service is not None and self.selected_creator_id is not None:
            try:
                imports = self.analytics_service.list_imports(self.selected_creator_id)
            except Exception:
                imports = []
            for import_record in imports:
                tasks.append(
                    BackgroundTaskRecord(
                        task_id=import_record.id,
                        title="Importacion de analytics",
                        status=import_record.status.value,
                        stage_name=import_record.status.value,
                        video_id=None,
                        video_title=import_record.source_filename,
                        action_id=import_record.channel_id,
                        progress_percent=100.0 if import_record.status.value in {"completed", "completed_with_warnings"} else 0.0,
                        message=import_record.error_message or import_record.status.value,
                        error=import_record.error_message,
                        cancellable=import_record.status.value in {"queued", "running", "verifying"},
                        created_at=to_iso_z(import_record.created_at),
                        updated_at=to_iso_z(import_record.updated_at),
                        interrupted_at=to_iso_z(import_record.completed_at) if import_record.status.value == "interrupted" else None,
                        completed_at=to_iso_z(import_record.completed_at),
                        payload={"import": import_record.to_dict(), "kind": "analytics_import"},
                    )
                )
        return sorted(tasks, key=lambda item: item.updated_at, reverse=True)

    def _update_tasks(self, tasks: tuple[BackgroundTaskRecord, ...]) -> None:
        self.ui_state = self.ui_state_store.update(self.ui_state, tasks=tasks)

    def register_background_task(
        self,
        *,
        title: str,
        status: str,
        stage_name: str | None = None,
        video_id: str | None = None,
        video_title: str | None = None,
        action_id: str | None = None,
        progress_percent: float = 0.0,
        message: str | None = None,
        error: str | None = None,
        cancellable: bool = True,
        payload: dict[str, object] | None = None,
    ) -> BackgroundTaskRecord:
        from datetime import datetime, timezone
        from uuid import uuid4

        task = BackgroundTaskRecord(
            task_id=str(uuid4()),
            title=title,
            status=status,
            stage_name=stage_name,
            video_id=video_id,
            video_title=video_title,
            action_id=action_id,
            progress_percent=progress_percent,
            message=message,
            error=error,
            cancellable=cancellable,
            payload=payload or {},
            created_at=to_iso_z(datetime.now(timezone.utc)),
            updated_at=to_iso_z(datetime.now(timezone.utc)),
        )
        self._update_tasks(tuple(self.ui_state.tasks) + (task,))
        return task

    def update_background_task(self, task_id: str, **changes) -> BackgroundTaskRecord | None:
        from datetime import datetime, timezone

        updated: BackgroundTaskRecord | None = None
        tasks: list[BackgroundTaskRecord] = []
        now = to_iso_z(datetime.now(timezone.utc))
        for task in self.ui_state.tasks:
            if task.task_id == task_id:
                updated = replace(task, updated_at=now, **changes)
                tasks.append(updated)
            else:
                tasks.append(task)
        if updated is not None:
            self._update_tasks(tuple(tasks))
        return updated

    def complete_background_task(self, task_id: str, message: str | None = None) -> BackgroundTaskRecord | None:
        from datetime import datetime, timezone

        return self.update_background_task(
            task_id,
            status="completed",
            progress_percent=100.0,
            message=message,
            completed_at=to_iso_z(datetime.now(timezone.utc)),
        )

    def fail_background_task(self, task_id: str, error: str) -> BackgroundTaskRecord | None:
        return self.update_background_task(task_id, status="failed", error=error, message=error)

    def interrupt_background_task(self, task_id: str, message: str | None = None) -> BackgroundTaskRecord | None:
        from datetime import datetime, timezone

        return self.update_background_task(
            task_id,
            status="interrupted",
            message=message,
            interrupted_at=to_iso_z(datetime.now(timezone.utc)),
        )

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
        active_tasks = [task for task in self.background_tasks() if task.status in {"running", "pending", "interrupted"}]
        readiness_value = "Sin dato"
        readiness_detail = "No hay dataset disponible"
        if active_creator and self.personalization_service is not None:
            try:
                readiness = self.get_creator_readiness(active_creator.id)
                readiness_value = readiness.readiness_status.value
                readiness_detail = f"Score: {readiness.readiness_score:.3f}"
            except Exception:
                readiness_value = "No disponible"
                readiness_detail = "No se pudo evaluar"
        return [
            CardViewModel(title="Creador activo", value=active_creator.display_name if active_creator else "Ninguno", detail=active_creator.slug if active_creator else "Seleccione uno", icon="○"),
            CardViewModel(title="Proyecto activo", value=active_project.name if active_project else "Ninguno", detail=active_project.project_type.value if active_project else "Seleccione uno", accent="accent_ml", icon="◧"),
            CardViewModel(title="Proyectos activos", value=str(len(active_projects)), detail=f"Total de proyectos: {len(projects)}", accent="accent_ml", icon="◪"),
            CardViewModel(title="Videos registrados", value=str(len(videos)), detail="Metadatos locales registrados", icon="▶"),
            CardViewModel(title="Tareas activas", value=str(len(active_tasks)), detail="Workflow, transcripcion o evaluacion en segundo plano", accent="warning", icon="⏳"),
            CardViewModel(title="Videos pendientes", value=str(len(pending_videos)), detail="Registrados, en cola o procesando", accent="warning", icon="⏳"),
            CardViewModel(title="Personalizacion", value=readiness_value, detail=readiness_detail, accent="success" if readiness_value.startswith("ready") else "accent_ml", icon="λ"),
            CardViewModel(title="Almacenamiento disponible", value=_humanize_bytes(self.paths.free_space_bytes()), detail="Espacio libre en la unidad del proyecto", icon="¤"),
            CardViewModel(title="GPU detectada", value=self.diagnostic.gpu_devices[0].name if self.diagnostic.gpu_devices else "No verificada", detail=(f"VRAM: {self.diagnostic.gpu_devices[0].memory_total_mib / 1024:.1f} GiB" if self.diagnostic.gpu_devices and self.diagnostic.gpu_devices[0].memory_total_mib is not None else "VRAM no verificada"), accent="success" if self.diagnostic.gpu_devices else "warning", icon="◬"),
            CardViewModel(title="Estado CUDA", value=(f"Detectada por el controlador: {self.diagnostic.cuda_version_reported}" if self.diagnostic.cuda_version_reported else "Detectada por el controlador: no verificado"), detail="Runtime: no verificado", accent="accent_ml", icon="↻"),
            CardViewModel(title="Actividad reciente", value=self.activity_log[0] if self.activity_log else "Sin actividad reciente", detail=active_project.name if active_project else "Sin proyecto activo", accent="accent", icon="↻"),
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
        items = [
            InspectorItemViewModel("ID", creator.id),
            InspectorItemViewModel("Nombre", creator.display_name),
            InspectorItemViewModel("Slug", creator.slug),
            InspectorItemViewModel("Estado", _creator_status_label(creator.status)),
            InspectorItemViewModel("Descripcion", creator.description or "Sin descripcion"),
        ]
        if self.personalization_service is not None:
            readiness = self.get_creator_readiness(creator.id)
            items.extend(
                [
                    InspectorItemViewModel("Dataset personalizacion", readiness.readiness_status.value),
                    InspectorItemViewModel("Dataset readiness", f"{readiness.readiness_score:.3f}"),
                ]
            )
        return items

    def project_inspector_items(self, project) -> list[InspectorItemViewModel]:
        if project is None:
            return []
        items = [
            InspectorItemViewModel("ID", project.id),
            InspectorItemViewModel("Creador", project.creator_id),
            InspectorItemViewModel("Nombre", project.name),
            InspectorItemViewModel("Tipo", _project_type_label(project.project_type.value)),
            InspectorItemViewModel("Estado", _project_status_label(project.status)),
            InspectorItemViewModel("Descripcion", project.description or "Sin descripcion"),
        ]
        if self.personalization_service is not None:
            readiness = self.get_creator_readiness(project.creator_id)
            items.extend(
                [
                    InspectorItemViewModel("Dataset personalizacion", readiness.readiness_status.value),
                    InspectorItemViewModel("Dataset readiness", f"{readiness.readiness_score:.3f}"),
                ]
            )
        return items

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

    def render_capabilities(self):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.render_capabilities()

    def render_subtitle_capabilities(self):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.render_subtitle_capabilities()

    def render_subtitle_styles(self):
        if self.render_service is None:
            return []
        return self.render_service.render_subtitle_styles()

    def render_profiles(self):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.render_profiles()

    def create_render_job(self, candidate_id: str, *, profile: str = "balanced", output: str | None = None, output_root_override: str | None = None, explicit: bool = False, allow_stale: bool = False, allow_overwrite: bool = False, custom_name: str | None = None, collection_id: str | None = None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.create_render_job(
            candidate_id,
            profile=profile,
            output=output,
            output_root_override=output_root_override,
            explicit=explicit,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            custom_name=custom_name,
            collection_id=collection_id,
        )

    def create_sidecar_delivery(self, job_id: str, track_id: str, *, format_name: str = "srt", output: str | None = None, allow_stale: bool = False, allow_overwrite: bool = False, custom_name: str | None = None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.create_sidecar_delivery(
            job_id,
            track_id,
            format_name=format_name,
            output=output,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            custom_name=custom_name,
        )

    def create_burn_in_render(self, candidate_id: str, track_id: str, *, profile: str = "balanced", style: str = "clean", output: str | None = None, output_root_override: str | None = None, allow_stale: bool = False, allow_overwrite: bool = False, custom_name: str | None = None, progress_callback=None, cancellation_token=None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.create_burn_in_render(
            candidate_id,
            track_id,
            profile=profile,
            style_preset=style,
            output=output,
            output_root_override=output_root_override,
            allow_stale=allow_stale,
            allow_overwrite=allow_overwrite,
            custom_name=custom_name,
            progress_callback=progress_callback,
            cancellation_token=cancellation_token,
        )

    def render_candidate(self, candidate_id: str, *, profile: str = "balanced", output: str | None = None, output_root_override: str | None = None, explicit: bool = False, allow_stale: bool = False, allow_overwrite: bool = False, custom_name: str | None = None, collection_id: str | None = None, progress_callback=None, cancellation_token=None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        token = cancellation_token
        token_key = candidate_id
        own_token = False
        if token is None:
            token = _RenderCancellationToken()
            own_token = True
        self._active_render_tokens[token_key] = token
        try:
            report = self.render_service.render_candidate(
                candidate_id,
                profile=profile,
                output=output,
                output_root_override=output_root_override,
                explicit=explicit,
                allow_stale=allow_stale,
                allow_overwrite=allow_overwrite,
                custom_name=custom_name,
                collection_id=collection_id,
                progress_callback=progress_callback,
                cancellation_token=token,
            )
        finally:
            current_token = self._active_render_tokens.get(token_key)
            if current_token is token:
                self._active_render_tokens.pop(token_key, None)
        self.activity_log.insert(0, f"Render de clip: {report.job.status.value}")
        return report

    def get_render_job(self, job_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.get_render_job(job_id)

    def list_render_jobs(self):
        if self.render_service is None:
            return []
        return self.render_service.list_render_jobs()

    def get_delivery(self, delivery_id: str):
        if self.render_service is None:
            return None
        return self.render_service.get_delivery(delivery_id)

    def list_render_deliveries(self, job_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_render_deliveries(job_id)

    def list_candidate_deliveries(self, candidate_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_candidate_deliveries(candidate_id)

    def list_video_deliveries(self, video_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_video_deliveries(video_id)

    def list_candidate_renders(self, candidate_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_candidate_renders(candidate_id)

    def list_collection_renders(self, collection_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_collection_renders(collection_id)

    def list_clip_collections(self, video_id: str):
        return self.clip_service.list_clip_collections(video_id)

    def get_clip_collection(self, collection_id: str):
        return self.clip_service.get_clip_collection(collection_id)

    def list_render_batches_for_collection(self, collection_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_render_batches_for_collection(collection_id)

    def get_render_batch(self, batch_id: str):
        if self.render_service is None:
            return None
        return self.render_service.get_render_batch(batch_id)

    def list_batch_items(self, batch_id: str):
        if self.render_service is None:
            return []
        return self.render_service.list_batch_items(batch_id)

    def render_collection(self, collection_id: str, *, profile: str = "balanced", output_root: str | None = None, explicit: bool = False, allow_stale: bool = False, continue_on_failure: bool = False):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        report = self.render_service.render_collection(
            collection_id,
            profile=profile,
            output_root=output_root,
            explicit=explicit,
            allow_stale=allow_stale,
            continue_on_failure=continue_on_failure,
        )
        self.activity_log.insert(0, f"Render de coleccion: {report.batch.status.value}")
        return report

    def verify_render(self, job_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.verify_render(job_id)

    def verify_delivery(self, delivery_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.verify_delivery(delivery_id)

    def cancel_render(self, job_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        job = self.render_service.get_render_job(job_id)
        if job is not None and job.ranked_clip_candidate_id is not None:
            token = self._active_render_tokens.get(job.ranked_clip_candidate_id)
            if token is not None:
                token.cancel()
                self._active_render_tokens.pop(job.ranked_clip_candidate_id, None)
        return self.render_service.cancel_render(job_id)

    def cancel_render_batch(self, batch_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.cancel_render_batch(batch_id)

    def cancel_delivery(self, delivery_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.cancel_delivery(delivery_id)

    def retry_render(self, job_id: str, *, progress_callback=None, cancellation_token=None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.retry_render(job_id, progress_callback=progress_callback, cancellation_token=cancellation_token)

    def retry_render_batch(self, batch_id: str, *, progress_callback=None, cancellation_token=None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.retry_render_batch(batch_id, progress_callback=progress_callback, cancellation_token=cancellation_token)

    def retry_delivery(self, delivery_id: str, *, progress_callback=None, cancellation_token=None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.retry_delivery(delivery_id, progress_callback=progress_callback, cancellation_token=cancellation_token)

    def delete_render_artifact(self, job_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.delete_render_artifact(job_id)

    def delete_delivery(self, delivery_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.delete_delivery(delivery_id)

    def reveal_render_output(self, job_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.reveal_render_output(job_id)

    def reveal_delivery(self, delivery_id: str):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.reveal_delivery(delivery_id)

    def export_render_plan(self, job_id: str, destination: str | None = None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.export_render_plan(job_id, destination=destination)

    def export_delivery_manifest(self, delivery_id: str, destination: str | None = None):
        if self.render_service is None:
            raise RuntimeError("El servicio de render no esta disponible.")
        return self.render_service.export_delivery_manifest(delivery_id, destination=destination)

    def generate_video_subtitles(self, video_id: str, *, custom_name: str | None = None, force: bool = False):
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        report = self.subtitle_service.generate_video_subtitles(video_id, custom_name=custom_name, force=force)
        self.activity_log.insert(0, f"Subtitulos de video: {report.status.value}")
        return report

    def generate_clip_subtitles(self, candidate_id: str, *, custom_name: str | None = None, force: bool = False):
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        report = self.subtitle_service.generate_clip_subtitles(candidate_id, custom_name=custom_name, force=force)
        self.activity_log.insert(0, f"Subtitulos de clip: {report.status.value}")
        return report

    def get_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.get_subtitle_track(track_id)

    def list_video_subtitle_tracks(self, video_id: str):
        if self.subtitle_service is None:
            return []
        return self.subtitle_service.list_video_subtitle_tracks(video_id)

    def list_clip_subtitle_tracks(self, candidate_id: str):
        if self.subtitle_service is None:
            return []
        return self.subtitle_service.list_clip_subtitle_tracks(candidate_id)

    def list_render_job_subtitle_tracks(self, render_job_id: str):
        if self.subtitle_service is None:
            return []
        return self.subtitle_service.list_render_job_subtitle_tracks(render_job_id)

    def validate_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.validate_subtitle_track(track_id)

    def update_subtitle_cue_text(self, cue_id: str, text: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.update_cue_text(cue_id, text)

    def update_subtitle_cue_timing(self, cue_id: str, start_seconds: float, end_seconds: float) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.update_cue_timing(cue_id, start_seconds, end_seconds)

    def split_subtitle_cue(self, cue_id: str, split_position: int) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.split_cue(cue_id, split_position)

    def merge_subtitle_cues(self, first_cue_id: str, second_cue_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.merge_cues(first_cue_id, second_cue_id)

    def insert_subtitle_cue(self, track_id: str, index: int, start_seconds: float, end_seconds: float, text: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.insert_cue(track_id, index, start_seconds, end_seconds, text)

    def delete_subtitle_cue(self, cue_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.delete_cue(cue_id)

    def move_subtitle_cue(self, cue_id: str, new_index: int) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.move_cue(cue_id, new_index)

    def shift_subtitle_track(self, track_id: str, offset_seconds: float) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.shift_track(track_id, offset_seconds)

    def restore_subtitle_cue(self, cue_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.restore_cue(cue_id)

    def restore_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.restore_track(track_id)

    def lock_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.lock_track(track_id)

    def unlock_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.unlock_track(track_id)

    def duplicate_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.duplicate_track(track_id)

    def import_subtitles(self, video_id: str, file_path: str):
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.import_subtitles(video_id, Path(file_path))

    def export_subtitles(self, track_id: str, format_name: str, *, output: str | None = None):
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat

        destination = Path(output) if output else None
        return self.subtitle_service.export_subtitles(track_id, SubtitleExportFormat(format_name), output=destination)

    def archive_subtitle_track(self, track_id: str) -> SubtitleTrackReport:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.archive_subtitle_track(track_id)

    def delete_subtitle_track(self, track_id: str) -> bool:
        if self.subtitle_service is None:
            raise RuntimeError("El servicio de subtitulos no esta disponible.")
        return self.subtitle_service.delete_subtitle_track(track_id)

    def get_subtitle_edit_history(self, track_id: str):
        if self.subtitle_service is None:
            return []
        return self.subtitle_service.get_subtitle_edit_history(track_id)

    def list_analytics_platforms(self):
        if self.analytics_service is None:
            return []
        return self.analytics_service.list_platforms()

    def list_analytics_channels(self, creator_id: str):
        if self.analytics_service is None:
            return []
        return self.analytics_service.list_channels(creator_id)

    def create_analytics_channel(self, **kwargs):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.create_channel(**kwargs)

    def list_analytics_imports(self, creator_id: str):
        if self.analytics_service is None:
            return []
        return self.analytics_service.list_imports(creator_id)

    def get_analytics_import(self, import_id: str):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.get_import(import_id)

    def list_analytics_import_rows(self, import_id: str, status: str | None = None):
        if self.analytics_service is None:
            return []
        return self.analytics_service.get_import_rows(import_id, status=status)

    def detect_analytics_schema(self, file_path: str, *, sheet_name: str | None = None):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.detect_schema(Path(file_path), sheet_name=sheet_name)

    def inspect_analytics_file(self, file_path: str, *, sheet_name: str | None = None):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.inspect_file(Path(file_path), sheet_name=sheet_name)

    def import_analytics_csv(self, *, creator_id: str, file_path: str, channel_id: str | None = None, platform: str | None = None, mapping_name: str | None = None, delimiter: str | None = None):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.import_csv(creator_id=creator_id, file=Path(file_path), channel_id=channel_id, platform=platform, mapping_name=mapping_name, delimiter=delimiter)

    def import_analytics_excel(self, *, creator_id: str, file_path: str, channel_id: str | None = None, platform: str | None = None, sheet_name: str | None = None, mapping_name: str | None = None):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.import_excel(creator_id=creator_id, file=Path(file_path), channel_id=channel_id, platform=platform, sheet_name=sheet_name, mapping_name=mapping_name)

    def list_analytics_mappings(self, creator_id: str):
        if self.analytics_service is None:
            return []
        return self.analytics_service.list_mappings(creator_id)

    def save_analytics_mapping(self, **kwargs):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.save_mapping(**kwargs)

    def list_analytics_publications(self, creator_id: str, *, filters=None):
        if self.analytics_service is None:
            return []
        return self.analytics_service.list_publications(creator_id, filters=filters)

    def get_analytics_publication(self, publication_id: str):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.get_publication(publication_id)

    def get_analytics_latest_metrics(self, publication_id: str):
        if self.analytics_service is None:
            return {}
        return self.analytics_service.get_latest_metrics(publication_id)

    def export_normalized_analytics(self, creator_id: str, format_name: str = "json"):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.export_normalized_data(creator_id=creator_id, format_name=format_name)

    def cancel_analytics_import(self, import_id: str):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.cancel_import(import_id)

    def retry_analytics_import(self, import_id: str):
        if self.analytics_service is None:
            raise RuntimeError("El servicio de analytics no esta disponible.")
        return self.analytics_service.retry_import(import_id)

    def reveal_analytics_import_report(self, import_id: str):
        if self.analytics_service is None:
            return None
        return self.analytics_service.get_import_report_path(import_id)

    def build_creator_dataset(self, creator_id: str, project_id: str | None = None, force: bool = False, *, progress_callback=None) -> PersonalizationDatasetReport:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        report = self.personalization_service.build_creator_dataset(
            creator_id,
            project_id=project_id,
            force=force,
            progress_callback=progress_callback,
        )
        self.activity_log.insert(0, f"Dataset de personalizacion: {report.status.value}")
        return report

    def get_dataset_snapshot(self, snapshot_id: str) -> PersonalizationDatasetReport:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.get_dataset_snapshot(snapshot_id)

    def get_latest_creator_dataset(self, creator_id: str) -> PersonalizationDatasetReport:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.get_latest_creator_dataset(creator_id)

    def list_creator_datasets(self, creator_id: str):
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.list_creator_datasets(creator_id)

    def list_dataset_examples(self, snapshot_id: str, filters=None):
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.list_dataset_examples(snapshot_id, filters=filters)

    def get_dataset_example(self, example_id: str):
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.get_dataset_example(example_id)

    def get_dataset_quality_report(self, snapshot_id: str):
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.get_dataset_quality_report(snapshot_id)

    def get_creator_readiness(self, creator_id: str) -> CreatorReadinessReport:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.get_creator_readiness(creator_id)

    def compare_dataset_snapshots(self, snapshot_a_id: str, snapshot_b_id: str) -> DatasetSnapshotComparison:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.compare_dataset_snapshots(snapshot_a_id, snapshot_b_id)

    def archive_dataset_snapshot(self, snapshot_id: str):
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        snapshot = self.personalization_service.archive_dataset_snapshot(snapshot_id)
        self.activity_log.insert(0, f"Dataset archivado: {snapshot.id}")
        return snapshot

    def export_dataset(self, snapshot_id: str, format_name: str, *, include_sensitive: bool = False) -> PersonalizationDatasetExportResult:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        result = self.personalization_service.export_dataset(snapshot_id, format_name, include_sensitive=include_sensitive)
        self.activity_log.insert(0, f"Exportacion de dataset: {format_name}")
        return result

    def is_dataset_stale(self, snapshot_id: str) -> bool:
        if self.personalization_service is None:
            raise RuntimeError("El servicio de personalizacion no esta disponible.")
        return self.personalization_service.is_dataset_stale(snapshot_id)

    def validate_training_snapshot(self, snapshot_id: str) -> TrainingValidationReport:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.validate_training_snapshot(snapshot_id)

    def train_personalization_baseline(self, snapshot_id: str, force: bool = False, *, progress_callback=None) -> PersonalizationTrainingReport:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        report = self.model_service.train_personalization_baseline(
            snapshot_id,
            force=force,
            progress_callback=progress_callback,
        )
        self.activity_log.insert(0, f"Modelo personalizado: {report.outcome_status}")
        return report

    def get_training_run(self, training_run_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.get_training_run(training_run_id)

    def list_creator_training_runs(self, creator_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.list_creator_training_runs(creator_id)

    def get_training_metrics(self, training_run_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.get_training_metrics(training_run_id)

    def list_training_predictions(self, training_run_id: str, split: str | None = None):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.list_training_predictions(training_run_id, split=split)

    def compare_training_runs(self, baseline_run_id: str, candidate_run_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.compare_training_runs(baseline_run_id, candidate_run_id)

    def activate_model(self, training_run_id: str) -> PersonalizationActiveModelReport:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.activate_model(training_run_id)

    def deactivate_model(self, training_run_id: str) -> PersonalizationActiveModelReport | None:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.deactivate_model(training_run_id)

    def retire_model(self, training_run_id: str) -> PersonalizationActiveModelReport | None:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.retire_model(training_run_id)

    def get_active_creator_model(self, creator_id: str, project_id: str | None = None) -> PersonalizationActiveModelReport | None:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.get_active_creator_model(creator_id, project_id=project_id)

    def verify_model_artifact(self, training_run_id: str) -> PersonalizationActiveModelReport:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.verify_model_artifact(training_run_id)

    def delete_model_artifact(self, training_run_id: str) -> bool:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.delete_model_artifact(training_run_id)

    def score_candidate_for_creator(self, creator_id: str, candidate_id: str) -> PersonalizedScoreReport:
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.score_candidate_for_creator(creator_id, candidate_id)

    def score_candidates_for_video(self, creator_id: str, video_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.score_candidates_for_video(creator_id, video_id)

    def explain_personalized_score(self, creator_id: str, candidate_id: str):
        if self.model_service is None:
            raise RuntimeError("El servicio de modelos personalizados no esta disponible.")
        return self.model_service.explain_personalized_score(creator_id, candidate_id)

    def list_operational_scenarios(self):
        if self.evaluation_service is None:
            return []
        return self.evaluation_service.list_scenarios()

    def run_operational_evaluation(self, scenario_id: str, force: bool = False, *, progress_callback=None):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.run_scenario(scenario_id, force=force, progress_callback=progress_callback)

    def get_operational_evaluation_run(self, run_id: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.get_report(run_id)

    def list_operational_evaluation_stages(self, run_id: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.list_stages(run_id)

    def list_operational_evaluation_metrics(self, run_id: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.list_metrics(run_id)

    def list_operational_evaluation_assertions(self, run_id: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.list_assertions(run_id)

    def list_operational_evaluation_artifacts(self, run_id: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.list_artifacts(run_id)

    def retry_operational_evaluation_stage(self, run_id: str, stage_name: str):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.retry_stage(run_id, stage_name)

    def cancel_operational_evaluation(self, run_id: str) -> bool:
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.cancel(run_id)

    def export_operational_evaluation(self, run_id: str, format_name: str, *, destination: Path | None = None):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.export(run_id, format_name, destination=destination)

    def compare_operational_evaluations(self, baseline_run_id: str, candidate_run_id: str) -> OperationalEvaluationComparisonReport:
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.compare_runs(baseline_run_id, candidate_run_id)

    def clean_operational_evaluation(self, run_id: str, *, dry_run: bool = False):
        if self.evaluation_service is None:
            raise RuntimeError("El servicio de evaluacion operativa no esta disponible.")
        return self.evaluation_service.clean(run_id, dry_run=dry_run)
