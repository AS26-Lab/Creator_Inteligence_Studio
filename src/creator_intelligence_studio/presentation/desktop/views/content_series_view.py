"""Vista de series de contenido."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class ContentSeriesView(PlanningSectionView):
    section_title = "Series"
    data_method = "list_series"
