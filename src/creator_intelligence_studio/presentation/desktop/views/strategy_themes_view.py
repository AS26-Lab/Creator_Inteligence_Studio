"""Vista de temas estrategicos."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class StrategyThemesView(PlanningSectionView):
    section_title = "Themes"
    data_method = "list_themes"
