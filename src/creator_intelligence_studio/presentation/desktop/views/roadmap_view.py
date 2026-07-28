"""Vista de roadmap estrategico."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class RoadmapView(PlanningSectionView):
    section_title = "Roadmap"
    data_method = "list_roadmap_items"
