from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionPrivacyView(ProductionSectionView):
    section_title = "Privacy"
    data_method = "list_requests"
    scope = "creator"
