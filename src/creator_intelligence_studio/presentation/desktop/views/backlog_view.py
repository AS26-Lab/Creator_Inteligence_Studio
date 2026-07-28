"""Vista de backlog estrategico."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class BacklogView(PlanningSectionView):
    section_title = "Backlog"
    data_method = "list_backlog_items"
