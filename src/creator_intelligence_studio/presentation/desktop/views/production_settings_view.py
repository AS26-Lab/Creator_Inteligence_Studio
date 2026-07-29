from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionSettingsView(ProductionSectionView):
    section_title = "Settings"
    data_method = "list_requests"
    scope = "creator"
