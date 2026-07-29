from __future__ import annotations

from .production_base_view import ProductionSectionView


class OutlineDetailView(ProductionSectionView):
    section_title = "Outline Structure"
    data_method = "list_sections"
