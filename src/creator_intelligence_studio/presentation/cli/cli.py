"""Interfaz de linea de comandos."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from creator_intelligence_studio.application.commands.creator_commands import (
    ArchiveCreatorCommand,
    CreateCreatorCommand,
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
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    MediaToolsReport,
    VideoInspectionReport,
)
from creator_intelligence_studio.domain.errors import DomainError
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


def dispatch(
    args: argparse.Namespace,
    *,
    service: CatalogService,
    media_service: MediaInspectionService,
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
        raise ValueError("Comando no reconocido.")
    except DomainError as exc:
        print(f"Error: {exc}", file=stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado: {exc}", file=stderr)
        return 1
