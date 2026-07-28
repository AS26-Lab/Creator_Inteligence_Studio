"""Vista de overview estrategico."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .planning_base_view import PlanningSectionView


class PlanningOverviewView(PlanningSectionView):
    section_title = "Strategic Planning"
    data_method = "list_plans"

    def refresh(self) -> None:
        planning_service = getattr(self.workspace, "planning_service", None)
        creator_id = self.workspace.selected_creator_id
        if planning_service is None or creator_id is None:
            super().refresh()
            return
        overview = None
        plans = planning_service.list_plans(creator_id)
        if plans:
            active_plan = next((plan for plan in plans if plan.status.value == "active"), plans[0])
            overview = planning_service.build_overview(active_plan.id)
        if overview is not None:
            self.subtitle.setText(
                f"Plan activo: {overview.get('plan', {}).get('name', 'sin plan')} | "
                f"Objetivos: {overview.get('objectives', 0)} | "
                f"Roadmap: {overview.get('roadmap_items', 0)} | "
                f"Overload: {overview.get('overload', False)}"
            )
        super().refresh()
