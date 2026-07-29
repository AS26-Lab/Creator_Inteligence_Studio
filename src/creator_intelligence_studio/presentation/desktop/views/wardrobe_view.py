from __future__ import annotations

from .production_base_view import ProductionSectionView


class WardrobeView(ProductionSectionView):
    section_title = "Wardrobe"
    data_method = "list_wardrobe"
