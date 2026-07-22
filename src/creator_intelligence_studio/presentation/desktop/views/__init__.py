"""Vistas principales de escritorio."""

from __future__ import annotations

from .creators_view import CreatorsView
from .dashboard_view import DashboardView
from .projects_view import ProjectsView
from .system_view import SystemView
from .transcription_view import TranscriptionView
from .videos_view import VideosView

__all__ = ["CreatorsView", "DashboardView", "ProjectsView", "SystemView", "TranscriptionView", "VideosView"]
