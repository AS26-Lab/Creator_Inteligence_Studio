"""Bootstrap minimo de la aplicacion."""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
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
from creator_intelligence_studio.application.services.experiment_service import (
    ExperimentService,
    build_experiment_services,
)
from creator_intelligence_studio.application.services.creator_memory_service import (
    CreatorMemoryService,
)
from creator_intelligence_studio.application.services.creator_corpus_service import (
    CreatorCorpusService,
    build_creator_corpus_service,
)
from creator_intelligence_studio.application.services.creator_corpus_retrieval_service import (
    CreatorCorpusRetrievalService,
)
from creator_intelligence_studio.application.services.creator_language_service import (
    CreatorLanguageService,
    build_creator_language_service,
)
from creator_intelligence_studio.application.services.creative_packaging_service import (
    CreativePackagingService,
    build_creative_packaging_service,
)
from creator_intelligence_studio.application.services.youtube_integration_service import (
    YouTubeIntegrationService,
    build_youtube_integration_service,
)
from creator_intelligence_studio.application.services.instagram_integration_service import (
    InstagramIntegrationService,
    build_instagram_integration_service,
)
from creator_intelligence_studio.application.services.tiktok_integration_service import (
    TikTokIntegrationService,
    build_tiktok_integration_service,
)
from creator_intelligence_studio.application.services.audience_model_service import (
    AudienceModelService,
    build_audience_model_service,
)
from creator_intelligence_studio.application.services.platform_integration_service import (
    PlatformIntegrationService,
)
from creator_intelligence_studio.application.services.market_intelligence_service import (
    MarketIntelligenceService,
    build_market_intelligence_service,
)
from creator_intelligence_studio.application.services.recommendation_engine_service import (
    RecommendationEngineService,
    build_recommendation_engine_service,
)
from creator_intelligence_studio.application.services.content_brief_service import (
    ContentBriefService,
    build_content_brief_service,
)
from creator_intelligence_studio.application.services.production_preparation_service import (
    ProductionPreparationService,
    build_production_preparation_service,
)
from creator_intelligence_studio.application.services.strategic_planning_service import (
    StrategicPlanningService,
    build_strategic_planning_service,
)
from creator_intelligence_studio.application.services.transcription_service import (
    TranscriptionService,
    build_transcription_service,
)
from creator_intelligence_studio.application.services.component_manager_service import (
    ComponentManagerService,
)
from creator_intelligence_studio.application.services.ai_runtime_service import (
    AIRuntimeService,
    build_ai_runtime_service,
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
from creator_intelligence_studio.infrastructure.persistence.sqlite_component_manager_repository import (
    SQLiteComponentManagerRepository,
)
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
from creator_intelligence_studio.infrastructure.persistence.sqlite_experiment_repository import (
    SQLiteExperimentRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_memory_repository import (
    SQLiteCreatorMemoryRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_corpus_repository import (
    SQLiteCreatorCorpusRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creator_language_repository import (
    SQLiteCreatorLanguageRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_creative_packaging_repository import (
    SQLiteCreativePackagingRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_youtube_repository import (
    SQLiteYouTubeRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_instagram_repository import (
    SQLiteInstagramRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_tiktok_repository import (
    SQLiteTikTokRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_audience_repository import (
    SQLiteAudienceRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_platform_integration_repository import (
    SQLitePlatformIntegrationRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_market_intelligence_repository import (
    SQLiteMarketIntelligenceRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_recommendation_repository import (
    SQLiteRecommendationRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_content_brief_repository import (
    SQLiteContentBriefRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_production_preparation_repository import (
    SQLiteProductionPreparationRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_strategic_planning_repository import (
    SQLiteStrategicPlanningRepository,
)
from creator_intelligence_studio.infrastructure.persistence.sqlite_project_repository import (
    SQLiteProjectRepository,
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
from creator_intelligence_studio.infrastructure.media.ffmpeg_locator import MediaToolLocator
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
    experiment_service: ExperimentService | None = None
    creator_memory_service: CreatorMemoryService | None = None
    creator_corpus_service: CreatorCorpusService | None = None
    creator_corpus_retrieval_service: CreatorCorpusRetrievalService | None = None
    creator_language_service: CreatorLanguageService | None = None
    creative_packaging_service: CreativePackagingService | None = None
    youtube_service: YouTubeIntegrationService | None = None
    instagram_service: InstagramIntegrationService | None = None
    tiktok_service: TikTokIntegrationService | None = None
    audience_service: AudienceModelService | None = None
    platform_service: PlatformIntegrationService | None = None
    market_service: MarketIntelligenceService | None = None
    recommendation_service: RecommendationEngineService | None = None
    planning_service: StrategicPlanningService | None = None
    brief_service: ContentBriefService | None = None
    production_service: ProductionPreparationService | None = None
    personalization_service: PersonalizationDatasetService | None = None
    model_service: PersonalizationTrainingService | None = None
    evaluation_service: OperationalEvaluationService | None = None
    ai_runtime_service: AIRuntimeService | None = None
    component_manager_service: ComponentManagerService | None = None


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
    ai_runtime_service = build_ai_runtime_service(
        settings=context.settings,
        paths=context.paths,
        database=database,
    )
    ai_status = ai_runtime_service.status()
    diagnostic = replace(
        context.diagnostic,
        ai_runtime_available=ai_status.ai_runtime_available,
        openai_configured=ai_status.openai_configured,
        anthropic_configured=ai_status.anthropic_configured,
        model_roles_configured=ai_status.model_roles_configured,
        budget_policy_configured=ai_status.budget_policy_configured,
        credential_store_available=ai_status.credential_store_available,
    )
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
    component_manager_service = ComponentManagerService(
        paths=context.paths,
        repository=SQLiteComponentManagerRepository(database),
        logger=context.logger,
    )
    media_tool_locator = MediaToolLocator(
        settings=context.settings,
        project_root=context.paths.project_root,
        resolution_service=component_manager_service,
    )
    media_service = build_media_inspection_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        inspection_repository=inspection_repository,
        logger=context.logger,
        tool_locator=media_tool_locator,
    )
    audio_service = build_audio_preparation_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        inspection_service=media_service,
        audio_repository=prepared_audio_repository,
        logger=context.logger,
        tool_locator=media_tool_locator,
    )
    transcription_service = build_transcription_service(
        settings=context.settings,
        paths=context.paths,
        video_repository=video_repository,
        prepared_audio_repository=prepared_audio_repository,
        transcription_repository=transcription_repository,
        capability_resolver=component_manager_service.resolver,
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
        tool_locator=media_tool_locator,
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
        tool_locator=media_tool_locator,
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
    experiment_repository = SQLiteExperimentRepository(database)
    experiment_service, _, _, _, _ = build_experiment_services(
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        repository=experiment_repository,
        paths=context.paths,
        logger=context.logger,
    )
    project_repository = SQLiteProjectRepository(database)
    creator_memory_service = CreatorMemoryService(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteCreatorMemoryRepository(database),
        logger=context.logger,
    )
    creator_corpus_repository = SQLiteCreatorCorpusRepository(database)
    creator_corpus_service = build_creator_corpus_service(
        settings=context.settings,
        paths=context.paths,
        repository=creator_corpus_repository,
        project_repository=project_repository,
        video_repository=video_repository,
        transcription_repository=transcription_repository,
        logger=context.logger,
    )
    transcription_service.creator_corpus_service = creator_corpus_service
    creator_corpus_retrieval_service = CreatorCorpusRetrievalService(
        repository=creator_corpus_repository,
        logger=context.logger,
    )
    creator_language_service = build_creator_language_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteCreatorLanguageRepository(database),
        database=database,
        transcription_repository=transcription_repository,
        subtitle_repository=SQLiteSubtitleRepository(database),
        analytics_repository=analytics_repository,
        creator_memory_service=creator_memory_service,
        logger=context.logger,
    )
    creative_packaging_service = build_creative_packaging_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteCreativePackagingRepository(database),
        database=database,
        catalog_service=service,
        analytics_repository=analytics_repository,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        experiment_service=experiment_service,
        logger=context.logger,
    )
    youtube_service = build_youtube_integration_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteYouTubeRepository(database),
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=SQLiteCreativePackagingRepository(database),
        logger=context.logger,
    )
    instagram_service = build_instagram_integration_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteInstagramRepository(database),
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=SQLiteCreativePackagingRepository(database),
        logger=context.logger,
    )
    tiktok_service = build_tiktok_integration_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteTikTokRepository(database),
        database=database,
        analytics_repository=analytics_repository,
        creative_packaging_repository=SQLiteCreativePackagingRepository(database),
        logger=context.logger,
    )
    audience_service = build_audience_model_service(
        settings=context.settings,
        paths=context.paths,
        analytics_service=analytics_service,
        repository=SQLiteAudienceRepository(database),
        database=database,
        logger=context.logger,
    )
    platform_service = PlatformIntegrationService(
        settings=context.settings,
        paths=context.paths,
        database=database,
        repository=SQLitePlatformIntegrationRepository(database),
        youtube_service=youtube_service,
        instagram_service=instagram_service,
        tiktok_service=tiktok_service,
        analytics_service=analytics_service,
        logger=context.logger,
    )
    market_service = build_market_intelligence_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteMarketIntelligenceRepository(database),
        database=database,
        catalog_service=service,
        analytics_service=analytics_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        analytics_lab_service=analytics_lab_service,
        logger=context.logger,
    )
    recommendation_service = build_recommendation_engine_service(
        settings=context.settings,
        paths=context.paths,
        database=database,
        repository=SQLiteRecommendationRepository(database),
        catalog_service=service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        market_service=market_service,
        platform_service=platform_service,
        creative_packaging_service=creative_packaging_service,
        experiment_service=experiment_service,
        logger=context.logger,
    )
    planning_service = build_strategic_planning_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteStrategicPlanningRepository(database),
        recommendation_service=recommendation_service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        market_service=market_service,
        experiment_service=experiment_service,
        content_library_service=service,
        platform_service=platform_service,
        logger=context.logger,
    )
    brief_service = build_content_brief_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteContentBriefRepository(database),
        planning_service=planning_service,
        recommendation_service=recommendation_service,
        experiment_service=experiment_service,
        content_library_service=service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        analytics_service=analytics_service,
        analytics_lab_service=analytics_lab_service,
        market_service=market_service,
        platform_service=platform_service,
        packaging_service=creative_packaging_service,
        logger=context.logger,
    )
    production_service = build_production_preparation_service(
        settings=context.settings,
        paths=context.paths,
        repository=SQLiteProductionPreparationRepository(database),
        brief_service=brief_service,
        planning_service=planning_service,
        recommendation_service=recommendation_service,
        experiment_service=experiment_service,
        content_library_service=service,
        creator_memory_service=creator_memory_service,
        creator_language_service=creator_language_service,
        audience_service=audience_service,
        platform_service=platform_service,
        packaging_service=creative_packaging_service,
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
        diagnostic=diagnostic,
        logger=context.logger,
        service=service,
        ai_runtime_service=ai_runtime_service,
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
        experiment_service=experiment_service,
        creator_memory_service=creator_memory_service,
        creator_corpus_service=creator_corpus_service,
        creator_corpus_retrieval_service=creator_corpus_retrieval_service,
        creator_language_service=creator_language_service,
        creative_packaging_service=creative_packaging_service,
        youtube_service=youtube_service,
        instagram_service=instagram_service,
        tiktok_service=tiktok_service,
        audience_service=audience_service,
        platform_service=platform_service,
        market_service=market_service,
        recommendation_service=recommendation_service,
        planning_service=planning_service,
        brief_service=brief_service,
        production_service=production_service,
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
            print("GUI_BOOT_03 before_bootstrap", file=stderr)
            context = _load_service_context()
            print("GUI_BOOT_04 bootstrap_completed", file=stderr)
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
            component_manager_service=context.component_manager_service,
            transcription_service=context.transcription_service,
            acoustic_service=context.acoustic_service,
            visual_service=context.visual_service,
            multimodal_service=context.multimodal_service,
            clip_service=context.clip_service,
            youtube_service=context.youtube_service,
            instagram_service=context.instagram_service,
            tiktok_service=context.tiktok_service,
            audience_service=context.audience_service,
            platform_service=context.platform_service,
            market_service=context.market_service,
            recommendation_service=context.recommendation_service,
            planning_service=context.planning_service,
            brief_service=context.brief_service,
            production_service=context.production_service,
            analytics_service=context.analytics_service,
            analytics_lab_service=context.analytics_lab_service,
            experiment_service=context.experiment_service,
            creator_memory_service=context.creator_memory_service,
            creator_corpus_retrieval_service=context.creator_corpus_retrieval_service,
            creator_language_service=context.creator_language_service,
            packaging_service=context.creative_packaging_service,
            render_service=context.render_service,
            subtitle_service=context.subtitle_service,
            personalization_service=context.personalization_service,
            ai_runtime_service=context.ai_runtime_service,
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
