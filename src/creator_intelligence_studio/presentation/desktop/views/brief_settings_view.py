from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout

from .briefs_base_view import BriefSectionView


class BriefSettingsView(BriefSectionView):
    section_title = "Settings"
    data_method = None

    def refresh(self) -> None:
        brief_service = getattr(self.workspace, "brief_service", None)
        if brief_service is None:
            return super().refresh()
        self.empty_state.hide()
        self.table.hide()
        self.subtitle.setText(
            f"Human review: {brief_service.preferences.get('require_human_review', True)} | "
            f"Auto approval: {brief_service.preferences.get('allow_automatic_approval', False)} | "
            f"Auto generation: {brief_service.preferences.get('automatic_script_generation', False)}"
        )
