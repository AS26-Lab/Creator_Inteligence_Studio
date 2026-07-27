"""Interfaz de linea de comandos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from creator_intelligence_studio.application.commands.creator_commands import (
    ArchiveCreatorCommand,
    CreateCreatorCommand,
)
from creator_intelligence_studio.application.commands.audio_commands import (
    ClearAudioCacheCommand,
    PrepareAudioCommand,
    ShowPreparedAudioCommand,
    VerifyPreparedAudioCommand,
)
from creator_intelligence_studio.application.commands.acoustic_commands import (
    AnalyzeAcousticCommand,
    DeleteAcousticCommand,
    EventsAcousticCommand,
    ExportAcousticCommand,
    ShowAcousticCommand,
    TimelineAcousticCommand,
)
from creator_intelligence_studio.application.commands.visual_commands import (
    AnalyzeVisualCommand,
    DeleteVisualCommand,
    EventsVisualCommand,
    ExportVisualCommand,
    ScenesVisualCommand,
    ShowVisualCommand,
    TimelineVisualCommand,
)
from creator_intelligence_studio.application.commands.multimodal_commands import (
    AnalyzeMultimodalCommand,
    CandidateMultimodalCommand,
    CandidatesMultimodalCommand,
    DeleteMultimodalCommand,
    ExportMultimodalCommand,
    ShowMultimodalCommand,
    TimelineMultimodalCommand,
)
from creator_intelligence_studio.application.commands.clip_commands import (
    AdjustClipCandidateCommand,
    AddClipToCollectionCommand,
    CandidateClipCommand,
    CreateClipCollectionCommand,
    DeleteClipRankingCommand,
    ExportClipPlanCommand,
    ListClipCandidatesCommand,
    NoteClipCandidateCommand,
    RankClipCandidatesCommand,
    RateClipCandidateCommand,
    RemoveClipFromCollectionCommand,
    ShowClipRankingCommand,
    TagsClipCandidateCommand,
)
from creator_intelligence_studio.application.commands.render_commands import (
    CancelRenderBatchCommand,
    CancelRenderCommand,
    CancelRenderDeliveryCommand,
    DeleteRenderArtifactCommand,
    DeleteRenderDeliveryCommand,
    ExportRenderPlanCommand,
    ExportRenderDeliveryManifestCommand,
    ListRenderDeliveriesCommand,
    ListCandidateRendersCommand,
    RenderCapabilitiesCommand,
    RenderCandidateCommand,
    RenderBurnInCommand,
    RenderSidecarCommand,
    RenderSubtitlesCapabilitiesCommand,
    RenderSubtitlesStylesCommand,
    RenderCollectionCommand,
    RenderProfilesCommand,
    RetryRenderBatchCommand,
    RetryRenderCommand,
    RetryRenderDeliveryCommand,
    ShowRenderDeliveryCommand,
    ShowRenderBatchCommand,
    ShowRenderJobCommand,
    VerifyRenderCommand,
    VerifyRenderDeliveryCommand,
)
from creator_intelligence_studio.application.commands.personalization_commands import (
    ArchiveDatasetSnapshotCommand,
    BuildCreatorDatasetCommand,
    CompareDatasetSnapshotsCommand,
    CreatorReadinessCommand,
    DatasetExamplesCommand,
    DatasetQualityCommand,
    ExportDatasetCommand,
    LatestCreatorDatasetCommand,
    ListCreatorDatasetsCommand,
    ShowCreatorDatasetCommand,
)
from creator_intelligence_studio.application.commands.model_commands import (
    ActivatePersonalizationModelCommand,
    ComparePersonalizationModelRunsCommand,
    DeletePersonalizationModelArtifactCommand,
    DeactivatePersonalizationModelCommand,
    ExplainPersonalizedScoreCommand,
    ListPersonalizationModelRunsCommand,
    PersonalizationModelMetricsCommand,
    PersonalizationModelPredictionsCommand,
    RetirePersonalizationModelCommand,
    ScoreCandidateForCreatorCommand,
    ScoreVideoForCreatorCommand,
    ShowPersonalizationModelRunCommand,
    TrainPersonalizationModelCommand,
    ValidatePersonalizationSnapshotCommand,
    VerifyPersonalizationModelCommand,
    ActivePersonalizationModelCommand,
)
from creator_intelligence_studio.application.commands.evaluation_commands import (
    CancelOperationalEvaluationCommand,
    CleanOperationalEvaluationCommand,
    ExportOperationalEvaluationCommand,
    RetryOperationalEvaluationStageCommand,
    RunOperationalEvaluationCommand,
    ShowOperationalEvaluationCommand,
    StageOperationalEvaluationCommand,
)
from creator_intelligence_studio.application.commands.transcription_commands import (
    DeleteTranscriptionCommand,
    DownloadModelCommand,
    ExportTranscriptionCommand,
    ListSegmentsCommand,
    ModelStatusCommand,
    ShowTranscriptionCommand,
    TranscribeVideoCommand,
    VerifyModelCommand,
)
from creator_intelligence_studio.application.commands.subtitle_commands import (
    ArchiveSubtitleTrackCommand,
    DeleteSubtitleCueCommand,
    DeleteSubtitleTrackCommand,
    DuplicateSubtitleTrackCommand,
    ExportSubtitleTrackCommand,
    GenerateClipSubtitlesCommand,
    GenerateVideoSubtitlesCommand,
    ImportSubtitleTrackCommand,
    InsertSubtitleCueCommand,
    ListClipSubtitleTracksCommand,
    ListVideoSubtitleTracksCommand,
    LockSubtitleTrackCommand,
    MergeSubtitleCuesCommand,
    MoveSubtitleCueCommand,
    RegenerateSubtitleTrackCommand,
    ShiftSubtitleTrackCommand,
    ShowSubtitleTrackCommand,
    SplitSubtitleCueCommand,
    SubtitleHistoryCommand,
    UnlockSubtitleTrackCommand,
    UpdateSubtitleTextCommand,
    UpdateSubtitleTimeCommand,
    ValidateSubtitleTrackCommand,
)
from creator_intelligence_studio.application.commands.media_commands import (
    InspectVideoCommand,
    ShowVideoInspectionCommand,
)
from creator_intelligence_studio.application.commands.project_commands import (
    ArchiveProjectCommand,
    CreateProjectCommand,
)
from creator_intelligence_studio.application.commands.video_commands import (
    RegisterVideoCommand,
    VerifyVideoAvailabilityCommand,
)
from creator_intelligence_studio.application.commands.youtube_commands import (
    ConnectYouTubeCommand,
    DisconnectYouTubeConnectionCommand,
    ExportYouTubeSyncReportCommand,
    LinkYouTubeContentCommand,
    ListYouTubeChannelsCommand,
    ListYouTubeConnectionsCommand,
    ListYouTubeVideosCommand,
    RevokeYouTubeConnectionCommand,
    ResumeYouTubeSyncCommand,
    SelectYouTubeChannelCommand,
    ShowYouTubeChannelCommand,
    ShowYouTubeConnectionCommand,
    ShowYouTubeSyncRunCommand,
    ShowYouTubeVideoCommand,
    SyncYouTubeChannelCommand,
    SyncYouTubeHistoryCommand,
    UnlinkYouTubeContentCommand,
    VerifyYouTubeConnectionCommand,
    YouTubeQuotaCommand,
)
from creator_intelligence_studio.application.commands.analytics_commands import (
    CreateAnalyticsChannelCommand,
    DetectAnalyticsSchemaCommand,
    ExportNormalizedAnalyticsCommand,
    ImportAnalyticsCsvCommand,
    ImportAnalyticsExcelCommand,
    InspectAnalyticsFileCommand,
    ListAnalyticsChannelsCommand,
    ListAnalyticsImportsCommand,
    ListAnalyticsMappingsCommand,
    ListAnalyticsPlatformsCommand,
    ListAnalyticsImportRowsCommand,
    ListAnalyticsPublicationsCommand,
    PublicationMetricsCommand,
    SaveAnalyticsMappingCommand,
    ShowAnalyticsImportCommand,
    ShowAnalyticsPublicationCommand,
)
from creator_intelligence_studio.application.commands.analytics_lab_commands import (
    AnalyzeAnalyticsCohortCommand,
    ConfirmAnalyticsFindingCommand,
    CreateAnalyticsCohortCommand,
    ExportAnalyticsReportCommand,
    GenerateAnalyticsWeeklyReportCommand,
    ListAnalyticsCohortsCommand,
    ListAnalyticsFindingsCommand,
    ListAnalyticsReportsCommand,
    CompareAnalyticsPublicationCommand,
    RejectAnalyticsFindingCommand,
    ShowAnalyticsAnalysisCommand,
    ShowAnalyticsCohortCommand,
    ShowAnalyticsFindingCommand,
    ShowAnalyticsReportCommand,
)
from creator_intelligence_studio.presentation.cli.audience_cli import (
    build_audience_parser,
    handle_audience,
)
from creator_intelligence_studio.application.commands.experiment_commands import (
    AddExperimentGuardrailCommand,
    AddExperimentVariableCommand,
    ArchiveExperimentCommand,
    AssignExperimentCommand,
    ConfirmLearningCommand,
    CreateExperimentCommand,
    CreateRecommendationCommand,
    DecideRecommendationCommand,
    DeprecateLearningCommand,
    EvaluateExperimentCommand,
    ExportExperimentReportCommand,
    GenerateExperimentReportCommand,
    ListExperimentsCommand,
    ListLearningsCommand,
    ListRecommendationsCommand,
    NeedsMoreDataLearningCommand,
    RecordExecutionCommand,
    RejectLearningCommand,
    UpdateExperimentCommand,
    ShowExperimentCommand,
    ShowExperimentEvaluationCommand,
    ShowLearningCommand,
    ShowRecommendationCommand,
)
from creator_intelligence_studio.application.commands.creator_memory_commands import (
    AddCreatorTraitEvidenceCommand,
    CompareCreatorSnapshotsCommand,
    CreateCreatorExampleCommand,
    CreateCreatorLimitCommand,
    CreateCreatorRuleCommand,
    CreateCreatorSnapshotCommand,
    CreateCreatorTraitCommand,
    CreateCreatorVocabularyCommand,
    CreatorMemoryProfileCommand,
    ListCreatorExamplesCommand,
    ListCreatorLimitsCommand,
    ListCreatorRulesCommand,
    ListCreatorSnapshotsCommand,
    ListCreatorTraitsCommand,
    ListCreatorVocabularyCommand,
    RecordCreatorMemoryFeedbackCommand,
    RetrieveCreatorMemoryCommand,
    ReviewCreatorExampleCommand,
    ReviewCreatorRuleCommand,
    ShowCreatorTraitCommand,
    UpdateCreatorLimitCommand,
    UpdateCreatorMemoryProfileCommand,
    UpdateCreatorTraitCommand,
)
from creator_intelligence_studio.application.services.catalog_service import (
    CatalogService,
    VideoVerificationReport,
)
from creator_intelligence_studio.application.services.audio_preparation_service import (
    AudioCacheDeletionResult,
    AudioPreparationService,
    PreparedAudioReport,
)
from creator_intelligence_studio.application.services.transcription_service import (
    TranscriptionExportResult,
    TranscriptionReport,
    TranscriptionService,
)
from creator_intelligence_studio.application.services.subtitle_service import (
    SubtitleExportResult,
    SubtitleService,
    SubtitleTrackReport,
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
from creator_intelligence_studio.application.services.analytics_import_service import (
    AnalyticsImportService,
)
from creator_intelligence_studio.application.services.analytics_lab_service import (
    AnalyticsLabService,
)
from creator_intelligence_studio.application.services.experiment_service import (
    ExperimentService,
)
from creator_intelligence_studio.application.services.creator_memory_service import (
    CreatorMemoryService,
)
from creator_intelligence_studio.application.services.creator_language_service import (
    CreatorLanguageService,
)
from creator_intelligence_studio.application.services.creative_packaging_service import (
    CreativePackagingService,
)
from creator_intelligence_studio.application.services.youtube_integration_service import (
    YouTubeIntegrationService,
)
from creator_intelligence_studio.application.services.audience_model_service import AudienceModelService
from creator_intelligence_studio.domain.operational_evaluation.value_objects import (
    OperationalEvaluationRunStatus,
)
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
)
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticAnalysisStatus
from creator_intelligence_studio.domain.visual_analysis.entities import VisualAnalysis, VisualEvent, VisualScene, VisualTimelineWindow
from creator_intelligence_studio.domain.visual_analysis.value_objects import VisualAnalysisStatus
from creator_intelligence_studio.domain.multimodal_analysis.entities import MultimodalAnalysis, MultimodalMomentCandidate, MultimodalTimelineWindow
from creator_intelligence_studio.domain.multimodal_analysis.value_objects import MultimodalAnalysisStatus
from creator_intelligence_studio.domain.transcription.entities import Transcription, TranscriptionSegment, TranscriptionStatus
from creator_intelligence_studio.domain.transcription.value_objects import TranscriptionExportFormat, TranscriptionOptions
from creator_intelligence_studio.domain.subtitles.value_objects import SubtitleExportFormat, SubtitleGenerationOptions
from creator_intelligence_studio.infrastructure.diagnostics.models import EnvironmentDiagnostic


def _json_default(value):
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de CLI."""

    parser = argparse.ArgumentParser(
        prog="creator_intelligence_studio",
        description="Creator Intelligence Studio",
    )
    parser.add_argument(
        "--diagnostic-json",
        action="store_true",
        help="Imprime el diagnostico de entorno en JSON.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre la interfaz de escritorio.",
    )

    subparsers = parser.add_subparsers(dest="entity")

    creator_parser = subparsers.add_parser("creator", help="Gestion de creadores")
    creator_sub = creator_parser.add_subparsers(dest="action", required=True)

    creator_create = creator_sub.add_parser("create", help="Crear un creador")
    creator_create.add_argument("--name", required=True)
    creator_create.add_argument("--slug")
    creator_create.add_argument("--description")
    creator_sub.add_parser("list", help="Listar creadores")
    creator_show = creator_sub.add_parser("show", help="Mostrar un creador")
    creator_show.add_argument("creator_id_or_slug")
    creator_archive = creator_sub.add_parser("archive", help="Archivar un creador")
    creator_archive.add_argument("creator_id_or_slug")

    project_parser = subparsers.add_parser("project", help="Gestion de proyectos")
    project_sub = project_parser.add_subparsers(dest="action", required=True)
    project_create = project_sub.add_parser("create", help="Crear un proyecto")
    project_create.add_argument("--creator", required=True)
    project_create.add_argument("--name", required=True)
    project_create.add_argument("--type", required=True, dest="project_type")
    project_create.add_argument("--description")
    project_list = project_sub.add_parser("list", help="Listar proyectos")
    project_list.add_argument("--creator", required=True)
    project_show = project_sub.add_parser("show", help="Mostrar un proyecto")
    project_show.add_argument("project_id")
    project_archive = project_sub.add_parser("archive", help="Archivar un proyecto")
    project_archive.add_argument("project_id")

    video_parser = subparsers.add_parser("video", help="Gestion de videos")
    video_sub = video_parser.add_subparsers(dest="action", required=True)
    video_register = video_sub.add_parser("register", help="Registrar un video")
    video_register.add_argument("--project", required=True)
    video_register.add_argument("--file", required=True, dest="file_path")
    video_register.add_argument("--title", required=True)
    video_register.add_argument("--notes")
    video_list = video_sub.add_parser("list", help="Listar videos")
    video_list.add_argument("--project", required=True)
    video_show = video_sub.add_parser("show", help="Mostrar un video")
    video_show.add_argument("video_id")
    video_verify = video_sub.add_parser("verify", help="Verificar disponibilidad")
    video_verify.add_argument("video_id")

    youtube_parser = subparsers.add_parser("youtube", help="Integracion de solo lectura con YouTube")
    youtube_sub = youtube_parser.add_subparsers(dest="action", required=True)

    youtube_connections = youtube_sub.add_parser("connections", help="Listar conexiones")
    youtube_connections.add_argument("--creator-id", required=True)
    youtube_connections.add_argument("--json", action="store_true")

    youtube_connect = youtube_sub.add_parser("connect", help="Conectar una cuenta")
    youtube_connect.add_argument("--creator-id", required=True)
    youtube_connect.add_argument("--client-id", required=True)
    youtube_connect.add_argument("--client-secret")
    youtube_connect.add_argument("--authorization-code")
    youtube_connect.add_argument("--redirect-uri")
    youtube_connect.add_argument("--scopes-json")
    youtube_connect.add_argument("--google-account-identifier")
    youtube_connect.add_argument("--json", action="store_true")

    youtube_connection_show = youtube_sub.add_parser("connection-show", help="Mostrar una conexion")
    youtube_connection_show.add_argument("--connection-id", required=True)
    youtube_connection_show.add_argument("--json", action="store_true")

    youtube_verify = youtube_sub.add_parser("verify", help="Verificar una conexion")
    youtube_verify.add_argument("--connection-id", required=True)
    youtube_verify.add_argument("--json", action="store_true")

    youtube_disconnect = youtube_sub.add_parser("disconnect", help="Desconectar localmente")
    youtube_disconnect.add_argument("--connection-id", required=True)
    youtube_disconnect.add_argument("--json", action="store_true")

    youtube_revoke = youtube_sub.add_parser("revoke", help="Revocar credenciales")
    youtube_revoke.add_argument("--connection-id", required=True)
    youtube_revoke.add_argument("--json", action="store_true")

    youtube_channels = youtube_sub.add_parser("channels", help="Listar canales")
    youtube_channels.add_argument("--creator-id", required=True)
    youtube_channels.add_argument("--json", action="store_true")

    youtube_channel_select = youtube_sub.add_parser("channel-select", help="Seleccionar un canal")
    youtube_channel_select.add_argument("--channel-id", required=True)
    youtube_channel_select.add_argument("--json", action="store_true")

    youtube_channel_show = youtube_sub.add_parser("channel-show", help="Mostrar un canal")
    youtube_channel_show.add_argument("--channel-id", required=True)
    youtube_channel_show.add_argument("--json", action="store_true")

    youtube_sync_channel = youtube_sub.add_parser("sync-channel", help="Sincronizar canal")
    youtube_sync_channel.add_argument("--channel-id", required=True)
    youtube_sync_channel.add_argument("--sync-type", default="incremental_sync")
    youtube_sync_channel.add_argument("--cursor")
    youtube_sync_channel.add_argument("--full-resync", action="store_true")
    youtube_sync_channel.add_argument("--include-analytics", action="store_true", default=True)
    youtube_sync_channel.add_argument("--include-thumbnails", action="store_true")
    youtube_sync_channel.add_argument("--metrics-json")
    youtube_sync_channel.add_argument("--json", action="store_true")

    youtube_sync_content = youtube_sub.add_parser("sync-content", help="Sincronizar catalogo")
    youtube_sync_content.add_argument("--channel-id", required=True)
    youtube_sync_content.add_argument("--cursor")
    youtube_sync_content.add_argument("--json", action="store_true")

    youtube_sync_analytics = youtube_sub.add_parser("sync-analytics", help="Sincronizar analiticas")
    youtube_sync_analytics.add_argument("--channel-id", required=True)
    youtube_sync_analytics.add_argument("--cursor")
    youtube_sync_analytics.add_argument("--metrics-json")
    youtube_sync_analytics.add_argument("--json", action="store_true")

    youtube_sync_incremental = youtube_sub.add_parser("sync-incremental", help="Sincronizacion incremental")
    youtube_sync_incremental.add_argument("--channel-id", required=True)
    youtube_sync_incremental.add_argument("--cursor")
    youtube_sync_incremental.add_argument("--json", action="store_true")

    youtube_sync_resume = youtube_sub.add_parser("sync-resume", help="Reanudar una sincronizacion")
    youtube_sync_resume.add_argument("--run-id", required=True)
    youtube_sync_resume.add_argument("--json", action="store_true")

    youtube_sync_repair = youtube_sub.add_parser("sync-repair", help="Reparar sincronizacion")
    youtube_sync_repair.add_argument("--channel-id", required=True)
    youtube_sync_repair.add_argument("--json", action="store_true")

    youtube_sync_history = youtube_sub.add_parser("sync-history", help="Historial de sincronizaciones")
    youtube_sync_history.add_argument("--creator-id", required=True)
    youtube_sync_history.add_argument("--json", action="store_true")

    youtube_sync_show = youtube_sub.add_parser("sync-show", help="Mostrar una sincronizacion")
    youtube_sync_show.add_argument("--run-id", required=True)
    youtube_sync_show.add_argument("--json", action="store_true")

    youtube_videos = youtube_sub.add_parser("videos", help="Listar videos remotos")
    youtube_videos.add_argument("--channel-id", required=True)
    youtube_videos.add_argument("--json", action="store_true")

    youtube_video_show = youtube_sub.add_parser("video-show", help="Mostrar un video remoto")
    youtube_video_show.add_argument("--remote-video-id", required=True)
    youtube_video_show.add_argument("--json", action="store_true")

    youtube_link_content = youtube_sub.add_parser("link-content", help="Vincular contenido remoto")
    youtube_link_content.add_argument("--remote-video-id", required=True)
    youtube_link_content.add_argument("--publication-id")
    youtube_link_content.add_argument("--video-asset-id")
    youtube_link_content.add_argument("--link-method", default="manual")
    youtube_link_content.add_argument("--confidence-level", default="low")
    youtube_link_content.add_argument("--status", default="pending")
    youtube_link_content.add_argument("--json", action="store_true")

    youtube_unlink_content = youtube_sub.add_parser("unlink-content", help="Desvincular contenido remoto")
    youtube_unlink_content.add_argument("--remote-video-id", required=True)
    youtube_unlink_content.add_argument("--json", action="store_true")

    youtube_quota = youtube_sub.add_parser("quota", help="Mostrar cuota estimada")
    youtube_quota.add_argument("--connection-id", required=True)
    youtube_quota.add_argument("--json", action="store_true")

    youtube_export_report = youtube_sub.add_parser("export-report", help="Exportar un reporte de sincronizacion")
    youtube_export_report.add_argument("--run-id", required=True)
    youtube_export_report.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    youtube_export_report.add_argument("--output")
    youtube_export_report.add_argument("--json", action="store_true")

    media_parser = subparsers.add_parser("media", help="Inspeccion tecnica de medios")
    media_sub = media_parser.add_subparsers(dest="action", required=True)
    media_tools = media_sub.add_parser("tools", help="Verificar herramientas multimedia")
    media_tools.add_argument("--json", action="store_true")
    media_inspect = media_sub.add_parser("inspect", help="Inspeccionar un video")
    media_inspect.add_argument("--video-id", required=True)
    media_inspect.add_argument("--force", action="store_true")
    media_inspect.add_argument("--json", action="store_true")
    media_show = media_sub.add_parser("show", help="Mostrar una inspeccion tecnica")
    media_show.add_argument("--video-id", required=True)
    media_show.add_argument("--json", action="store_true")

    audio_parser = subparsers.add_parser("audio", help="Preparacion tecnica de audio")
    audio_sub = audio_parser.add_subparsers(dest="action", required=True)
    audio_prepare = audio_sub.add_parser("prepare", help="Preparar audio normalizado")
    audio_prepare.add_argument("--video-id", required=True)
    audio_prepare.add_argument("--force", action="store_true")
    audio_prepare.add_argument("--json", action="store_true")
    audio_show = audio_sub.add_parser("show", help="Mostrar un audio preparado")
    audio_show.add_argument("--video-id", required=True)
    audio_show.add_argument("--json", action="store_true")
    audio_verify = audio_sub.add_parser("verify", help="Verificar audio preparado")
    audio_verify.add_argument("--video-id", required=True)
    audio_verify.add_argument("--json", action="store_true")
    audio_clear = audio_sub.add_parser("clear-cache", help="Limpiar caché de audio")
    audio_clear.add_argument("--video-id", required=True)
    audio_clear.add_argument("--json", action="store_true")

    build_audience_parser(subparsers)

    transcription_parser = subparsers.add_parser("transcription", help="Gestion de transcripcion local")
    transcription_sub = transcription_parser.add_subparsers(dest="action", required=True)

    transcription_backend = transcription_sub.add_parser("backend", help="Verificar backend de transcripcion")
    transcription_backend.add_argument("--json", action="store_true")

    transcription_models = transcription_sub.add_parser("models", help="Listar modelos de transcripcion")
    transcription_models.add_argument("--json", action="store_true")

    transcription_model_status = transcription_sub.add_parser("model-status", help="Mostrar el estado de un modelo")
    transcription_model_status.add_argument("--model", required=True)
    transcription_model_status.add_argument("--json", action="store_true")

    transcription_download_model = transcription_sub.add_parser("download-model", help="Descargar un modelo")
    transcription_download_model.add_argument("--model", required=True)
    transcription_download_model.add_argument("--json", action="store_true")

    transcription_verify_model = transcription_sub.add_parser("verify-model", help="Verificar un modelo local")
    transcription_verify_model.add_argument("--model", required=True)
    transcription_verify_model.add_argument("--json", action="store_true")

    transcription_transcribe = transcription_sub.add_parser("transcribe", help="Transcribir un video")
    transcription_transcribe.add_argument("--video-id", required=True)
    transcription_transcribe.add_argument("--profile", default="balanced")
    transcription_transcribe.add_argument("--model-name")
    transcription_transcribe.add_argument("--device", default="auto")
    transcription_transcribe.add_argument("--compute-type")
    transcription_transcribe.add_argument("--language", default="auto")
    transcription_transcribe.add_argument("--beam-size", type=int, default=5)
    transcription_transcribe.add_argument("--vad-filter", action="store_true")
    transcription_transcribe.add_argument("--word-timestamps", action="store_true")
    transcription_transcribe.add_argument("--json", action="store_true")

    transcription_show = transcription_sub.add_parser("show", help="Mostrar una transcripcion")
    transcription_show.add_argument("--video-id", required=True)
    transcription_show.add_argument("--json", action="store_true")

    transcription_segments = transcription_sub.add_parser("segments", help="Listar segmentos de transcripcion")
    transcription_segments.add_argument("--video-id", required=True)
    transcription_segments.add_argument("--json", action="store_true")

    transcription_export = transcription_sub.add_parser("export", help="Exportar una transcripcion")
    transcription_export.add_argument("--video-id", required=True)
    transcription_export.add_argument("--format", required=True, choices=["txt", "srt", "json"])
    transcription_export.add_argument("--output")
    transcription_export.add_argument("--json", action="store_true")

    transcription_delete = transcription_sub.add_parser("delete", help="Eliminar una transcripcion")
    transcription_delete.add_argument("--video-id", required=True)
    transcription_delete.add_argument("--json", action="store_true")

    subtitles_parser = subparsers.add_parser("subtitles", help="Subtitulos locales")
    subtitles_sub = subtitles_parser.add_subparsers(dest="action", required=True)

    def _subtitle_options(subparser):
        subparser.add_argument("--language", default="es")
        subparser.add_argument("--max-lines", type=int, default=2)
        subparser.add_argument("--max-chars-per-line", type=int, default=42)
        subparser.add_argument("--max-chars-per-cue", type=int, default=84)
        subparser.add_argument("--min-duration", type=float, default=0.8)
        subparser.add_argument("--max-duration", type=float, default=7.0)
        subparser.add_argument("--min-gap", type=float, default=0.05)
        subparser.add_argument("--cps-warning", type=float, default=22.0)
        subparser.add_argument("--custom-name")
        subparser.add_argument("--json", action="store_true")

    subtitles_generate_video = subtitles_sub.add_parser("generate-video", help="Generar subtitulos para un video")
    subtitles_generate_video.add_argument("--video-id", required=True)
    _subtitle_options(subtitles_generate_video)

    subtitles_generate_clip = subtitles_sub.add_parser("generate-clip", help="Generar subtitulos para un candidato")
    subtitles_generate_clip.add_argument("--candidate-id", required=True)
    _subtitle_options(subtitles_generate_clip)

    subtitles_show = subtitles_sub.add_parser("show", help="Mostrar un track de subtitulos")
    subtitles_show.add_argument("--track-id", required=True)
    subtitles_show.add_argument("--json", action="store_true")

    subtitles_list_video = subtitles_sub.add_parser("list-video", help="Listar tracks por video")
    subtitles_list_video.add_argument("--video-id", required=True)
    subtitles_list_video.add_argument("--json", action="store_true")

    subtitles_list_clip = subtitles_sub.add_parser("list-clip", help="Listar tracks por candidato")
    subtitles_list_clip.add_argument("--candidate-id", required=True)
    subtitles_list_clip.add_argument("--json", action="store_true")

    subtitles_validate = subtitles_sub.add_parser("validate", help="Validar un track")
    subtitles_validate.add_argument("--track-id", required=True)
    subtitles_validate.add_argument("--json", action="store_true")

    subtitles_update_text = subtitles_sub.add_parser("update-text", help="Editar texto de un cue")
    subtitles_update_text.add_argument("--cue-id", required=True)
    subtitles_update_text.add_argument("--text", required=True)
    subtitles_update_text.add_argument("--json", action="store_true")

    subtitles_update_time = subtitles_sub.add_parser("update-time", help="Editar tiempos de un cue")
    subtitles_update_time.add_argument("--cue-id", required=True)
    subtitles_update_time.add_argument("--start", required=True, type=float)
    subtitles_update_time.add_argument("--end", required=True, type=float)
    subtitles_update_time.add_argument("--json", action="store_true")

    subtitles_split = subtitles_sub.add_parser("split", help="Dividir un cue")
    subtitles_split.add_argument("--cue-id", required=True)
    subtitles_split.add_argument("--position", required=True, type=int)
    subtitles_split.add_argument("--json", action="store_true")

    subtitles_merge = subtitles_sub.add_parser("merge", help="Fusionar cues")
    subtitles_merge.add_argument("--first-cue-id", required=True)
    subtitles_merge.add_argument("--second-cue-id", required=True)
    subtitles_merge.add_argument("--json", action="store_true")

    subtitles_insert = subtitles_sub.add_parser("insert", help="Insertar un cue")
    subtitles_insert.add_argument("--track-id", required=True)
    subtitles_insert.add_argument("--index", required=True, type=int)
    subtitles_insert.add_argument("--start", required=True, type=float)
    subtitles_insert.add_argument("--end", required=True, type=float)
    subtitles_insert.add_argument("--text", required=True)
    subtitles_insert.add_argument("--json", action="store_true")

    subtitles_delete_cue = subtitles_sub.add_parser("delete-cue", help="Eliminar un cue")
    subtitles_delete_cue.add_argument("--cue-id", required=True)
    subtitles_delete_cue.add_argument("--json", action="store_true")

    subtitles_shift = subtitles_sub.add_parser("shift", help="Desplazar un track")
    subtitles_shift.add_argument("--track-id", required=True)
    subtitles_shift.add_argument("--offset", required=True, type=float)
    subtitles_shift.add_argument("--json", action="store_true")

    subtitles_lock = subtitles_sub.add_parser("lock", help="Bloquear un track")
    subtitles_lock.add_argument("--track-id", required=True)
    subtitles_lock.add_argument("--json", action="store_true")

    subtitles_unlock = subtitles_sub.add_parser("unlock", help="Desbloquear un track")
    subtitles_unlock.add_argument("--track-id", required=True)
    subtitles_unlock.add_argument("--json", action="store_true")

    subtitles_duplicate = subtitles_sub.add_parser("duplicate", help="Duplicar un track")
    subtitles_duplicate.add_argument("--track-id", required=True)
    subtitles_duplicate.add_argument("--json", action="store_true")

    subtitles_import = subtitles_sub.add_parser("import", help="Importar subtitulos")
    subtitles_import.add_argument("--video-id", required=True)
    subtitles_import.add_argument("--file", required=True)
    subtitles_import.add_argument("--format", choices=["srt", "vtt", "ass", "json"], default=None)
    subtitles_import.add_argument("--json", action="store_true")

    subtitles_export = subtitles_sub.add_parser("export", help="Exportar subtitulos")
    subtitles_export.add_argument("--track-id", required=True)
    subtitles_export.add_argument("--format", required=True, choices=["srt", "vtt", "ass", "txt", "json"])
    subtitles_export.add_argument("--output")
    subtitles_export.add_argument("--json", action="store_true")

    subtitles_history = subtitles_sub.add_parser("history", help="Mostrar historial de un track")
    subtitles_history.add_argument("--track-id", required=True)
    subtitles_history.add_argument("--json", action="store_true")

    subtitles_archive = subtitles_sub.add_parser("archive", help="Archivar un track")
    subtitles_archive.add_argument("--track-id", required=True)
    subtitles_archive.add_argument("--json", action="store_true")

    subtitles_delete = subtitles_sub.add_parser("delete", help="Eliminar un track")
    subtitles_delete.add_argument("--track-id", required=True)
    subtitles_delete.add_argument("--json", action="store_true")

    analytics_parser = subparsers.add_parser("analytics", help="Analitica manual y aprendizaje")
    analytics_sub = analytics_parser.add_subparsers(dest="action", required=True)

    analytics_platforms = analytics_sub.add_parser("platforms", help="Listar plataformas")
    analytics_platforms.add_argument("--json", action="store_true")

    analytics_channels = analytics_sub.add_parser("channels", help="Listar canales")
    analytics_channels.add_argument("--creator-id", required=True)
    analytics_channels.add_argument("--json", action="store_true")

    analytics_channel_create = analytics_sub.add_parser("channel-create", help="Crear canal")
    analytics_channel_create.add_argument("--creator-id", required=True)
    analytics_channel_create.add_argument("--platform", required=True)
    analytics_channel_create.add_argument("--name", required=True)
    analytics_channel_create.add_argument("--external-channel-id")
    analytics_channel_create.add_argument("--channel-url")
    analytics_channel_create.add_argument("--timezone")
    analytics_channel_create.add_argument("--primary", action="store_true")

    analytics_imports = analytics_sub.add_parser("imports", help="Listar importaciones")
    analytics_imports.add_argument("--creator-id", required=True)
    analytics_imports.add_argument("--json", action="store_true")

    analytics_import_csv = analytics_sub.add_parser("import-csv", help="Importar CSV")
    analytics_import_csv.add_argument("--creator-id", required=True)
    analytics_import_csv.add_argument("--file", required=True)
    analytics_import_csv.add_argument("--channel-id")
    analytics_import_csv.add_argument("--platform")
    analytics_import_csv.add_argument("--mapping-name")
    analytics_import_csv.add_argument("--delimiter")
    analytics_import_csv.add_argument("--json", action="store_true")

    analytics_import_excel = analytics_sub.add_parser("import-excel", help="Importar Excel")
    analytics_import_excel.add_argument("--creator-id", required=True)
    analytics_import_excel.add_argument("--file", required=True)
    analytics_import_excel.add_argument("--channel-id")
    analytics_import_excel.add_argument("--platform")
    analytics_import_excel.add_argument("--sheet-name")
    analytics_import_excel.add_argument("--mapping-name")
    analytics_import_excel.add_argument("--json", action="store_true")

    analytics_inspect = analytics_sub.add_parser("inspect-file", help="Inspeccionar archivo")
    analytics_inspect.add_argument("--file", required=True)
    analytics_inspect.add_argument("--sheet-name")
    analytics_inspect.add_argument("--json", action="store_true")

    analytics_detect = analytics_sub.add_parser("detect-schema", help="Detectar schema")
    analytics_detect.add_argument("--file", required=True)
    analytics_detect.add_argument("--sheet-name")
    analytics_detect.add_argument("--json", action="store_true")

    analytics_mappings = analytics_sub.add_parser("mappings", help="Listar mappings")
    analytics_mappings.add_argument("--creator-id", required=True)
    analytics_mappings.add_argument("--json", action="store_true")

    analytics_mapping_save = analytics_sub.add_parser("mapping-save", help="Guardar mapping")
    analytics_mapping_save.add_argument("--creator-id")
    analytics_mapping_save.add_argument("--platform", required=True)
    analytics_mapping_save.add_argument("--mapping-name", required=True)
    analytics_mapping_save.add_argument("--source-field", required=True)
    analytics_mapping_save.add_argument("--target-field", required=True)
    analytics_mapping_save.add_argument("--transformation", default="identity")
    analytics_mapping_save.add_argument("--confidence", type=float, default=1.0)
    analytics_mapping_save.add_argument("--inactive", action="store_true")
    analytics_mapping_save.add_argument("--json", action="store_true")

    analytics_publications = analytics_sub.add_parser("publications", help="Listar publicaciones")
    analytics_publications.add_argument("--creator-id", required=True)
    analytics_publications.add_argument("--json", action="store_true")

    analytics_publication_show = analytics_sub.add_parser("publication-show", help="Mostrar una publicacion")
    analytics_publication_show.add_argument("--publication-id", required=True)
    analytics_publication_show.add_argument("--json", action="store_true")

    analytics_publication_metrics = analytics_sub.add_parser("publication-metrics", help="Mostrar metricas de una publicacion")
    analytics_publication_metrics.add_argument("--publication-id", required=True)
    analytics_publication_metrics.add_argument("--json", action="store_true")

    analytics_import_show = analytics_sub.add_parser("import-show", help="Mostrar una importacion")
    analytics_import_show.add_argument("--import-id", required=True)
    analytics_import_show.add_argument("--json", action="store_true")

    analytics_import_rows = analytics_sub.add_parser("import-rows", help="Listar filas de una importacion")
    analytics_import_rows.add_argument("--import-id", required=True)
    analytics_import_rows.add_argument("--status")
    analytics_import_rows.add_argument("--json", action="store_true")

    analytics_export = analytics_sub.add_parser("export-normalized", help="Exportar datos normalizados")
    analytics_export.add_argument("--creator-id", required=True)
    analytics_export.add_argument("--format", required=True, choices=["csv", "json"])
    analytics_export.add_argument("--json", action="store_true")

    analytics_cohorts = analytics_sub.add_parser("cohorts", help="Listar cohortes")
    analytics_cohorts.add_argument("--creator-id", required=True)
    analytics_cohorts.add_argument("--json", action="store_true")

    analytics_cohort_create = analytics_sub.add_parser("cohort-create", help="Crear cohorte")
    analytics_cohort_create.add_argument("--creator-id", required=True)
    analytics_cohort_create.add_argument("--name", required=True)
    analytics_cohort_create.add_argument("--description", required=True)
    analytics_cohort_create.add_argument("--platform")
    analytics_cohort_create.add_argument("--content-type")
    analytics_cohort_create.add_argument("--date-from")
    analytics_cohort_create.add_argument("--date-to")
    analytics_cohort_create.add_argument("--duration-min-seconds", type=float)
    analytics_cohort_create.add_argument("--duration-max-seconds", type=float)
    analytics_cohort_create.add_argument("--topic")
    analytics_cohort_create.add_argument("--format")
    analytics_cohort_create.add_argument("--language")
    analytics_cohort_create.add_argument("--channel-id")
    analytics_cohort_create.add_argument("--linked", action="store_true")
    analytics_cohort_create.add_argument("--json", action="store_true")

    analytics_cohort_show = analytics_sub.add_parser("cohort-show", help="Mostrar cohorte")
    analytics_cohort_show.add_argument("--cohort-id", required=True)
    analytics_cohort_show.add_argument("--json", action="store_true")

    analytics_cohort_analyze = analytics_sub.add_parser("cohort-analyze", help="Analizar cohorte")
    analytics_cohort_analyze.add_argument("--cohort-id", required=True)
    analytics_cohort_analyze.add_argument("--json", action="store_true")

    analytics_compare = analytics_sub.add_parser("compare-publication", help="Comparar publicacion con cohorte")
    analytics_compare.add_argument("--publication-id", required=True)
    analytics_compare.add_argument("--cohort-id", required=True)
    analytics_compare.add_argument("--json", action="store_true")

    analytics_analysis_show = analytics_sub.add_parser("analysis-show", help="Mostrar corrida de analisis")
    analytics_analysis_show.add_argument("--run-id", required=True)
    analytics_analysis_show.add_argument("--json", action="store_true")

    analytics_findings = analytics_sub.add_parser("findings", help="Listar findings")
    analytics_findings.add_argument("--creator-id", required=True)
    analytics_findings.add_argument("--json", action="store_true")

    analytics_finding_show = analytics_sub.add_parser("finding-show", help="Mostrar finding")
    analytics_finding_show.add_argument("--finding-id", required=True)
    analytics_finding_show.add_argument("--json", action="store_true")

    analytics_finding_confirm = analytics_sub.add_parser("finding-confirm", help="Confirmar finding")
    analytics_finding_confirm.add_argument("--finding-id", required=True)
    analytics_finding_confirm.add_argument("--json", action="store_true")

    analytics_finding_reject = analytics_sub.add_parser("finding-reject", help="Rechazar finding")
    analytics_finding_reject.add_argument("--finding-id", required=True)
    analytics_finding_reject.add_argument("--json", action="store_true")

    analytics_weekly = analytics_sub.add_parser("weekly-report", help="Generar reporte semanal")
    analytics_weekly.add_argument("--creator-id", required=True)
    analytics_weekly.add_argument("--from", dest="period_start", required=True)
    analytics_weekly.add_argument("--to", dest="period_end", required=True)
    analytics_weekly.add_argument("--json", action="store_true")

    analytics_reports = analytics_sub.add_parser("reports", help="Listar reportes")
    analytics_reports.add_argument("--creator-id", required=True)
    analytics_reports.add_argument("--json", action="store_true")

    analytics_report_show = analytics_sub.add_parser("report-show", help="Mostrar reporte")
    analytics_report_show.add_argument("--report-id", required=True)
    analytics_report_show.add_argument("--json", action="store_true")

    analytics_report_export = analytics_sub.add_parser("report-export", help="Exportar reporte")
    analytics_report_export.add_argument("--report-id", required=True)
    analytics_report_export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    analytics_report_export.add_argument("--json", action="store_true")

    experiments_parser = subparsers.add_parser("experiments", help="Experiments and Verifiable Learning")
    experiments_sub = experiments_parser.add_subparsers(dest="action", required=True)

    experiments_list = experiments_sub.add_parser("list", help="Listar experimentos")
    experiments_list.add_argument("--creator-id", required=True)
    experiments_list.add_argument("--json", action="store_true")

    experiments_create = experiments_sub.add_parser("create", help="Crear experimento")
    experiments_create.add_argument("--creator-id", required=True)
    experiments_create.add_argument("--name", required=True)
    experiments_create.add_argument("--description", required=True)
    experiments_create.add_argument("--experiment-type", required=True)
    experiments_create.add_argument("--hypothesis", required=True)
    experiments_create.add_argument("--rationale", required=True)
    experiments_create.add_argument("--primary-metric-key", required=True)
    experiments_create.add_argument("--expected-direction", required=True)
    experiments_create.add_argument("--minimum-sample-size", required=True, type=int)
    experiments_create.add_argument("--platform")
    experiments_create.add_argument("--content-type")
    experiments_create.add_argument("--start-date")
    experiments_create.add_argument("--end-date")
    experiments_create.add_argument("--json", action="store_true")

    experiments_show = experiments_sub.add_parser("show", help="Mostrar experimento")
    experiments_show.add_argument("--experiment-id", required=True)
    experiments_show.add_argument("--json", action="store_true")

    experiments_update = experiments_sub.add_parser("update", help="Actualizar experimento")
    experiments_update.add_argument("--experiment-id", required=True)
    experiments_update.add_argument("--name")
    experiments_update.add_argument("--description")
    experiments_update.add_argument("--experiment-type")
    experiments_update.add_argument("--status")
    experiments_update.add_argument("--hypothesis")
    experiments_update.add_argument("--rationale")
    experiments_update.add_argument("--primary-metric-key")
    experiments_update.add_argument("--expected-direction")
    experiments_update.add_argument("--minimum-sample-size", type=int)
    experiments_update.add_argument("--platform")
    experiments_update.add_argument("--content-type")
    experiments_update.add_argument("--start-date")
    experiments_update.add_argument("--end-date")
    experiments_update.add_argument("--json", action="store_true")

    experiments_archive = experiments_sub.add_parser("archive", help="Archivar experimento")
    experiments_archive.add_argument("--experiment-id", required=True)
    experiments_archive.add_argument("--json", action="store_true")

    experiments_variable_add = experiments_sub.add_parser("variable-add", help="Agregar variable")
    experiments_variable_add.add_argument("--experiment-id", required=True)
    experiments_variable_add.add_argument("--variable-key", required=True)
    experiments_variable_add.add_argument("--variable-type", required=True)
    experiments_variable_add.add_argument("--description", required=True)
    experiments_variable_add.add_argument("--control-value-json", required=True)
    experiments_variable_add.add_argument("--treatment-value-json", required=True)
    experiments_variable_add.add_argument("--allowed-values-json", required=True)
    experiments_variable_add.add_argument("--json", action="store_true")

    experiments_guardrail_add = experiments_sub.add_parser("guardrail-add", help="Agregar guardrail")
    experiments_guardrail_add.add_argument("--experiment-id", required=True)
    experiments_guardrail_add.add_argument("--metric-key", required=True)
    experiments_guardrail_add.add_argument("--comparison-operator", required=True)
    experiments_guardrail_add.add_argument("--threshold-value", type=float)
    experiments_guardrail_add.add_argument("--allowed-change", type=float)
    experiments_guardrail_add.add_argument("--description", required=True)
    experiments_guardrail_add.add_argument("--json", action="store_true")

    experiments_assign = experiments_sub.add_parser("assign", help="Asignar publicacion")
    experiments_assign.add_argument("--experiment-id", required=True)
    experiments_assign.add_argument("--publication-id", required=True)
    experiments_assign.add_argument("--variant", required=True)
    experiments_assign.add_argument("--actual-variant")
    experiments_assign.add_argument("--notes", default="")
    experiments_assign.add_argument("--json", action="store_true")

    experiments_execution = experiments_sub.add_parser("execution-record", help="Registrar ejecucion real")
    experiments_execution.add_argument("--creator-id", required=True)
    experiments_execution.add_argument("--recommendation-id")
    experiments_execution.add_argument("--experiment-assignment-id")
    experiments_execution.add_argument("--publication-id")
    experiments_execution.add_argument("--execution-status", required=True)
    experiments_execution.add_argument("--executed-value-json", required=True)
    experiments_execution.add_argument("--deviation-from-recommendation-json", required=True)
    experiments_execution.add_argument("--json", action="store_true")

    experiments_evaluate = experiments_sub.add_parser("evaluate", help="Evaluar experimento")
    experiments_evaluate.add_argument("--experiment-id", required=True)
    experiments_evaluate.add_argument("--json", action="store_true")

    experiments_evaluation_show = experiments_sub.add_parser("evaluation-show", help="Mostrar evaluacion")
    experiments_evaluation_show.add_argument("--evaluation-id", required=True)
    experiments_evaluation_show.add_argument("--json", action="store_true")

    experiments_report = experiments_sub.add_parser("report", help="Generar reporte")
    experiments_report.add_argument("--experiment-id", required=True)
    experiments_report.add_argument("--evaluation-id")
    experiments_report.add_argument("--json", action="store_true")

    experiments_report_export = experiments_sub.add_parser("report-export", help="Exportar reporte")
    experiments_report_export.add_argument("--report-id", required=True)
    experiments_report_export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    experiments_report_export.add_argument("--json", action="store_true")

    recommendations_parser = subparsers.add_parser("recommendations", help="Recomendaciones rastreadas")
    recommendations_sub = recommendations_parser.add_subparsers(dest="action", required=True)

    recommendations_list = recommendations_sub.add_parser("list", help="Listar recomendaciones")
    recommendations_list.add_argument("--creator-id", required=True)
    recommendations_list.add_argument("--json", action="store_true")

    recommendations_create = recommendations_sub.add_parser("create", help="Crear recomendacion")
    recommendations_create.add_argument("--creator-id", required=True)
    recommendations_create.add_argument("--source-type", required=True)
    recommendations_create.add_argument("--source-id")
    recommendations_create.add_argument("--recommendation-type", required=True)
    recommendations_create.add_argument("--title", required=True)
    recommendations_create.add_argument("--recommendation-text", required=True)
    recommendations_create.add_argument("--evidence-json", required=True)
    recommendations_create.add_argument("--confidence-level", required=True)
    recommendations_create.add_argument("--platform")
    recommendations_create.add_argument("--content-type")
    recommendations_create.add_argument("--json", action="store_true")

    recommendations_show = recommendations_sub.add_parser("show", help="Mostrar recomendacion")
    recommendations_show.add_argument("--recommendation-id", required=True)
    recommendations_show.add_argument("--json", action="store_true")

    recommendations_decide = recommendations_sub.add_parser("decide", help="Decidir recomendacion")
    recommendations_decide.add_argument("--recommendation-id", required=True)
    recommendations_decide.add_argument("--decision", required=True)
    recommendations_decide.add_argument("--reason", required=True)
    recommendations_decide.add_argument("--modified-value-json")
    recommendations_decide.add_argument("--json", action="store_true")

    learnings_parser = subparsers.add_parser("learnings", help="Memoria estructurada de aprendizaje")
    learnings_sub = learnings_parser.add_subparsers(dest="action", required=True)

    learnings_list = learnings_sub.add_parser("list", help="Listar aprendizajes")
    learnings_list.add_argument("--creator-id", required=True)
    learnings_list.add_argument("--json", action="store_true")

    learnings_show = learnings_sub.add_parser("show", help="Mostrar aprendizaje")
    learnings_show.add_argument("--learning-id", required=True)
    learnings_show.add_argument("--json", action="store_true")

    learnings_confirm = learnings_sub.add_parser("confirm", help="Confirmar aprendizaje")
    learnings_confirm.add_argument("--learning-id", required=True)
    learnings_confirm.add_argument("--json", action="store_true")

    learnings_reject = learnings_sub.add_parser("reject", help="Rechazar aprendizaje")
    learnings_reject.add_argument("--learning-id", required=True)
    learnings_reject.add_argument("--json", action="store_true")

    learnings_more_data = learnings_sub.add_parser("needs-more-data", help="Marcar aprendizaje con mas datos")
    learnings_more_data.add_argument("--learning-id", required=True)
    learnings_more_data.add_argument("--json", action="store_true")

    learnings_deprecate = learnings_sub.add_parser("deprecate", help="Depreciar aprendizaje")
    learnings_deprecate.add_argument("--learning-id", required=True)
    learnings_deprecate.add_argument("--json", action="store_true")

    creator_memory_parser = subparsers.add_parser("creator-memory", help="Creator Memory / Creator Profile Foundation")
    creator_memory_sub = creator_memory_parser.add_subparsers(dest="action", required=True)

    creator_memory_profile = creator_memory_sub.add_parser("profile", help="Mostrar perfil del creador")
    creator_memory_profile.add_argument("--creator-id", required=True)
    creator_memory_profile.add_argument("--json", action="store_true")

    creator_memory_profile_update = creator_memory_sub.add_parser("profile-update", help="Actualizar perfil del creador")
    creator_memory_profile_update.add_argument("--creator-id", required=True)
    creator_memory_profile_update.add_argument("--display-name")
    creator_memory_profile_update.add_argument("--summary")
    creator_memory_profile_update.add_argument("--primary-language")
    creator_memory_profile_update.add_argument("--secondary-languages-json")
    creator_memory_profile_update.add_argument("--default-tone")
    creator_memory_profile_update.add_argument("--default-formality")
    creator_memory_profile_update.add_argument("--objectives-json")
    creator_memory_profile_update.add_argument("--status")
    creator_memory_profile_update.add_argument("--json", action="store_true")

    creator_memory_traits = creator_memory_sub.add_parser("traits", help="Listar traits")
    creator_memory_traits.add_argument("--creator-id", required=True)
    creator_memory_traits.add_argument("--platform")
    creator_memory_traits.add_argument("--content-type")
    creator_memory_traits.add_argument("--topic")
    creator_memory_traits.add_argument("--trait-type")
    creator_memory_traits.add_argument("--status")
    creator_memory_traits.add_argument("--confidence-level")
    creator_memory_traits.add_argument("--json", action="store_true")

    creator_memory_trait_create = creator_memory_sub.add_parser("trait-create", help="Crear trait")
    creator_memory_trait_create.add_argument("--creator-id", required=True)
    creator_memory_trait_create.add_argument("--trait-type", required=True)
    creator_memory_trait_create.add_argument("--trait-key", required=True)
    creator_memory_trait_create.add_argument("--display-name", required=True)
    creator_memory_trait_create.add_argument("--description")
    creator_memory_trait_create.add_argument("--value-json", default="{}")
    creator_memory_trait_create.add_argument("--scope", default="creator_general")
    creator_memory_trait_create.add_argument("--platform")
    creator_memory_trait_create.add_argument("--content-type")
    creator_memory_trait_create.add_argument("--topic")
    creator_memory_trait_create.add_argument("--confidence-level", default="low")
    creator_memory_trait_create.add_argument("--confidence-score", type=float)
    creator_memory_trait_create.add_argument("--status", default="observed")
    creator_memory_trait_create.add_argument("--json", action="store_true")

    creator_memory_trait_show = creator_memory_sub.add_parser("trait-show", help="Mostrar trait")
    creator_memory_trait_show.add_argument("--trait-id", required=True)
    creator_memory_trait_show.add_argument("--json", action="store_true")

    creator_memory_trait_update = creator_memory_sub.add_parser("trait-update", help="Actualizar trait")
    creator_memory_trait_update.add_argument("--trait-id", required=True)
    creator_memory_trait_update.add_argument("--trait-type")
    creator_memory_trait_update.add_argument("--trait-key")
    creator_memory_trait_update.add_argument("--display-name")
    creator_memory_trait_update.add_argument("--description")
    creator_memory_trait_update.add_argument("--value-json")
    creator_memory_trait_update.add_argument("--scope")
    creator_memory_trait_update.add_argument("--platform")
    creator_memory_trait_update.add_argument("--content-type")
    creator_memory_trait_update.add_argument("--topic")
    creator_memory_trait_update.add_argument("--confidence-level")
    creator_memory_trait_update.add_argument("--confidence-score", type=float)
    creator_memory_trait_update.add_argument("--status")
    creator_memory_trait_update.add_argument("--json", action="store_true")

    creator_memory_trait_evidence = creator_memory_sub.add_parser("trait-evidence-add", help="Agregar evidencia a un trait")
    creator_memory_trait_evidence.add_argument("--trait-id", required=True)
    creator_memory_trait_evidence.add_argument("--source-type", required=True)
    creator_memory_trait_evidence.add_argument("--source-id")
    creator_memory_trait_evidence.add_argument("--publication-id")
    creator_memory_trait_evidence.add_argument("--video-asset-id")
    creator_memory_trait_evidence.add_argument("--transcript-segment-id")
    creator_memory_trait_evidence.add_argument("--start-seconds", type=float)
    creator_memory_trait_evidence.add_argument("--end-seconds", type=float)
    creator_memory_trait_evidence.add_argument("--quoted-text")
    creator_memory_trait_evidence.add_argument("--evidence-type", default="manual_observation")
    creator_memory_trait_evidence.add_argument("--supports-trait", action="store_true")
    creator_memory_trait_evidence.add_argument("--weight", type=float, default=1.0)
    creator_memory_trait_evidence.add_argument("--notes")
    creator_memory_trait_evidence.add_argument("--json", action="store_true")

    creator_memory_examples = creator_memory_sub.add_parser("examples", help="Listar ejemplos")
    creator_memory_examples.add_argument("--creator-id", required=True)
    creator_memory_examples.add_argument("--platform")
    creator_memory_examples.add_argument("--content-type")
    creator_memory_examples.add_argument("--topic")
    creator_memory_examples.add_argument("--example-type")
    creator_memory_examples.add_argument("--approval-status")
    creator_memory_examples.add_argument("--json", action="store_true")

    creator_memory_example_create = creator_memory_sub.add_parser("example-create", help="Crear ejemplo")
    creator_memory_example_create.add_argument("--creator-id", required=True)
    creator_memory_example_create.add_argument("--example-type", required=True)
    creator_memory_example_create.add_argument("--category", required=True)
    creator_memory_example_create.add_argument("--title", required=True)
    creator_memory_example_create.add_argument("--source-type", required=True)
    creator_memory_example_create.add_argument("--platform")
    creator_memory_example_create.add_argument("--content-type")
    creator_memory_example_create.add_argument("--topic")
    creator_memory_example_create.add_argument("--text-content")
    creator_memory_example_create.add_argument("--source-id")
    creator_memory_example_create.add_argument("--publication-id")
    creator_memory_example_create.add_argument("--video-asset-id")
    creator_memory_example_create.add_argument("--start-seconds", type=float)
    creator_memory_example_create.add_argument("--end-seconds", type=float)
    creator_memory_example_create.add_argument("--representativeness", type=float)
    creator_memory_example_create.add_argument("--approval-status", default="pending")
    creator_memory_example_create.add_argument("--approval-reason")
    creator_memory_example_create.add_argument("--json", action="store_true")

    creator_memory_example_review = creator_memory_sub.add_parser("example-review", help="Revisar ejemplo")
    creator_memory_example_review.add_argument("--example-id", required=True)
    creator_memory_example_review.add_argument("--approval-status", required=True)
    creator_memory_example_review.add_argument("--reason")
    creator_memory_example_review.add_argument("--json", action="store_true")

    creator_memory_vocabulary = creator_memory_sub.add_parser("vocabulary", help="Listar vocabulario")
    creator_memory_vocabulary.add_argument("--creator-id", required=True)
    creator_memory_vocabulary.add_argument("--platform")
    creator_memory_vocabulary.add_argument("--content-type")
    creator_memory_vocabulary.add_argument("--vocabulary-type")
    creator_memory_vocabulary.add_argument("--json", action="store_true")

    creator_memory_vocabulary_add = creator_memory_sub.add_parser("vocabulary-add", help="Agregar vocabulario")
    creator_memory_vocabulary_add.add_argument("--creator-id", required=True)
    creator_memory_vocabulary_add.add_argument("--term", required=True)
    creator_memory_vocabulary_add.add_argument("--vocabulary-type", required=True)
    creator_memory_vocabulary_add.add_argument("--meaning")
    creator_memory_vocabulary_add.add_argument("--usage-notes")
    creator_memory_vocabulary_add.add_argument("--platform")
    creator_memory_vocabulary_add.add_argument("--content-type")
    creator_memory_vocabulary_add.add_argument("--confidence-level", default="low")
    creator_memory_vocabulary_add.add_argument("--frequency-count", type=int, default=1)
    creator_memory_vocabulary_add.add_argument("--status", default="active")
    creator_memory_vocabulary_add.add_argument("--json", action="store_true")

    creator_memory_rules = creator_memory_sub.add_parser("rules", help="Listar reglas")
    creator_memory_rules.add_argument("--creator-id", required=True)
    creator_memory_rules.add_argument("--platform")
    creator_memory_rules.add_argument("--content-type")
    creator_memory_rules.add_argument("--topic")
    creator_memory_rules.add_argument("--status")
    creator_memory_rules.add_argument("--json", action="store_true")

    creator_memory_rule_create = creator_memory_sub.add_parser("rule-create", help="Crear regla")
    creator_memory_rule_create.add_argument("--creator-id", required=True)
    creator_memory_rule_create.add_argument("--rule-type", required=True)
    creator_memory_rule_create.add_argument("--statement", required=True)
    creator_memory_rule_create.add_argument("--scope", default="creator_general")
    creator_memory_rule_create.add_argument("--rationale")
    creator_memory_rule_create.add_argument("--platform")
    creator_memory_rule_create.add_argument("--content-type")
    creator_memory_rule_create.add_argument("--topic")
    creator_memory_rule_create.add_argument("--confidence-level", default="low")
    creator_memory_rule_create.add_argument("--status", default="observed")
    creator_memory_rule_create.add_argument("--supporting-example-count", type=int, default=0)
    creator_memory_rule_create.add_argument("--contradicting-example-count", type=int, default=0)
    creator_memory_rule_create.add_argument("--json", action="store_true")

    creator_memory_rule_review = creator_memory_sub.add_parser("rule-review", help="Revisar regla")
    creator_memory_rule_review.add_argument("--rule-id", required=True)
    creator_memory_rule_review.add_argument("--decision", required=True)
    creator_memory_rule_review.add_argument("--reason", required=True)
    creator_memory_rule_review.add_argument("--previous-statement")
    creator_memory_rule_review.add_argument("--new-statement")
    creator_memory_rule_review.add_argument("--json", action="store_true")

    creator_memory_limits = creator_memory_sub.add_parser("limits", help="Listar limites")
    creator_memory_limits.add_argument("--creator-id", required=True)
    creator_memory_limits.add_argument("--json", action="store_true")

    creator_memory_limit_create = creator_memory_sub.add_parser("limit-create", help="Crear limite")
    creator_memory_limit_create.add_argument("--creator-id", required=True)
    creator_memory_limit_create.add_argument("--limit-type", required=True)
    creator_memory_limit_create.add_argument("--category", required=True)
    creator_memory_limit_create.add_argument("--statement", required=True)
    creator_memory_limit_create.add_argument("--severity", default="caution")
    creator_memory_limit_create.add_argument("--scope", default="creator_general")
    creator_memory_limit_create.add_argument("--platform")
    creator_memory_limit_create.add_argument("--status", default="active")
    creator_memory_limit_create.add_argument("--json", action="store_true")

    creator_memory_limit_update = creator_memory_sub.add_parser("limit-update", help="Actualizar limite")
    creator_memory_limit_update.add_argument("--limit-id", required=True)
    creator_memory_limit_update.add_argument("--creator-id", required=True)
    creator_memory_limit_update.add_argument("--limit-type")
    creator_memory_limit_update.add_argument("--category")
    creator_memory_limit_update.add_argument("--statement")
    creator_memory_limit_update.add_argument("--severity")
    creator_memory_limit_update.add_argument("--scope")
    creator_memory_limit_update.add_argument("--platform")
    creator_memory_limit_update.add_argument("--status")
    creator_memory_limit_update.add_argument("--json", action="store_true")

    creator_memory_snapshots = creator_memory_sub.add_parser("snapshots", help="Listar snapshots")
    creator_memory_snapshots.add_argument("--creator-id", required=True)
    creator_memory_snapshots.add_argument("--json", action="store_true")

    creator_memory_snapshot_create = creator_memory_sub.add_parser("snapshot-create", help="Crear snapshot")
    creator_memory_snapshot_create.add_argument("--creator-id", required=True)
    creator_memory_snapshot_create.add_argument("--json", action="store_true")

    creator_memory_snapshot_compare = creator_memory_sub.add_parser("snapshot-compare", help="Comparar snapshots")
    creator_memory_snapshot_compare.add_argument("--creator-id", required=True)
    creator_memory_snapshot_compare.add_argument("--base-snapshot-id", required=True)
    creator_memory_snapshot_compare.add_argument("--compare-snapshot-id", required=True)
    creator_memory_snapshot_compare.add_argument("--json", action="store_true")

    creator_memory_retrieve = creator_memory_sub.add_parser("retrieve", help="Recuperar contexto")
    creator_memory_retrieve.add_argument("--creator-id", required=True)
    creator_memory_retrieve.add_argument("--query")
    creator_memory_retrieve.add_argument("--platform")
    creator_memory_retrieve.add_argument("--content-type")
    creator_memory_retrieve.add_argument("--topic")
    creator_memory_retrieve.add_argument("--trait-type")
    creator_memory_retrieve.add_argument("--example-type")
    creator_memory_retrieve.add_argument("--approval-status")
    creator_memory_retrieve.add_argument("--confidence-level")
    creator_memory_retrieve.add_argument("--status")
    creator_memory_retrieve.add_argument("--json", action="store_true")

    creator_memory_feedback = creator_memory_sub.add_parser("feedback", help="Registrar feedback")
    creator_memory_feedback.add_argument("--creator-id", required=True)
    creator_memory_feedback.add_argument("--target-type", required=True)
    creator_memory_feedback.add_argument("--target-id", required=True)
    creator_memory_feedback.add_argument("--feedback-type", required=True)
    creator_memory_feedback.add_argument("--reason", required=True)
    creator_memory_feedback.add_argument("--corrected-value-json")
    creator_memory_feedback.add_argument("--json", action="store_true")

    packaging_parser = subparsers.add_parser("packaging", help="Thumbnail Lab and Titles Foundation")
    packaging_sub = packaging_parser.add_subparsers(dest="action", required=True)

    packaging_assets = packaging_sub.add_parser("assets", help="Listar assets de packaging")
    packaging_assets.add_argument("--creator-id", required=True)
    packaging_assets.add_argument("--json", action="store_true")

    packaging_asset_show = packaging_sub.add_parser("asset-show", help="Mostrar asset de packaging")
    packaging_asset_show.add_argument("--asset-id", required=True)
    packaging_asset_show.add_argument("--json", action="store_true")

    packaging_brand_profile = packaging_sub.add_parser("brand-profile", help="Mostrar perfil de marca")
    packaging_brand_profile.add_argument("--creator-id", required=True)
    packaging_brand_profile.add_argument("--json", action="store_true")

    packaging_brand_build = packaging_sub.add_parser("brand-profile-build", help="Construir perfil de marca")
    packaging_brand_build.add_argument("--creator-id", required=True)
    packaging_brand_build.add_argument("--json", action="store_true")

    packaging_brand_history = packaging_sub.add_parser("brand-profile-history", help="Historial de perfil de marca")
    packaging_brand_history.add_argument("--creator-id", required=True)
    packaging_brand_history.add_argument("--json", action="store_true")

    packaging_references = packaging_sub.add_parser("references", help="Listar referencias")
    packaging_references.add_argument("--creator-id", required=True)
    packaging_references.add_argument("--json", action="store_true")

    packaging_reference_add = packaging_sub.add_parser("reference-add", help="Agregar referencia")
    packaging_reference_add.add_argument("--creator-id", required=True)
    packaging_reference_add.add_argument("--reference-type", required=True)
    packaging_reference_add.add_argument("--image-path")
    packaging_reference_add.add_argument("--text-content")
    packaging_reference_add.add_argument("--platform")
    packaging_reference_add.add_argument("--content-type")
    packaging_reference_add.add_argument("--topic")
    packaging_reference_add.add_argument("--source-type", required=True)
    packaging_reference_add.add_argument("--source-creator-name")
    packaging_reference_add.add_argument("--source-url")
    packaging_reference_add.add_argument("--usage-permission", required=True)
    packaging_reference_add.add_argument("--represents-creator", action="store_true")
    packaging_reference_add.add_argument("--approval-status", default="pending")
    packaging_reference_add.add_argument("--reference-purpose", required=True)
    packaging_reference_add.add_argument("--notes")
    packaging_reference_add.add_argument("--json", action="store_true")

    packaging_reference_show = packaging_sub.add_parser("reference-show", help="Mostrar referencia")
    packaging_reference_show.add_argument("--reference-id", required=True)
    packaging_reference_show.add_argument("--json", action="store_true")

    packaging_reference_review = packaging_sub.add_parser("reference-review", help="Revisar referencia")
    packaging_reference_review.add_argument("--reference-id", required=True)
    packaging_reference_review.add_argument("--approval-status", required=True)
    packaging_reference_review.add_argument("--notes")
    packaging_reference_review.add_argument("--json", action="store_true")

    packaging_titles = packaging_sub.add_parser("titles", help="Listar titulos")
    packaging_titles.add_argument("--creator-id", required=True)
    packaging_titles.add_argument("--json", action="store_true")

    packaging_title_create = packaging_sub.add_parser("title-create", help="Crear titulo")
    packaging_title_create.add_argument("--creator-id", required=True)
    packaging_title_create.add_argument("--title-text", required=True)
    packaging_title_create.add_argument("--platform", required=True)
    packaging_title_create.add_argument("--content-type", required=True)
    packaging_title_create.add_argument("--source-type", default="manual")
    packaging_title_create.add_argument("--language", default="es")
    packaging_title_create.add_argument("--topic")
    packaging_title_create.add_argument("--publication-id")
    packaging_title_create.add_argument("--video-asset-id")
    packaging_title_create.add_argument("--packaging-asset-id")
    packaging_title_create.add_argument("--is-published", action="store_true")
    packaging_title_create.add_argument("--is-selected", action="store_true")
    packaging_title_create.add_argument("--creator-approval-status", default="pending")
    packaging_title_create.add_argument("--creator-feedback")
    packaging_title_create.add_argument("--json", action="store_true")

    packaging_title_show = packaging_sub.add_parser("title-show", help="Mostrar titulo")
    packaging_title_show.add_argument("--title-id", required=True)
    packaging_title_show.add_argument("--json", action="store_true")

    packaging_title_analyze = packaging_sub.add_parser("title-analyze", help="Analizar titulo")
    packaging_title_analyze.add_argument("--title-id", required=True)
    packaging_title_analyze.add_argument("--json", action="store_true")

    packaging_title_compare = packaging_sub.add_parser("title-compare", help="Comparar titulos")
    packaging_title_compare.add_argument("--base-title-id", required=True)
    packaging_title_compare.add_argument("--compare-title-id", required=True)
    packaging_title_compare.add_argument("--json", action="store_true")

    packaging_thumbnails = packaging_sub.add_parser("thumbnails", help="Listar miniaturas")
    packaging_thumbnails.add_argument("--creator-id", required=True)
    packaging_thumbnails.add_argument("--json", action="store_true")

    packaging_thumbnail_create = packaging_sub.add_parser("thumbnail-create", help="Crear miniatura")
    packaging_thumbnail_create.add_argument("--creator-id", required=True)
    packaging_thumbnail_create.add_argument("--image-path")
    packaging_thumbnail_create.add_argument("--source-type", default="manual")
    packaging_thumbnail_create.add_argument("--platform", required=True)
    packaging_thumbnail_create.add_argument("--content-type", required=True)
    packaging_thumbnail_create.add_argument("--topic")
    packaging_thumbnail_create.add_argument("--publication-id")
    packaging_thumbnail_create.add_argument("--video-asset-id")
    packaging_thumbnail_create.add_argument("--packaging-asset-id")
    packaging_thumbnail_create.add_argument("--concept-id")
    packaging_thumbnail_create.add_argument("--is-published", action="store_true")
    packaging_thumbnail_create.add_argument("--is-selected", action="store_true")
    packaging_thumbnail_create.add_argument("--creator-approval-status", default="pending")
    packaging_thumbnail_create.add_argument("--creator-feedback")
    packaging_thumbnail_create.add_argument("--json", action="store_true")

    packaging_thumbnail_show = packaging_sub.add_parser("thumbnail-show", help="Mostrar miniatura")
    packaging_thumbnail_show.add_argument("--thumbnail-id", required=True)
    packaging_thumbnail_show.add_argument("--json", action="store_true")

    packaging_thumbnail_analyze = packaging_sub.add_parser("thumbnail-analyze", help="Analizar miniatura")
    packaging_thumbnail_analyze.add_argument("--thumbnail-id", required=True)
    packaging_thumbnail_analyze.add_argument("--json", action="store_true")

    packaging_pair_evaluate = packaging_sub.add_parser("pair-evaluate", help="Evaluar titulo y miniatura")
    packaging_pair_evaluate.add_argument("--title-id", required=True)
    packaging_pair_evaluate.add_argument("--thumbnail-id", required=True)
    packaging_pair_evaluate.add_argument("--publication-id")
    packaging_pair_evaluate.add_argument("--json", action="store_true")

    packaging_pair_show = packaging_sub.add_parser("pair-show", help="Mostrar evaluacion de par")
    packaging_pair_show.add_argument("--evaluation-id", required=True)
    packaging_pair_show.add_argument("--json", action="store_true")

    packaging_frames = packaging_sub.add_parser("frames", help="Listar frames candidatos")
    packaging_frames.add_argument("--creator-id", required=True)
    packaging_frames.add_argument("--video-id")
    packaging_frames.add_argument("--json", action="store_true")

    packaging_frame_extract = packaging_sub.add_parser("frame-extract", help="Extraer frames candidatos")
    packaging_frame_extract.add_argument("--creator-id", required=True)
    packaging_frame_extract.add_argument("--video-id", required=True)
    packaging_frame_extract.add_argument("--timestamps-json")
    packaging_frame_extract.add_argument("--json", action="store_true")

    packaging_frame_review = packaging_sub.add_parser("frame-review", help="Revisar frame candidato")
    packaging_frame_review.add_argument("--creator-id", required=True)
    packaging_frame_review.add_argument("--frame-id", required=True)
    packaging_frame_review.add_argument("--decision", required=True)
    packaging_frame_review.add_argument("--json", action="store_true")

    packaging_concepts = packaging_sub.add_parser("concepts", help="Listar conceptos")
    packaging_concepts.add_argument("--creator-id", required=True)
    packaging_concepts.add_argument("--json", action="store_true")

    packaging_concept_create = packaging_sub.add_parser("concept-create", help="Crear concepto")
    packaging_concept_create.add_argument("--creator-id", required=True)
    packaging_concept_create.add_argument("--publication-id")
    packaging_concept_create.add_argument("--video-asset-id")
    packaging_concept_create.add_argument("--concept-type", default="curiosity_driven")
    packaging_concept_create.add_argument("--platform", required=True)
    packaging_concept_create.add_argument("--content-type", required=True)
    packaging_concept_create.add_argument("--topic")
    packaging_concept_create.add_argument("--title")
    packaging_concept_create.add_argument("--objective")
    packaging_concept_create.add_argument("--audience")
    packaging_concept_create.add_argument("--json", action="store_true")

    packaging_concept_build = packaging_sub.add_parser("concept-build", help="Construir concepto")
    packaging_concept_build.add_argument("--creator-id", required=True)
    packaging_concept_build.add_argument("--platform", required=True)
    packaging_concept_build.add_argument("--content-type", required=True)
    packaging_concept_build.add_argument("--topic")
    packaging_concept_build.add_argument("--title")
    packaging_concept_build.add_argument("--objective")
    packaging_concept_build.add_argument("--audience")
    packaging_concept_build.add_argument("--concept-type", default="curiosity_driven")
    packaging_concept_build.add_argument("--publication-id")
    packaging_concept_build.add_argument("--video-asset-id")
    packaging_concept_build.add_argument("--references-json")
    packaging_concept_build.add_argument("--constraints-json")
    packaging_concept_build.add_argument("--json", action="store_true")

    packaging_concept_show = packaging_sub.add_parser("concept-show", help="Mostrar concepto")
    packaging_concept_show.add_argument("--concept-id", required=True)
    packaging_concept_show.add_argument("--json", action="store_true")

    packaging_prompt_build = packaging_sub.add_parser("prompt-build", help="Construir prompt")
    packaging_prompt_build.add_argument("--concept-id", required=True)
    packaging_prompt_build.add_argument("--target-tool", required=True)
    packaging_prompt_build.add_argument("--title")
    packaging_prompt_build.add_argument("--json", action="store_true")

    packaging_prompt_show = packaging_sub.add_parser("prompt-show", help="Mostrar prompt")
    packaging_prompt_show.add_argument("--prompt-id", required=True)
    packaging_prompt_show.add_argument("--json", action="store_true")

    packaging_prompt_refs = packaging_sub.add_parser("prompt-references", help="Listar referencias del prompt")
    packaging_prompt_refs.add_argument("--prompt-id", required=True)
    packaging_prompt_refs.add_argument("--json", action="store_true")

    packaging_prompt_export = packaging_sub.add_parser("prompt-export", help="Exportar prompt")
    packaging_prompt_export.add_argument("--prompt-id", required=True)
    packaging_prompt_export.add_argument("--json", action="store_true")

    packaging_review = packaging_sub.add_parser("review-thumbnail", help="Revisar miniatura")
    packaging_review.add_argument("--thumbnail-id", required=True)
    packaging_review.add_argument("--title-id")
    packaging_review.add_argument("--publication-id")
    packaging_review.add_argument("--concept-id")
    packaging_review.add_argument("--prompt-id")
    packaging_review.add_argument("--json", action="store_true")

    packaging_review_show = packaging_sub.add_parser("review-show", help="Mostrar revision")
    packaging_review_show.add_argument("--review-id", required=True)
    packaging_review_show.add_argument("--json", action="store_true")

    packaging_revision = packaging_sub.add_parser("review-revision-instructions", help="Mostrar instrucciones de revision")
    packaging_revision.add_argument("--review-id", required=True)
    packaging_revision.add_argument("--json", action="store_true")

    packaging_decisions = packaging_sub.add_parser("decisions", help="Listar decisiones")
    packaging_decisions.add_argument("--creator-id", required=True)
    packaging_decisions.add_argument("--json", action="store_true")

    packaging_export = packaging_sub.add_parser("export", help="Exportar packaging")
    packaging_export.add_argument("--creator-id", required=True)
    packaging_export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    packaging_export.add_argument("--summary", action="store_true")
    packaging_export.add_argument("--json", action="store_true")

    creator_language_parser = subparsers.add_parser("creator-language", help="Creator Language Analysis")
    creator_language_sub = creator_language_parser.add_subparsers(dest="action", required=True)

    creator_language_corpora = creator_language_sub.add_parser("corpora", help="Listar corpus")
    creator_language_corpora.add_argument("--creator-id", required=True)
    creator_language_corpora.add_argument("--json", action="store_true")

    creator_language_corpus_create = creator_language_sub.add_parser("corpus-create", help="Crear corpus")
    creator_language_corpus_create.add_argument("--creator-id", required=True)
    creator_language_corpus_create.add_argument("--name", required=True)
    creator_language_corpus_create.add_argument("--description")
    creator_language_corpus_create.add_argument("--language", default="es")
    creator_language_corpus_create.add_argument("--platform")
    creator_language_corpus_create.add_argument("--content-type")
    creator_language_corpus_create.add_argument("--topic")
    creator_language_corpus_create.add_argument("--json", action="store_true")

    creator_language_corpus_show = creator_language_sub.add_parser("corpus-show", help="Mostrar corpus")
    creator_language_corpus_show.add_argument("--corpus-id", required=True)
    creator_language_corpus_show.add_argument("--json", action="store_true")

    creator_language_corpus_source_add = creator_language_sub.add_parser("corpus-source-add", help="Agregar fuente al corpus")
    creator_language_corpus_source_add.add_argument("--corpus-id", required=True)
    creator_language_corpus_source_add.add_argument("--source-type", required=True)
    creator_language_corpus_source_add.add_argument("--source-id", required=True)
    creator_language_corpus_source_add.add_argument("--text-snapshot")
    creator_language_corpus_source_add.add_argument("--language")
    creator_language_corpus_source_add.add_argument("--platform")
    creator_language_corpus_source_add.add_argument("--content-type")
    creator_language_corpus_source_add.add_argument("--topic")
    creator_language_corpus_source_add.add_argument("--include-status", default="included")
    creator_language_corpus_source_add.add_argument("--exclusion-reason")
    creator_language_corpus_source_add.add_argument("--json", action="store_true")

    creator_language_corpus_source_remove = creator_language_sub.add_parser("corpus-source-remove", help="Excluir fuente")
    creator_language_corpus_source_remove.add_argument("--source-id", required=True)
    creator_language_corpus_source_remove.add_argument("--reason")
    creator_language_corpus_source_remove.add_argument("--json", action="store_true")

    creator_language_analyze = creator_language_sub.add_parser("analyze", help="Analizar corpus")
    creator_language_analyze.add_argument("--corpus-id", required=True)
    creator_language_analyze.add_argument("--json", action="store_true")

    creator_language_analysis_show = creator_language_sub.add_parser("analysis-show", help="Mostrar corrida")
    creator_language_analysis_show.add_argument("--run-id", required=True)
    creator_language_analysis_show.add_argument("--json", action="store_true")

    creator_language_metrics = creator_language_sub.add_parser("metrics", help="Mostrar metricas")
    creator_language_metrics.add_argument("--run-id", required=True)
    creator_language_metrics.add_argument("--json", action="store_true")

    creator_language_patterns = creator_language_sub.add_parser("patterns", help="Listar patrones")
    creator_language_patterns.add_argument("--creator-id", required=True)
    creator_language_patterns.add_argument("--run-id")
    creator_language_patterns.add_argument("--json", action="store_true")

    creator_language_pattern_show = creator_language_sub.add_parser("pattern-show", help="Mostrar patron")
    creator_language_pattern_show.add_argument("--pattern-id", required=True)
    creator_language_pattern_show.add_argument("--json", action="store_true")

    creator_language_profile = creator_language_sub.add_parser("profile", help="Mostrar perfil")
    creator_language_profile.add_argument("--creator-id", required=True)
    creator_language_profile.add_argument("--json", action="store_true")

    creator_language_profile_history = creator_language_sub.add_parser("profile-history", help="Historial de perfil")
    creator_language_profile_history.add_argument("--creator-id", required=True)
    creator_language_profile_history.add_argument("--json", action="store_true")

    creator_language_profile_compare = creator_language_sub.add_parser("profile-compare", help="Comparar versiones")
    creator_language_profile_compare.add_argument("--creator-id", required=True)
    creator_language_profile_compare.add_argument("--base-profile-version", required=True, type=int)
    creator_language_profile_compare.add_argument("--compare-profile-version", required=True, type=int)
    creator_language_profile_compare.add_argument("--json", action="store_true")

    creator_language_candidates = creator_language_sub.add_parser("candidates", help="Listar candidatos")
    creator_language_candidates.add_argument("--creator-id", required=True)
    creator_language_candidates.add_argument("--json", action="store_true")

    creator_language_candidate_review = creator_language_sub.add_parser("candidate-review", help="Revisar candidato")
    creator_language_candidate_review.add_argument("--candidate-id", required=True)
    creator_language_candidate_review.add_argument("--decision", required=True)
    creator_language_candidate_review.add_argument("--reason")
    creator_language_candidate_review.add_argument("--modified-value-json")
    creator_language_candidate_review.add_argument("--json", action="store_true")

    creator_language_retrieve = creator_language_sub.add_parser("retrieve", help="Recuperar contexto")
    creator_language_retrieve.add_argument("--creator-id", required=True)
    creator_language_retrieve.add_argument("--query")
    creator_language_retrieve.add_argument("--platform")
    creator_language_retrieve.add_argument("--content-type")
    creator_language_retrieve.add_argument("--topic")
    creator_language_retrieve.add_argument("--trait-type")
    creator_language_retrieve.add_argument("--example-type")
    creator_language_retrieve.add_argument("--approval-status")
    creator_language_retrieve.add_argument("--confidence-level")
    creator_language_retrieve.add_argument("--status")
    creator_language_retrieve.add_argument("--json", action="store_true")

    creator_language_export = creator_language_sub.add_parser("export", help="Exportar memoria de lenguaje")
    creator_language_export.add_argument("--creator-id", required=True)
    creator_language_export.add_argument("--format", required=True, choices=["json", "txt", "csv"])
    creator_language_export.add_argument("--summary", action="store_true")
    creator_language_export.add_argument("--json", action="store_true")

    acoustic_parser = subparsers.add_parser("acoustic", help="Analisis acustico local")
    acoustic_sub = acoustic_parser.add_subparsers(dest="action", required=True)

    acoustic_analyze = acoustic_sub.add_parser("analyze", help="Analizar audio preparado")
    acoustic_analyze.add_argument("--video-id", required=True)
    acoustic_analyze.add_argument("--force", action="store_true")
    acoustic_analyze.add_argument("--json", action="store_true")

    acoustic_show = acoustic_sub.add_parser("show", help="Mostrar el analisis acustico")
    acoustic_show.add_argument("--video-id", required=True)
    acoustic_show.add_argument("--json", action="store_true")

    acoustic_timeline = acoustic_sub.add_parser("timeline", help="Mostrar la linea temporal")
    acoustic_timeline.add_argument("--video-id", required=True)
    acoustic_timeline.add_argument("--json", action="store_true")

    acoustic_events = acoustic_sub.add_parser("events", help="Mostrar eventos candidatos")
    acoustic_events.add_argument("--video-id", required=True)
    acoustic_events.add_argument("--json", action="store_true")

    acoustic_export = acoustic_sub.add_parser("export", help="Exportar el analisis acustico")
    acoustic_export.add_argument("--video-id", required=True)
    acoustic_export.add_argument("--format", required=True, choices=["json", "csv", "txt"])
    acoustic_export.add_argument("--output")
    acoustic_export.add_argument("--json", action="store_true")

    acoustic_delete = acoustic_sub.add_parser("delete", help="Eliminar el analisis acustico")
    acoustic_delete.add_argument("--video-id", required=True)
    acoustic_delete.add_argument("--json", action="store_true")

    visual_parser = subparsers.add_parser("visual", help="Analisis visual local")
    visual_sub = visual_parser.add_subparsers(dest="action", required=True)

    visual_analyze = visual_sub.add_parser("analyze", help="Analizar video")
    visual_analyze.add_argument("--video-id", required=True)
    visual_analyze.add_argument("--force", action="store_true")
    visual_analyze.add_argument("--json", action="store_true")

    visual_show = visual_sub.add_parser("show", help="Mostrar el analisis visual")
    visual_show.add_argument("--video-id", required=True)
    visual_show.add_argument("--json", action="store_true")

    visual_timeline = visual_sub.add_parser("timeline", help="Mostrar la linea temporal visual")
    visual_timeline.add_argument("--video-id", required=True)
    visual_timeline.add_argument("--json", action="store_true")

    visual_scenes = visual_sub.add_parser("scenes", help="Mostrar las escenas visuales")
    visual_scenes.add_argument("--video-id", required=True)
    visual_scenes.add_argument("--json", action="store_true")

    visual_events = visual_sub.add_parser("events", help="Mostrar eventos visuales")
    visual_events.add_argument("--video-id", required=True)
    visual_events.add_argument("--json", action="store_true")

    visual_export = visual_sub.add_parser("export", help="Exportar el analisis visual")
    visual_export.add_argument("--video-id", required=True)
    visual_export.add_argument("--format", required=True, choices=["json", "timeline-csv", "scenes-csv", "txt"])
    visual_export.add_argument("--output")
    visual_export.add_argument("--json", action="store_true")

    visual_delete = visual_sub.add_parser("delete", help="Eliminar el analisis visual")
    visual_delete.add_argument("--video-id", required=True)
    visual_delete.add_argument("--json", action="store_true")

    multimodal_parser = subparsers.add_parser("multimodal", help="Linea temporal multimodal")
    multimodal_sub = multimodal_parser.add_subparsers(dest="action", required=True)

    multimodal_analyze = multimodal_sub.add_parser("analyze", help="Analizar multimodalmente un video")
    multimodal_analyze.add_argument("--video-id", required=True)
    multimodal_analyze.add_argument("--force", action="store_true")
    multimodal_analyze.add_argument("--json", action="store_true")

    multimodal_show = multimodal_sub.add_parser("show", help="Mostrar el analisis multimodal")
    multimodal_show.add_argument("--video-id", required=True)
    multimodal_show.add_argument("--json", action="store_true")

    multimodal_timeline = multimodal_sub.add_parser("timeline", help="Mostrar la linea temporal multimodal")
    multimodal_timeline.add_argument("--video-id", required=True)
    multimodal_timeline.add_argument("--json", action="store_true")

    multimodal_candidates = multimodal_sub.add_parser("candidates", help="Listar candidatos multimodales")
    multimodal_candidates.add_argument("--video-id", required=True)
    multimodal_candidates.add_argument("--json", action="store_true")

    multimodal_candidate = multimodal_sub.add_parser("candidate", help="Mostrar un candidato multimodal")
    multimodal_candidate.add_argument("--candidate-id", required=True)
    multimodal_candidate.add_argument("--json", action="store_true")

    multimodal_export = multimodal_sub.add_parser("export", help="Exportar el analisis multimodal")
    multimodal_export.add_argument("--video-id", required=True)
    multimodal_export.add_argument("--format", required=True, choices=["json", "timeline-csv", "candidates-csv", "txt"])
    multimodal_export.add_argument("--output")
    multimodal_export.add_argument("--json", action="store_true")

    multimodal_delete = multimodal_sub.add_parser("delete", help="Eliminar el analisis multimodal")
    multimodal_delete.add_argument("--video-id", required=True)
    multimodal_delete.add_argument("--json", action="store_true")

    clips_parser = subparsers.add_parser("clips", help="Ranking de clips")
    clips_sub = clips_parser.add_subparsers(dest="action", required=True)

    clips_rank = clips_sub.add_parser("rank", help="Calcular ranking de clips")
    clips_rank.add_argument("--video-id", required=True)
    clips_rank.add_argument("--profile", default="balanced")
    clips_rank.add_argument("--force", action="store_true")
    clips_rank.add_argument("--json", action="store_true")

    clips_show = clips_sub.add_parser("show", help="Mostrar ranking de clips")
    clips_show.add_argument("--video-id", required=True)
    clips_show.add_argument("--json", action="store_true")

    clips_list = clips_sub.add_parser("list", help="Listar candidatos rankeados")
    clips_list.add_argument("--video-id", required=True)
    clips_list.add_argument("--json", action="store_true")

    clips_candidate = clips_sub.add_parser("candidate", help="Mostrar un candidato rankeado")
    clips_candidate.add_argument("--candidate-id", required=True)
    clips_candidate.add_argument("--json", action="store_true")

    clips_approve = clips_sub.add_parser("approve", help="Aprobar un candidato")
    clips_approve.add_argument("--candidate-id", required=True)
    clips_approve.add_argument("--json", action="store_true")

    clips_reject = clips_sub.add_parser("reject", help="Rechazar un candidato")
    clips_reject.add_argument("--candidate-id", required=True)
    clips_reject.add_argument("--json", action="store_true")

    clips_shortlist = clips_sub.add_parser("shortlist", help="Preseleccionar un candidato")
    clips_shortlist.add_argument("--candidate-id", required=True)
    clips_shortlist.add_argument("--json", action="store_true")

    clips_needs_review = clips_sub.add_parser("needs-review", help="Marcar un candidato para revision")
    clips_needs_review.add_argument("--candidate-id", required=True)
    clips_needs_review.add_argument("--json", action="store_true")

    clips_rate = clips_sub.add_parser("rate", help="Calificar un candidato")
    clips_rate.add_argument("--candidate-id", required=True)
    clips_rate.add_argument("--rating", required=True, type=int)
    clips_rate.add_argument("--json", action="store_true")

    clips_note = clips_sub.add_parser("note", help="Agregar nota a un candidato")
    clips_note.add_argument("--candidate-id", required=True)
    clips_note.add_argument("--text", required=True)
    clips_note.add_argument("--json", action="store_true")

    clips_tags = clips_sub.add_parser("tags", help="Asignar tags a un candidato")
    clips_tags.add_argument("--candidate-id", required=True)
    clips_tags.add_argument("--tags", required=True)
    clips_tags.add_argument("--json", action="store_true")

    clips_adjust = clips_sub.add_parser("adjust", help="Ajustar bordes de un candidato")
    clips_adjust.add_argument("--candidate-id", required=True)
    clips_adjust.add_argument("--start", required=True, type=float)
    clips_adjust.add_argument("--end", required=True, type=float)
    clips_adjust.add_argument("--json", action="store_true")

    clips_history = clips_sub.add_parser("history", help="Mostrar historial de revision")
    clips_history.add_argument("--candidate-id", required=True)
    clips_history.add_argument("--json", action="store_true")

    clips_export = clips_sub.add_parser("export", help="Exportar plan de clips")
    clips_export.add_argument("--video-id", required=True)
    clips_export.add_argument("--format", required=True, choices=["json", "csv", "edl"])
    clips_export.add_argument("--output")
    clips_export.add_argument("--json", action="store_true")

    clips_delete = clips_sub.add_parser("delete", help="Eliminar ranking de clips")
    clips_delete.add_argument("--video-id", required=True)
    clips_delete.add_argument("--json", action="store_true")

    clips_collection = clips_sub.add_parser("collection", help="Crear una coleccion")
    clips_collection.add_argument("--video-id", required=True)
    clips_collection.add_argument("--name", required=True)
    clips_collection.add_argument("--description")
    clips_collection.add_argument("--json", action="store_true")

    clips_add_to_collection = clips_sub.add_parser("collection-add", help="Agregar candidato a coleccion")
    clips_add_to_collection.add_argument("--collection-id", required=True)
    clips_add_to_collection.add_argument("--candidate-id", required=True)
    clips_add_to_collection.add_argument("--json", action="store_true")

    clips_remove_from_collection = clips_sub.add_parser("collection-remove", help="Quitar candidato de coleccion")
    clips_remove_from_collection.add_argument("--collection-id", required=True)
    clips_remove_from_collection.add_argument("--candidate-id", required=True)
    clips_remove_from_collection.add_argument("--json", action="store_true")

    render_parser = subparsers.add_parser("render", help="Render local de clips")
    render_sub = render_parser.add_subparsers(dest="action", required=True)

    render_capabilities = render_sub.add_parser("capabilities", help="Mostrar capacidades de FFmpeg")
    render_capabilities.add_argument("--json", action="store_true")

    render_profiles = render_sub.add_parser("profiles", help="Listar perfiles de render")
    render_profiles.add_argument("--json", action="store_true")

    render_subtitles = render_sub.add_parser("subtitles", help="Capacidades y estilos de subtitulos")
    render_subtitles_sub = render_subtitles.add_subparsers(dest="subaction", required=True)
    render_subtitles_capabilities = render_subtitles_sub.add_parser("capabilities", help="Mostrar capacidades de subtitulos")
    render_subtitles_capabilities.add_argument("--json", action="store_true")
    render_subtitles_styles = render_subtitles_sub.add_parser("styles", help="Mostrar estilos de subtitulos")
    render_subtitles_styles.add_argument("--json", action="store_true")

    render_candidate = render_sub.add_parser("candidate", help="Renderizar un candidato")
    render_candidate.add_argument("--candidate-id", required=True)
    render_candidate.add_argument("--profile", default="balanced")
    render_candidate.add_argument("--output")
    render_candidate.add_argument("--explicit", action="store_true")
    render_candidate.add_argument("--allow-stale", action="store_true")
    render_candidate.add_argument("--allow-overwrite", action="store_true")
    render_candidate.add_argument("--custom-name")
    render_candidate.add_argument("--json", action="store_true")

    render_sidecar = render_sub.add_parser("sidecar", help="Crear una entrega sidecar")
    render_sidecar.add_argument("--job-id", required=True)
    render_sidecar.add_argument("--track-id", required=True)
    render_sidecar.add_argument("--format", required=True, choices=["srt", "vtt"])
    render_sidecar.add_argument("--output")
    render_sidecar.add_argument("--allow-stale", action="store_true")
    render_sidecar.add_argument("--allow-overwrite", action="store_true")
    render_sidecar.add_argument("--custom-name")
    render_sidecar.add_argument("--json", action="store_true")

    render_burn_in = render_sub.add_parser("burn-in", help="Renderizar con subtitulos incrustados")
    render_burn_in.add_argument("--candidate-id", required=True)
    render_burn_in.add_argument("--track-id", required=True)
    render_burn_in.add_argument("--profile", default="balanced")
    render_burn_in.add_argument("--style", default="clean")
    render_burn_in.add_argument("--output")
    render_burn_in.add_argument("--allow-stale", action="store_true")
    render_burn_in.add_argument("--allow-overwrite", action="store_true")
    render_burn_in.add_argument("--custom-name")
    render_burn_in.add_argument("--json", action="store_true")

    render_show = render_sub.add_parser("show", help="Mostrar un job de render")
    render_show.add_argument("--job-id", required=True)
    render_show.add_argument("--json", action="store_true")

    render_list = render_sub.add_parser("list", help="Listar renders de un candidato")
    render_list.add_argument("--candidate-id", required=True)
    render_list.add_argument("--json", action="store_true")

    render_verify = render_sub.add_parser("verify", help="Verificar un render")
    render_verify.add_argument("--job-id", required=True)
    render_verify.add_argument("--json", action="store_true")

    render_cancel = render_sub.add_parser("cancel", help="Cancelar un render")
    render_cancel.add_argument("--job-id", required=True)
    render_cancel.add_argument("--json", action="store_true")

    render_retry = render_sub.add_parser("retry", help="Reintentar un render")
    render_retry.add_argument("--job-id", required=True)
    render_retry.add_argument("--json", action="store_true")

    render_delete = render_sub.add_parser("delete-artifact", help="Eliminar artefacto de render")
    render_delete.add_argument("--job-id", required=True)
    render_delete.add_argument("--json", action="store_true")

    render_collection = render_sub.add_parser("collection", help="Renderizar una coleccion")
    render_collection.add_argument("--collection-id", required=True)
    render_collection.add_argument("--profile", default="balanced")
    render_collection.add_argument("--output-root")
    render_collection.add_argument("--explicit", action="store_true")
    render_collection.add_argument("--allow-stale", action="store_true")
    render_collection.add_argument("--continue-on-failure", action="store_true")
    render_collection.add_argument("--json", action="store_true")

    render_batch_show = render_sub.add_parser("batch-show", help="Mostrar un lote de renders")
    render_batch_show.add_argument("--batch-id", required=True)
    render_batch_show.add_argument("--json", action="store_true")

    render_batch_cancel = render_sub.add_parser("batch-cancel", help="Cancelar un lote de renders")
    render_batch_cancel.add_argument("--batch-id", required=True)
    render_batch_cancel.add_argument("--json", action="store_true")

    render_batch_retry = render_sub.add_parser("batch-retry", help="Reintentar un lote de renders")
    render_batch_retry.add_argument("--batch-id", required=True)
    render_batch_retry.add_argument("--json", action="store_true")

    render_export_plan = render_sub.add_parser("export-plan", help="Exportar el plan tecnico de render")
    render_export_plan.add_argument("--job-id", required=True)
    render_export_plan.add_argument("--format", default="json")
    render_export_plan.add_argument("--output")
    render_export_plan.add_argument("--json", action="store_true")

    render_delivery_show = render_sub.add_parser("delivery-show", help="Mostrar una entrega")
    render_delivery_show.add_argument("--delivery-id", required=True)
    render_delivery_show.add_argument("--json", action="store_true")

    render_delivery_list = render_sub.add_parser("delivery-list", help="Listar entregas de un job")
    render_delivery_list.add_argument("--job-id", required=True)
    render_delivery_list.add_argument("--json", action="store_true")

    render_delivery_verify = render_sub.add_parser("delivery-verify", help="Verificar una entrega")
    render_delivery_verify.add_argument("--delivery-id", required=True)
    render_delivery_verify.add_argument("--json", action="store_true")

    render_delivery_cancel = render_sub.add_parser("delivery-cancel", help="Cancelar una entrega")
    render_delivery_cancel.add_argument("--delivery-id", required=True)
    render_delivery_cancel.add_argument("--json", action="store_true")

    render_delivery_retry = render_sub.add_parser("delivery-retry", help="Reintentar una entrega")
    render_delivery_retry.add_argument("--delivery-id", required=True)
    render_delivery_retry.add_argument("--json", action="store_true")

    render_delivery_delete = render_sub.add_parser("delivery-delete", help="Eliminar una entrega")
    render_delivery_delete.add_argument("--delivery-id", required=True)
    render_delivery_delete.add_argument("--json", action="store_true")

    render_delivery_export = render_sub.add_parser("delivery-export-manifest", help="Exportar el manifest de una entrega")
    render_delivery_export.add_argument("--delivery-id", required=True)
    render_delivery_export.add_argument("--output")
    render_delivery_export.add_argument("--json", action="store_true")

    personalization_parser = subparsers.add_parser("personalization", help="Preparacion de datos por creador")
    personalization_sub = personalization_parser.add_subparsers(dest="action", required=True)

    personalization_build = personalization_sub.add_parser("build", help="Construir un snapshot")
    personalization_build.add_argument("--creator-id", required=True)
    personalization_build.add_argument("--project-id")
    personalization_build.add_argument("--force", action="store_true")
    personalization_build.add_argument("--json", action="store_true")

    personalization_show = personalization_sub.add_parser("show", help="Mostrar un snapshot")
    personalization_show.add_argument("--snapshot-id", required=True)
    personalization_show.add_argument("--json", action="store_true")

    personalization_latest = personalization_sub.add_parser("latest", help="Mostrar el snapshot mas reciente")
    personalization_latest.add_argument("--creator-id", required=True)
    personalization_latest.add_argument("--json", action="store_true")

    personalization_list = personalization_sub.add_parser("list", help="Listar snapshots")
    personalization_list.add_argument("--creator-id", required=True)
    personalization_list.add_argument("--json", action="store_true")

    personalization_examples = personalization_sub.add_parser("examples", help="Listar ejemplos")
    personalization_examples.add_argument("--snapshot-id", required=True)
    personalization_examples.add_argument("--json", action="store_true")

    personalization_quality = personalization_sub.add_parser("quality", help="Mostrar quality report")
    personalization_quality.add_argument("--snapshot-id", required=True)
    personalization_quality.add_argument("--json", action="store_true")

    personalization_readiness = personalization_sub.add_parser("readiness", help="Mostrar readiness del creador")
    personalization_readiness.add_argument("--creator-id", required=True)
    personalization_readiness.add_argument("--json", action="store_true")

    personalization_compare = personalization_sub.add_parser("compare", help="Comparar snapshots")
    personalization_compare.add_argument("--snapshot-a", required=True)
    personalization_compare.add_argument("--snapshot-b", required=True)
    personalization_compare.add_argument("--json", action="store_true")

    personalization_archive = personalization_sub.add_parser("archive", help="Archivar snapshot")
    personalization_archive.add_argument("--snapshot-id", required=True)
    personalization_archive.add_argument("--json", action="store_true")

    personalization_export = personalization_sub.add_parser("export", help="Exportar snapshot")
    personalization_export.add_argument("--snapshot-id", required=True)
    personalization_export.add_argument("--format", required=True, choices=["json", "csv", "jsonl"])
    personalization_export.add_argument("--output")
    personalization_export.add_argument("--include-sensitive", action="store_true")
    personalization_export.add_argument("--json", action="store_true")

    models_parser = subparsers.add_parser("models", help="Modelos personalizados por creador")
    models_sub = models_parser.add_subparsers(dest="action", required=True)

    models_validate = models_sub.add_parser("validate", help="Validar un snapshot para entrenamiento")
    models_validate.add_argument("--snapshot-id", required=True)
    models_validate.add_argument("--json", action="store_true")

    models_train = models_sub.add_parser("train", help="Entrenar el baseline personalizado")
    models_train.add_argument("--snapshot-id", required=True)
    models_train.add_argument("--force", action="store_true")
    models_train.add_argument("--json", action="store_true")

    models_show = models_sub.add_parser("show", help="Mostrar un training run")
    models_show.add_argument("--run-id", required=True)
    models_show.add_argument("--json", action="store_true")

    models_list = models_sub.add_parser("list", help="Listar training runs")
    models_list.add_argument("--creator-id", required=True)
    models_list.add_argument("--json", action="store_true")

    models_metrics = models_sub.add_parser("metrics", help="Mostrar metrics")
    models_metrics.add_argument("--run-id", required=True)
    models_metrics.add_argument("--json", action="store_true")

    models_predictions = models_sub.add_parser("predictions", help="Listar predicciones")
    models_predictions.add_argument("--run-id", required=True)
    models_predictions.add_argument("--split")
    models_predictions.add_argument("--json", action="store_true")

    models_compare = models_sub.add_parser("compare", help="Comparar training runs")
    models_compare.add_argument("--baseline-run", required=True)
    models_compare.add_argument("--candidate-run", required=True)
    models_compare.add_argument("--json", action="store_true")

    models_activate = models_sub.add_parser("activate", help="Activar un modelo")
    models_activate.add_argument("--run-id", required=True)
    models_activate.add_argument("--json", action="store_true")

    models_deactivate = models_sub.add_parser("deactivate", help="Desactivar un modelo")
    models_deactivate.add_argument("--run-id", required=True)
    models_deactivate.add_argument("--json", action="store_true")

    models_retire = models_sub.add_parser("retire", help="Retirar un modelo")
    models_retire.add_argument("--run-id", required=True)
    models_retire.add_argument("--json", action="store_true")

    models_active = models_sub.add_parser("active", help="Mostrar el modelo activo")
    models_active.add_argument("--creator-id", required=True)
    models_active.add_argument("--project-id")
    models_active.add_argument("--json", action="store_true")

    models_verify = models_sub.add_parser("verify", help="Verificar artefacto")
    models_verify.add_argument("--run-id", required=True)
    models_verify.add_argument("--json", action="store_true")

    models_delete_artifact = models_sub.add_parser("delete-artifact", help="Eliminar artefacto local")
    models_delete_artifact.add_argument("--run-id", required=True)
    models_delete_artifact.add_argument("--json", action="store_true")

    models_score_candidate = models_sub.add_parser("score-candidate", help="Puntuar un candidato")
    models_score_candidate.add_argument("--creator-id", required=True)
    models_score_candidate.add_argument("--candidate-id", required=True)
    models_score_candidate.add_argument("--json", action="store_true")

    models_score_video = models_sub.add_parser("score-video", help="Puntuar todos los candidatos de un video")
    models_score_video.add_argument("--creator-id", required=True)
    models_score_video.add_argument("--video-id", required=True)
    models_score_video.add_argument("--json", action="store_true")

    models_explain = models_sub.add_parser("explain", help="Explicar una puntuacion personalizada")
    models_explain.add_argument("--creator-id", required=True)
    models_explain.add_argument("--candidate-id", required=True)
    models_explain.add_argument("--json", action="store_true")

    evaluation_parser = subparsers.add_parser("evaluation", help="Evaluacion operativa end-to-end")
    evaluation_sub = evaluation_parser.add_subparsers(dest="action", required=True)

    evaluation_scenarios = evaluation_sub.add_parser("scenarios", help="Listar escenarios disponibles")
    evaluation_scenarios.add_argument("--json", action="store_true")

    evaluation_run = evaluation_sub.add_parser("run", help="Ejecutar un escenario")
    evaluation_run.add_argument("--scenario", required=True)
    evaluation_run.add_argument("--force", action="store_true")
    evaluation_run.add_argument("--json", action="store_true")

    evaluation_show = evaluation_sub.add_parser("show", help="Mostrar un run")
    evaluation_show.add_argument("--run-id", required=True)
    evaluation_show.add_argument("--json", action="store_true")

    evaluation_stages = evaluation_sub.add_parser("stages", help="Listar etapas")
    evaluation_stages.add_argument("--run-id", required=True)
    evaluation_stages.add_argument("--json", action="store_true")

    evaluation_metrics = evaluation_sub.add_parser("metrics", help="Listar metricas")
    evaluation_metrics.add_argument("--run-id", required=True)
    evaluation_metrics.add_argument("--json", action="store_true")

    evaluation_assertions = evaluation_sub.add_parser("assertions", help="Listar assertions")
    evaluation_assertions.add_argument("--run-id", required=True)
    evaluation_assertions.add_argument("--json", action="store_true")
    evaluation_assertions.add_argument("--severity")

    evaluation_artifacts = evaluation_sub.add_parser("artifacts", help="Listar artefactos")
    evaluation_artifacts.add_argument("--run-id", required=True)
    evaluation_artifacts.add_argument("--json", action="store_true")

    evaluation_retry = evaluation_sub.add_parser("retry-stage", help="Reintentar una etapa")
    evaluation_retry.add_argument("--run-id", required=True)
    evaluation_retry.add_argument("--stage", required=True)
    evaluation_retry.add_argument("--json", action="store_true")

    evaluation_cancel = evaluation_sub.add_parser("cancel", help="Cancelar un run")
    evaluation_cancel.add_argument("--run-id", required=True)
    evaluation_cancel.add_argument("--json", action="store_true")

    evaluation_export = evaluation_sub.add_parser("export", help="Exportar un run")
    evaluation_export.add_argument("--run-id", required=True)
    evaluation_export.add_argument("--format", required=True, choices=["json", "csv", "txt"])
    evaluation_export.add_argument("--output")
    evaluation_export.add_argument("--json", action="store_true")

    evaluation_clean = evaluation_sub.add_parser("clean", help="Limpiar assets administrados")
    evaluation_clean.add_argument("--run-id", required=True)
    evaluation_clean.add_argument("--dry-run", action="store_true")
    evaluation_clean.add_argument("--json", action="store_true")

    return parser


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def render_diagnostic_summary(diagnostic: EnvironmentDiagnostic, stream) -> None:
    """Muestra un resumen humano del diagnostico."""

    print(f"{diagnostic.application_name} v{diagnostic.application_version}", file=stream)
    print("Entorno: development", file=stream)
    print(f"Ruta del proyecto: {diagnostic.project_root}", file=stream)
    print(f"Python: {diagnostic.python_version} ({diagnostic.python_executable})", file=stream)
    print(f"Backend preferido: {diagnostic.preferred_compute_backend}", file=stream)
    print("Modo basico disponible: " + ("si" if diagnostic.state.ready_for_basic_mode else "no"), file=stream)
    print("CUDA detectado por driver: " + ("si" if diagnostic.state.cuda_driver_detected else "no"), file=stream)
    print("CUDA verificado en runtime: " + ("si" if not diagnostic.state.cuda_runtime_not_verified else "no"), file=stream)
    if diagnostic.gpu_devices:
        gpu = diagnostic.gpu_devices[0]
        memory = f"{gpu.memory_total_mib} MiB" if gpu.memory_total_mib is not None else "no verificado"
        print(f"GPU NVIDIA: {gpu.name} | VRAM: {memory}", file=stream)
    else:
        print("GPU NVIDIA: no verificado", file=stream)
    for warning in diagnostic.warnings:
        print(f"Advertencia: {warning}", file=stream)


