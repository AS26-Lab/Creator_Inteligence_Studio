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
from creator_intelligence_studio.application.services.acoustic_analysis_service import (
    AcousticAnalysisService,
    build_acoustic_analysis_service,
)
from creator_intelligence_studio.application.services.visual_analysis_service import (
    VisualAnalysisService,
    build_visual_analysis_service,
)
from creator_intelligence_studio.application.services.multimodal_analysis_service import (
    MultimodalAnalysisService,
    build_multimodal_analysis_service,
)
from creator_intelligence_studio.application.services.clip_ranking_service import (
    ClipRankingService,
    build_clip_ranking_service,
)
from creator_intelligence_studio.application.services.clip_rendering_service import (
    ClipRenderService,
    build_clip_render_service,
)
from creator_intelligence_studio.application.services.subtitle_service import (
    SubtitleService,
    build_subtitle_service,
)
from creator_intelligence_studio.application.services.personalization_dataset_service import (
    PersonalizationDatasetService,
    build_personalization_dataset_service,
)
from creator_intelligence_studio.application.services.personalization_training_service import (
    PersonalizationTrainingService,
    build_personalization_training_service,
)
from creator_intelligence_studio.application.services.operational_evaluation_service import (
    OperationalEvaluationService,
    build_operational_evaluation_service,
)
from creator_intelligence_studio.application.services.analytics_import_service import (
    AnalyticsImportService,
    build_analytics_services,
)
from creator_intelligence_studio.application.services.analytics_lab_service import (
    AnalyticsLabService,
    build_analytics_lab_services,
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
from creator_intelligence_studio.infrastructure.persistence.sqlite_acoustic_analysis_repository import (
    SQLiteAcousticAnalysisRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_visual_analysis_repository import (
    SQLiteVisualAnalysisRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_multimodal_analysis_repository import (
    SQLiteMultimodalAnalysisRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_clip_ranking_repository import (
    SQLiteClipRankingRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_clip_rendering_repository import (
    SQLiteClipRenderingRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_subtitle_repository import (
    SQLiteSubtitleRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_personalization_repository import (
    SQLitePersonalizationRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_personalization_model_repository import (
    SQLitePersonalizationModelRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_operational_evaluation_repository import (
    SQLiteOperationalEvaluationRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_repository import (
    SQLiteAnalyticsRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_analytics_lab_repository import (
    SQLiteAnalyticsLabRepository,
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
    acoustic_service: AcousticAnalysisService
    visual_service: VisualAnalysisService
    multimodal_service: MultimodalAnalysisService | None = None
    clip_service: ClipRankingService | None = None
    render_service: ClipRenderService | None = None
    subtitle_service: SubtitleService | None = None
    analytics_service: AnalyticsImportService | None = None
    analytics_lab_service: AnalyticsLabService | None = None
    personalization_service: PersonalizationDatasetService | None = None
    model_service: PersonalizationTrainingService | None = None
    evaluation_service: OperationalEvaluationService | None = None


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
    inspection_repository = SQLiteVideoInspectionRepository(database)
    video_repository = SQLiteVideoRepository(database)
    prepared_audio_repository = SQLitePreparedAudioRepository(database)
    transcription_repository = SQLiteTranscriptionRepository(database)
    media_service = build_media_inspection_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        inspection_repository=inspection_repository,
        logger=context.logger,
    )
    audio_service = build_audio_preparation_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        inspection_service=media_service,
        audio_repository=prepared_audio_repository,
        logger=context.logger,
    )
    transcription_service = build_transcription_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        logger=context.logger,
    )
    acoustic_service = build_acoustic_analysis_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=SQLiteAcousticAnalysisRepository(database),
        logger=context.logger,
    )
    visual_service = build_visual_analysis_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        inspection_repository=inspection_repository,
        visual_repository=SQLiteVisualAnalysisRepository(database),
        logger=context.logger,
    )
    multimodal_service = build_multimodal_analysis_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        transcription_repository=transcription_repository,
        acoustic_repository=SQLiteAcousticAnalysisRepository(database),
        visual_repository=SQLiteVisualAnalysisRepository(database),
        multimodal_repository=SQLiteMultimodalAnalysisRepository(database),
        logger=context.logger,
    )
    clip_service = build_clip_ranking_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        multimodal_service=multimodal_service,
        transcription_repository=transcription_repository,
        clip_repository=SQLiteClipRankingRepository(database),
        logger=context.logger,
    )
    subtitle_service = build_subtitle_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        transcription_service=transcription_service,
        clip_service=clip_service,
        repository=SQLiteSubtitleRepository(database),
        logger=context.logger,
    )
    render_service = build_clip_render_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        media_service=media_service,
        clip_service=clip_service,
        repository=SQLiteClipRenderingRepository(database),
        subtitle_service=subtitle_service,
        logger=context.logger,
    )
    analytics_repository = SQLiteAnalyticsRepository(database)
    analytics_service, _ = build_analytics_services(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        repository=analytics_repository,
        database=database,
        logger=context.logger,
    )
    analytics_lab_repository = SQLiteAnalyticsLabRepository(database)
    analytics_lab_service, _, _, _, _ = build_analytics_lab_services(
        analytics_service=analytics_service,
        repository=analytics_lab_repository,
        paths=context.paths,
        logger=context.logger,
    )
    personalization_service = build_personalization_dataset_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        clip_service=clip_service,
        personalization_repository=SQLitePersonalizationRepository(database),
        logger=context.logger,
    )
    model_service = build_personalization_training_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        clip_service=clip_service,
        dataset_service=personalization_service,
        model_repository=SQLitePersonalizationModelRepository(database),
        logger=context.logger,
    )
    evaluation_service = build_operational_evaluation_service(
        settings=context.settings,
        paths=context.paths,
        catalog_service=service,
        media_service=media_service,
        audio_service=audio_service,
        transcription_service=transcription_service,
        acoustic_service=acoustic_service,
        visual_service=visual_service,
        multimodal_service=multimodal_service,
        clip_service=clip_service,
        personalization_service=personalization_service,
        model_service=model_service,
        repository=SQLiteOperationalEvaluationRepository(database),
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
        acoustic_service=acoustic_service,
        visual_service=visual_service,
        multimodal_service=multimodal_service,
        clip_service=clip_service,
        render_service=render_service,
        subtitle_service=subtitle_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        personalization_service=personalization_service,
        model_service=model_service,
        evaluation_service=evaluation_service,
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
            acoustic_service=context.acoustic_service,
            visual_service=context.visual_service,
            multimodal_service=context.multimodal_service,
            clip_service=context.clip_service,
            analytics_service=context.analytics_service,
            analytics_lab_service=context.analytics_lab_service,
            render_service=context.render_service,
            subtitle_service=context.subtitle_service,
            personalization_service=context.personalization_service,
            model_service=context.model_service,
            evaluation_service=context.evaluation_service,
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
