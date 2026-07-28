"""Vista de pilares de contenido."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class ContentPillarsView(PlanningSectionView):
    section_title = "Content Pillars"
    data_method = "list_pillars"