def _print_creator(creator, stream) -> None:
    print("Creador:", file=stream)
    print(f"ID: {creator.id}", file=stream)
    print(f"Nombre: {creator.display_name}", file=stream)
    print(f"Slug: {creator.slug}", file=stream)
    print(f"Estado: {creator.status.value}", file=stream)
    if creator.description:
        print(f"Descripcion: {creator.description}", file=stream)


def _print_project(project, stream) -> None:
    print("Proyecto:", file=stream)
    print(f"ID: {project.id}", file=stream)
    print(f"Creador: {project.creator_id}", file=stream)
    print(f"Nombre: {project.name}", file=stream)
    print(f"Tipo: {project.project_type.value}", file=stream)
    print(f"Estado: {project.status.value}", file=stream)
    if project.description:
        print(f"Descripcion: {project.description}", file=stream)


def _print_video(video, stream) -> None:
    print("Video:", file=stream)
    print(f"ID: {video.id}", file=stream)
    print(f"Proyecto: {video.project_id}", file=stream)
    print(f"Titulo: {video.title}", file=stream)
    print(f"Ruta: {video.source_path}", file=stream)
    print(f"Archivo disponible: {'si' if video.file_available else 'no'}", file=stream)
    print(f"Estado de procesamiento: {video.processing_status.value}", file=stream)
    print(f"Fuente: {video.source_type.value}", file=stream)
    if video.notes:
        print(f"Notas: {video.notes}", file=stream)


