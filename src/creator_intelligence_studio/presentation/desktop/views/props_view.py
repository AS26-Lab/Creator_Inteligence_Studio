from __future__ import annotations

from .production_base_view import ProductionSectionView


class PropsView(ProductionSectionView):
    section_title = "Props"
    data_method = "list_props"
