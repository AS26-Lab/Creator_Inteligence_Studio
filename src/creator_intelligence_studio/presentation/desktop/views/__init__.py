"""Vistas principales de escritorio."""

from __future__ import annotations

from .acoustic_analysis_view import AcousticAnalysisView
from .creators_view import CreatorsView
from .clip_ranking_view import ClipRankingView
from .dashboard_view import DashboardView
from .analytics_view import AnalyticsView
from .analytics_lab_view import AnalyticsLabView
from .audience_overview_view import AudienceOverviewView
from .audience_segments_view import AudienceSegmentsView
from .audience_journeys_view import AudienceJourneysView
from .audience_affinity_view import AudienceAffinityView
from .audience_history_view import AudienceHistoryView
from .experiments_view import ExperimentsView
from .recommendations_overview_view import RecommendationsOverviewView
from .planning_overview_view import PlanningOverviewView
from .strategic_objectives_view import StrategicObjectivesView
from .strategy_themes_view import StrategyThemesView
from .content_pillars_view import ContentPillarsView
from .initiatives_view import InitiativesView
from .campaigns_view import CampaignsView
from .content_series_view import ContentSeriesView
from .roadmap_view import RoadmapView
from .backlog_view import BacklogView
from .capacity_view import CapacityView
from .dependencies_view import DependenciesView
from .milestones_view import MilestonesView
from .scenarios_view import ScenariosView
from .reviews_view import ReviewsView
from .planning_history_view import PlanningHistoryView
from .planning_settings_view import PlanningSettingsView
from .planning_privacy_view import PlanningPrivacyView
from .briefs_overview_view import BriefsOverviewView
from .brief_requests_view import BriefRequestsView
from .content_briefs_view import ContentBriefsView
from .brief_detail_view import BriefDetailView
from .brief_audience_view import BriefAudienceView
from .brief_promise_angle_view import BriefPromiseAngleView
from .brief_message_view import BriefMessageView
from .brief_structure_view import BriefStructureView
from .brief_claims_view import BriefClaimsView
from .brief_packaging_view import BriefPackagingView
from .brief_platform_adaptations_view import BriefPlatformAdaptationsView
from .brief_references_view import BriefReferencesView
from .brief_rights_view import BriefRightsView
from .brief_assets_view import BriefAssetsView
from .brief_preproduction_view import BriefPreproductionView
from .brief_shot_plan_view import BriefShotPlanView
from .brief_checklist_view import BriefChecklistView
from .brief_approval_gates_view import BriefApprovalGatesView
from .brief_readiness_view import BriefReadinessView
from .brief_risks_view import BriefRisksView
from .brief_reviews_view import BriefReviewsView
from .brief_history_view import BriefHistoryView
from .brief_settings_view import BriefSettingsView
from .brief_privacy_view import BriefPrivacyView
from .production_base_view import ProductionSectionView
from .production_overview_view import ProductionOverviewView
from .production_requests_view import ProductionRequestsView
from .script_outlines_view import ScriptOutlinesView
from .outline_detail_view import OutlineDetailView
from .beats_view import BeatsView
from .segments_view import SegmentsView
from .claims_proof_view import ClaimsProofView
from .scenes_view import ScenesView
from .shots_view import ShotsView
from .shot_groups_view import ShotGroupsView
from .recording_blocks_view import RecordingBlocksView
from .recording_order_view import RecordingOrderView
from .visual_cues_view import VisualCuesView
from .audio_cues_view import AudioCuesView
from .on_screen_text_view import OnScreenTextView
from .broll_requirements_view import BrollRequirementsView
from .graphics_requirements_view import GraphicsRequirementsView
from .screen_recordings_view import ScreenRecordingsView
from .participants_view import ParticipantsView
from .locations_view import LocationsView
from .props_view import PropsView
from .wardrobe_view import WardrobeView
from .equipment_view import EquipmentView
from .continuity_view import ContinuityView
from .platform_variants_view import PlatformVariantsView
from .reusable_segments_view import ReusableSegmentsView
from .production_dependencies_view import ProductionDependenciesView
from .production_milestones_view import ProductionMilestonesView
from .production_checklists_view import ProductionChecklistsView
from .production_readiness_view import ProductionReadinessView
from .production_risks_view import ProductionRisksView
from .production_reviews_view import ProductionReviewsView
from .production_history_view import ProductionHistoryView
from .production_settings_view import ProductionSettingsView
from .production_privacy_view import ProductionPrivacyView
from .recommendation_candidates_view import RecommendationCandidatesView
from .recommendation_detail_view import RecommendationDetailView
from .recommendation_evidence_view import RecommendationEvidenceView
from .recommendation_risks_view import RecommendationRisksView
from .recommendation_alternatives_view import RecommendationAlternativesView
from .recommendation_review_view import RecommendationReviewView
from .recommendation_history_view import RecommendationHistoryView
from .recommendation_settings_view import RecommendationSettingsView
from .recommendation_privacy_view import RecommendationPrivacyView
from .creator_memory_view import CreatorMemoryView
from .creator_profile_view import CreatorProfileView
from .creator_language_view import CreatorLanguageView
from .ai_runtime_overview_view import AIRuntimeOverviewView
from .narrative_profile_view import NarrativeProfileView
from .multimodal_analysis_view import MultimodalAnalysisView
from .operational_evaluation_view import OperationalEvaluationView
from .personalization_data_view import PersonalizationDataView
from .personalization_models_view import PersonalizationModelsView
from .projects_view import ProjectsView
from .task_center_view import TaskCenterView
from .workflow_view import WorkflowView
from .onboarding_view import OnboardingView
from .preferences_dialog import PreferencesDialog
from .visual_analysis_view import VisualAnalysisView
from .system_view import SystemView
from .transcription_view import TranscriptionView
from .subtitle_editor_view import SubtitleEditorView
from .learning_memory_view import LearningMemoryView
from .thumbnail_lab_view import ThumbnailLabView
from .packaging_history_view import PackagingHistoryView
from .youtube_connection_view import YouTubeConnectionView
from .youtube_channels_view import YouTubeChannelsView
from .youtube_sync_view import YouTubeSyncView
from .youtube_sync_history_view import YouTubeSyncHistoryView
from .youtube_integration_view import YouTubeIntegrationView
from .instagram_integration_view import InstagramIntegrationView
from .tiktok_integration_view import TikTokIntegrationView
from .tiktok_connection_view import TikTokConnectionView
from .tiktok_profile_view import TikTokProfileView
from .tiktok_sync_view import TikTokSyncView
from .tiktok_videos_view import TikTokVideosView
from .tiktok_metrics_view import TikTokMetricsView
from .tiktok_sync_history_view import TikTokSyncHistoryView
from .integrations_overview_view import (
    IntegrationsOverviewView,
    IntegrationConnectionsView,
    IntegrationSyncCenterView,
    IntegrationHealthView,
    IntegrationCapabilitiesView,
    IntegrationDataAvailabilityView,
    IntegrationHistoryView,
    IntegrationPrivacyView,
    IntegrationOnboardingView,
)
from .market_overview_view import MarketOverviewView
from .market_sources_view import MarketSourcesView
from .competitor_library_view import CompetitorLibraryView
from .external_content_view import ExternalContentView
from .trend_signals_view import TrendSignalsView
from .topic_landscape_view import TopicLandscapeView
from .format_patterns_view import FormatPatternsView
from .saturation_view import SaturationView
from .creator_fit_view import CreatorFitView
from .opportunity_candidates_view import OpportunityCandidatesView
from .research_history_view import ResearchHistoryView
from .market_privacy_view import MarketPrivacyView
from .videos_view import VideosView