def _print_creator_list(creators, stream) -> None:
    if not creators:
        print("No hay creadores registrados.", file=stream)
        return
    for creator in creators:
        _print_creator(creator, stream)
        print("", file=stream)


def _print_project_list(projects, stream) -> None:
    if not projects:
        print("No hay proyectos registrados.", file=stream)
        return
    for project in projects:
        _print_project(project, stream)
        print("", file=stream)


def _print_video_list(videos, stream) -> None:
    if not videos:
        print("No hay videos registrados.", file=stream)
        return
    for video in videos:
        _print_video(video, stream)
        print("", file=stream)


def _print_media_tool(tool, stream) -> None:
    print(f"{tool.name}: {'si' if tool.available else 'no'}", file=stream)
    print(f"Ruta: {tool.path or 'no verificada'}", file=stream)
    print(f"Version: {tool.version or 'no verificada'}", file=stream)
    if tool.error_message:
        print(f"Advertencia: {tool.error_message}", file=stream)


def _print_media_tools_report(report: MediaToolsReport, stream) -> None:
    print("Herramientas multimedia:", file=stream)
    _print_media_tool(report.ffmpeg, stream)
    _print_media_tool(report.ffprobe, stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)


def _print_video_inspection(report: VideoInspectionReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de inspeccion: {report.status.value}", file=stream)
    print(f"Archivo disponible: {'si' if report.file_available else 'no'}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    if report.summary:
        summary = report.summary
        duration = f"{summary.duration_seconds:.3f} s" if summary.duration_seconds is not None else "no verificada"
        fps = summary.average_frame_rate.to_float() or summary.frame_rate.to_float()
        fps_text = f"{fps:.3f} fps" if fps is not None else "no verificado"
        resolution = f"{summary.width}x{summary.height}" if summary.width and summary.height else "no verificada"
        print(f"Duracion: {duration}", file=stream)
        print(f"Resolucion: {resolution}", file=stream)
        print(f"FPS: {fps_text}", file=stream)
        print(f"Video codec: {summary.video_codec or 'no verificado'}", file=stream)
        print(f"Audio codec: {summary.audio_codec or 'no verificado'}", file=stream)
        print(f"Canales: {summary.audio_channels if summary.audio_channels is not None else 'no verificados'}", file=stream)
        print(f"Frecuencia de muestreo: {summary.audio_sample_rate if summary.audio_sample_rate is not None else 'no verificada'} Hz", file=stream)
        print(f"Bitrate general: {summary.overall_bitrate if summary.overall_bitrate is not None else 'no verificado'}", file=stream)
        print(f"Streams: {summary.stream_count}", file=stream)
        print(f"Ultima inspeccion: {report.inspection.inspected_at if report.inspection else 'no verificada'}", file=stream)
    if report.thumbnail_path:
        print(f"Miniatura: {report.thumbnail_path}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_audio_report(report: PreparedAudioReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de audio: {report.status.value}", file=stream)
    print(f"Audio stale: {'si' if report.is_stale else 'no'}", file=stream)
    print(f"Stream seleccionado: {_audio_stream_summary(report)}", file=stream)
    if report.prepared_audio:
        print(f"Formato: {report.prepared_audio.format_name or 'no verificado'}", file=stream)
        print(f"Codec: {report.prepared_audio.codec_name or 'no verificado'}", file=stream)
        print(
            f"Sample rate: {report.prepared_audio.sample_rate_hz or 'no verificado'} Hz",
            file=stream,
        )
        print(f"Canales: {report.prepared_audio.channels or 'no verificado'}", file=stream)
        print(f"Bit depth: {report.prepared_audio.bit_depth or 'no verificado'}", file=stream)
        print(
            f"Duracion: {report.prepared_audio.duration_seconds:.3f} s"
            if report.prepared_audio.duration_seconds is not None
            else "Duracion: no verificada",
            file=stream,
        )
        print(
            f"Tamano: {report.prepared_audio.file_size_bytes} bytes"
            if report.prepared_audio.file_size_bytes is not None
            else "Tamano: no verificado",
            file=stream,
        )
        print(
            f"Generado: {report.prepared_audio.extraction_completed_at.isoformat()}"
            if report.prepared_audio.extraction_completed_at
            else "Generado: no verificado",
            file=stream,
        )
        print(f"Ruta de caché: {report.cache_path or 'no disponible'}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_transcription_segment(segment: TranscriptionSegment, stream) -> None:
    print(f"[{segment.segment_index}] {segment.start_seconds:.3f} -> {segment.end_seconds:.3f}", file=stream)
    print(segment.text, file=stream)


def _print_transcription_report(report: TranscriptionReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de transcripcion: {report.status.value}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    if report.transcription:
        transcription = report.transcription
        print(f"Motor: {transcription.engine}", file=stream)
        print(f"Modelo: {transcription.model_name}", file=stream)
        print(f"Dispositivo: {transcription.device}", file=stream)
        print(f"Compute type: {transcription.compute_type}", file=stream)
        print(f"Idioma detectado: {transcription.detected_language or 'no verificado'}", file=stream)
        print(
            f"Probabilidad de idioma: {transcription.language_probability if transcription.language_probability is not None else 'no verificada'}",
            file=stream,
        )
        print(f"Texto completo: {transcription.full_text}", file=stream)
        print(f"Segmentos: {transcription.segment_count}", file=stream)
        print(f"Tiempo de procesamiento: {transcription.processing_time_seconds:.3f} s", file=stream)
        print(f"Real-time factor: {transcription.real_time_factor:.3f}", file=stream)
    if report.backend:
        print(f"Backend: {report.backend.backend}", file=stream)
        print(f"CUDA device count: {report.backend.device_count}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_model_info(model_info, stream) -> None:
    print(f"Modelo: {model_info.model_name}", file=stream)
    print(f"Perfil: {model_info.profile}", file=stream)
    print(f"Instalado: {'si' if model_info.installed else 'no'}", file=stream)
    print(f"Estado: {model_info.status.value}", file=stream)
    print(f"Ruta: {model_info.path}", file=stream)
    if model_info.size_bytes is not None:
        print(f"Tamano: {model_info.size_bytes} bytes", file=stream)
    if model_info.notes:
        print(f"Notas: {model_info.notes}", file=stream)
    if model_info.error_message:
        print(f"Error: {model_info.error_message}", file=stream)


def _print_acoustic_window(window: AcousticTimelineWindow, stream) -> None:
    print(
        f"[{window.window_index}] {window.start_seconds:.3f} -> {window.end_seconds:.3f} | "
        f"{window.activity_label.value} | speech={window.speech_probability:.3f} | "
        f"energy={window.normalized_energy:.4f}",
        file=stream,
    )


def _print_acoustic_event(event: AcousticEvent, stream) -> None:
    print(
        f"[{event.event_index}] {event.event_type.value} {event.start_seconds:.3f} -> {event.end_seconds:.3f} "
        f"(conf={event.confidence:.3f})",
        file=stream,
    )


def _print_acoustic_report(report: AcousticAnalysisReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de analisis acustico: {report.status.value}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    if report.analysis is not None:
        analysis = report.analysis
        print(f"Analizador: {analysis.analyzer_version}", file=stream)
        print(f"Duracion de voz: {analysis.speech_duration_seconds:.3f} s", file=stream)
        print(f"Duracion de silencio: {analysis.silence_duration_seconds:.3f} s", file=stream)
        print(f"Speech ratio: {analysis.speech_ratio:.3f}", file=stream)
        print(
            f"Palabras por minuto: {analysis.words_per_minute:.3f}"
            if analysis.words_per_minute is not None
            else "Palabras por minuto: no verificado",
            file=stream,
        )
        print(f"Pausas: {analysis.pause_count}", file=stream)
        print(
            f"Pausa mas larga: {analysis.longest_pause_seconds:.3f} s"
            if analysis.longest_pause_seconds is not None
            else "Pausa mas larga: no verificada",
            file=stream,
        )
        print(f"Energia media: {analysis.average_energy:.6f}", file=stream)
        print(f"Rango dinamico: {analysis.dynamic_range:.6f}", file=stream)
        print(f"Cambios bruscos: {analysis.abrupt_change_count}", file=stream)
        print(f"Eventos candidatos: {analysis.event_candidate_count}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_visual_scene(scene: VisualScene, stream) -> None:
    print(
        f"[{scene.scene_index}] {scene.start_seconds:.3f} -> {scene.end_seconds:.3f} "
        f"(duracion={scene.duration_seconds:.3f} s)",
        file=stream,
    )
    print(f"Keyframe: {scene.representative_keyframe_path or 'no disponible'}", file=stream)


def _print_visual_event(event: VisualEvent, stream) -> None:
    print(
        f"[{event.event_index}] {event.event_type.value} {event.start_seconds:.3f} -> {event.end_seconds:.3f} "
        f"(conf={event.confidence:.3f})",
        file=stream,
    )


def _print_visual_report(report: VisualAnalysisReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de analisis visual: {report.status.value}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    if report.analysis is not None:
        analysis = report.analysis
        print(f"Analizador: {analysis.analyzer_version}", file=stream)
        print(f"Cortes: {analysis.detected_cut_count}", file=stream)
        print(f"Escenas: {analysis.detected_scene_count}", file=stream)
        print(f"Keyframes: {analysis.keyframe_count}", file=stream)
        print(f"Movimiento medio: {analysis.average_motion:.4f}", file=stream)
        print(f"Movimiento pico: {analysis.peak_motion:.4f}", file=stream)
        print(f"Brillo medio: {analysis.average_brightness:.4f}", file=stream)
        print(f"Contraste medio: {analysis.average_contrast:.4f}", file=stream)
        print(f"Segmentos estaticos: {analysis.static_segment_count}", file=stream)
        print(f"Frames negros: {analysis.black_frame_event_count}", file=stream)
        print(f"Congelamientos: {analysis.freeze_event_count}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_multimodal_window(window: MultimodalTimelineWindow, stream) -> None:
    print(
        f"[{window.window_index}] {window.start_seconds:.3f} -> {window.end_seconds:.3f} | "
        f"activity={window.combined_activity_score:.3f} | transition={window.transition_score:.3f} | "
        f"novelty={window.novelty_score:.3f}",
        file=stream,
    )


def _print_multimodal_candidate(candidate: MultimodalMomentCandidate, stream) -> None:
    print(
        f"[{candidate.candidate_index}] {candidate.candidate_type.value} "
        f"{candidate.start_seconds:.3f} -> {candidate.end_seconds:.3f} "
        f"(score={candidate.score:.3f}, conf={candidate.confidence:.3f})",
        file=stream,
    )
    print(f"Titulo: {candidate.title}", file=stream)
    print(f"Resumen: {candidate.summary}", file=stream)


def _print_multimodal_report(report: MultimodalAnalysisReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de analisis multimodal: {report.status.value}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    print(f"Fuentes disponibles: {', '.join(report.available_sources) or 'ninguna'}", file=stream)
    print(f"Fuentes faltantes: {', '.join(report.missing_sources) or 'ninguna'}", file=stream)
    if report.analysis is not None:
        analysis = report.analysis
        print(f"Analizador: {analysis.analyzer_version}", file=stream)
        print(f"Duracion: {analysis.duration_seconds:.3f} s", file=stream)
        print(f"Ventanas: {analysis.window_count}", file=stream)
        print(f"Candidatos: {analysis.candidate_count}", file=stream)
        print(f"Alta actividad: {analysis.high_activity_candidate_count}", file=stream)
        print(f"Transicion: {analysis.transition_candidate_count}", file=stream)
        print(f"Baja actividad: {analysis.silence_candidate_count}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_clip_candidate(candidate, stream) -> None:
    print(
        f"[{candidate.rank_position}] {candidate.candidate_type} "
        f"{candidate.adjusted_start_seconds:.3f} -> {candidate.adjusted_end_seconds:.3f} "
        f"(score={candidate.rank_score:.3f}, conf={candidate.source_confidence:.3f})",
        file=stream,
    )
    print(f"Estado: {candidate.review_status.value}", file=stream)
    print(f"Rating: {candidate.user_rating if candidate.user_rating is not None else 'sin rating'}", file=stream)
    if candidate.tags:
        print(f"Tags: {', '.join(candidate.tags)}", file=stream)
    if candidate.user_note:
        print(f"Nota: {candidate.user_note}", file=stream)


def _print_clip_report(report: ClipRankingReport, stream) -> None:
    _print_video(report.video, stream)
    print(f"Estado de ranking de clips: {report.status.value}", file=stream)
    print(f"Stale: {'si' if report.is_stale else 'no'}", file=stream)
    print(f"Fuentes disponibles: {', '.join(report.available_sources) or 'ninguna'}", file=stream)
    print(f"Fuentes faltantes: {', '.join(report.missing_sources) or 'ninguna'}", file=stream)
    if report.run is not None:
        run = report.run
        print(f"Ranker: {run.ranker_version}", file=stream)
        print(f"Candidatos origen: {run.candidate_count}", file=stream)
        print(f"Candidatos rankeados: {run.ranked_candidate_count}", file=stream)
        print(f"Seleccionados: {run.selected_count}", file=stream)
        print(f"Rechazados: {run.rejected_count}", file=stream)
        print(f"Revision humana: {run.review_count}", file=stream)
    for warning in report.warnings:
        print(f"Advertencia: {warning}", file=stream)
    for error in report.errors:
        print(f"Error: {error}", file=stream)


def _print_personalization_snapshot(report: PersonalizationDatasetReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_personalization_examples(examples, stream) -> None:
    print(json.dumps([example.to_dict() for example in examples], ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_personalization_quality(report, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_personalization_readiness(report: CreatorReadinessReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_personalization_comparison(report: DatasetSnapshotComparison, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_model_validation(report: TrainingValidationReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_model_training_report(report: PersonalizationTrainingReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_model_active_report(report: PersonalizationActiveModelReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_model_scores(scores, stream) -> None:
    print(json.dumps([score.to_dict() for score in scores], ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _print_model_score(report: PersonalizedScoreReport, stream) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stream)


def _audio_stream_summary(report: PreparedAudioReport) -> str:
    if report.selected_stream is None:
        return "No seleccionado"
    stream = report.selected_stream
    pieces = [f"stream {stream.index}"]
    if stream.channels is not None:
        pieces.append(f"{stream.channels} canales")
    if stream.language:
        pieces.append(stream.language)
    if stream.is_default:
        pieces.append("default")
    return " · ".join(pieces)


def _handle_creator(args, service: CatalogService, stdout) -> int:
    if args.action == "create":
        command = CreateCreatorCommand(
            display_name=args.name,
            slug=args.slug,
            description=args.description,
        )
        creator = service.create_creator(
            display_name=command.display_name,
            slug=command.slug,
            description=command.description,
        )
        print("Creador creado correctamente", file=stdout)
        _print_creator(creator, stdout)
        return 0
    if args.action == "list":
        _print_creator_list(service.list_creators(), stdout)
        return 0
    if args.action == "show":
        _print_creator(service.get_creator(args.creator_id_or_slug), stdout)
        return 0
    if args.action == "archive":
        command = ArchiveCreatorCommand(args.creator_id_or_slug)
        creator = service.archive_creator(command.creator_reference)
        print("Creador archivado correctamente", file=stdout)
        _print_creator(creator, stdout)
        return 0
    raise ValueError("Accion de creador no reconocida.")


def _handle_project(args, service: CatalogService, stdout) -> int:
    if args.action == "create":
        command = CreateProjectCommand(
            creator_reference=args.creator,
            name=args.name,
            project_type=args.project_type,
            description=args.description,
        )
        project = service.create_project(
            creator_reference=command.creator_reference,
            name=command.name,
            project_type=command.project_type,
            description=command.description,
        )
        print("Proyecto creado correctamente", file=stdout)
        _print_project(project, stdout)
        return 0
    if args.action == "list":
        _print_project_list(service.list_projects(args.creator), stdout)
        return 0
    if args.action == "show":
        _print_project(service.get_project(args.project_id), stdout)
        return 0
    if args.action == "archive":
        command = ArchiveProjectCommand(args.project_id)
        project = service.archive_project(command.project_id)
        print("Proyecto archivado correctamente", file=stdout)
        _print_project(project, stdout)
        return 0
    raise ValueError("Accion de proyecto no reconocida.")


def _handle_video(args, service: CatalogService, stdout) -> int:
    if args.action == "register":
        command = RegisterVideoCommand(
            project_id=args.project,
            file_path=args.file_path,
            title=args.title,
            notes=args.notes,
        )
        video = service.register_video(
            project_id=command.project_id,
            file_path=command.file_path,
            title=command.title,
            notes=command.notes,
        )
        print("Video registrado correctamente", file=stdout)
        _print_video(video, stdout)
        return 0
    if args.action == "list":
        _print_video_list(service.list_videos(args.project), stdout)
        return 0
    if args.action == "show":
        _print_video(service.get_video(args.video_id), stdout)
        return 0
    if args.action == "verify":
        command = VerifyVideoAvailabilityCommand(args.video_id)
        report = service.verify_video_availability(command.video_id)
        _print_video(report.video, stdout)
        print(f"Estado: {report.status}", file=stdout)
        print(f"metadata_changed: {'si' if report.metadata_changed else 'no'}", file=stdout)
        return 0
    raise ValueError("Accion de video no reconocida.")


def _handle_media(args, service: MediaInspectionService, stdout) -> int:
    if args.action == "tools":
        report = service.verify_media_tools()
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_media_tools_report(report, stdout)
        return 0 if report.available else 1
    if args.action == "inspect":
        command = InspectVideoCommand(video_id=args.video_id, force=args.force)
        report = service.inspect_video(command.video_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Inspeccion completada", file=stdout)
            _print_video_inspection(report, stdout)
        return 0
    if args.action == "show":
        command = ShowVideoInspectionCommand(args.video_id)
        report = service.get_video_inspection(command.video_id)
        if report is None:
            print("No hay inspeccion tecnica para este video.", file=stdout)
            return 1
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_video_inspection(report, stdout)
        return 0
    raise ValueError("Accion de media no reconocida.")


def _handle_audio(args, service: AudioPreparationService, stdout) -> int:
    if args.action == "prepare":
        command = PrepareAudioCommand(video_id=args.video_id, force=args.force)
        report = service.prepare_audio(command.video_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Preparacion de audio completada", file=stdout)
            _print_audio_report(report, stdout)
        return 0 if report.status.value == "completed" and not report.is_stale else 1
    if args.action == "show":
        command = ShowPreparedAudioCommand(args.video_id)
        report = service.get_prepared_audio(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_audio_report(report, stdout)
        return 0
    if args.action == "verify":
        command = VerifyPreparedAudioCommand(args.video_id)
        report = service.verify_prepared_audio(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Verificacion de audio completada", file=stdout)
            _print_audio_report(report, stdout)
        return 0 if report.status.value == "completed" and not report.is_stale else 1
    if args.action == "clear-cache":
        command = ClearAudioCacheCommand(args.video_id)
        result = service.delete_prepared_audio_cache(command.video_id)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Cache de audio limpiada", file=stdout)
            print(f"Registro eliminado: {'si' if result.deleted_record else 'no'}", file=stdout)
            print(f"Archivos eliminados: {len(result.deleted_files)}", file=stdout)
        return 0
    raise ValueError("Accion de audio no reconocida.")


def _handle_transcription(args, service: TranscriptionService, stdout, stderr) -> int:
    if args.action == "backend":
        report = service.verify_transcription_backend()
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Backend de transcripcion:", file=stdout)
            print(f"Backend: {report.backend.backend}", file=stdout)
            print(f"Disponible: {'si' if report.backend.available else 'no'}", file=stdout)
            print(f"Device count: {report.backend.device_count}", file=stdout)
            print(f"Compute types: {', '.join(report.backend.supported_compute_types) or 'no verificados'}", file=stdout)
        return 0 if report.backend.available else 1
    if args.action == "models":
        models = service.list_models()
        if args.json:
            print(json.dumps([model.to_dict() for model in models], ensure_ascii=False, indent=2), file=stdout)
        else:
            for model in models:
                _print_model_info(model, stdout)
                print("", file=stdout)
        return 0
    if args.action == "model-status":
        command = ModelStatusCommand(args.model)
        model = service.get_model_status(command.model_name)
        if args.json:
            print(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_model_info(model, stdout)
        return 0
    if args.action == "download-model":
        command = DownloadModelCommand(args.model)
        model = service.download_model(command.model_name)
        if args.json:
            print(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Descarga de modelo completada", file=stdout)
            _print_model_info(model, stdout)
        return 0 if model.installed else 1
    if args.action == "verify-model":
        command = VerifyModelCommand(args.model)
        model = service.verify_model(command.model_name)
        if args.json:
            print(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Verificacion de modelo completada", file=stdout)
            _print_model_info(model, stdout)
        return 0 if model.installed else 1
    if args.action == "transcribe":
        model_name = args.model_name or "small"
        options = TranscriptionOptions(
            profile=args.profile,
            model_name=model_name,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
            beam_size=args.beam_size,
            vad_filter=args.vad_filter,
            word_timestamps=args.word_timestamps,
        )
        report = service.transcribe_video(args.video_id, options)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Transcripcion completada", file=stdout)
            _print_transcription_report(report, stdout)
        return 0 if report.status == TranscriptionStatus.COMPLETED else 1
    if args.action == "show":
        command = ShowTranscriptionCommand(args.video_id)
        report = service.get_transcription(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_transcription_report(report, stdout)
        return 0 if report.transcription is not None else 1
    if args.action == "segments":
        command = ListSegmentsCommand(args.video_id)
        report = service.get_transcription(command.video_id)
        segments = list(report.segments)
        if args.json:
            print(json.dumps([segment.to_dict() for segment in segments], ensure_ascii=False, indent=2), file=stdout)
        else:
            for segment in segments:
                _print_transcription_segment(segment, stdout)
                print("", file=stdout)
        return 0
    if args.action == "export":
        command = ExportTranscriptionCommand(args.video_id, TranscriptionExportFormat(args.format))
        destination = Path(args.output) if args.output else None
        result = service.export_transcription(command.video_id, command.format, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteTranscriptionCommand(args.video_id)
        deleted = service.delete_transcription(command.video_id)
        if args.json:
            print(json.dumps({"video_id": command.video_id, "deleted": deleted}, ensure_ascii=False), file=stdout)
        else:
            print("Transcripcion eliminada" if deleted else "No existia transcripcion", file=stdout)
        return 0
    raise ValueError("Accion de transcripcion no reconocida.")


def _build_subtitle_options(args) -> SubtitleGenerationOptions:
    return SubtitleGenerationOptions(
        language=args.language,
        max_lines=args.max_lines,
        max_chars_per_line=args.max_chars_per_line,
        max_chars_per_cue=args.max_chars_per_cue,
        min_duration_seconds=args.min_duration,
        max_duration_seconds=args.max_duration,
        min_gap_seconds=args.min_gap,
        cps_warning_threshold=args.cps_warning,
    )


def _handle_subtitles(args, service: SubtitleService, stdout, stderr) -> int:
    if args.action == "generate-video":
        command = GenerateVideoSubtitlesCommand(args.video_id, options=_build_subtitle_options(args))
        report = service.generate_video_subtitles(command.video_id, command.options, custom_name=args.custom_name)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "generate-clip":
        command = GenerateClipSubtitlesCommand(args.candidate_id, options=_build_subtitle_options(args))
        report = service.generate_clip_subtitles(command.candidate_id, command.options, custom_name=args.custom_name)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "show":
        command = ShowSubtitleTrackCommand(args.track_id)
        report = service.get_subtitle_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "list-video":
        command = ListVideoSubtitleTracksCommand(args.video_id)
        tracks = service.list_video_subtitle_tracks(command.video_id)
        print(json.dumps([track.to_dict() for track in tracks], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "list-clip":
        command = ListClipSubtitleTracksCommand(args.candidate_id)
        tracks = service.list_clip_subtitle_tracks(command.candidate_id)
        print(json.dumps([track.to_dict() for track in tracks], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "validate":
        command = ValidateSubtitleTrackCommand(args.track_id)
        report = service.validate_subtitle_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if not (report.validation and report.validation.blocking_errors) else 1
    if args.action == "update-text":
        command = UpdateSubtitleTextCommand(args.cue_id, args.text)
        report = service.update_cue_text(command.cue_id, command.text)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "update-time":
        command = UpdateSubtitleTimeCommand(args.cue_id, args.start, args.end)
        report = service.update_cue_timing(command.cue_id, command.start_seconds, command.end_seconds)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "split":
        command = SplitSubtitleCueCommand(args.cue_id, args.position)
        report = service.split_cue(command.cue_id, command.split_position)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "merge":
        command = MergeSubtitleCuesCommand(args.first_cue_id, args.second_cue_id)
        report = service.merge_cues(command.first_cue_id, command.second_cue_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "insert":
        command = InsertSubtitleCueCommand(args.track_id, args.index, args.start, args.end, args.text)
        report = service.insert_cue(command.track_id, command.index, command.start_seconds, command.end_seconds, command.text)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delete-cue":
        command = DeleteSubtitleCueCommand(args.cue_id)
        report = service.delete_cue(command.cue_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "shift":
        command = ShiftSubtitleTrackCommand(args.track_id, args.offset)
        report = service.shift_track(command.track_id, command.offset_seconds)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "lock":
        command = LockSubtitleTrackCommand(args.track_id)
        report = service.lock_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "unlock":
        command = UnlockSubtitleTrackCommand(args.track_id)
        report = service.unlock_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "duplicate":
        command = DuplicateSubtitleTrackCommand(args.track_id)
        report = service.duplicate_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "import":
        command = ImportSubtitleTrackCommand(args.video_id, Path(args.file), format=SubtitleExportFormat(args.format) if args.format else None)
        report = service.import_subtitles(command.video_id, command.file, format=command.format)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        command = ExportSubtitleTrackCommand(args.track_id, SubtitleExportFormat(args.format), output=Path(args.output) if args.output else None)
        result = service.export_subtitles(command.track_id, command.format, output=command.output)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "history":
        command = SubtitleHistoryCommand(args.track_id)
        events = service.get_subtitle_edit_history(command.track_id)
        print(json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "archive":
        command = ArchiveSubtitleTrackCommand(args.track_id)
        report = service.archive_subtitle_track(command.track_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteSubtitleTrackCommand(args.track_id)
        deleted = service.delete_subtitle_track(command.track_id)
        print(json.dumps({"track_id": command.track_id, "deleted": deleted}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if deleted else 1
    raise ValueError("Accion de subtitulos no reconocida.")


def _handle_acoustic(args, service: AcousticAnalysisService, stdout, stderr) -> int:
    if args.action == "analyze":
        command = AnalyzeAcousticCommand(args.video_id, force=args.force)
        report = service.analyze_acoustics(command.video_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Analisis acustico completado", file=stdout)
            _print_acoustic_report(report, stdout)
        return 0 if report.status == AcousticAnalysisStatus.COMPLETED else 1
    if args.action == "show":
        command = ShowAcousticCommand(args.video_id)
        report = service.get_acoustic_analysis(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_acoustic_report(report, stdout)
        return 0 if report.analysis is not None else 1
    if args.action == "timeline":
        command = TimelineAcousticCommand(args.video_id)
        windows = service.get_acoustic_timeline(command.video_id)
        if args.json:
            print(json.dumps([window.to_dict() for window in windows], ensure_ascii=False, indent=2), file=stdout)
        else:
            for window in windows:
                _print_acoustic_window(window, stdout)
        return 0 if windows else 1
    if args.action == "events":
        command = EventsAcousticCommand(args.video_id)
        events = service.list_acoustic_events(command.video_id)
        if args.json:
            print(json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2), file=stdout)
        else:
            for event in events:
                _print_acoustic_event(event, stdout)
        return 0 if events else 1
    if args.action == "export":
        command = ExportAcousticCommand(args.video_id, args.format)
        destination = Path(args.output) if args.output else None
        result = service.export_acoustic_analysis(command.video_id, command.format, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteAcousticCommand(args.video_id)
        deleted = service.delete_acoustic_analysis(command.video_id)
        if args.json:
            print(json.dumps({"video_id": command.video_id, "deleted": deleted}, ensure_ascii=False), file=stdout)
        else:
            print("Analisis acustico eliminado" if deleted else "No existia analisis acustico", file=stdout)
        return 0
    raise ValueError("Accion de analisis acustico no reconocida.")


def _handle_visual(args, service: VisualAnalysisService, stdout, stderr) -> int:
    if args.action == "analyze":
        command = AnalyzeVisualCommand(args.video_id, force=args.force)
        report = service.analyze_visuals(command.video_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Analisis visual completado", file=stdout)
            _print_visual_report(report, stdout)
        return 0 if report.status == VisualAnalysisStatus.COMPLETED else 1
    if args.action == "show":
        command = ShowVisualCommand(args.video_id)
        report = service.get_visual_analysis(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_visual_report(report, stdout)
        return 0 if report.analysis is not None else 1
    if args.action == "timeline":
        command = TimelineVisualCommand(args.video_id)
        windows = service.get_visual_timeline(command.video_id)
        if args.json:
            print(json.dumps([window.to_dict() for window in windows], ensure_ascii=False, indent=2), file=stdout)
        else:
            for window in windows:
                print(
                    f"[{window.window_index}] {window.start_seconds:.3f} -> {window.end_seconds:.3f} | "
                    f"{window.activity_label.value} | motion={window.motion_score:.4f}",
                    file=stdout,
                )
        return 0 if windows else 1
    if args.action == "scenes":
        command = ScenesVisualCommand(args.video_id)
        scenes = service.list_visual_scenes(command.video_id)
        if args.json:
            print(json.dumps([scene.to_dict() for scene in scenes], ensure_ascii=False, indent=2), file=stdout)
        else:
            for scene in scenes:
                _print_visual_scene(scene, stdout)
                print("", file=stdout)
        return 0 if scenes else 1
    if args.action == "events":
        command = EventsVisualCommand(args.video_id)
        events = service.list_visual_events(command.video_id)
        if args.json:
            print(json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2), file=stdout)
        else:
            for event in events:
                _print_visual_event(event, stdout)
                print("", file=stdout)
        return 0 if events else 1
    if args.action == "export":
        command = ExportVisualCommand(args.video_id, args.format)
        destination = Path(args.output) if args.output else None
        result = service.export_visual_analysis(command.video_id, command.format, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteVisualCommand(args.video_id)
        deleted = service.delete_visual_analysis(command.video_id)
        if args.json:
            print(json.dumps({"video_id": command.video_id, "deleted": deleted}, ensure_ascii=False), file=stdout)
        else:
            print("Analisis visual eliminado" if deleted else "No existia analisis visual", file=stdout)
        return 0
    raise ValueError("Accion de analisis visual no reconocida.")


def _handle_multimodal(args, service: MultimodalAnalysisService, stdout, stderr) -> int:
    if args.action == "analyze":
        command = AnalyzeMultimodalCommand(args.video_id, force=args.force)
        report = service.analyze_multimodal(command.video_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print("Analisis multimodal completado", file=stdout)
            _print_multimodal_report(report, stdout)
        return 0 if report.status == MultimodalAnalysisStatus.COMPLETED else 1
    if args.action == "show":
        command = ShowMultimodalCommand(args.video_id)
        report = service.get_multimodal_analysis(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_multimodal_report(report, stdout)
        return 0 if report.analysis is not None else 1
    if args.action == "timeline":
        command = TimelineMultimodalCommand(args.video_id)
        windows = service.get_multimodal_timeline(command.video_id)
        if args.json:
            print(json.dumps([window.to_dict() for window in windows], ensure_ascii=False, indent=2), file=stdout)
        else:
            for window in windows:
                _print_multimodal_window(window, stdout)
        return 0 if windows else 1
    if args.action == "candidates":
        command = CandidatesMultimodalCommand(args.video_id)
        candidates = service.list_moment_candidates(command.video_id)
        if args.json:
            print(json.dumps([candidate.to_dict() for candidate in candidates], ensure_ascii=False, indent=2), file=stdout)
        else:
            for candidate in candidates:
                _print_multimodal_candidate(candidate, stdout)
                print("", file=stdout)
        return 0 if candidates else 1
    if args.action == "candidate":
        command = CandidateMultimodalCommand(args.candidate_id)
        candidate = service.get_moment_candidate(command.candidate_id)
        if args.json:
            print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            _print_multimodal_candidate(candidate, stdout)
        return 0
    if args.action == "export":
        command = ExportMultimodalCommand(args.video_id, args.format)
        destination = Path(args.output) if args.output else None
        result = service.export_multimodal_analysis(command.video_id, command.format, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteMultimodalCommand(args.video_id)
        deleted = service.delete_multimodal_analysis(command.video_id)
        if args.json:
            print(json.dumps({"video_id": command.video_id, "deleted": deleted}, ensure_ascii=False), file=stdout)
        else:
            print("Analisis multimodal eliminado" if deleted else "No existia analisis multimodal", file=stdout)
        return 0
    raise ValueError("Accion de analisis multimodal no reconocida.")


def _handle_clips(args, service: ClipRankingService, stdout, stderr) -> int:
    if args.action == "rank":
        command = RankClipCandidatesCommand(video_id=args.video_id, profile=args.profile, force=args.force)
        report = service.rank_clip_candidates(command.video_id, profile=command.profile, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print("Ranking de clips completado", file=stdout)
            _print_clip_report(report, stdout)
        return 0
    if args.action == "show":
        command = ShowClipRankingCommand(args.video_id)
        report = service.get_ranking_run(command.video_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_clip_report(report, stdout)
        return 0
    if args.action == "list":
        command = ListClipCandidatesCommand(args.video_id)
        candidates = service.list_ranked_candidates(command.video_id)
        if args.json:
            print(json.dumps([candidate.to_dict() for candidate in candidates], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            for candidate in candidates:
                _print_clip_candidate(candidate, stdout)
                print("", file=stdout)
        return 0
    if args.action == "candidate":
        command = CandidateClipCommand(args.candidate_id)
        candidate = service.get_ranked_candidate(command.candidate_id)
        if args.json:
            print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "approve":
        candidate = service.approve_candidate(args.candidate_id)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Candidato aprobado", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "reject":
        candidate = service.reject_candidate(args.candidate_id)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Candidato rechazado", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "shortlist":
        candidate = service.shortlist_candidate(args.candidate_id)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Candidato preseleccionado", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "needs-review":
        candidate = service.mark_candidate_needs_review(args.candidate_id)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Candidato marcado para revision", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "rate":
        command = RateClipCandidateCommand(args.candidate_id, args.rating)
        candidate = service.rate_candidate(command.candidate_id, command.rating)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Rating aplicado", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "note":
        command = NoteClipCandidateCommand(args.candidate_id, args.text)
        candidate = service.add_candidate_note(command.candidate_id, command.text)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Nota agregada", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "tags":
        command = TagsClipCandidateCommand(args.candidate_id, [tag.strip() for tag in args.tags.split(",") if tag.strip()])
        candidate = service.set_candidate_tags(command.candidate_id, command.tags)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Tags aplicados", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "adjust":
        command = AdjustClipCandidateCommand(args.candidate_id, args.start, args.end)
        candidate = service.adjust_candidate_bounds(command.candidate_id, command.start_seconds, command.end_seconds)
        print(json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, default=_json_default) if args.json else "Bordes ajustados", file=stdout)
        if not args.json:
            _print_clip_candidate(candidate, stdout)
        return 0
    if args.action == "history":
        history = service.get_candidate_review_history(args.candidate_id)
        if args.json:
            print(json.dumps([event.to_dict() for event in history], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            for event in history:
                print(json.dumps(event.to_dict(), ensure_ascii=False, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        command = ExportClipPlanCommand(args.video_id, args.format)
        destination = Path(args.output) if args.output else None
        result = service.export_clip_plan(command.video_id, command.format, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    if args.action == "delete":
        command = DeleteClipRankingCommand(args.video_id)
        deleted = service.delete_clip_ranking(command.video_id)
        if args.json:
            print(json.dumps({"video_id": command.video_id, "deleted": deleted}, ensure_ascii=False), file=stdout)
        else:
            print("Ranking de clips eliminado" if deleted else "No existia ranking de clips", file=stdout)
        return 0
    if args.action == "collection":
        command = CreateClipCollectionCommand(args.video_id, args.name)
        collection = service.create_clip_collection(command.video_id, command.name, description=args.description)
        if args.json:
            print(json.dumps(collection.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print("Coleccion creada", file=stdout)
            print(json.dumps(collection.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "collection-add":
        command = AddClipToCollectionCommand(args.collection_id, args.candidate_id)
        item = service.add_candidate_to_collection(command.collection_id, command.candidate_id)
        if args.json:
            print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print("Clip agregado a la coleccion", file=stdout)
            print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "collection-remove":
        command = RemoveClipFromCollectionCommand(args.collection_id, args.candidate_id)
        removed = service.remove_candidate_from_collection(command.collection_id, command.candidate_id)
        if args.json:
            print(json.dumps({"collection_id": command.collection_id, "candidate_id": command.candidate_id, "removed": removed}, ensure_ascii=False), file=stdout)
        else:
            print("Clip removido de la coleccion" if removed else "No existia el clip en la coleccion", file=stdout)
        return 0
    raise ValueError("Accion de ranking de clips no reconocida.")


def _handle_youtube(args, service: YouTubeIntegrationService, stdout, stderr) -> int:
    if args.action == "connections":
        command = ListYouTubeConnectionsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_connections(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "connect":
        command = ConnectYouTubeCommand(
            args.creator_id,
            args.client_id,
            client_secret=args.client_secret,
            authorization_code=args.authorization_code,
            redirect_uri=args.redirect_uri,
            scopes_json=args.scopes_json,
            google_account_identifier=args.google_account_identifier,
        )
        connect_kwargs = {
            "creator_id": command.creator_id,
            "client_id": command.client_id,
            "client_secret": command.client_secret,
            "authorization_code": command.authorization_code,
            "redirect_uri": command.redirect_uri,
            "google_account_identifier": command.google_account_identifier,
        }
        if command.scopes_json:
            connect_kwargs["scopes"] = tuple(json.loads(command.scopes_json))
        result = service.connect_account(**connect_kwargs)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "connection-show":
        command = ShowYouTubeConnectionCommand(args.connection_id)
        payload = service.get_connection(command.connection_id)
        if payload is None:
            print("Conexion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "verify":
        command = VerifyYouTubeConnectionCommand(args.connection_id)
        payload = service.verify_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "disconnect":
        command = DisconnectYouTubeConnectionCommand(args.connection_id)
        payload = service.disconnect_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "revoke":
        command = RevokeYouTubeConnectionCommand(args.connection_id)
        payload = service.revoke_connection(command.connection_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "channels":
        command = ListYouTubeChannelsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_channels(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "channel-select":
        command = SelectYouTubeChannelCommand(args.channel_id)
        payload = service.select_channel(command.channel_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "channel-show":
        command = ShowYouTubeChannelCommand(args.channel_id)
        payload = service.get_channel(command.channel_id)
        if payload is None:
            print("Canal no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action in {"sync-channel", "sync-content", "sync-analytics", "sync-incremental", "sync-repair"}:
        metrics = tuple(json.loads(args.metrics_json)) if getattr(args, "metrics_json", None) else None
        channel = service.get_channel(args.channel_id)
        if channel is None:
            print("Canal no encontrado.", file=stderr)
            return 1
        if args.action == "sync-channel":
            command = SyncYouTubeChannelCommand(
                args.channel_id,
                sync_type=args.sync_type,
                cursor=args.cursor,
                full_resync=args.full_resync,
                include_analytics=args.include_analytics,
                include_thumbnails=args.include_thumbnails,
                metrics_json=args.metrics_json,
            )
            payload = service.sync_channel(
                creator_id=channel.creator_id,
                channel_id=command.channel_id,
                sync_type=command.sync_type,
                cursor=command.cursor,
                full_resync=command.full_resync,
                include_analytics=command.include_analytics,
                include_thumbnails=command.include_thumbnails,
                metrics=metrics,
            )
        elif args.action == "sync-content":
            command = SyncYouTubeChannelCommand(args.channel_id, sync_type="content_catalog", cursor=args.cursor)
            payload = service.sync_content(creator_id=channel.creator_id, channel_id=command.channel_id, cursor=command.cursor)
        elif args.action == "sync-analytics":
            command = SyncYouTubeChannelCommand(args.channel_id, sync_type="video_analytics", cursor=args.cursor, metrics_json=args.metrics_json)
            payload = service.sync_analytics(creator_id=channel.creator_id, channel_id=command.channel_id, cursor=command.cursor, metrics=metrics)
        elif args.action == "sync-incremental":
            command = SyncYouTubeChannelCommand(args.channel_id, sync_type="incremental_sync", cursor=args.cursor)
            payload = service.sync_incremental(creator_id=channel.creator_id, channel_id=command.channel_id, cursor=command.cursor)
        else:
            command = SyncYouTubeChannelCommand(args.channel_id, sync_type="repair_sync")
            payload = service.sync_repair(creator_id=channel.creator_id, channel_id=command.channel_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-resume":
        command = ResumeYouTubeSyncCommand(args.run_id)
        payload = service.resume_sync(command.run_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-history":
        command = SyncYouTubeHistoryCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_sync_runs(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sync-show":
        command = ShowYouTubeSyncRunCommand(args.run_id)
        run = service.get_sync_run(command.run_id)
        if run is None:
            print("Sincronizacion no encontrada.", file=stderr)
            return 1
        report_path = service.export_sync_report(run.id, "json")
        payload = {
            "run": run.to_dict(),
            "items": [item.to_dict() for item in service.list_sync_items(run.id)],
            "report": json.loads(report_path.read_text(encoding="utf-8")),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "videos":
        command = ListYouTubeVideosCommand(args.channel_id)
        payload = [item.to_dict() for item in service.list_remote_videos(command.channel_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "video-show":
        command = ShowYouTubeVideoCommand(args.remote_video_id)
        payload = service.get_remote_video(command.remote_video_id)
        if payload is None:
            print("Video remoto no encontrado.", file=stderr)
            return 1
        detail = payload.to_dict()
        detail["thumbnails"] = [item.to_dict() for item in service.list_video_thumbnails(payload.id)]
        print(json.dumps(detail, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "link-content":
        command = LinkYouTubeContentCommand(
            args.remote_video_id,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            link_method=args.link_method,
            confidence_level=args.confidence_level,
            status=args.status,
        )
        remote_video = service.get_remote_video(command.remote_video_id)
        if remote_video is None:
            print("Video remoto no encontrado.", file=stderr)
            return 1
        payload = service.link_content(
            creator_id=remote_video.creator_id,
            remote_video_id=command.remote_video_id,
            publication_id=command.publication_id,
            video_asset_id=command.video_asset_id,
            link_method=command.link_method,
            confidence_level=command.confidence_level,
            status=command.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "unlink-content":
        command = UnlinkYouTubeContentCommand(args.remote_video_id)
        remote_video = service.get_remote_video(command.remote_video_id)
        if remote_video is None:
            print("Video remoto no encontrado.", file=stderr)
            return 1
        payload = service.unlink_content(
            creator_id=remote_video.creator_id,
            remote_video_id=command.remote_video_id,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "quota":
        command = YouTubeQuotaCommand(args.connection_id)
        payload = [item.to_dict() for item in service.list_quota_usage(command.connection_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-report":
        command = ExportYouTubeSyncReportCommand(args.run_id, args.format, output=Path(args.output) if args.output else None)
        path = service.export_sync_report(command.run_id, command.format, destination=command.output)
        print(json.dumps({"run_id": command.run_id, "format": command.format, "path": str(path)}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de youtube no reconocida.")


def _handle_render(args, service: ClipRenderService, stdout, stderr) -> int:
    if args.action == "subtitles":
        if args.subaction == "capabilities":
            payload = service.render_subtitle_capabilities()
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
            return 0
        if args.subaction == "styles":
            styles = service.render_subtitle_styles()
            print(json.dumps(list(styles), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
            return 0
        raise ValueError("Accion de subtitulos no reconocida.")
    if args.action == "capabilities":
        command = RenderCapabilitiesCommand()
        report = service.render_capabilities()
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if report.available else 1
    if args.action == "profiles":
        command = RenderProfilesCommand()
        profiles = service.render_profiles()
        print(json.dumps([profile for profile in profiles], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "candidate":
        command = RenderCandidateCommand(
            candidate_id=args.candidate_id,
            profile=args.profile,
            output=args.output,
            explicit=args.explicit,
            allow_stale=args.allow_stale,
            allow_overwrite=args.allow_overwrite,
            custom_name=args.custom_name,
        )
        report = service.render_candidate(
            command.candidate_id,
            profile=command.profile,
            output=command.output,
            explicit=command.explicit,
            allow_stale=command.allow_stale,
            allow_overwrite=command.allow_overwrite,
            custom_name=command.custom_name,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "show":
        command = ShowRenderJobCommand(args.job_id)
        job = service.get_render_job(command.job_id)
        if job is None:
            print("Job de render no encontrado.", file=stderr)
            return 1
        print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "list":
        command = ListCandidateRendersCommand(args.candidate_id)
        jobs = service.list_candidate_renders(command.candidate_id)
        print(json.dumps([job.to_dict() for job in jobs], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "verify":
        command = VerifyRenderCommand(args.job_id)
        report = service.verify_render(command.job_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if report.verification.verified else 1
    if args.action == "cancel":
        command = CancelRenderCommand(args.job_id)
        job = service.cancel_render(command.job_id)
        if job is None:
            print("Job de render no encontrado.", file=stderr)
            return 1
        print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "retry":
        command = RetryRenderCommand(args.job_id)
        report = service.retry_render(command.job_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delete-artifact":
        command = DeleteRenderArtifactCommand(args.job_id)
        deleted = service.delete_render_artifact(command.job_id)
        print(json.dumps({"job_id": command.job_id, "deleted": deleted}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if deleted else 1
    if args.action == "collection":
        command = RenderCollectionCommand(
            collection_id=args.collection_id,
            profile=args.profile,
            output_root=args.output_root,
            explicit=args.explicit,
            allow_stale=args.allow_stale,
            continue_on_failure=args.continue_on_failure,
        )
        report = service.render_collection(
            command.collection_id,
            profile=command.profile,
            output_root=command.output_root,
            explicit=command.explicit,
            allow_stale=command.allow_stale,
            continue_on_failure=command.continue_on_failure,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "batch-show":
        command = ShowRenderBatchCommand(args.batch_id)
        batch = service.get_render_batch(command.batch_id)
        if batch is None:
            print("Batch de render no encontrado.", file=stderr)
            return 1
        items = service.list_batch_items(command.batch_id)
        payload = {"batch": batch.to_dict(), "items": [item.to_dict() for item in items]}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "batch-cancel":
        command = CancelRenderBatchCommand(args.batch_id)
        batch = service.cancel_render_batch(command.batch_id)
        if batch is None:
            print("Batch de render no encontrado.", file=stderr)
            return 1
        print(json.dumps(batch.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "batch-retry":
        command = RetryRenderBatchCommand(args.batch_id)
        report = service.retry_render_batch(command.batch_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-plan":
        command = ExportRenderPlanCommand(args.job_id, format=args.format, output=args.output)
        path = service.export_render_plan(command.job_id, destination=command.output)
        print(json.dumps({"job_id": command.job_id, "format": command.format, "path": str(path)}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "sidecar":
        command = RenderSidecarCommand(
            job_id=args.job_id,
            track_id=args.track_id,
            format=args.format,
            output=args.output,
            allow_stale=args.allow_stale,
            allow_overwrite=args.allow_overwrite,
            custom_name=args.custom_name,
        )
        report = service.create_sidecar_delivery(
            command.job_id,
            command.track_id,
            format_name=command.format,
            output=command.output,
            allow_stale=command.allow_stale,
            allow_overwrite=command.allow_overwrite,
            custom_name=command.custom_name,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "burn-in":
        command = RenderBurnInCommand(
            candidate_id=args.candidate_id,
            track_id=args.track_id,
            profile=args.profile,
            style=args.style,
            output=args.output,
            allow_stale=args.allow_stale,
            allow_overwrite=args.allow_overwrite,
            custom_name=args.custom_name,
        )
        report = service.create_burn_in_render(
            command.candidate_id,
            command.track_id,
            profile=command.profile,
            style_preset=command.style,
            output=command.output,
            allow_stale=command.allow_stale,
            allow_overwrite=command.allow_overwrite,
            custom_name=command.custom_name,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delivery-show":
        command = ShowRenderDeliveryCommand(args.delivery_id)
        delivery = service.get_delivery(command.delivery_id)
        if delivery is None:
            print("Entrega no encontrada.", file=stderr)
            return 1
        print(json.dumps(delivery.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delivery-list":
        command = ListRenderDeliveriesCommand(args.job_id)
        deliveries = service.list_render_deliveries(command.job_id)
        print(json.dumps([delivery.to_dict() for delivery in deliveries], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delivery-verify":
        command = VerifyRenderDeliveryCommand(args.delivery_id)
        report = service.verify_delivery(command.delivery_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if report.verification.verified else 1
    if args.action == "delivery-cancel":
        command = CancelRenderDeliveryCommand(args.delivery_id)
        delivery = service.cancel_delivery(command.delivery_id)
        if delivery is None:
            print("Entrega no encontrada.", file=stderr)
            return 1
        print(json.dumps(delivery.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delivery-retry":
        command = RetryRenderDeliveryCommand(args.delivery_id)
        report = service.retry_delivery(command.delivery_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "delivery-delete":
        command = DeleteRenderDeliveryCommand(args.delivery_id)
        deleted = service.delete_delivery(command.delivery_id)
        print(json.dumps({"delivery_id": command.delivery_id, "deleted": deleted}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0 if deleted else 1
    if args.action == "delivery-export-manifest":
        command = ExportRenderDeliveryManifestCommand(args.delivery_id, output=args.output)
        path = service.export_delivery_manifest(command.delivery_id, destination=command.output)
        print(json.dumps({"delivery_id": command.delivery_id, "path": str(path)}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de render no reconocida.")


def _handle_personalization(args, service: PersonalizationDatasetService, stdout, stderr) -> int:
    if args.action == "build":
        command = BuildCreatorDatasetCommand(args.creator_id, project_id=args.project_id, force=args.force)
        report = service.build_creator_dataset(command.creator_id, project_id=command.project_id, force=command.force)
        if args.json:
            _print_personalization_snapshot(report, stdout)
        else:
            print("Dataset de personalizacion construido", file=stdout)
            _print_personalization_snapshot(report, stdout)
        return 0
    if args.action == "show":
        command = ShowCreatorDatasetCommand(args.snapshot_id)
        report = service.get_dataset_snapshot(command.snapshot_id)
        if args.json:
            _print_personalization_snapshot(report, stdout)
        else:
            _print_personalization_snapshot(report, stdout)
        return 0
    if args.action == "latest":
        command = LatestCreatorDatasetCommand(args.creator_id)
        report = service.get_latest_creator_dataset(command.creator_id)
        if args.json:
            _print_personalization_snapshot(report, stdout)
        else:
            print("Snapshot mas reciente", file=stdout)
            _print_personalization_snapshot(report, stdout)
        return 0
    if args.action == "list":
        command = ListCreatorDatasetsCommand(args.creator_id)
        snapshots = service.list_creator_datasets(command.creator_id)
        if args.json:
            print(json.dumps([snapshot.to_dict() for snapshot in snapshots], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            for snapshot in snapshots:
                print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "examples":
        command = DatasetExamplesCommand(args.snapshot_id)
        examples = service.list_dataset_examples(command.snapshot_id)
        _print_personalization_examples(examples, stdout)
        return 0
    if args.action == "quality":
        command = DatasetQualityCommand(args.snapshot_id)
        report = service.get_dataset_quality_report(command.snapshot_id)
        _print_personalization_quality(report, stdout)
        return 0
    if args.action == "readiness":
        command = CreatorReadinessCommand(args.creator_id)
        report = service.get_creator_readiness(command.creator_id)
        _print_personalization_readiness(report, stdout)
        return 0
    if args.action == "compare":
        command = CompareDatasetSnapshotsCommand(args.snapshot_a, args.snapshot_b)
        report = service.compare_dataset_snapshots(command.snapshot_a_id, command.snapshot_b_id)
        _print_personalization_comparison(report, stdout)
        return 0
    if args.action == "archive":
        command = ArchiveDatasetSnapshotCommand(args.snapshot_id)
        snapshot = service.archive_dataset_snapshot(command.snapshot_id)
        if args.json:
            print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print("Snapshot archivado", file=stdout)
            print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        command = ExportDatasetCommand(args.snapshot_id, args.format)
        destination = Path(args.output) if args.output else None
        result = service.export_dataset(command.snapshot_id, command.format, include_sensitive=args.include_sensitive, destination=destination)
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print(f"Exportado: {result.path}", file=stdout)
        return 0
    raise ValueError("Accion de personalizacion no reconocida.")


def _handle_models(args, service: PersonalizationTrainingService, stdout, stderr) -> int:
    if args.action == "validate":
        command = ValidatePersonalizationSnapshotCommand(args.snapshot_id)
        report = service.validate_training_snapshot(command.snapshot_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_validation(report, stdout)
        return 0 if report.eligible else 1
    if args.action == "train":
        command = TrainPersonalizationModelCommand(args.snapshot_id, force=args.force)
        report = service.train_personalization_baseline(command.snapshot_id, force=command.force)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_training_report(report, stdout)
        return 0
    if args.action == "show":
        command = ShowPersonalizationModelRunCommand(args.run_id)
        run = service.get_training_run(command.run_id)
        if run is None:
            print("Training run no encontrado.", file=stderr)
            return 1
        print(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "list":
        command = ListPersonalizationModelRunsCommand(args.creator_id)
        runs = service.list_creator_training_runs(command.creator_id)
        print(json.dumps([run.to_dict() for run in runs], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "metrics":
        command = PersonalizationModelMetricsCommand(args.run_id)
        metrics = service.get_training_metrics(command.run_id)
        if args.json:
            print(json.dumps([metric.to_dict() for metric in metrics], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            for metric in metrics:
                print(json.dumps(metric.to_dict(), ensure_ascii=False, default=_json_default), file=stdout)
        return 0
    if args.action == "predictions":
        command = PersonalizationModelPredictionsCommand(args.run_id, split=args.split)
        predictions = service.list_training_predictions(command.run_id, split=command.split)
        if args.json:
            print(json.dumps([prediction.to_dict() for prediction in predictions], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_scores(predictions, stdout)
        return 0
    if args.action == "compare":
        command = ComparePersonalizationModelRunsCommand(args.baseline_run, args.candidate_run)
        report = service.compare_training_runs(command.baseline_run_id, command.candidate_run_id)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "activate":
        command = ActivatePersonalizationModelCommand(args.run_id)
        entry = service.activate_model(command.run_id)
        print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "deactivate":
        command = DeactivatePersonalizationModelCommand(args.run_id)
        entry = service.deactivate_model(command.run_id)
        print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout) if entry else print("Modelo no encontrado.", file=stderr)
        return 0 if entry else 1
    if args.action == "retire":
        command = RetirePersonalizationModelCommand(args.run_id)
        entry = service.retire_model(command.run_id)
        print(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout) if entry else print("Modelo no encontrado.", file=stderr)
        return 0 if entry else 1
    if args.action == "active":
        command = ActivePersonalizationModelCommand(args.creator_id, project_id=args.project_id)
        report = service.get_active_creator_model(command.creator_id, project_id=command.project_id)
        if report is None:
            print("No existe modelo activo.", file=stderr)
            return 1
        _print_model_active_report(report, stdout)
        return 0
    if args.action == "verify":
        command = VerifyPersonalizationModelCommand(args.run_id)
        report = service.verify_model_artifact(command.run_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_active_report(report, stdout)
        return 0 if report.artifact_verified else 1
    if args.action == "delete-artifact":
        command = DeletePersonalizationModelArtifactCommand(args.run_id)
        deleted = service.delete_model_artifact(command.run_id)
        print(json.dumps({"run_id": command.run_id, "deleted": deleted}, ensure_ascii=False, indent=2), file=stdout)
        return 0 if deleted else 1
    if args.action == "score-candidate":
        command = ScoreCandidateForCreatorCommand(args.creator_id, args.candidate_id)
        report = service.score_candidate_for_creator(command.creator_id, command.candidate_id)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_score(report, stdout)
        return 0
    if args.action == "score-video":
        command = ScoreVideoForCreatorCommand(args.creator_id, args.video_id)
        scores = service.score_candidates_for_video(command.creator_id, command.video_id)
        if args.json:
            print(json.dumps([score.to_dict() for score in scores], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            _print_model_scores(scores, stdout)
        return 0
    if args.action == "explain":
        command = ExplainPersonalizedScoreCommand(args.creator_id, args.candidate_id)
        explanation = service.explain_personalized_score(command.creator_id, command.candidate_id)
        print(json.dumps(explanation, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de modelos no reconocida.")


def _handle_evaluation(args, service: OperationalEvaluationService, stdout, stderr) -> int:
    if args.action == "scenarios":
        scenarios = service.list_scenarios()
        payload = [scenario.to_dict() for scenario in scenarios]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "run":
        command = RunOperationalEvaluationCommand(args.scenario, force=args.force)
        report = service.run_scenario(command.scenario_id, force=command.force)
        payload = report.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print(build_evaluation_text(report), file=stdout)
        return 0 if report.run.status not in {OperationalEvaluationRunStatus.FAILED, OperationalEvaluationRunStatus.CANCELLED, OperationalEvaluationRunStatus.BLOCKED} else 1
    if args.action == "show":
        command = ShowOperationalEvaluationCommand(args.run_id)
        report = service.get_report(command.run_id)
        if report is None:
            print("Run de evaluacion no encontrado.", file=stderr)
            return 1
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "stages":
        command = StageOperationalEvaluationCommand(args.run_id)
        stages = service.list_stages(command.run_id)
        print(json.dumps([stage.to_dict() for stage in stages], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "metrics":
        command = StageOperationalEvaluationCommand(args.run_id)
        metrics = service.list_metrics(command.run_id)
        print(json.dumps([metric.to_dict() for metric in metrics], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "assertions":
        command = StageOperationalEvaluationCommand(args.run_id)
        assertions = service.list_assertions(command.run_id)
        if args.severity:
            assertions = [item for item in assertions if item.severity.value == args.severity]
        print(json.dumps([assertion.to_dict() for assertion in assertions], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "artifacts":
        command = StageOperationalEvaluationCommand(args.run_id)
        artifacts = service.list_artifacts(command.run_id)
        print(json.dumps([artifact.to_dict() for artifact in artifacts], ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "retry-stage":
        command = RetryOperationalEvaluationStageCommand(args.run_id, args.stage)
        report = service.retry_stage(command.run_id, command.stage_name)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "cancel":
        command = CancelOperationalEvaluationCommand(args.run_id)
        cancelled = service.cancel(command.run_id)
        print(json.dumps({"run_id": command.run_id, "cancelled": cancelled}, ensure_ascii=False, indent=2), file=stdout)
        return 0 if cancelled else 1
    if args.action == "export":
        command = ExportOperationalEvaluationCommand(args.run_id, args.format)
        destination = Path(args.output) if args.output else None
        path = service.export(command.run_id, command.format, destination=destination)
        payload = {"run_id": command.run_id, "format": command.format, "path": str(path)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "clean":
        command = CleanOperationalEvaluationCommand(args.run_id, dry_run=args.dry_run)
        payload = service.clean(command.run_id, dry_run=command.dry_run)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de evaluacion no reconocida.")


def _handle_experiments(args, service: ExperimentService, stdout, stderr) -> int:
    if args.action == "list":
        command = ListExperimentsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_experiments(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "create":
        command = CreateExperimentCommand(
            args.creator_id,
            args.name,
            args.description,
            args.experiment_type,
            args.hypothesis,
            args.rationale,
            args.primary_metric_key,
            args.expected_direction,
            args.minimum_sample_size,
            platform=args.platform,
            content_type=args.content_type,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        payload = service.create_experiment(
            creator_id=command.creator_id,
            name=command.name,
            description=command.description,
            experiment_type=command.experiment_type,
            hypothesis=command.hypothesis,
            rationale=command.rationale,
            primary_metric_key=command.primary_metric_key,
            expected_direction=command.expected_direction,
            minimum_sample_size=command.minimum_sample_size,
            platform=command.platform,
            content_type=command.content_type,
            start_date=command.start_date,
            end_date=command.end_date,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "show":
        command = ShowExperimentCommand(args.experiment_id)
        payload = service.get_experiment(command.experiment_id)
        if payload is None:
            print("Experimento no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "update":
        command = UpdateExperimentCommand(args.experiment_id)
        changes = {
            key: value
            for key, value in {
                "name": args.name,
                "description": args.description,
                "experiment_type": args.experiment_type,
                "status": args.status,
                "hypothesis": args.hypothesis,
                "rationale": args.rationale,
                "primary_metric_key": args.primary_metric_key,
                "expected_direction": args.expected_direction,
                "minimum_sample_size": args.minimum_sample_size,
                "platform": args.platform,
                "content_type": args.content_type,
                "start_date": args.start_date,
                "end_date": args.end_date,
            }.items()
            if value is not None
        }
        payload = service.update_experiment(command.experiment_id, **changes)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "archive":
        command = ArchiveExperimentCommand(args.experiment_id)
        payload = service.archive_experiment(command.experiment_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "variable-add":
        command = AddExperimentVariableCommand(
            args.experiment_id,
            args.variable_key,
            args.variable_type,
            args.description,
            args.control_value_json,
            args.treatment_value_json,
            args.allowed_values_json,
        )
        payload = service.add_variable(
            experiment_id=command.experiment_id,
            variable_key=command.variable_key,
            variable_type=command.variable_type,
            description=command.description,
            control_value_json=command.control_value_json,
            treatment_value_json=command.treatment_value_json,
            allowed_values_json=command.allowed_values_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "guardrail-add":
        command = AddExperimentGuardrailCommand(
            args.experiment_id,
            args.metric_key,
            args.comparison_operator,
            args.description,
            threshold_value=args.threshold_value,
            allowed_change=args.allowed_change,
        )
        payload = service.add_guardrail(
            experiment_id=command.experiment_id,
            metric_key=command.metric_key,
            comparison_operator=command.comparison_operator,
            threshold_value=command.threshold_value,
            allowed_change=command.allowed_change,
            description=command.description,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "assign":
        command = AssignExperimentCommand(
            args.experiment_id,
            args.publication_id,
            args.variant,
            actual_variant=args.actual_variant,
            notes=args.notes,
        )
        payload = service.assign_publication(
            experiment_id=command.experiment_id,
            publication_id=command.publication_id,
            variant=command.variant,
            actual_variant=command.actual_variant,
            notes=command.notes,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "execution-record":
        command = RecordExecutionCommand(
            args.creator_id,
            args.recommendation_id,
            args.experiment_assignment_id,
            args.publication_id,
            args.execution_status,
            args.executed_value_json,
            args.deviation_from_recommendation_json,
        )
        payload = service.record_execution(
            creator_id=command.creator_id,
            recommendation_id=command.recommendation_id,
            experiment_assignment_id=command.experiment_assignment_id,
            publication_id=command.publication_id,
            execution_status=command.execution_status,
            executed_value_json=command.executed_value_json,
            deviation_from_recommendation_json=command.deviation_from_recommendation_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "evaluate":
        command = EvaluateExperimentCommand(args.experiment_id)
        payload = service.evaluate_experiment(command.experiment_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "evaluation-show":
        command = ShowExperimentEvaluationCommand(args.evaluation_id)
        payload = service.get_evaluation_detail(command.evaluation_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report":
        command = GenerateExperimentReportCommand(args.experiment_id, evaluation_id=args.evaluation_id)
        payload = service.generate_report(command.experiment_id, command.evaluation_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report-export":
        command = ExportExperimentReportCommand(args.report_id, args.format)
        payload = {
            "report_id": command.report_id,
            "format": command.format,
            "path": str(service.export_report(command.report_id, command.format)),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de experiments no reconocida.")


def _handle_recommendations(args, service: ExperimentService, stdout, stderr) -> int:
    if args.action == "list":
        command = ListRecommendationsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_recommendations(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "create":
        command = CreateRecommendationCommand(
            args.creator_id,
            args.source_type,
            args.source_id,
            args.recommendation_type,
            args.title,
            args.recommendation_text,
            args.evidence_json,
            args.confidence_level,
            platform=args.platform,
            content_type=args.content_type,
        )
        payload = service.create_recommendation(
            creator_id=command.creator_id,
            source_type=command.source_type,
            source_id=command.source_id,
            recommendation_type=command.recommendation_type,
            title=command.title,
            recommendation_text=command.recommendation_text,
            evidence_json=command.evidence_json,
            confidence_level=command.confidence_level,
            platform=command.platform,
            content_type=command.content_type,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "show":
        command = ShowRecommendationCommand(args.recommendation_id)
        payload = service.get_recommendation(command.recommendation_id)
        if payload is None:
            print("Recomendacion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "decide":
        command = DecideRecommendationCommand(
            args.recommendation_id,
            args.decision,
            args.reason,
            modified_value_json=args.modified_value_json,
        )
        payload = service.decide_recommendation(
            command.recommendation_id,
            decision=command.decision,
            reason=command.reason,
            modified_value_json=command.modified_value_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de recommendations no reconocida.")


def _handle_learnings(args, service: ExperimentService, stdout, stderr) -> int:
    if args.action == "list":
        command = ListLearningsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_learnings(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "show":
        command = ShowLearningCommand(args.learning_id)
        payload = service.get_learning(command.learning_id)
        if payload is None:
            print("Aprendizaje no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "confirm":
        command = ConfirmLearningCommand(args.learning_id)
        payload = service.confirm_learning(command.learning_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "reject":
        command = RejectLearningCommand(args.learning_id)
        payload = service.reject_learning(command.learning_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "needs-more-data":
        command = NeedsMoreDataLearningCommand(args.learning_id)
        payload = service.needs_more_data(command.learning_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "deprecate":
        command = DeprecateLearningCommand(args.learning_id)
        payload = service.deprecate_learning(command.learning_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de learnings no reconocida.")


def _handle_creator_memory(args, service: CreatorMemoryService, stdout, stderr) -> int:
    if args.action == "profile":
        command = CreatorMemoryProfileCommand(args.creator_id)
        payload = service.get_profile_detail(command.creator_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile-update":
        command = UpdateCreatorMemoryProfileCommand(args.creator_id)
        payload = service.update_creator_profile(
            creator_id=command.creator_id,
            display_name=args.display_name,
            summary=args.summary,
            primary_language=args.primary_language,
            secondary_languages=args.secondary_languages_json,
            default_tone=args.default_tone,
            default_formality=args.default_formality,
            objectives=args.objectives_json,
            status=args.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "traits":
        command = ListCreatorTraitsCommand(args.creator_id)
        payload = [
            item.to_dict()
            for item in service.list_traits(
                command.creator_id,
                filters={
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "topic": args.topic,
                    "trait_type": args.trait_type,
                    "status": args.status,
                    "confidence_level": args.confidence_level,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "trait-create":
        command = CreateCreatorTraitCommand(args.creator_id, args.trait_type, args.trait_key, args.display_name)
        payload = service.create_trait(
            creator_id=command.creator_id,
            trait_type=command.trait_type,
            trait_key=command.trait_key,
            display_name=command.display_name,
            description=args.description,
            value_json=args.value_json,
            scope=args.scope,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            confidence_level=args.confidence_level,
            confidence_score=args.confidence_score,
            status=args.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "trait-show":
        command = ShowCreatorTraitCommand(args.trait_id)
        payload = service.get_trait(command.trait_id)
        if payload is None:
            print("Trait no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "trait-update":
        command = UpdateCreatorTraitCommand(args.trait_id)
        changes = {
            key: value
            for key, value in {
                "trait_type": args.trait_type,
                "trait_key": args.trait_key,
                "display_name": args.display_name,
                "description": args.description,
                "value_json": args.value_json,
                "scope": args.scope,
                "platform": args.platform,
                "content_type": args.content_type,
                "topic": args.topic,
                "confidence_level": args.confidence_level,
                "confidence_score": args.confidence_score,
                "status": args.status,
            }.items()
            if value is not None
        }
        payload = service.update_trait(command.trait_id, **changes)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "trait-evidence-add":
        command = AddCreatorTraitEvidenceCommand(args.trait_id, args.source_type)
        payload = service.add_trait_evidence(
            trait_id=command.trait_id,
            source_type=command.source_type,
            source_id=args.source_id,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            transcript_segment_id=args.transcript_segment_id,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
            quoted_text=args.quoted_text,
            evidence_type=args.evidence_type,
            supports_trait=args.supports_trait,
            weight=args.weight,
            notes=args.notes,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "examples":
        command = ListCreatorExamplesCommand(args.creator_id)
        payload = [
            item.to_dict()
            for item in service.list_examples(
                command.creator_id,
                filters={
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "topic": args.topic,
                    "example_type": args.example_type,
                    "approval_status": args.approval_status,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "example-create":
        command = CreateCreatorExampleCommand(args.creator_id, args.example_type, args.category, args.title, args.source_type)
        payload = service.create_example(
            creator_id=command.creator_id,
            example_type=command.example_type,
            category=command.category,
            title=command.title,
            source_type=command.source_type,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            text_content=args.text_content,
            source_id=args.source_id,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
            representativeness=args.representativeness,
            approval_status=args.approval_status,
            approval_reason=args.approval_reason,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "example-review":
        command = ReviewCreatorExampleCommand(args.example_id, args.approval_status, reason=args.reason)
        payload = service.review_example(command.example_id, approval_status=command.approval_status, reason=command.reason)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "vocabulary":
        command = ListCreatorVocabularyCommand(args.creator_id)
        payload = [
            item.to_dict()
            for item in service.list_vocabulary(
                command.creator_id,
                filters={
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "vocabulary_type": args.vocabulary_type,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "vocabulary-add":
        command = CreateCreatorVocabularyCommand(args.creator_id, args.term, args.vocabulary_type)
        payload = service.create_vocabulary_entry(
            creator_id=command.creator_id,
            term=command.term,
            vocabulary_type=command.vocabulary_type,
            meaning=args.meaning,
            usage_notes=args.usage_notes,
            platform=args.platform,
            content_type=args.content_type,
            confidence_level=args.confidence_level,
            frequency_count=args.frequency_count,
            status=args.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "rules":
        command = ListCreatorRulesCommand(args.creator_id)
        payload = [
            item.to_dict()
            for item in service.list_style_rules(
                command.creator_id,
                filters={
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "topic": args.topic,
                    "status": args.status,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "rule-create":
        command = CreateCreatorRuleCommand(args.creator_id, args.rule_type, args.statement)
        payload = service.create_style_rule(
            creator_id=command.creator_id,
            rule_type=command.rule_type,
            statement=command.statement,
            scope=args.scope,
            rationale=args.rationale,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            confidence_level=args.confidence_level,
            status=args.status,
            supporting_example_count=args.supporting_example_count,
            contradicting_example_count=args.contradicting_example_count,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "rule-review":
        command = ReviewCreatorRuleCommand(args.rule_id, args.decision, args.reason)
        payload = service.review_style_rule(
            command.rule_id,
            decision=command.decision,
            reason=command.reason,
            previous_statement=args.previous_statement,
            new_statement=args.new_statement,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "limits":
        command = ListCreatorLimitsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_limits(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "limit-create":
        command = CreateCreatorLimitCommand(args.creator_id, args.limit_type, args.category, args.statement)
        payload = service.create_limit(
            creator_id=command.creator_id,
            limit_type=command.limit_type,
            category=command.category,
            statement=command.statement,
            severity=args.severity,
            scope=args.scope,
            platform=args.platform,
            status=args.status,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "limit-update":
        command = UpdateCreatorLimitCommand(args.limit_id, args.creator_id)
        changes = {
            key: value
            for key, value in {
                "limit_type": args.limit_type,
                "category": args.category,
                "statement": args.statement,
                "severity": args.severity,
                "scope": args.scope,
                "platform": args.platform,
                "status": args.status,
            }.items()
            if value is not None
        }
        payload = service.update_limit(command.limit_id, creator_id=command.creator_id, **changes)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "snapshots":
        command = ListCreatorSnapshotsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_profile_snapshots(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "snapshot-create":
        command = CreateCreatorSnapshotCommand(args.creator_id)
        payload = service.create_profile_snapshot(command.creator_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "snapshot-compare":
        command = CompareCreatorSnapshotsCommand(args.creator_id, args.base_snapshot_id, args.compare_snapshot_id)
        payload = service.compare_profile_snapshots(command.creator_id, command.base_snapshot_id, command.compare_snapshot_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "retrieve":
        command = RetrieveCreatorMemoryCommand(args.creator_id)
        payload = [
            item.to_dict()
            for item in service.retrieve_creator_context(
                command.creator_id,
                {
                    "query": args.query,
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "topic": args.topic,
                    "trait_type": args.trait_type,
                    "example_type": args.example_type,
                    "approval_status": args.approval_status,
                    "confidence_level": args.confidence_level,
                    "status": args.status,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "feedback":
        command = RecordCreatorMemoryFeedbackCommand(args.creator_id, args.target_type, args.target_id, args.feedback_type, args.reason)
        payload = service.record_memory_feedback(
            creator_id=command.creator_id,
            target_type=command.target_type,
            target_id=command.target_id,
            feedback_type=command.feedback_type,
            reason=command.reason,
            corrected_value_json=args.corrected_value_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de creator-memory no reconocida.")


def _handle_creator_language(args, service: CreatorLanguageService, stdout, stderr) -> int:
    if args.action == "corpora":
        payload = [item.to_dict() for item in service.list_corpora(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "corpus-create":
        payload = service.create_corpus(
            creator_id=args.creator_id,
            name=args.name,
            description=args.description,
            language=args.language,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "corpus-show":
        payload = service.get_corpus(args.corpus_id)
        if payload is None:
            print("Corpus no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "corpus-source-add":
        payload = service.add_corpus_source(
            corpus_id=args.corpus_id,
            source_type=args.source_type,
            source_id=args.source_id,
            text_snapshot=args.text_snapshot,
            language=args.language,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            include_status=args.include_status,
            exclusion_reason=args.exclusion_reason,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "corpus-source-remove":
        payload = service.remove_corpus_source(args.source_id, reason=args.reason)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "analyze":
        payload = service.analyze_corpus(args.corpus_id, force_recompute=True)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "analysis-show":
        payload = service.get_analysis_detail(args.run_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "metrics":
        payload = [item.to_dict() for item in service.list_metrics(args.run_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "patterns":
        payload = [item.to_dict() for item in service.list_patterns(args.creator_id, args.run_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "pattern-show":
        payload = service.get_pattern(args.pattern_id)
        if payload is None:
            print("Patron no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile":
        payload = service.get_profile_detail(args.creator_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile-history":
        payload = [item.to_dict() for item in service.list_profile_history(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "profile-compare":
        payload = service.compare_profile_versions(args.creator_id, args.base_profile_version, args.compare_profile_version)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "candidates":
        payload = [item.to_dict() for item in service.list_candidates(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "candidate-review":
        payload = service.review_candidate(
            args.candidate_id,
            decision=args.decision,
            reason=args.reason,
            modified_value_json=args.modified_value_json,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "retrieve":
        payload = [
            item.to_dict()
            for item in service.retrieve_creator_context(
                args.creator_id,
                {
                    "query": args.query,
                    "platform": args.platform,
                    "content_type": args.content_type,
                    "topic": args.topic,
                    "trait_type": args.trait_type,
                    "example_type": args.example_type,
                    "approval_status": args.approval_status,
                    "confidence_level": args.confidence_level,
                    "status": args.status,
                },
            )
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        payload = service.export(creator_id=args.creator_id, format_name=args.format, summary=args.summary)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de creator-language no reconocida.")


def _handle_packaging(args, service: CreativePackagingService, stdout, stderr) -> int:
    if args.action == "assets":
        payload = [item.to_dict() for item in service.list_assets(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "asset-show":
        asset = service.get_asset(args.asset_id)
        if asset is None:
            print("Asset no encontrado.", file=stderr)
            return 1
        print(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "brand-profile":
        detail = service.get_brand_profile_detail(args.creator_id)
        print(json.dumps(detail.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "brand-profile-build":
        payload = service.build_brand_profile(args.creator_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "brand-profile-history":
        payload = [item.to_dict() for item in service.list_brand_profiles(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "references":
        payload = [item.to_dict() for item in service.list_reference_assets(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "reference-add":
        payload = service.add_reference_asset(
            creator_id=args.creator_id,
            reference_type=args.reference_type,
            image_path=args.image_path,
            text_content=args.text_content,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            source_type=args.source_type,
            source_creator_name=args.source_creator_name,
            source_url=args.source_url,
            usage_permission=args.usage_permission,
            represents_creator=args.represents_creator,
            approval_status=args.approval_status,
            reference_purpose=args.reference_purpose,
            notes=args.notes,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "reference-show":
        payload = service.get_reference_asset(args.reference_id)
        if payload is None:
            print("Referencia no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "reference-review":
        payload = service.review_reference_asset(args.reference_id, approval_status=args.approval_status, notes=args.notes)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "titles":
        payload = [title.to_dict() for asset in service.list_assets(args.creator_id) for title in service.list_title_versions(asset.id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "title-create":
        payload = service.create_title_version(
            creator_id=args.creator_id,
            title_text=args.title_text,
            platform=args.platform,
            content_type=args.content_type,
            source_type=args.source_type,
            language=args.language,
            topic=args.topic,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            packaging_asset_id=args.packaging_asset_id,
            is_published=args.is_published,
            is_selected=args.is_selected,
            creator_approval_status=args.creator_approval_status,
            creator_feedback=args.creator_feedback,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "title-show":
        payload = service.get_title_version(args.title_id)
        if payload is None:
            print("Titulo no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "title-analyze":
        payload = service.analyze_title(args.title_id, force_recompute=True)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "title-compare":
        base = service.get_title_version(args.base_title_id)
        compare = service.get_title_version(args.compare_title_id)
        if base is None or compare is None:
            print("Titulo no encontrado.", file=stderr)
            return 1
        base_detail = service.analyze_title(base.id, force_recompute=False)
        compare_detail = service.analyze_title(compare.id, force_recompute=False)
        base_metrics = {item.metric_key: item.numeric_value for item in base_detail.metrics}
        compare_metrics = {item.metric_key: item.numeric_value for item in compare_detail.metrics}
        comparison = {
            metric_key: {
                "base": base_metrics.get(metric_key),
                "compare": compare_metrics.get(metric_key),
                "delta": (
                    compare_metrics.get(metric_key) - base_metrics.get(metric_key)
                    if isinstance(base_metrics.get(metric_key), (int, float)) and isinstance(compare_metrics.get(metric_key), (int, float))
                    else None
                ),
            }
            for metric_key in sorted(set(base_metrics) | set(compare_metrics))
        }
        print(
            json.dumps(
                {"base": base_detail.to_dict(), "compare": compare_detail.to_dict(), "comparison": comparison},
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            ),
            file=stdout,
        )
        return 0
    if args.action == "thumbnails":
        payload = [thumbnail.to_dict() for asset in service.list_assets(args.creator_id) for thumbnail in service.list_thumbnail_versions(asset.id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "thumbnail-create":
        payload = service.create_thumbnail_version(
            creator_id=args.creator_id,
            image_path=args.image_path,
            source_type=args.source_type,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            packaging_asset_id=args.packaging_asset_id,
            concept_id=args.concept_id,
            is_published=args.is_published,
            is_selected=args.is_selected,
            creator_approval_status=args.creator_approval_status,
            creator_feedback=args.creator_feedback,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "thumbnail-show":
        payload = service.get_thumbnail_version(args.thumbnail_id)
        if payload is None:
            print("Miniatura no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "thumbnail-analyze":
        payload = service.analyze_thumbnail(args.thumbnail_id, force_recompute=True)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "pair-evaluate":
        payload = service.evaluate_pair(
            title_version_id=args.title_id,
            thumbnail_version_id=args.thumbnail_id,
            publication_id=args.publication_id,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "pair-show":
        payload = service.get_pair_evaluation(args.evaluation_id)
        if payload is None:
            print("Evaluacion no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "frames":
        payload = [item.to_dict() for item in service.list_frame_candidates(args.creator_id, video_asset_id=args.video_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "frame-extract":
        timestamps = json.loads(args.timestamps_json) if args.timestamps_json else None
        payload = [item.to_dict() for item in service.extract_frame_candidates(creator_id=args.creator_id, video_asset_id=args.video_id, timestamps=timestamps)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "frame-review":
        service.record_decision(
            creator_id=args.creator_id,
            target_type="thumbnail_frame_candidate",
            target_id=args.frame_id,
            decision=args.decision,
            reason="CLI review",
        )
        print(json.dumps({"frame_id": args.frame_id, "decision": args.decision}, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "concepts":
        payload = [item.to_dict() for item in service.list_concepts(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "concept-create":
        payload = service.build_concepts(
            creator_id=args.creator_id,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            title=args.title,
            objective=args.objective,
            audience=args.audience,
            concept_type=args.concept_type,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "concept-build":
        references = json.loads(args.references_json) if args.references_json else None
        constraints = json.loads(args.constraints_json) if args.constraints_json else None
        payload = service.build_concepts(
            creator_id=args.creator_id,
            platform=args.platform,
            content_type=args.content_type,
            topic=args.topic,
            title=args.title,
            objective=args.objective,
            audience=args.audience,
            concept_type=args.concept_type,
            publication_id=args.publication_id,
            video_asset_id=args.video_asset_id,
            references=references,
            constraints=constraints,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "concept-show":
        payload = service.get_concept(args.concept_id)
        if payload is None:
            print("Concepto no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "prompt-build":
        payload = service.build_prompt(concept_id=args.concept_id, target_tool=args.target_tool, title=args.title)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "prompt-show":
        payload = service.get_prompt(args.prompt_id)
        if payload is None:
            print("Prompt no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "prompt-references":
        payload = [item.to_dict() for item in service.list_prompt_references(args.prompt_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "prompt-export":
        prompt = service.get_prompt(args.prompt_id)
        if prompt is None:
            print("Prompt no encontrado.", file=stderr)
            return 1
        payload = {
            "prompt": prompt.to_dict(),
            "references": [item.to_dict() for item in service.list_prompt_references(args.prompt_id)],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "review-thumbnail":
        payload = service.review_thumbnail(
            thumbnail_version_id=args.thumbnail_id,
            title_version_id=args.title_id,
            publication_id=args.publication_id,
            concept_id=args.concept_id,
            prompt_id=args.prompt_id,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "review-show":
        payload = service.get_thumbnail_review(args.review_id)
        if payload is None:
            print("Revision no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "review-revision-instructions":
        payload = service.get_thumbnail_review(args.review_id)
        if payload is None:
            print("Revision no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "decisions":
        payload = [item.to_dict() for item in service.list_decisions(args.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export":
        payload = service.export(creator_id=args.creator_id, format_name=args.format, summary=args.summary)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de packaging no reconocida.")


def _handle_analytics(args, service: AnalyticsImportService, lab_service: AnalyticsLabService | None, stdout, stderr) -> int:
    if args.action == "platforms":
        command = ListAnalyticsPlatformsCommand()
        payload = [platform.to_dict() for platform in service.list_platforms()]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "channels":
        command = ListAnalyticsChannelsCommand(args.creator_id)
        payload = [channel.to_dict() for channel in service.list_channels(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "channel-create":
        command = CreateAnalyticsChannelCommand(
            args.creator_id,
            args.platform,
            args.name,
            external_channel_id=args.external_channel_id,
            channel_url=args.channel_url,
            timezone_name=args.timezone,
            is_primary=args.primary,
        )
        channel = service.create_channel(
            creator_id=command.creator_id,
            platform=command.platform,
            name=command.name,
            external_channel_id=command.external_channel_id,
            channel_url=command.channel_url,
            timezone_name=command.timezone_name,
            is_primary=command.is_primary,
        )
        print(json.dumps(channel.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "imports":
        command = ListAnalyticsImportsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_imports(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "import-csv":
        command = ImportAnalyticsCsvCommand(
            args.creator_id,
            Path(args.file),
            channel_id=args.channel_id,
            platform=args.platform,
            mapping_name=args.mapping_name,
            delimiter=args.delimiter,
        )
        result = service.import_csv(
            creator_id=command.creator_id,
            file=command.file,
            channel_id=command.channel_id,
            platform=command.platform,
            mapping_name=command.mapping_name,
            delimiter=command.delimiter,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "import-excel":
        command = ImportAnalyticsExcelCommand(
            args.creator_id,
            Path(args.file),
            channel_id=args.channel_id,
            platform=args.platform,
            sheet_name=args.sheet_name,
            mapping_name=args.mapping_name,
        )
        result = service.import_excel(
            creator_id=command.creator_id,
            file=command.file,
            channel_id=command.channel_id,
            platform=command.platform,
            sheet_name=command.sheet_name,
            mapping_name=command.mapping_name,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "inspect-file":
        command = InspectAnalyticsFileCommand(Path(args.file), sheet_name=args.sheet_name)
        payload = service.inspect_file(command.file, sheet_name=command.sheet_name)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "detect-schema":
        command = DetectAnalyticsSchemaCommand(Path(args.file), sheet_name=args.sheet_name)
        payload = service.detect_schema(command.file, sheet_name=command.sheet_name)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "mappings":
        command = ListAnalyticsMappingsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_mappings(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "mapping-save":
        command = SaveAnalyticsMappingCommand(
            args.creator_id,
            args.platform,
            args.mapping_name,
            args.source_field,
            args.target_field,
            transformation=args.transformation,
            confidence=args.confidence,
            active=not args.inactive,
        )
        payload = service.save_mapping(
            creator_id=command.creator_id,
            platform=command.platform,
            mapping_name=command.mapping_name,
            source_field=command.source_field,
            target_field=command.target_field,
            transformation=command.transformation,
            confidence=command.confidence,
            active=command.active,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "publications":
        command = ListAnalyticsPublicationsCommand(args.creator_id)
        payload = [item.to_dict() for item in service.list_publications(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "publication-show":
        command = ShowAnalyticsPublicationCommand(args.publication_id)
        publication = service.get_publication(command.publication_id)
        if publication is None:
            print("Publicacion no encontrada.", file=stderr)
            return 1
        print(json.dumps(publication.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "publication-metrics":
        command = PublicationMetricsCommand(args.publication_id)
        payload = {metric_key: snapshot.to_dict() for metric_key, snapshot in service.get_latest_metrics(command.publication_id).items()}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "import-show":
        command = ShowAnalyticsImportCommand(args.import_id)
        import_record = service.get_import(command.import_id)
        if import_record is None:
            print("Importacion no encontrada.", file=stderr)
            return 1
        print(json.dumps(import_record.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "import-rows":
        command = ListAnalyticsImportRowsCommand(args.import_id)
        payload = [item.to_dict() for item in service.get_import_rows(command.import_id, status=args.status)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "export-normalized":
        command = ExportNormalizedAnalyticsCommand(args.creator_id, args.format)
        payload = service.export_normalized_data(creator_id=command.creator_id, format_name=command.format)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "cohorts":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ListAnalyticsCohortsCommand(args.creator_id)
        payload = [item.to_dict() for item in lab_service.list_cohorts(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "cohort-create":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = CreateAnalyticsCohortCommand(
            args.creator_id,
            args.name,
            args.description,
            platform=args.platform,
            content_type=args.content_type,
            date_from=args.date_from,
            date_to=args.date_to,
            duration_min_seconds=args.duration_min_seconds,
            duration_max_seconds=args.duration_max_seconds,
            topic=args.topic,
            format=args.format,
            language=args.language,
            channel_id=args.channel_id,
            linked=args.linked,
        )
        payload = lab_service.create_cohort(
            creator_id=command.creator_id,
            name=command.name,
            description=command.description,
            platform=command.platform,
            content_type=command.content_type,
            date_from=command.date_from,
            date_to=command.date_to,
            duration_min_seconds=command.duration_min_seconds,
            duration_max_seconds=command.duration_max_seconds,
            topic=command.topic,
            format=command.format,
            language=command.language,
            channel_id=command.channel_id,
            linked=command.linked,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "cohort-show":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ShowAnalyticsCohortCommand(args.cohort_id)
        payload = lab_service.get_cohort(command.cohort_id)
        if payload is None:
            print("Cohorte no encontrada.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "cohort-analyze":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = AnalyzeAnalyticsCohortCommand(args.cohort_id)
        payload = lab_service.analyze_cohort(command.cohort_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "compare-publication":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = CompareAnalyticsPublicationCommand(args.publication_id, args.cohort_id)
        payload = lab_service.compare_publication(command.publication_id, command.cohort_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "analysis-show":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ShowAnalyticsAnalysisCommand(args.run_id)
        payload = lab_service.get_analysis_detail(command.run_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "findings":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ListAnalyticsFindingsCommand(args.creator_id)
        payload = [item.to_dict() for item in lab_service.list_findings(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "finding-show":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ShowAnalyticsFindingCommand(args.finding_id)
        payload = lab_service.get_finding(command.finding_id)
        if payload is None:
            print("Finding no encontrado.", file=stderr)
            return 1
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "finding-confirm":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ConfirmAnalyticsFindingCommand(args.finding_id)
        payload = lab_service.confirm_finding(command.finding_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "finding-reject":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = RejectAnalyticsFindingCommand(args.finding_id)
        payload = lab_service.reject_finding(command.finding_id)
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "weekly-report":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = GenerateAnalyticsWeeklyReportCommand(args.creator_id, args.period_start, args.period_end)
        payload = lab_service.generate_weekly_report(
            creator_id=command.creator_id,
            period_start=command.period_start,
            period_end=command.period_end,
        )
        print(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "reports":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ListAnalyticsReportsCommand(args.creator_id)
        payload = [item.to_dict() for item in lab_service.list_reports(command.creator_id)]
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report-show":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ShowAnalyticsReportCommand(args.report_id)
        payload = lab_service.get_report_detail(command.report_id)
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    if args.action == "report-export":
        if lab_service is None:
            raise DomainError("El servicio de analytics lab no esta disponible.")
        command = ExportAnalyticsReportCommand(args.report_id, args.format)
        path = lab_service.export_report(command.report_id, command.format)
        payload = {"report_id": command.report_id, "format": command.format, "path": str(path)}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), file=stdout)
        return 0
    raise ValueError("Accion de analytics no reconocida.")


def build_evaluation_text(report) -> str:
    lines = [
        f"Escenario: {report.scenario.id}",
        f"Run: {report.run.id}",
        f"Estado: {report.run.status.value}",
        f"Resultado final: {report.run.final_result.value}",
        f"Duracion total: {report.run.total_duration_seconds if report.run.total_duration_seconds is not None else 'no verificada'}",
        f"Etapas: {report.run.completed_stage_count}/{report.run.stage_count}",
        f"Assertions: {report.run.assertion_pass_count} OK / {report.run.assertion_fail_count} fallidas",
        f"Cache: {report.run.cache_hit_count} hits / {report.run.cache_miss_count} misses",
    ]
    for stage in report.stages:
        lines.append(f"- {stage.stage_index}. {stage.stage_name}: {stage.status.value} [{stage.cache_status.value}]")
    return "\n".join(lines)


def dispatch(
    args: argparse.Namespace,
    *,
    service: CatalogService,
    media_service: MediaInspectionService,
    audio_service: AudioPreparationService,
    transcription_service: TranscriptionService,
    acoustic_service: AcousticAnalysisService,
    visual_service: VisualAnalysisService,
    multimodal_service: MultimodalAnalysisService,
    clip_service: ClipRankingService,
    youtube_service: YouTubeIntegrationService | None = None,
    audience_service: AudienceModelService | None = None,
    analytics_service: AnalyticsImportService | None = None,
    analytics_lab_service: AnalyticsLabService | None = None,
    experiment_service: ExperimentService | None = None,
    creator_memory_service: CreatorMemoryService | None = None,
    creator_language_service: CreatorLanguageService | None = None,
    packaging_service: CreativePackagingService | None = None,
    render_service: ClipRenderService | None = None,
    subtitle_service: SubtitleService | None = None,
    personalization_service: PersonalizationDatasetService | None = None,
    diagnostic: EnvironmentDiagnostic,
    stdout=None,
    stderr=None,
    model_service: PersonalizationTrainingService | None = None,
    evaluation_service: OperationalEvaluationService | None = None,
) -> int:
    """Ejecuta el comando solicitado."""

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    try:
        if args.diagnostic_json:
            print(diagnostic.to_json(), file=stdout)
            return 0 if diagnostic.state.ready_for_basic_mode else 1
        if args.entity is None:
            render_diagnostic_summary(diagnostic, stdout)
            return 0 if diagnostic.state.ready_for_basic_mode else 1
        if args.entity == "creator":
            return _handle_creator(args, service, stdout)
        if args.entity == "project":
            return _handle_project(args, service, stdout)
        if args.entity == "video":
            return _handle_video(args, service, stdout)
        if args.entity == "media":
            return _handle_media(args, media_service, stdout)
        if args.entity == "audio":
            return _handle_audio(args, audio_service, stdout)
        if args.entity == "transcription":
            return _handle_transcription(args, transcription_service, stdout, stderr)
        if args.entity == "acoustic":
            return _handle_acoustic(args, acoustic_service, stdout, stderr)
        if args.entity == "visual":
            return _handle_visual(args, visual_service, stdout, stderr)
        if args.entity == "multimodal":
            return _handle_multimodal(args, multimodal_service, stdout, stderr)
        if args.entity == "clips":
            return _handle_clips(args, clip_service, stdout, stderr)
        if args.entity == "youtube":
            if youtube_service is None:
                raise DomainError("El servicio de youtube no esta disponible.")
            return _handle_youtube(args, youtube_service, stdout, stderr)
        if args.entity == "audience":
            if audience_service is None:
                raise DomainError("El servicio de audiencia no esta disponible.")
            return handle_audience(args, service=audience_service, stdout=stdout, stderr=stderr)
        if args.entity == "analytics":
            if analytics_service is None:
                raise DomainError("El servicio de analytics no esta disponible.")
            return _handle_analytics(args, analytics_service, analytics_lab_service, stdout, stderr)
        if args.entity == "experiments":
            if experiment_service is None:
                raise DomainError("El servicio de experiments no esta disponible.")
            return _handle_experiments(args, experiment_service, stdout, stderr)
        if args.entity == "recommendations":
            if experiment_service is None:
                raise DomainError("El servicio de experiments no esta disponible.")
            return _handle_recommendations(args, experiment_service, stdout, stderr)
        if args.entity == "learnings":
            if experiment_service is None:
                raise DomainError("El servicio de experiments no esta disponible.")
            return _handle_learnings(args, experiment_service, stdout, stderr)
        if args.entity == "creator-memory":
            if creator_memory_service is None:
                raise DomainError("El servicio de creator memory no esta disponible.")
            return _handle_creator_memory(args, creator_memory_service, stdout, stderr)
        if args.entity == "creator-language":
            if creator_language_service is None:
                raise DomainError("El servicio de creator language no esta disponible.")
            return _handle_creator_language(args, creator_language_service, stdout, stderr)
        if args.entity == "packaging":
            if packaging_service is None:
                raise DomainError("El servicio de packaging no esta disponible.")
            return _handle_packaging(args, packaging_service, stdout, stderr)
        if args.entity == "render":
            if render_service is None:
                raise DomainError("El servicio de render no esta disponible.")
            return _handle_render(args, render_service, stdout, stderr)
        if args.entity == "subtitles":
            if subtitle_service is None:
                raise DomainError("El servicio de subtitulos no esta disponible.")
            return _handle_subtitles(args, subtitle_service, stdout, stderr)
        if args.entity == "personalization":
            if personalization_service is None:
                raise DomainError("El servicio de personalizacion no esta disponible.")
            return _handle_personalization(args, personalization_service, stdout, stderr)
        if args.entity == "models":
            if model_service is None:
                raise DomainError("El servicio de modelos personalizados no esta disponible.")
            return _handle_models(args, model_service, stdout, stderr)
        if args.entity == "evaluation":
            if evaluation_service is None:
                raise DomainError("El servicio de evaluacion operativa no esta disponible.")
            return _handle_evaluation(args, evaluation_service, stdout, stderr)
        raise ValueError("Comando no reconocido.")
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
