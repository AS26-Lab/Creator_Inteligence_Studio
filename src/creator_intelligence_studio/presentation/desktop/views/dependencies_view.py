"""Vista de dependencias estrategicas."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class DependenciesView(PlanningSectionView):
    section_title = "Dependencies"
    data_method = "list_dependencies"
