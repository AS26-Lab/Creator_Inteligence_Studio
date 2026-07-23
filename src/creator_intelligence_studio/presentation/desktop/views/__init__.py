"""Vistas principales de escritorio."""

from __future__ import annotations

from .acoustic_analysis_view import AcousticAnalysisView
from .creators_view import CreatorsView
from .clip_ranking_view import ClipRankingView
from .dashboard_view import DashboardView
from .multimodal_analysis_view import MultimodalAnalysisView
from .personalization_data_view import PersonalizationDataView
from .projects_view import ProjectsView
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
    "PersonalizationDataView",
    "ProjectsView",
    "VisualAnalysisView",
    "SystemView",
    "TranscriptionView",
    "VideosView",
]
