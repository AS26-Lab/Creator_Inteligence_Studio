from __future__ import annotations

from .production_base_view import ProductionSectionView


class VisualCuesView(ProductionSectionView):
    section_title = "Visual Cues"
    data_method = "list_visual_cues"
