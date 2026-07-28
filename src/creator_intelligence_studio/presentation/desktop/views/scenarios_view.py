"""Vista de escenarios estrategicos."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class ScenariosView(PlanningSectionView):
    section_title = "Scenarios"
    data_method = "list_scenarios"
