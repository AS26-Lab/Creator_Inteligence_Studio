from __future__ import annotations

from .production_base_view import ProductionSectionView


class ScenesView(ProductionSectionView):
    section_title = "Scenes"
    data_method = "list_scenes"
