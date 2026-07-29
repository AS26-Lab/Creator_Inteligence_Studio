from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionMilestonesView(ProductionSectionView):
    section_title = "Milestones"
    data_method = "list_milestones"
