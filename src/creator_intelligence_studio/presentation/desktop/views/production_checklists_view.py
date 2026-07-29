from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionChecklistsView(ProductionSectionView):
    section_title = "Checklists"
    data_method = "list_checklists"
