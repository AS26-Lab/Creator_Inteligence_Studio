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
