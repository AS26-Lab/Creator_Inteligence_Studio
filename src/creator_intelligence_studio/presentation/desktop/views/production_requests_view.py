from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionRequestsView(ProductionSectionView):
    section_title = "Requests"
    data_method = "list_requests"
    scope = "creator"
