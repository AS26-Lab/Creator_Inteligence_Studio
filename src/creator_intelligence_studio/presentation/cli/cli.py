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
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
)
from creator_intelligence_studio.domain.errors import DomainError
from creator_intelligence_studio.domain.acoustic_analysis.entities import AcousticAnalysis, AcousticEvent, AcousticTimelineWindow
from creator_intelligence_studio.domain.acoustic_analysis.value_objects import AcousticAnalysisStatus
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


def dispatch(
    args: argparse.Namespace,
    *,
    service: CatalogService,
    media_service: MediaInspectionService,
    audio_service: AudioPreparationService,
    transcription_service: TranscriptionService,
    acoustic_service: AcousticAnalysisService,
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
        raise ValueError("Comando no reconocido.")
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
