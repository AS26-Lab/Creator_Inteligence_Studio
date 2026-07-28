"""Vista de objetivos estrategicos."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class StrategicObjectivesView(PlanningSectionView):
    section_title = "Objectives"
    data_method = "list_objectives"