__all__ = [
    "AcousticAnalysisView",
    "CreatorsView",
    "AnalyticsView",
    "ClipRankingView",
    "DashboardView",
    "AudienceOverviewView",
    "AudienceSegmentsView",
    "AudienceJourneysView",
    "AudienceAffinityView",
    "AudienceHistoryView",
    "ExperimentsView",
    "RecommendationsOverviewView",
    "PlanningOverviewView",
    "StrategicObjectivesView",
    "StrategyThemesView",
    "ContentPillarsView",
    "InitiativesView",
    "CampaignsView",
    "ContentSeriesView",
    "RoadmapView",
    "BacklogView",
    "CapacityView",
    "DependenciesView",
    "MilestonesView",
    "ScenariosView",
    "ReviewsView",
    "PlanningHistoryView",
    "PlanningSettingsView",
    "PlanningPrivacyView",
    "BriefsOverviewView",
    "BriefRequestsView",
    "ContentBriefsView",
    "BriefDetailView",
    "BriefAudienceView",
    "BriefPromiseAngleView",
    "BriefMessageView",
    "BriefStructureView",
    "BriefClaimsView",
    "BriefPackagingView",
    "BriefPlatformAdaptationsView",
    "BriefReferencesView",
    "BriefRightsView",
    "BriefAssetsView",
    "BriefPreproductionView",
    "BriefShotPlanView",
    "BriefChecklistView",
    "BriefApprovalGatesView",
    "BriefReadinessView",
    "BriefRisksView",
    "BriefReviewsView",
    "BriefHistoryView",
    "BriefSettingsView",
    "BriefPrivacyView",
    "ProductionSectionView",
    "ProductionOverviewView",
    "ProductionRequestsView",
    "ScriptOutlinesView",
    "OutlineDetailView",
    "BeatsView",
    "SegmentsView",
    "ClaimsProofView",
    "ScenesView",
    "ShotsView",
    "ShotGroupsView",
    "RecordingBlocksView",
    "RecordingOrderView",
    "VisualCuesView",
    "AudioCuesView",
    "OnScreenTextView",
    "BrollRequirementsView",
    "GraphicsRequirementsView",
    "ScreenRecordingsView",
    "ParticipantsView",
    "LocationsView",
    "PropsView",
    "WardrobeView",
    "EquipmentView",
    "ContinuityView",
    "PlatformVariantsView",
    "ReusableSegmentsView",
    "ProductionDependenciesView",
    "ProductionMilestonesView",
    "ProductionChecklistsView",
    "ProductionReadinessView",
    "ProductionRisksView",
    "ProductionReviewsView",
    "ProductionHistoryView",
    "ProductionSettingsView",
    "ProductionPrivacyView",
    "RecommendationCandidatesView",
    "RecommendationDetailView",
    "RecommendationEvidenceView",
    "RecommendationRisksView",
    "RecommendationAlternativesView",
    "RecommendationReviewView",
    "RecommendationHistoryView",
    "RecommendationSettingsView",
    "RecommendationPrivacyView",
    "MultimodalAnalysisView",
    "AnalyticsLabView",
    "OperationalEvaluationView",
    "PersonalizationDataView",
    "PersonalizationModelsView",
    "ProjectsView",
    "CreatorMemoryView",
    "CreatorProfileView",
    "CreatorLanguageView",
    "AIRuntimeOverviewView",
    "NarrativeProfileView",
    "TaskCenterView",
    "WorkflowView",
    "OnboardingView",
    "PreferencesDialog",
    "VisualAnalysisView",
    "SystemView",
    "TranscriptionView",
    "SubtitleEditorView",
    "LearningMemoryView",
    "ThumbnailLabView",
    "YouTubeConnectionView",
    "YouTubeChannelsView",
    "YouTubeSyncView",
    "YouTubeSyncHistoryView",
    "YouTubeIntegrationView",
    "InstagramIntegrationView",
    "TikTokIntegrationView",
    "TikTokConnectionView",
    "TikTokProfileView",
    "TikTokSyncView",
    "TikTokVideosView",
    "TikTokMetricsView",
    "TikTokSyncHistoryView",
    "IntegrationsOverviewView",
    "IntegrationConnectionsView",
    "IntegrationSyncCenterView",
    "IntegrationHealthView",
    "IntegrationCapabilitiesView",
    "IntegrationDataAvailabilityView",
    "IntegrationHistoryView",
    "IntegrationPrivacyView",
    "IntegrationOnboardingView",
    "MarketOverviewView",
    "MarketSourcesView",
    "CompetitorLibraryView",
    "ExternalContentView",
    "TrendSignalsView",
    "TopicLandscapeView",
    "FormatPatternsView",
    "SaturationView",
    "CreatorFitView",
    "OpportunityCandidatesView",
    "ResearchHistoryView",
    "MarketPrivacyView",
    "PackagingHistoryView",
    "VideosView",
]
