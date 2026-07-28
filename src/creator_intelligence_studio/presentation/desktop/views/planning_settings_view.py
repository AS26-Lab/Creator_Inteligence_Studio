"""Vista de ajustes estrategicos."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .planning_base_view import PlanningSectionView


class PlanningSettingsView(PlanningSectionView):
    section_title = "Settings"
    data_method = None

    def refresh(self) -> None:
        planning_service = getattr(self.workspace, "planning_service", None)
        if planning_service is None:
            super().refresh()
            return
        self.subtitle.setText(
            f"Human review: {planning_service.preferences.get('require_human_review', True)} | "
            f"Auto activation: {planning_service.preferences.get('allow_automatic_activation', False)} | "
            f"External calendar sync: {planning_service.preferences.get('automatic_external_calendar_sync', False)}"
        )
        super().refresh()
