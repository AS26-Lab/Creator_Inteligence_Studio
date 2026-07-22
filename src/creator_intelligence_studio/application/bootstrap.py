"""Bootstrap minimo de la aplicacion."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from logging import Logger
from typing import Sequence

from creator_intelligence_studio import APP_NAME, VERSION
from creator_intelligence_studio.application.services.catalog_service import (
    CatalogService,
    build_catalog_service,
)
from creator_intelligence_studio.application.services.audio_preparation_service import (
    AudioPreparationService,
    build_audio_preparation_service,
)
from creator_intelligence_studio.application.services.media_inspection_service import (
    MediaInspectionService,
    build_media_inspection_service,
)
from creator_intelligence_studio.application.services.transcription_service import (
    TranscriptionService,
    build_transcription_service,
)
from creator_intelligence_studio.infrastructure.configuration.settings import (
    AppSettings,
    SettingsError,
    load_settings,
)
from creator_intelligence_studio.infrastructure.diagnostics.environment_diagnostic import (
    collect_environment_diagnostic,
)
from creator_intelligence_studio.infrastructure.diagnostics.models import (
    EnvironmentDiagnostic,
)
from creator_intelligence_studio.infrastructure.logging.logging_setup import (
    setup_logging,
)
from creator_intelligence_studio.infrastructure.persistence.database import build_database
from creator_intelligence_studio.infrastructure.persistence.migrations import run_migrations
from creator_intelligence_studio.infrastructure.persistence.sqlite_prepared_audio_repository import (
    SQLitePreparedAudioRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_transcription_repository import (
    SQLiteTranscriptionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_inspection_repository import (
    SQLiteVideoInspectionRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_video_repository import (
    SQLiteVideoRepository,
)
from creator_intelligence_studio.presentation.cli.cli import dispatch, parse_args
from creator_intelligence_studio.shared.paths import ProjectPaths, discover_project_root


@dataclass(frozen=True, slots=True)
class BootstrapContext:
    """Contexto preparado por el bootstrap."""

    settings: AppSettings
    paths: ProjectPaths
    diagnostic: EnvironmentDiagnostic
    logger: Logger


@dataclass(frozen=True, slots=True)
class ServiceContext(BootstrapContext):
    """Contexto con servicios listos."""

    service: CatalogService
    media_service: MediaInspectionService
    audio_service: AudioPreparationService
    transcription_service: TranscriptionService


def _load_context() -> BootstrapContext:
    project_root = discover_project_root()
    settings = load_settings(project_root / "config" / "default.json")
    paths = ProjectPaths.from_settings(project_root, settings)
    paths.ensure_runtime_directories()
    logger = setup_logging(settings=settings, paths=paths)
    logger.info("Inicializacion del entorno completada.")
    diagnostic = collect_environment_diagnostic(
        settings=settings,
        paths=paths,
    )
    return BootstrapContext(
        settings=settings,
        paths=paths,
        diagnostic=diagnostic,
        logger=logger,
    )


def _load_service_context() -> ServiceContext:
    context = _load_context()
    database = build_database(context.settings, context.paths)
    with database.connect() as connection:
        run_migrations(connection)
    service = build_catalog_service(
        settings=context.settings,
        paths=context.paths,
        logger=context.logger,
        database=database,
    )
    media_service = build_media_inspection_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=SQLiteVideoRepository(database),
        inspection_repository=SQLiteVideoInspectionRepository(database),
        logger=context.logger,
    )
    audio_service = build_audio_preparation_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=SQLiteVideoRepository(database),
        inspection_service=media_service,
        audio_repository=SQLitePreparedAudioRepository(database),
        logger=context.logger,
    )
    transcription_service = build_transcription_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=SQLiteVideoRepository(database),
        prepared_audio_repository=SQLitePreparedAudioRepository(database),
        transcription_repository=SQLiteTranscriptionRepository(database),
        logger=context.logger,
    )
    return ServiceContext(
        settings=context.settings,
        paths=context.paths,
        diagnostic=context.diagnostic,
        logger=context.logger,
        service=service,
        media_service=media_service,
        audio_service=audio_service,
        transcription_service=transcription_service,
    )


def _print_summary(context: BootstrapContext, stream) -> None:
    diagnostic = context.diagnostic
    print(f"{APP_NAME} v{VERSION}", file=stream)
    print(f"Entorno: {context.settings.environment}", file=stream)
    print(f"Ruta del proyecto: {context.paths.project_root}", file=stream)
    print(f"Python: {diagnostic.python_version} ({diagnostic.python_executable})", file=stream)
    print(f"Backend preferido: {diagnostic.preferred_compute_backend}", file=stream)
    print(
        "Modo basico disponible: "
        + ("si" if diagnostic.state.ready_for_basic_mode else "no"),
        file=stream,
    )
    print(
        "CUDA detectado por driver: "
        + ("si" if diagnostic.state.cuda_driver_detected else "no"),
        file=stream,
    )
    print(
        "CUDA verificado en runtime: "
        + ("si" if not diagnostic.state.cuda_runtime_not_verified else "no"),
        file=stream,
    )
    if diagnostic.gpu_devices:
        gpu = diagnostic.gpu_devices[0]
        memory = (
            f"{gpu.memory_total_mib} MiB"
            if gpu.memory_total_mib is not None
            else "no verificado"
        )
        print(f"GPU NVIDIA: {gpu.name} | VRAM: {memory}", file=stream)
    else:
        print("GPU NVIDIA: no verificado", file=stream)
    for warning in diagnostic.warnings:
        print(f"Advertencia: {warning}", file=stream)


def run(argv: Sequence[str] | None = (), stdout=None, stderr=None) -> int:
    """Ejecuta el bootstrap de la aplicacion."""

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = parse_args(argv)

    try:
        if args.gui:
            context = _load_service_context()
            from creator_intelligence_studio.presentation.desktop.app import launch_gui

            return launch_gui(context, stdout=stdout, stderr=stderr)
        if args.diagnostic_json or args.entity is None:
            context = _load_context()
            if args.diagnostic_json:
                print(context.diagnostic.to_json(), file=stdout)
            else:
                _print_summary(context, stdout)
            return 0 if context.diagnostic.state.ready_for_basic_mode else 1

        context = _load_service_context()
        return dispatch(
            args,
            service=context.service,
            media_service=context.media_service,
            audio_service=context.audio_service,
            transcription_service=context.transcription_service,
            diagnostic=context.diagnostic,
            stdout=stdout,
            stderr=stderr,
        )
    except SettingsError as exc:
        print(f"Error de configuracion: {exc}", file=stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensa general
        print(f"Error inesperado durante el arranque: {exc}", file=stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada principal."""

    return run(argv=sys.argv[1:] if argv is None else argv)
