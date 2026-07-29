from __future__ import annotations

from .production_base_view import ProductionSectionView


class SegmentsView(ProductionSectionView):
    section_title = "Segments"
    data_method = "list_segments"
