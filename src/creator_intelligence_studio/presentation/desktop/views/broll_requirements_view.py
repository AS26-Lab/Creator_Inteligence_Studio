from __future__ import annotations

from .production_base_view import ProductionSectionView


class BrollRequirementsView(ProductionSectionView):
    section_title = "B-Roll"
    data_method = "list_broll_requirements"
