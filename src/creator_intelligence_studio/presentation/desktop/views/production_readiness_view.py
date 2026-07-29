from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionReadinessView(ProductionSectionView):
    section_title = "Readiness"
    data_method = "list_outlines"
    scope = "creator"
