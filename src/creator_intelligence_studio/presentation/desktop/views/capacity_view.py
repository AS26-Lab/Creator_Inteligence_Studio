"""Vista de capacidad estrategica."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class CapacityView(PlanningSectionView):
    section_title = "Capacity"
    data_method = "list_capacity_profiles"
