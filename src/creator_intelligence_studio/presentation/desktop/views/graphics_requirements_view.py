from __future__ import annotations

from .production_base_view import ProductionSectionView


class GraphicsRequirementsView(ProductionSectionView):
    section_title = "Graphics"
    data_method = "list_graphic_requirements"
