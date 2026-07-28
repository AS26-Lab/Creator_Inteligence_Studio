"""Vista de historial estrategico."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .planning_base_view import PlanningSectionView


class PlanningHistoryView(PlanningSectionView):
    section_title = "History"
    data_method = "list_snapshots"
