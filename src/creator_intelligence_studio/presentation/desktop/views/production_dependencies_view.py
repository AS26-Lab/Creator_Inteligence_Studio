from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionDependenciesView(ProductionSectionView):
    section_title = "Dependencies"
    data_method = "list_dependencies"
