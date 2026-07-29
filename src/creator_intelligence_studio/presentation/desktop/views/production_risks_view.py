from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionRisksView(ProductionSectionView):
    section_title = "Risks"
    data_method = "list_risks"
