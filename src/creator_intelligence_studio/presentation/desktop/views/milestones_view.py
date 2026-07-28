"""Vista de hitos estrategicos."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class MilestonesView(PlanningSectionView):
    section_title = "Milestones"
    data_method = "list_milestones"
