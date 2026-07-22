"""Interfaz de linea de comandos."""

from __future__ import annotations

import argparse
import json
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
from creator_intelligence_studio.infrastructure.diagnostics.models import EnvironmentDiagnostic


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
    diagnostic: EnvironmentDiagnostic,
    stdout,
    stderr,
) -> int:
    """Ejecuta el comando solicitado."""

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
        raise ValueError("Comando no reconocido.")
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
