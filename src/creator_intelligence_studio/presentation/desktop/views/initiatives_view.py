"""Vista de iniciativas estrategicas."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class InitiativesView(PlanningSectionView):
    section_title = "Initiatives"
    data_method = "list_initiatives"
