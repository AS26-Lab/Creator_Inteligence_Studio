from __future__ import annotations

from .production_base_view import ProductionSectionView


class ReusableSegmentsView(ProductionSectionView):
    section_title = "Reusable Segments"
    data_method = "list_reusable_segments"
