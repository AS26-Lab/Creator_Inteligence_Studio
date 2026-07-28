"""Vista de privacidad estrategica."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class PlanningPrivacyView(PlanningSectionView):
    section_title = "Privacy"
    data_method = None

    def refresh(self) -> None:
        self.subtitle.setText(
            "Procesamiento local, sin LLM, sin ML, sin scraping, sin calendario externo y con auditoria local."
        )
        super().refresh()
