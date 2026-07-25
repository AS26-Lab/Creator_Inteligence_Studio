"""Vistas principales de escritorio."""

from __future__ import annotations

from .acoustic_analysis_view import AcousticAnalysisView
from .creators_view import CreatorsView
from .clip_ranking_view import ClipRankingView
from .dashboard_view import DashboardView
from .analytics_view import AnalyticsView
from .analytics_lab_view import AnalyticsLabView
from .experiments_view import ExperimentsView
from .creator_memory_view import CreatorMemoryView
from .creator_profile_view import CreatorProfileView
from .creator_language_view import CreatorLanguageView
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
from .videos_view import VideosView

__all__ = [
    "AcousticAnalysisView",
    "CreatorsView",
    "AnalyticsView",
    "ClipRankingView",
    "DashboardView",
    "ExperimentsView",
    "MultimodalAnalysisView",
    "AnalyticsLabView",
    "OperationalEvaluationView",
    "PersonalizationDataView",
    "PersonalizationModelsView",
    "ProjectsView",
    "CreatorMemoryView",
    "CreatorProfileView",
    "CreatorLanguageView",
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
    "PackagingHistoryView",
    "VideosView",
]
