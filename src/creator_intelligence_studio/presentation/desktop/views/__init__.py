"""Vistas principales de escritorio."""

from __future__ import annotations

from .acoustic_analysis_view import AcousticAnalysisView
from .creators_view import CreatorsView
from .dashboard_view import DashboardView
from .projects_view import ProjectsView
from .system_view import SystemView
from .transcription_view import TranscriptionView
from .videos_view import VideosView

__all__ = [
    "AcousticAnalysisView",
    "CreatorsView",
    "DashboardView",
    "ProjectsView",
    "SystemView",
    "TranscriptionView",
    "VideosView",
]
