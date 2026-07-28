"""Vista de revisiones estrategicas."""

from __future__ import annotations

from .planning_base_view import PlanningSectionView


class ReviewsView(PlanningSectionView):
    section_title = "Reviews"
    data_method = "list_reviews"
