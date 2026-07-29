from __future__ import annotations

from .production_base_view import ProductionSectionView


class ProductionHistoryView(ProductionSectionView):
    section_title = "History"
    data_method = "list_snapshots"
    scope = "creator"
