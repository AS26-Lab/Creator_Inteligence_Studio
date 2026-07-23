"""Vistas principales de escritorio."""

from __future__ import annotations

from .acoustic_analysis_view import AcousticAnalysisView
from .creators_view import CreatorsView
from .clip_ranking_view import ClipRankingView
from .dashboard_view import DashboardView
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
from .videos_view import VideosView

__all__ = [
    "AcousticAnalysisView",
    "CreatorsView",
    "ClipRankingView",
    "DashboardView",
    "MultimodalAnalysisView",
    "OperationalEvaluationView",
    "PersonalizationDataView",
    "PersonalizationModelsView",
    "ProjectsView",
    "TaskCenterView",
    "WorkflowView",
    "OnboardingView",
    "PreferencesDialog",
    "VisualAnalysisView",
    "SystemView",
    "TranscriptionView",
    "VideosView",
]
