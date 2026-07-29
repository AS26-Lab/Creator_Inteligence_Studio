from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout

from .briefs_base_view import BriefSectionView


class BriefPrivacyView(BriefSectionView):
    section_title = "Privacy"
    data_method = None

    def refresh(self) -> None:
        self.table.hide()
        self.empty_state.hide()
        self.subtitle.setText(
            "Procesamiento local, sin LLM, sin ML, sin scraping, sin publicacion, sin calendario externo y con audit trail."
        )
