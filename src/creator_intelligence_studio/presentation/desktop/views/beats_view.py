from __future__ import annotations

from .production_base_view import ProductionSectionView


class BeatsView(ProductionSectionView):
    section_title = "Beats"
    data_method = "list_beats"
