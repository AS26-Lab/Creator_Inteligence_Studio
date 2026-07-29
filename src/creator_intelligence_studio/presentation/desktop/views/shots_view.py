from __future__ import annotations

from .production_base_view import ProductionSectionView


class ShotsView(ProductionSectionView):
    section_title = "Shots"
    data_method = "list_shots"
